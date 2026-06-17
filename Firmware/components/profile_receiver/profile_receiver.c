/**
 * AI Agent Deck - Profile 接收器
 * BLE GATT 服务：接收 PC Manager 的 Profile JSON，更新按键映射和屏幕
 *
 * 注意: 本组件不注册自己的 GATTS 回调，而是提供 handler 函数
 * 由 main.c 的统一回调中调用，避免覆盖 HID 的 GATTS 回调
 */

#include <string.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_bt.h"
#include "esp_bt_main.h"
#include "esp_gap_ble_api.h"
#include "esp_gatts_api.h"
#include "cJSON.h"

#include "profile_receiver.h"

static const char *TAG = "PROFILE";

/* ── GATT Service UUID (128-bit, 与 PC 端一致) ── */
/* 12345678-1234-5678-1234-56789abcdef0 */
static uint8_t profile_service_uuid[16] = {
    0xF0, 0xDE, 0xBC, 0x9A, 0x78, 0x56, 0x34, 0x12,
    0x78, 0x56, 0x34, 0x12, 0x78, 0x56, 0x34, 0x12
};
/* 12345678-1234-5678-1234-56789abcdef1 */
static uint8_t profile_char_uuid[16] = {
    0xF1, 0xDE, 0xBC, 0x9A, 0x78, 0x56, 0x34, 0x12,
    0x78, 0x56, 0x34, 0x12, 0x78, 0x56, 0x34, 0x12
};

/* ── 全局 Profile ────────────────────────── */
current_profile_t g_current_profile = {
    .name = "Default",
    .key_count = 6,
    .keys = {
        {"K1", "Key-A", "a"},
        {"K2", "Key-B", "b"},
        {"K3", "Key-C", "c"},
        {"K4", "Key-D", "d"},
        {"K5", "Key-E", "e"},
        {"K6", "Key-F", "f"},
    },
    .valid = true,
};

/* ── GATT 状态 ───────────────────────────── */
static uint16_t profile_service_handle = 0;
static uint16_t profile_char_handle = 0;
static uint16_t profile_conn_id = 0;
static bool profile_is_connected = false;
static esp_gatt_if_t profile_gatts_if = 0;

/* ── 接收缓冲区 ──────────────────────────── */
#define RECV_BUF_SIZE   2048
static uint8_t recv_buf[RECV_BUF_SIZE];
static int recv_len = 0;

/* ── 外部 UI 函数声明 ────────────────────── */
extern void draw_ui(void);

