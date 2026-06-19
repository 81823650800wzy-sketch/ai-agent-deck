/**
 * AI Agent Deck - WiFi 控制器
 * STA 模式 + TCP 服务器 + mDNS
 */

#include <string.h>
#include <stdlib.h>
#include <stdarg.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "esp_system.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
/* #include "mdns.h" -- 暂时禁用，需安装组件管理器依赖 */
#include "nvs_flash.h"
#include "nvs.h"
#include "lwip/sockets.h"
#include "lwip/netdb.h"
#include "cJSON.h"

#include "wifi_ctrl.h"
#include "ota_update.h"

static const char *TAG = "WIFI_CTRL";

/* ── 配置 ────────────────────────────────── */
#define TCP_PORT            8080
#define TCP_BUF_SIZE        4096
#define MDNS_HOSTNAME       "ai-deck"
#define MDNS_INSTANCE       "AI Agent Deck"
#define WIFI_RETRY_MAX      10
#define AP_SSID             "AI-Deck"
#define AP_PASS             "aideck123"
#define NVS_NAMESPACE       "wifi_cfg"

/* ── 事件组 ──────────────────────────────── */
static EventGroupHandle_t s_wifi_event_group;
#define WIFI_CONNECTED_BIT  BIT0
#define WIFI_FAIL_BIT       BIT1

/* ── 状态 ────────────────────────────────── */
static bool s_initialized = false;
static bool s_connected = false;
static int s_client_fd = -1;
static int s_retry_count = 0;
static char s_ip_str[16] = {0};
static bool s_log_to_wifi = true;  /* 是否将日志转发到 WiFi 客户端 */

/* ── 日志输出到 TCP 客户端 ──────────────── */
static int wifi_log_vprintf(const char *fmt, va_list args)
{
    /* 先输出到原始 UART */
    va_list args_copy;
    va_copy(args_copy, args);
    int ret = vprintf(fmt, args);
    va_end(args_copy);

    /* 如果有 TCP 客户端连接，也发送日志 */
    if (s_log_to_wifi && s_client_fd >= 0) {
        char buf[512];
        va_copy(args_copy, args);
        int len = vsnprintf(buf, sizeof(buf), fmt, args_copy);
        va_end(args_copy);
        if (len > 0 && len < (int)sizeof(buf)) {
            send(s_client_fd, buf, len, 0);
        }
    }

    return ret;
}

/* ── 外部函数声明 (来自 profile_receiver / wallpaper / main) ── */
extern void parse_profile_json(const char *json_str);
extern void wallpaper_parse_cmd(const char *json_str);

/* ── 命令处理 (与 serial_cmd_task 共享逻辑) ── */
static void wifi_handle_command(const char *json_str)
{
    if (!strstr(json_str, "\"cmd\"")) return;

    ESP_LOGI(TAG, "WiFi cmd: %.60s%s", json_str, strlen(json_str) > 60 ? "..." : "");

    if (strstr(json_str, "\"profile\"")) {
        parse_profile_json(json_str);
    } else if (strstr(json_str, "\"wallpaper\"") || strstr(json_str, "\"wp_")) {
        wallpaper_parse_cmd(json_str);
    } else if (strstr(json_str, "\"screen\"")) {
        /* screen_parse_cmd 是 main.c 中的 static 函数，这里通过外部声明调用 */
        extern void screen_parse_cmd(const char *json_str);
        screen_parse_cmd(json_str);
    } else if (strstr(json_str, "\"ota_")) {
        ota_handle_cmd(json_str);
    } else if (strstr(json_str, "\"ping\"")) {
        const char *pong = "{\"cmd\":\"pong\",\"src\":\"wifi\"}\n";
        wifi_ctrl_send(pong, strlen(pong));
    } else if (strstr(json_str, "\"wifi_save\"")) {
        /* 保存 WiFi 凭据 {"cmd":"wifi_save","ssid":"xxx","pass":"xxx"} */
        cJSON *root = cJSON_Parse(json_str);
        if (root) {
            const cJSON *j_ssid = cJSON_GetObjectItem(root, "ssid");
            const cJSON *j_pass = cJSON_GetObjectItem(root, "pass");
            if (j_ssid && cJSON_IsString(j_ssid) && j_pass && cJSON_IsString(j_pass)) {
                wifi_ctrl_save_credentials(j_ssid->valuestring, j_pass->valuestring);
                const char *ack = "{\"cmd\":\"wifi_ack\",\"status\":\"saved\"}\n";
                wifi_ctrl_send(ack, strlen(ack));
            }
            cJSON_Delete(root);
        }
    } else if (strstr(json_str, "\"wifi_status\"")) {
        /* 返回 WiFi 状态 */
        cJSON *resp = cJSON_CreateObject();
        cJSON_AddStringToObject(resp, "cmd", "wifi_status");
        cJSON_AddStringToObject(resp, "ip", s_ip_str);
        cJSON_AddBoolToObject(resp, "connected", s_connected);
        cJSON_AddNumberToObject(resp, "client", s_client_fd >= 0 ? 1 : 0);
        char *json = cJSON_PrintUnformatted(resp);
        wifi_ctrl_send(json, strlen(json));
        free(json);
        cJSON_Delete(resp);
    } else if (strstr(json_str, "\"wifi_scan\"")) {
        ESP_LOGI(TAG, "WiFi scan requested");
    } else {
        ESP_LOGW(TAG, "Unknown WiFi cmd");
    }
}

