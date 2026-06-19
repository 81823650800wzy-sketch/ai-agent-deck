/**
 * AI Agent Deck - OTA 更新
 * 通过 TCP 远程推送固件，无需 USB
 */

#pragma once

#include "esp_err.h"
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * 开始 OTA 更新
 * @param expected_size  固件总大小（字节）
 * @return ESP_OK 成功
 */
esp_err_t ota_begin(size_t expected_size);

/**
 * 写入 OTA 数据块
 * @param data  固件数据
 * @param len   数据长度
 * @return ESP_OK 成功
 */
esp_err_t ota_write(const uint8_t *data, size_t len);

/**
 * 完成 OTA 更新并重启
 * @return ESP_OK 成功（不会返回）
 */
esp_err_t ota_end(void);

/**
 * 处理 OTA 相关 JSON 命令
 * @param json_str  JSON 字符串
 * @return true 如果是 OTA 命令
 */
bool ota_handle_cmd(const char *json_str);

#ifdef __cplusplus
}
#endif
