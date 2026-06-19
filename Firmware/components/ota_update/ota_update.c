/**
 * AI Agent Deck - OTA 更新
 * TCP 协议：{"cmd":"ota_begin","size":N} -> {"cmd":"ota_data","data":"base64"} -> {"cmd":"ota_end"}
 */

#include <string.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_system.h"
#include "esp_ota_ops.h"
#include "esp_log.h"
#include "esp_err.h"
#include "cJSON.h"

#include "ota_update.h"

static const char *TAG = "OTA";

/* ── Base64 解码 ─────────────────────────── */
static const uint8_t b64_table[256] = {
    ['A']=0,  ['B']=1,  ['C']=2,  ['D']=3,  ['E']=4,  ['F']=5,
    ['G']=6,  ['H']=7,  ['I']=8,  ['J']=9,  ['K']=10, ['L']=11,
    ['M']=12, ['N']=13, ['O']=14, ['P']=15, ['Q']=16, ['R']=17,
    ['S']=18, ['T']=19, ['U']=20, ['V']=21, ['W']=22, ['X']=23,
    ['Y']=24, ['Z']=25, ['a']=26, ['b']=27, ['c']=28, ['d']=29,
    ['e']=30, ['f']=31, ['g']=32, ['h']=33, ['i']=34, ['j']=35,
    ['k']=36, ['l']=37, ['m']=38, ['n']=39, ['o']=40, ['p']=41,
    ['q']=42, ['r']=43, ['s']=44, ['t']=45, ['u']=46, ['v']=47,
    ['w']=48, ['x']=49, ['y']=50, ['z']=51, ['0']=52, ['1']=53,
    ['2']=54, ['3']=55, ['4']=56, ['5']=57, ['6']=58, ['7']=59,
    ['8']=60, ['9']=61, ['+']=62, ['/']=63
};

static uint8_t *base64_decode(const uint8_t *src, size_t src_len, size_t *out_len)
{
    if (src_len % 4 != 0) return NULL;

    size_t len = src_len / 4 * 3;
    if (src[src_len - 1] == '=') len--;
    if (src[src_len - 2] == '=') len--;

    uint8_t *out = malloc(len);
    if (!out) return NULL;

    size_t j = 0;
    for (size_t i = 0; i < src_len; i += 4) {
        uint32_t sextet = (b64_table[src[i]] << 18) |
                          (b64_table[src[i+1]] << 12) |
                          (b64_table[src[i+2]] << 6) |
                           b64_table[src[i+3]];

        if (j < len) out[j++] = (sextet >> 16) & 0xFF;
        if (j < len) out[j++] = (sextet >> 8) & 0xFF;
        if (j < len) out[j++] = sextet & 0xFF;
    }

    *out_len = len;
    return out;
}

/* ── OTA 状态 ────────────────────────────── */
static esp_ota_handle_t s_ota_handle = 0;
static const esp_partition_t *s_update_partition = NULL;
static bool s_ota_in_progress = false;
static size_t s_bytes_written = 0;
static size_t s_expected_size = 0;

/* ── 外部函数：通过 TCP 发送响应 ─────────── */
extern bool wifi_ctrl_send(const char *data, size_t len);

static void send_ack(const char *status, const char *msg)
{
    cJSON *resp = cJSON_CreateObject();
    cJSON_AddStringToObject(resp, "cmd", "ota_ack");
    cJSON_AddStringToObject(resp, "status", status);
    if (msg) cJSON_AddStringToObject(resp, "msg", msg);

    char *json = cJSON_PrintUnformatted(resp);
    strcat(json, "\n");
    wifi_ctrl_send(json, strlen(json));

    free(json);
    cJSON_Delete(resp);
}