/* ── mDNS 初始化（暂时禁用） ─────────────── */
static void mdns_init_service(void)
{
    ESP_LOGW(TAG, "mDNS disabled (component not installed)");
    /* TODO: 添加 mDNS 组件依赖后启用
    esp_err_t err = mdns_init();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "mDNS init failed: %s", esp_err_to_name(err));
        return;
    }
    mdns_hostname_set(MDNS_HOSTNAME);
    mdns_instance_name_set(MDNS_INSTANCE);
    mdns_service_add(NULL, "_ai-deck", "_tcp", TCP_PORT, NULL, 0);
    ESP_LOGI(TAG, "mDNS: %s.local (TCP:%d)", MDNS_HOSTNAME, TCP_PORT);
    */
}

/* ── TCP 服务器任务 ──────────────────────── */
static void tcp_server_task(void *arg)
{
    struct sockaddr_in server_addr = {
        .sin_family = AF_INET,
        .sin_port = htons(TCP_PORT),
        .sin_addr.s_addr = INADDR_ANY,
    };

    int listen_fd = socket(AF_INET, SOCK_STREAM, IPPROTO_IP);
    if (listen_fd < 0) {
        ESP_LOGE(TAG, "TCP socket create failed");
        vTaskDelete(NULL);
        return;
    }

    int opt = 1;
    setsockopt(listen_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    if (bind(listen_fd, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0) {
        ESP_LOGE(TAG, "TCP bind failed");
        close(listen_fd);
        vTaskDelete(NULL);
        return;
    }

    if (listen(listen_fd, 1) < 0) {
        ESP_LOGE(TAG, "TCP listen failed");
        close(listen_fd);
        vTaskDelete(NULL);
        return;
    }

    ESP_LOGI(TAG, "TCP server listening on :%d", TCP_PORT);

    while (1) {
        struct sockaddr_in client_addr;
        socklen_t addr_len = sizeof(client_addr);
        int client_fd = accept(listen_fd, (struct sockaddr *)&client_addr, &addr_len);

        if (client_fd < 0) {
            ESP_LOGE(TAG, "TCP accept failed");
            continue;
        }

        ESP_LOGI(TAG, "TCP client connected from %s:%d",
                 inet_ntoa(client_addr.sin_addr), ntohs(client_addr.sin_port));

        /* 只允许一个客户端 */
        if (s_client_fd >= 0) {
            close(s_client_fd);
        }
        s_client_fd = client_fd;

        /* 接收循环 */
        char *buf = malloc(TCP_BUF_SIZE);
        if (!buf) {
            close(client_fd);
            s_client_fd = -1;
            continue;
        }

        while (1) {
            int len = recv(client_fd, buf, TCP_BUF_SIZE - 1, 0);
            if (len <= 0) {
                ESP_LOGI(TAG, "TCP client disconnected");
                break;
            }
            buf[len] = '\0';

            /* 可能一次收到多条 JSON（用 \n 分隔） */
            char *line = buf;
            while (line && *line) {
                char *nl = strchr(line, '\n');
                if (nl) *nl = '\0';

                /* 跳过空行 */
                if (*line) {
                    /* 跳过前导非 JSON 字符 */
                    char *json_start = strchr(line, '{');
                    if (json_start) {
                        wifi_handle_command(json_start);
                    }
                }

                line = nl ? nl + 1 : NULL;
            }
        }

        free(buf);
        close(client_fd);
        s_client_fd = -1;
    }
}

/* ── WiFi 事件处理 ───────────────────────── */
static void wifi_event_handler(void *arg, esp_event_base_t event_base,
                               int32_t event_id, void *event_data)
{
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        s_connected = false;
        if (s_retry_count < WIFI_RETRY_MAX) {
            esp_wifi_connect();
            s_retry_count++;
            ESP_LOGI(TAG, "WiFi reconnecting... (%d/%d)", s_retry_count, WIFI_RETRY_MAX);
        } else {
            xEventGroupSetBits(s_wifi_event_group, WIFI_FAIL_BIT);
            ESP_LOGE(TAG, "WiFi connection failed after %d retries", WIFI_RETRY_MAX);
        }
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *event = (ip_event_got_ip_t *)event_data;
        snprintf(s_ip_str, sizeof(s_ip_str), IPSTR, IP2STR(&event->ip_info.ip));
        ESP_LOGI(TAG, "WiFi connected! IP: %s", s_ip_str);
        s_connected = true;
        s_retry_count = 0;
        xEventGroupSetBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
    }
}

/* ── NVS 读取 WiFi 凭据 ─────────────────── */
static esp_err_t load_credentials(char *ssid, size_t ssid_len, char *pass, size_t pass_len)
{
    nvs_handle_t handle;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READONLY, &handle);
    if (err != ESP_OK) return err;

    size_t slen = ssid_len;
    size_t plen = pass_len;
    err = nvs_get_str(handle, "ssid", ssid, &slen);
    if (err != ESP_OK) { nvs_close(handle); return err; }

    err = nvs_get_str(handle, "pass", pass, &plen);
    nvs_close(handle);
    return err;
}