/* ── JSON 解析 ───────────────────────────── */
void parse_profile_json(const char *json_str)
{
    cJSON *root = cJSON_Parse(json_str);
    if (!root) {
        ESP_LOGE(TAG, "JSON parse failed");
        return;
    }

    const cJSON *cmd = cJSON_GetObjectItem(root, "cmd");
    if (!cmd || !cJSON_IsString(cmd)) {
        cJSON_Delete(root);
        return;
    }

    if (strcmp(cmd->valuestring, "ping") == 0) {
        ESP_LOGI(TAG, "Ping received");
        profile_send_ack("pong", 0);
        cJSON_Delete(root);
        return;
    }

    if (strcmp(cmd->valuestring, "profile") != 0) {
        ESP_LOGW(TAG, "Unknown cmd: %s", cmd->valuestring);
        cJSON_Delete(root);
        return;
    }

    const cJSON *data = cJSON_GetObjectItem(root, "data");
    if (!data) {
        ESP_LOGE(TAG, "Missing data field");
        cJSON_Delete(root);
        return;
    }

    const cJSON *name = cJSON_GetObjectItem(data, "name");
    const cJSON *keys = cJSON_GetObjectItem(data, "keys");

    if (!name || !cJSON_IsString(name)) {
        ESP_LOGE(TAG, "Missing profile name");
        cJSON_Delete(root);
        return;
    }

    /* 构建新 Profile */
    current_profile_t new_profile;
    memset(&new_profile, 0, sizeof(new_profile));
    strncpy(new_profile.name, name->valuestring, PROFILE_NAME_LEN - 1);

    if (keys && cJSON_IsArray(keys)) {
        int count = cJSON_GetArraySize(keys);
        if (count > PROFILE_MAX_KEYS) count = PROFILE_MAX_KEYS;

        for (int i = 0; i < count; i++) {
            const cJSON *key = cJSON_GetArrayItem(keys, i);
            const cJSON *kid = cJSON_GetObjectItem(key, "id");
            const cJSON *kdisplay = cJSON_GetObjectItem(key, "display");
            const cJSON *kaction = cJSON_GetObjectItem(key, "action");

            if (kid && cJSON_IsString(kid))
                strncpy(new_profile.keys[i].id, kid->valuestring, 3);
            if (kdisplay && cJSON_IsString(kdisplay))
                strncpy(new_profile.keys[i].display, kdisplay->valuestring, PROFILE_KEY_NAME_LEN - 1);
            if (kaction && cJSON_IsString(kaction))
                strncpy(new_profile.keys[i].action, kaction->valuestring, 31);
        }
        new_profile.key_count = count;
    }

    new_profile.valid = true;
    g_current_profile = new_profile;

    ESP_LOGI(TAG, "Profile switch: %s (%d keys)", g_current_profile.name, g_current_profile.key_count);
    for (int i = 0; i < g_current_profile.key_count; i++) {
        ESP_LOGI(TAG, "  %s: %s (%s)",
                 g_current_profile.keys[i].id,
                 g_current_profile.keys[i].display,
                 g_current_profile.keys[i].action);
    }

    profile_send_ack(g_current_profile.name, g_current_profile.key_count);
    profile_refresh_display();

    cJSON_Delete(root);
}

/* ── 创建 Profile GATT 服务 ──────────────── */
static void create_profile_service(esp_gatt_if_t gatts_if)
{
    esp_gatt_srvc_id_t service_id;
    memset(&service_id, 0, sizeof(service_id));
    service_id.is_primary = true;
    service_id.id.inst_id = 0;
    service_id.id.uuid.len = ESP_UUID_LEN_128;
    memcpy(service_id.id.uuid.uuid.uuid128, profile_service_uuid, 16);

    esp_err_t ret = esp_ble_gatts_create_service(gatts_if, &service_id, 4);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Create service failed: %s", esp_err_to_name(ret));
    }
}