/* ── 开始 OTA ────────────────────────────── */
esp_err_t ota_begin(size_t expected_size)
{
    if (s_ota_in_progress) {
        ESP_LOGW(TAG, "OTA already in progress");
        return ESP_ERR_INVALID_STATE;
    }

    s_update_partition = esp_ota_get_next_update_partition(NULL);
    if (!s_update_partition) {
        ESP_LOGE(TAG, "No OTA partition found");
        return ESP_ERR_NOT_FOUND;
    }

    ESP_LOGI(TAG, "OTA begin: partition=%s offset=0x%lx size=%lu",
             s_update_partition->label,
             (unsigned long)s_update_partition->address,
             (unsigned long)s_update_partition->size);

    esp_err_t err = esp_ota_begin(s_update_partition, expected_size, &s_ota_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_ota_begin failed: %s", esp_err_to_name(err));
        return err;
    }

    s_ota_in_progress = true;
    s_bytes_written = 0;
    s_expected_size = expected_size;

    send_ack("ok", "OTA started");
    return ESP_OK;
}

/* ── 写入数据 ────────────────────────────── */
esp_err_t ota_write(const uint8_t *data, size_t len)
{
    if (!s_ota_in_progress) {
        return ESP_ERR_INVALID_STATE;
    }

    esp_err_t err = esp_ota_write(s_ota_handle, data, len);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_ota_write failed: %s", esp_err_to_name(err));
        esp_ota_abort(s_ota_handle);
        s_ota_in_progress = false;
        send_ack("error", "Write failed");
        return err;
    }

    s_bytes_written += len;

    /* 每 10KB 发一次进度 */
    if (s_bytes_written % 10240 < len) {
        int pct = s_expected_size > 0 ? (s_bytes_written * 100 / s_expected_size) : 0;
        ESP_LOGI(TAG, "OTA progress: %lu bytes (%d%%)", (unsigned long)s_bytes_written, pct);
    }

    return ESP_OK;
}

/* ── 完成并重启 ──────────────────────────── */
esp_err_t ota_end(void)
{
    if (!s_ota_in_progress) {
        return ESP_ERR_INVALID_STATE;
    }

    esp_err_t err = esp_ota_end(s_ota_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_ota_end failed: %s", esp_err_to_name(err));
        s_ota_in_progress = false;
        send_ack("error", "Finalize failed");
        return err;
    }

    err = esp_ota_set_boot_partition(s_update_partition);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_ota_set_boot_partition failed: %s", esp_err_to_name(err));
        s_ota_in_progress = false;
        send_ack("error", "Set boot failed");
        return err;
    }

    ESP_LOGI(TAG, "OTA complete! Rebooting in 2 seconds...");
    send_ack("ok", "OTA complete, rebooting...");

    s_ota_in_progress = false;

    /* 延迟重启，让 ACK 发出去 */
    vTaskDelay(pdMS_TO_TICKS(2000));
    esp_restart();

    return ESP_OK;  /* 不会到达 */
}

/* ── 处理 OTA JSON 命令 ──────────────────── */
bool ota_handle_cmd(const char *json_str)
{
    if (!strstr(json_str, "\"ota_")) return false;

    cJSON *root = cJSON_Parse(json_str);
    if (!root) return false;

    const cJSON *cmd = cJSON_GetObjectItem(root, "cmd");
    if (!cmd || !cJSON_IsString(cmd)) {
        cJSON_Delete(root);
        return false;
    }

    const char *cmd_str = cmd->valuestring;

    if (strcmp(cmd_str, "ota_begin") == 0) {
        const cJSON *size = cJSON_GetObjectItem(root, "size");
        size_t fw_size = size && cJSON_IsNumber(size) ? (size_t)size->valueint : 0;
        ota_begin(fw_size);
        cJSON_Delete(root);
        return true;
    }

    if (strcmp(cmd_str, "ota_data") == 0) {
        const cJSON *data = cJSON_GetObjectItem(root, "data");
        if (data && cJSON_IsString(data)) {
            /* Base64 解码 */
            size_t out_len = 0;
            uint8_t *decoded = base64_decode((const uint8_t *)data->valuestring,
                                              strlen(data->valuestring), &out_len);
            if (decoded) {
                ota_write(decoded, out_len);
                free(decoded);
            } else {
                send_ack("error", "Base64 decode failed");
            }
        }
        cJSON_Delete(root);
        return true;
    }

    if (strcmp(cmd_str, "ota_end") == 0) {
        ota_end();
        cJSON_Delete(root);
        return true;
    }

    cJSON_Delete(root);
    return false;
}