/* ── 初始化 ──────────────────────────────── */
esp_err_t wifi_ctrl_init(const char *ssid, const char *pass)
{
    if (s_initialized) {
        ESP_LOGW(TAG, "Already initialized");
        return ESP_OK;
    }

    s_wifi_event_group = xEventGroupCreate();

    /* 初始化网络栈 */
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();

    /* WiFi 初始化 */
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    /* 注册事件处理 */
    ESP_ERROR_CHECK(esp_event_handler_instance_register(
        WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler, NULL, NULL));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(
        IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event_handler, NULL, NULL));

    /* 配置 WiFi */
    char stored_ssid[33] = {0};
    char stored_pass[65] = {0};

    if (ssid && pass) {
        /* 使用传入的凭据 */
        strncpy(stored_ssid, ssid, sizeof(stored_ssid) - 1);
        strncpy(stored_pass, pass, sizeof(stored_pass) - 1);
    } else {
        /* 从 NVS 读取 */
        esp_err_t err = load_credentials(stored_ssid, sizeof(stored_ssid),
                                          stored_pass, sizeof(stored_pass));
        if (err != ESP_OK) {
            ESP_LOGW(TAG, "No WiFi credentials in NVS, starting AP mode");
            /* TODO: 启动 AP 模式让用户配置 */
            return ESP_ERR_NOT_FOUND;
        }
    }

    wifi_config_t wifi_config = {0};
    strncpy((char *)wifi_config.sta.ssid, stored_ssid, sizeof(wifi_config.sta.ssid) - 1);
    strncpy((char *)wifi_config.sta.password, stored_pass, sizeof(wifi_config.sta.password) - 1);
    wifi_config.sta.threshold.authmode = WIFI_AUTH_WPA2_PSK;

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());

    ESP_LOGI(TAG, "WiFi connecting to: %s", stored_ssid);

    /* 等待连接结果（最多 15 秒） */
    EventBits_t bits = xEventGroupWaitBits(s_wifi_event_group,
        WIFI_CONNECTED_BIT | WIFI_FAIL_BIT, pdFALSE, pdFALSE,
        pdMS_TO_TICKS(15000));

    if (bits & WIFI_CONNECTED_BIT) {
        ESP_LOGI(TAG, "WiFi connected, IP: %s", s_ip_str);
    } else {
        ESP_LOGW(TAG, "WiFi connection timeout, continuing anyway...");
        /* 不返回错误，让重连机制在后台工作 */
    }

    /* 启动 mDNS */
    mdns_init_service();

    /* 启动 TCP 服务器 */
    xTaskCreate(tcp_server_task, "tcp_srv", 8192, NULL, 5, NULL);

    /* 安装日志输出到 TCP 的处理函数 */
    esp_log_set_vprintf(wifi_log_vprintf);

    s_initialized = true;
    return ESP_OK;
}

/* ── 保存 WiFi 凭据 ─────────────────────── */
esp_err_t wifi_ctrl_save_credentials(const char *ssid, const char *pass)
{
    nvs_handle_t handle;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &handle);
    if (err != ESP_OK) return err;

    nvs_set_str(handle, "ssid", ssid);
    nvs_set_str(handle, "pass", pass);
    err = nvs_commit(handle);
    nvs_close(handle);

    ESP_LOGI(TAG, "WiFi credentials saved to NVS");
    return err;
}

/* ── 状态查询 ────────────────────────────── */
bool wifi_ctrl_is_connected(void)
{
    return s_connected;
}

esp_err_t wifi_ctrl_get_ip(char *buf, size_t len)
{
    if (!s_connected || s_ip_str[0] == '\0') {
        return ESP_ERR_INVALID_STATE;
    }
    strncpy(buf, s_ip_str, len);
    return ESP_OK;
}

/* ── TCP 发送 ────────────────────────────── */
bool wifi_ctrl_send(const char *data, size_t len)
{
    if (s_client_fd < 0) return false;

    int sent = send(s_client_fd, data, len, 0);
    return sent == (int)len;
}

bool wifi_ctrl_has_client(void)
{
    return s_client_fd >= 0;
}
