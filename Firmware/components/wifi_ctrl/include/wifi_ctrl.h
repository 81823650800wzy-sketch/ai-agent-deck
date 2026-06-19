/**
 * AI Agent Deck - WiFi 控制器
 * STA 模式连接家庭 WiFi，TCP 服务器接收 JSON 命令
 * mDNS 自动发现 (ai-deck.local)
 */

#pragma once

#include "esp_err.h"
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * 初始化 WiFi 控制器
 * 1. 连接 WiFi (STA 模式)
 * 2. 启动 TCP 服务器 (端口 8080)
 * 3. 注册 mDNS (ai-deck.local)
 *
 * @param ssid  WiFi SSID (NULL 时使用 NVS 存储的值)
 * @param pass  WiFi 密码 (NULL 时使用 NVS 存储的值)
 * @return ESP_OK 成功
 */
esp_err_t wifi_ctrl_init(const char *ssid, const char *pass);

/**
 * 获取 WiFi 连接状态
 * @return true 已连接
 */
bool wifi_ctrl_is_connected(void);

/**
 * 获取本机 IP 地址字符串
 * @param buf  输出缓冲区
 * @param len  缓冲区长度
 * @return ESP_OK 成功
 */
esp_err_t wifi_ctrl_get_ip(char *buf, size_t len);

/**
 * 保存 WiFi 凭据到 NVS
 */
esp_err_t wifi_ctrl_save_credentials(const char *ssid, const char *pass);

/**
 * 发送数据到已连接的 TCP 客户端
 * @param data  数据
 * @param len   数据长度
 * @return true 发送成功
 */
bool wifi_ctrl_send(const char *data, size_t len);

/**
 * 检查是否有 TCP 客户端连接
 */
bool wifi_ctrl_has_client(void);

#ifdef __cplusplus
}
#endif