/* ── 处理 GATT 事件 (由 main.c 统一回调调用) ── */
void profile_gatts_handler(esp_gatts_cb_event_t event,
                            esp_gatt_if_t gatts_if,
                            esp_ble_gatts_cb_param_t *param)
{
    switch (event) {
        case ESP_GATTS_REG_EVT:
            /* 只处理自己的 app_id (0x42) */
            if (param->reg.status == ESP_GATT_OK && param->reg.app_id == 0x42) {
                ESP_LOGI(TAG, "Profile app registered, gatts_if=%d", gatts_if);
                profile_gatts_if = gatts_if;
                create_profile_service(gatts_if);
            }
            return;  /* REG_EVT 总是返回，让 HID 也处理 */

        default:
            /* 非 REG_EVT: 只处理 Profile 自己的 gatts_if */
            if (profile_gatts_if == 0 || gatts_if != profile_gatts_if) {
                return;
            }
            break;
    }

    /* 调试: 打印所有事件 */
    ESP_LOGI(TAG, "Event=%d gatts_if=%d", event, gatts_if);

    switch (event) {
        case ESP_GATTS_CREATE_EVT:
            if (param->create.status == ESP_GATT_OK) {
                profile_service_handle = param->create.service_handle;
                ESP_LOGI(TAG, "Service created handle=%d", profile_service_handle);

                esp_bt_uuid_t char_uuid;
                memset(&char_uuid, 0, sizeof(char_uuid));
                char_uuid.len = ESP_UUID_LEN_128;
                memcpy(char_uuid.uuid.uuid128, profile_char_uuid, 16);
                esp_attr_value_t char_val = {
                    .attr_max_len = RECV_BUF_SIZE,
                    .attr_len = 0,
                    .attr_value = NULL,
                };
                esp_attr_control_t ctrl = {.auto_rsp = ESP_GATT_RSP_BY_APP};

                esp_ble_gatts_add_char(
                    profile_service_handle,
                    &char_uuid,
                    ESP_GATT_PERM_WRITE,
                    ESP_GATT_CHAR_PROP_BIT_WRITE | ESP_GATT_CHAR_PROP_BIT_WRITE_NR,
                    &char_val,
                    &ctrl
                );
            }
            break;

        case ESP_GATTS_ADD_CHAR_EVT:
            if (param->add_char.status == ESP_GATT_OK) {
                profile_char_handle = param->add_char.attr_handle;
                ESP_LOGI(TAG, "Char added handle=%d", profile_char_handle);
                esp_ble_gatts_start_service(profile_service_handle);
            }
            break;

        case ESP_GATTS_START_EVT:
            ESP_LOGI(TAG, "Profile service started");
            break;

        case ESP_GATTS_CONNECT_EVT:
            if (!profile_is_connected) {
                profile_conn_id = param->connect.conn_id;
                profile_is_connected = true;
                ESP_LOGI(TAG, "Profile connected conn_id=%d", profile_conn_id);
            }
            break;

        case ESP_GATTS_DISCONNECT_EVT:
            if (profile_is_connected) {
                profile_is_connected = false;
                ESP_LOGI(TAG, "Profile disconnected");
            }
            break;

        case ESP_GATTS_WRITE_EVT:
            ESP_LOGI(TAG, "WRITE_EVT: is_prep=%d len=%d offset=%d",
                     param->write.is_prep, param->write.len, param->write.offset);
            if (param->write.is_prep) {
                /* 准备写入 — 追加到缓冲区 */
                if (recv_len + param->write.len < RECV_BUF_SIZE) {
                    memcpy(recv_buf + recv_len, param->write.value, param->write.len);
                    recv_len += param->write.len;
                    ESP_LOGI(TAG, "Prepared %d bytes, total=%d", param->write.len, recv_len);
                }
            } else {
                /* 直接写入 */
                int data_len = param->write.len;
                if (data_len > 0 && data_len < RECV_BUF_SIZE) {
                    memcpy(recv_buf, param->write.value, data_len);
                    recv_buf[data_len] = '\0';
                    recv_len = data_len;
                    ESP_LOGI(TAG, "Direct write %d bytes", data_len);
                    parse_profile_json((char *)recv_buf);
                }
            }

            if (param->write.need_rsp) {
                esp_ble_gatts_send_response(
                    gatts_if, param->write.conn_id,
                    param->write.trans_id, ESP_GATT_OK, NULL
                );
            }
            break;

        case ESP_GATTS_EXEC_WRITE_EVT:
            ESP_LOGI(TAG, "EXEC_WRITE: total=%d bytes", recv_len);
            if (recv_len > 0) {
                recv_buf[recv_len] = '\0';
                ESP_LOGI(TAG, "Data: %.*s", recv_len > 80 ? 80 : recv_len, recv_buf);
                parse_profile_json((char *)recv_buf);
                recv_len = 0;
            }
            break;

        default:
            break;
    }
}

/* ── 初始化 (仅注册 app，不注册回调) ─────── */
esp_err_t profile_receiver_init(void)
{
    ESP_LOGI(TAG, "Registering Profile GATT app...");
    esp_err_t ret = esp_ble_gatts_app_register(0x42);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "App register failed: %s", esp_err_to_name(ret));
        return ret;
    }
    ESP_LOGI(TAG, "Profile receiver init done");
    return ESP_OK;
}

void profile_send_ack(const char *profile_name, int key_count)
{
    ESP_LOGI(TAG, "ACK: profile=%s keys=%d", profile_name, key_count);
}

void profile_update_keymap(const current_profile_t *profile)
{
    ESP_LOGI(TAG, "Keymap updated: %s", profile->name);
}

void profile_refresh_display(void)
{
    ESP_LOGI(TAG, "Refresh display: %s", g_current_profile.name);
    draw_ui();
}
