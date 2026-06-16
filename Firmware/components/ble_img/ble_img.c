/**
 * BLE 图片传输服务 (简化版)
 * GATT Service: FFF0
 */

#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_bt.h"
#include "esp_bt_main.h"
#include "esp_gap_ble_api.h"
#include "esp_gatts_api.h"
#include "ble_img.h"

static const char *TAG = "BLE_IMG";

#define BLE_IMG_SVC_UUID        0xFFF0
#define BLE_IMG_CHAR_CTRL_UUID  0xFFF1
#define BLE_IMG_CHAR_DATA_UUID  0xFFF2
#define BLE_IMG_CHAR_STATUS_UUID 0xFFF3

static uint16_t s_ctrl_handle = 0;
static uint16_t s_data_handle = 0;
static uint16_t s_status_handle = 0;
static uint16_t s_conn_id = 0xFFFF;
static esp_gatt_if_t s_gatts_if = 0;
static bool s_connected = false;

static ble_img_callbacks_t s_cb;

static void send_status(uint8_t status) {
    if (!s_connected || s_gatts_if == 0) return;
    esp_ble_gatts_send_indicate(s_gatts_if, s_conn_id, s_status_handle, 1, &status, false);
}

static void gatts_event_handler(esp_gatts_cb_event_t event, esp_gatt_if_t gatts_if,
                                esp_ble_gatts_cb_param_t *param) {
    switch (event) {
    case ESP_GATTS_REG_EVT:
        ESP_LOGI(TAG, "GATTS_REG_EVT, app_id=%d, status=%d", param->reg.app_id, param->reg.status);
        if (param->reg.status == ESP_GATT_OK) {
            s_gatts_if = gatts_if;
            esp_gatt_srvc_id_t svc_id = {
                .is_primary = true,
                .id = { .uuid = { .len = ESP_UUID_LEN_16, .uuid = { .uuid16 = BLE_IMG_SVC_UUID } } }
            };
            esp_ble_gatts_create_service(gatts_if, &svc_id, 10);
        }
        break;

    case ESP_GATTS_CREATE_EVT:
        ESP_LOGI(TAG, "CREATE_EVT, status=%d, handle=%d", param->create.status, param->create.service_handle);
        if (param->create.status == ESP_GATT_OK) {
            uint16_t svc_handle = param->create.service_handle;
            esp_ble_gatts_start_service(svc_handle);

            // 添加控制特征
            esp_bt_uuid_t ctrl_uuid = { .len = ESP_UUID_LEN_16, .uuid = { .uuid16 = BLE_IMG_CHAR_CTRL_UUID } };
            esp_ble_gatts_add_char(svc_handle, &ctrl_uuid, ESP_GATT_PERM_WRITE, ESP_GATT_CHAR_PROP_BIT_WRITE, NULL, NULL);

            // 添加数据特征
            esp_bt_uuid_t data_uuid = { .len = ESP_UUID_LEN_16, .uuid = { .uuid16 = BLE_IMG_CHAR_DATA_UUID } };
            esp_ble_gatts_add_char(svc_handle, &data_uuid, ESP_GATT_PERM_WRITE, ESP_GATT_CHAR_PROP_BIT_WRITE_NR, NULL, NULL);

            // 添加状态特征
            esp_bt_uuid_t status_uuid = { .len = ESP_UUID_LEN_16, .uuid = { .uuid16 = BLE_IMG_CHAR_STATUS_UUID } };
            esp_ble_gatts_add_char(svc_handle, &status_uuid, ESP_GATT_PERM_READ,
                ESP_GATT_CHAR_PROP_BIT_READ | ESP_GATT_CHAR_PROP_BIT_NOTIFY, NULL, NULL);
        }
        break;

    case ESP_GATTS_ADD_CHAR_EVT:
        ESP_LOGI(TAG, "ADD_CHAR_EVT, uuid=%04x, handle=%d", param->add_char.char_uuid.uuid.uuid16, param->add_char.attr_handle);
        if (param->add_char.char_uuid.uuid.uuid16 == BLE_IMG_CHAR_CTRL_UUID) {
            s_ctrl_handle = param->add_char.attr_handle;
        } else if (param->add_char.char_uuid.uuid.uuid16 == BLE_IMG_CHAR_DATA_UUID) {
            s_data_handle = param->add_char.attr_handle;
        } else if (param->add_char.char_uuid.uuid.uuid16 == BLE_IMG_CHAR_STATUS_UUID) {
            s_status_handle = param->add_char.attr_handle;
            // 直接配置广播数据，跳过描述符
            esp_ble_adv_data_t adv_data = {
                .set_scan_rsp = false,
                .include_name = true,
                .include_txpower = false,
                .flag = ESP_BLE_ADV_FLAG_GEN_DISC | ESP_BLE_ADV_FLAG_BREDR_NOT_SPT,
            };
            esp_ble_gap_config_adv_data(&adv_data);
        }
        break;

    case ESP_GATTS_ADD_CHAR_DESCR_EVT:
        ESP_LOGI(TAG, "ADD_CHAR_DESCR_EVT, handle=%d", param->add_char_descr.attr_handle);
        // 所有特征添加完成，配置广播数据
        esp_ble_adv_data_t adv_data = {
            .set_scan_rsp = false,
            .include_name = true,
            .include_txpower = false,
            .flag = ESP_BLE_ADV_FLAG_GEN_DISC | ESP_BLE_ADV_FLAG_BREDR_NOT_SPT,
        };
        esp_ble_gap_config_adv_data(&adv_data);
        break;

    case ESP_GATTS_START_EVT:
        ESP_LOGI(TAG, "START_EVT, status=%d", param->start.status);
        break;

    case ESP_GATTS_CONNECT_EVT:
        ESP_LOGI(TAG, "CONNECT_EVT, conn_id=%d", param->connect.conn_id);
        s_conn_id = param->connect.conn_id;
        s_connected = true;
        if (s_cb.on_status) s_cb.on_status(true);
        break;

    case ESP_GATTS_DISCONNECT_EVT:
        ESP_LOGI(TAG, "DISCONNECT_EVT");
        s_connected = false;
        s_conn_id = 0xFFFF;
        esp_ble_gap_start_advertising(&(esp_ble_adv_params_t){
            .adv_int_min = 0x20, .adv_int_max = 0x40,
            .adv_type = ADV_TYPE_IND,
            .own_addr_type = BLE_ADDR_TYPE_PUBLIC,
            .channel_map = ADV_CHNL_ALL,
            .adv_filter_policy = ADV_FILTER_ALLOW_SCAN_ANY_CON_ANY,
        });
        if (s_cb.on_status) s_cb.on_status(false);
        break;

    case ESP_GATTS_WRITE_EVT:
        if (param->write.handle == s_ctrl_handle && param->write.len > 0) {
            if (s_cb.on_ctrl) s_cb.on_ctrl(param->write.value, param->write.len);
        } else if (param->write.handle == s_data_handle && param->write.len > 0) {
            if (s_cb.on_data) s_cb.on_data(param->write.value, param->write.len);
        }
        break;

    default:
        break;
    }
}

static void gap_event_handler(esp_gap_ble_cb_event_t event, esp_ble_gap_cb_param_t *param) {
    switch (event) {
    case ESP_GAP_BLE_ADV_DATA_SET_COMPLETE_EVT:
        ESP_LOGI(TAG, "ADV_DATA_SET_COMPLETE, starting advertising...");
        esp_ble_gap_start_advertising(&(esp_ble_adv_params_t){
            .adv_int_min = 0x20, .adv_int_max = 0x40,
            .adv_type = ADV_TYPE_IND,
            .own_addr_type = BLE_ADDR_TYPE_PUBLIC,
            .channel_map = ADV_CHNL_ALL,
            .adv_filter_policy = ADV_FILTER_ALLOW_SCAN_ANY_CON_ANY,
        });
        break;
    case ESP_GAP_BLE_ADV_START_COMPLETE_EVT:
        if (param->adv_start_cmpl.status == ESP_BT_STATUS_SUCCESS) {
            ESP_LOGI(TAG, "Advertising started!");
        } else {
            ESP_LOGE(TAG, "Advertising failed: %d", param->adv_start_cmpl.status);
        }
        break;
    default:
        break;
    }
}

void ble_img_init(const ble_img_callbacks_t *cb) {
    if (cb) s_cb = *cb;

    ESP_ERROR_CHECK(esp_bt_controller_mem_release(ESP_BT_MODE_CLASSIC_BT));

    esp_bt_controller_config_t bt_cfg = BT_CONTROLLER_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_bt_controller_init(&bt_cfg));
    ESP_ERROR_CHECK(esp_bt_controller_enable(ESP_BT_MODE_BLE));
    ESP_ERROR_CHECK(esp_bluedroid_init());
    ESP_ERROR_CHECK(esp_bluedroid_enable());

    ESP_ERROR_CHECK(esp_ble_gatts_register_callback(gatts_event_handler));
    ESP_ERROR_CHECK(esp_ble_gap_register_callback(gap_event_handler));
    ESP_ERROR_CHECK(esp_ble_gatts_app_register(0));
    ESP_ERROR_CHECK(esp_ble_gap_set_device_name("AI-Agent-Deck"));

    ESP_LOGI(TAG, "BLE initialized");
}

bool ble_img_is_connected(void) {
    return s_connected;
}
