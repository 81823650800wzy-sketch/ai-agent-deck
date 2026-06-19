/**
 * AI Agent Deck - 壁纸管理器实现
 * 支持静态图片和 GIF 动图，数据存储在 PSRAM
 */

#include <string.h>
#include <stdlib.h>
#include <stdarg.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_heap_caps.h"
#include "esp_timer.h"
#include "cJSON.h"
#include "st7789.h"
#include "wallpaper.h"

static const char *TAG = "WALLPAPER";

/* ── 全局壁纸状态 ────────────────────────── */
static wallpaper_t s_wp = {0};
static volatile bool s_uploading = false;
static int64_t s_upload_start_time = 0;    /* 上传开始时间 (ms) */
#define UPLOAD_TIMEOUT_MS  60000            /* 上传超时: 60秒 */

/* ── 重组缓冲区（模块级，便于清理） ──────── */
static uint8_t *s_reasm_buf = NULL;
static uint32_t s_reasm_total = 0;
static uint32_t s_reasm_off = 0;

/* ── Base64 解码缓冲区（内部 RAM，避免栈溢出）── */
#define CHUNK_BUF_SIZE  1024
static uint8_t s_chunk_buf[CHUNK_BUF_SIZE];

/* ── ACK 响应回调（由调用方设置） ─────────── */
static wp_ack_callback_t s_ack_cb = NULL;

void wallpaper_set_ack_callback(wp_ack_callback_t cb)
{
    s_ack_cb = cb;
}

bool wallpaper_is_uploading(void)
{
    if (s_uploading) {
        /* 超时保护：超过 60 秒自动复位 */
        int64_t elapsed = (esp_timer_get_time() / 1000) - s_upload_start_time;
        if (elapsed > UPLOAD_TIMEOUT_MS) {
            ESP_LOGE(TAG, "Upload timeout (%lld ms), auto-reset", (long long)elapsed);
            s_uploading = false;
            if (s_reasm_buf) {
                heap_caps_free(s_reasm_buf);
                s_reasm_buf = NULL;
            }
        }
    }
    return s_uploading;
}

/* ── ACK 发送（通过回调路由） ─────────────── */
static void send_ack(const char *json_fmt, ...)
{
    char buf[256];
    va_list args;
    va_start(args, json_fmt);
    int len = vsnprintf(buf, sizeof(buf) - 2, json_fmt, args);
    va_end(args);

    /* 确保以 \n 结尾（Manager 按 \n 分割） */
    if (len > 0 && buf[len - 1] != '\n') {
        buf[len++] = '\n';
        buf[len] = '\0';
    }

    if (s_ack_cb) {
        s_ack_cb(buf, len);
    } else {
        /* 默认: 串口输出 */
        printf("%s", buf);
    }
}

/* ── 初始化 ──────────────────────────────── */
esp_err_t wallpaper_init(void)
{
    memset(&s_wp, 0, sizeof(s_wp));
    s_wp.type = WP_TYPE_NONE;
    s_reasm_buf = NULL;
    s_reasm_total = 0;
    s_reasm_off = 0;
    ESP_LOGI(TAG, "Wallpaper init (PSRAM: %d KB free)",
             heap_caps_get_free_size(MALLOC_CAP_SPIRAM) / 1024);

    /* 生成默认渐变壁纸（验证 PSRAM 分配和显示） */
    uint16_t *pixels = heap_caps_malloc(WP_FRAME_SIZE, MALLOC_CAP_SPIRAM);
    if (pixels) {
        for (int y = 0; y < WP_HEIGHT; y++) {
            for (int x = 0; x < WP_WIDTH; x++) {
                uint8_t r = (x * 31) / WP_WIDTH;
                uint8_t g = (y * 63) / WP_HEIGHT;
                uint8_t b = 15;
                pixels[y * WP_WIDTH + x] = (r << 11) | (g << 5) | b;
            }
        }
        s_wp.static_pixels = pixels;
        s_wp.type = WP_TYPE_STATIC;
        ESP_LOGI(TAG, "Default gradient wallpaper generated");
    }

    return ESP_OK;
}

wallpaper_t *wallpaper_get(void)
{
    return &s_wp;
}

/* ── 释放壁纸资源 ────────────────────────── */
static void free_static(void)
{
    if (s_wp.static_pixels) {
        heap_caps_free(s_wp.static_pixels);
        s_wp.static_pixels = NULL;
    }
}

static void free_gif(void)
{
    if (s_wp.frames) {
        for (int i = 0; i < s_wp.frame_count; i++) {
            if (s_wp.frames[i].pixels) {
                heap_caps_free(s_wp.frames[i].pixels);
            }
        }
        heap_caps_free(s_wp.frames);
        s_wp.frames = NULL;
    }
    s_wp.frame_count = 0;
    s_wp.current_frame = 0;
    s_wp.playing = false;
}

/* ── 清理重组缓冲区 ──────────────────────── */
static void cleanup_reasm(void)
{
    if (s_reasm_buf) {
        heap_caps_free(s_reasm_buf);
        s_reasm_buf = NULL;
    }
    s_reasm_total = 0;
    s_reasm_off = 0;
}

/* ── 设置静态壁纸 ────────────────────────── */
esp_err_t wallpaper_set_static(const uint16_t *data, uint32_t len)
{
    if (len < WP_FRAME_SIZE) {
        ESP_LOGE(TAG, "Static image too small: %d < %d", len, WP_FRAME_SIZE);
        return ESP_ERR_INVALID_SIZE;
    }

    free_static();
    free_gif();

    s_wp.static_pixels = heap_caps_malloc(WP_FRAME_SIZE, MALLOC_CAP_SPIRAM);
    if (!s_wp.static_pixels) {
        ESP_LOGE(TAG, "PSRAM alloc failed for static wallpaper");
        return ESP_ERR_NO_MEM;
    }

    memcpy(s_wp.static_pixels, data, WP_FRAME_SIZE);
    s_wp.type = WP_TYPE_STATIC;

    ESP_LOGI(TAG, "Static wallpaper set (%d bytes)", WP_FRAME_SIZE);
    return ESP_OK;
}

/* ── GIF 传输 ────────────────────────────── */
esp_err_t wallpaper_gif_start(uint16_t frame_count)
{
    if (frame_count == 0 || frame_count > 300) {
        ESP_LOGE(TAG, "Invalid frame count: %d", frame_count);
        return ESP_ERR_INVALID_ARG;
    }

    free_static();
    free_gif();

    s_wp.frames = heap_caps_calloc(frame_count, sizeof(wp_gif_frame_t), MALLOC_CAP_SPIRAM);
    if (!s_wp.frames) {
        ESP_LOGE(TAG, "PSRAM alloc failed for %d frames", frame_count);
        return ESP_ERR_NO_MEM;
    }

    s_wp.frame_count = frame_count;
    s_wp.current_frame = 0;
    s_wp.playing = false;

    ESP_LOGI(TAG, "GIF transfer start: %d frames", frame_count);
    return ESP_OK;
}

esp_err_t wallpaper_gif_add_frame(uint16_t frame_idx, const uint16_t *data,
                                   uint32_t len, uint16_t delay_ms)
{
    if (!s_wp.frames || frame_idx >= s_wp.frame_count) {
        ESP_LOGE(TAG, "Invalid frame idx %d (count=%d)", frame_idx, s_wp.frame_count);
        return ESP_ERR_INVALID_ARG;
    }

    if (len < WP_FRAME_SIZE) {
        ESP_LOGE(TAG, "Frame %d too small: %d < %d", frame_idx, len, WP_FRAME_SIZE);
        return ESP_ERR_INVALID_SIZE;
    }

    if (s_wp.frames[frame_idx].pixels) {
        heap_caps_free(s_wp.frames[frame_idx].pixels);
    }

    s_wp.frames[frame_idx].pixels = heap_caps_malloc(WP_FRAME_SIZE, MALLOC_CAP_SPIRAM);
    if (!s_wp.frames[frame_idx].pixels) {
        ESP_LOGE(TAG, "PSRAM alloc failed for frame %d", frame_idx);
        return ESP_ERR_NO_MEM;
    }

    memcpy(s_wp.frames[frame_idx].pixels, data, WP_FRAME_SIZE);
    s_wp.frames[frame_idx].delay_ms = delay_ms > 0 ? delay_ms : 100;

    ESP_LOGI(TAG, "GIF frame %d/%d added (delay=%dms)",
             frame_idx + 1, s_wp.frame_count, delay_ms);
    return ESP_OK;
}

esp_err_t wallpaper_gif_finish(void)
{
    if (!s_wp.frames || s_wp.frame_count == 0) {
        return ESP_ERR_INVALID_STATE;
    }

    int loaded = 0;
    for (int i = 0; i < s_wp.frame_count; i++) {
        if (s_wp.frames[i].pixels) loaded++;
    }

    if (loaded == 0) {
        ESP_LOGE(TAG, "No frames loaded");
        return ESP_ERR_INVALID_STATE;
    }

    s_wp.type = WP_TYPE_GIF;
    s_wp.current_frame = 0;
    s_wp.last_frame_time = esp_timer_get_time() / 1000;
    s_wp.playing = true;

    ESP_LOGI(TAG, "GIF ready: %d/%d frames loaded", loaded, s_wp.frame_count);
    return ESP_OK;
}

esp_err_t wallpaper_clear(void)
{
    free_static();
    free_gif();
    cleanup_reasm();
    s_wp.type = WP_TYPE_NONE;
    s_uploading = false;
    ESP_LOGI(TAG, "Wallpaper cleared");
    return ESP_OK;
}

bool wallpaper_update(void)
{
    if (s_wp.type != WP_TYPE_GIF || !s_wp.playing || !s_wp.frames) {
        return false;
    }

    int64_t now = esp_timer_get_time() / 1000;
    uint16_t delay = s_wp.frames[s_wp.current_frame].delay_ms;

    if ((now - s_wp.last_frame_time) >= delay) {
        s_wp.current_frame = (s_wp.current_frame + 1) % s_wp.frame_count;
        s_wp.last_frame_time = now;
        return true;
    }

    return false;
}

void wallpaper_draw(void)
{
    switch (s_wp.type) {
        case WP_TYPE_STATIC:
            if (s_wp.static_pixels) {
                st7789_draw_bitmap(0, 0, WP_WIDTH, WP_HEIGHT, s_wp.static_pixels);
            }
            break;

        case WP_TYPE_GIF:
            if (s_wp.frames && s_wp.frames[s_wp.current_frame].pixels) {
                st7789_draw_bitmap(0, 0, WP_WIDTH, WP_HEIGHT,
                                   s_wp.frames[s_wp.current_frame].pixels);
            }
            break;

        case WP_TYPE_NONE:
        default:
            break;
    }
}

/* ── Base64 解码 ─────────────────────────── */

static const int b64_table[256] = {
    ['A']=0,['B']=1,['C']=2,['D']=3,['E']=4,['F']=5,['G']=6,['H']=7,
    ['I']=8,['J']=9,['K']=10,['L']=11,['M']=12,['N']=13,['O']=14,['P']=15,
    ['Q']=16,['R']=17,['S']=18,['T']=19,['U']=20,['V']=21,['W']=22,['X']=23,
    ['Y']=24,['Z']=25,['a']=26,['b']=27,['c']=28,['d']=29,['e']=30,['f']=31,
    ['g']=32,['h']=33,['i']=34,['j']=35,['k']=36,['l']=37,['m']=38,['n']=39,
    ['o']=40,['p']=41,['q']=42,['r']=43,['s']=44,['t']=45,['u']=46,['v']=47,
    ['w']=48,['x']=49,['y']=50,['z']=51,['0']=52,['1']=53,['2']=54,['3']=55,
    ['4']=56,['5']=57,['6']=58,['7']=59,['8']=60,['9']=61,['+']=62,['/']=63,
};

static int base64_decode(const char *src, int src_len, uint8_t *dst, int dst_max)
{
    int out = 0;
    uint32_t acc = 0;
    int bits = 0;

    for (int i = 0; i < src_len && out < dst_max; i++) {
        char c = src[i];
        if (c == '=' || c == '\0') break;
        int val = b64_table[(unsigned char)c];
        acc = (acc << 6) | val;
        bits += 6;
        if (bits >= 8) {
            bits -= 8;
            dst[out++] = (acc >> bits) & 0xFF;
        }
    }
    return out;
}

/* ── 命令解析 ─────────────────────────────── */
void wallpaper_parse_cmd(const char *json_str)
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

    const char *cmd_str = cmd->valuestring;

    if (strcmp(cmd_str, "wallpaper_start") == 0) {
        const cJSON *size = cJSON_GetObjectItem(root, "size");
        if (size && cJSON_IsNumber(size)) {
            cleanup_reasm();
            s_uploading = true;
            s_upload_start_time = esp_timer_get_time() / 1000;
            ESP_LOGI(TAG, "Wallpaper upload start: %d bytes", size->valueint);
            send_ack("{\"cmd\":\"wallpaper_ack\",\"status\":\"ready\"}");
        }
    }
    else if (strcmp(cmd_str, "wallpaper_end") == 0) {
        ESP_LOGI(TAG, "Wallpaper upload end");
        s_uploading = false;
        cleanup_reasm();
        send_ack("{\"cmd\":\"wallpaper_ack\",\"status\":\"end\"}");
    }
    else if (strcmp(cmd_str, "wallpaper_set") == 0) {
        const cJSON *data = cJSON_GetObjectItem(root, "data");
        if (data && cJSON_IsString(data)) {
            int b64_len = strlen(data->valuestring);
            int max_decoded = (b64_len * 3) / 4 + 4;
            uint8_t *buf = heap_caps_malloc(max_decoded, MALLOC_CAP_SPIRAM);
            if (buf) {
                int decoded_len = base64_decode(data->valuestring, b64_len, buf, max_decoded);
                ESP_LOGI(TAG, "Wallpaper data: %d base64 -> %d bytes", b64_len, decoded_len);
                if (decoded_len >= WP_FRAME_SIZE) {
                    wallpaper_set_static((uint16_t *)buf, decoded_len);
                    send_ack("{\"cmd\":\"wallpaper_ack\",\"status\":\"ok\"}");
                } else {
                    ESP_LOGE(TAG, "Image too small: %d < %d", decoded_len, WP_FRAME_SIZE);
                    send_ack("{\"cmd\":\"wallpaper_ack\",\"status\":\"error\",\"msg\":\"too_small\"}");
                }
                heap_caps_free(buf);
            }
        }
    }
    else if (strcmp(cmd_str, "wp_chunk") == 0) {
        const cJSON *off = cJSON_GetObjectItem(root, "off");
        const cJSON *total = cJSON_GetObjectItem(root, "total");
        const cJSON *data = cJSON_GetObjectItem(root, "data");

        if (off && total && data && cJSON_IsNumber(off) && cJSON_IsNumber(total) && cJSON_IsString(data)) {
            uint32_t offset = off->valueint;
            uint32_t total_size = total->valueint;
            int b64_len = strlen(data->valuestring);

            if (offset == 0 || s_reasm_buf == NULL) {
                cleanup_reasm();
                if (total_size == WP_FRAME_SIZE) {
                    s_reasm_buf = heap_caps_malloc(total_size, MALLOC_CAP_SPIRAM);
                    s_reasm_total = total_size;
                    s_reasm_off = 0;
                    if (s_reasm_buf) {
                        ESP_LOGI(TAG, "Reasm buffer alloc: %lu bytes", (unsigned long)total_size);
                    } else {
                        ESP_LOGE(TAG, "Reasm buffer alloc FAILED");
                    }
                } else {
                    ESP_LOGW(TAG, "Invalid total size: %lu (expected %d)", (unsigned long)total_size, WP_FRAME_SIZE);
                }
            }

            if (s_reasm_buf) {
                int chunk_len = base64_decode(data->valuestring, b64_len,
                                               s_chunk_buf, CHUNK_BUF_SIZE);
                if (chunk_len > 0 && offset + chunk_len <= s_reasm_total) {
                    memcpy(s_reasm_buf + offset, s_chunk_buf, chunk_len);
                    s_reasm_off = offset + chunk_len;
                    ESP_LOGI(TAG, "Chunk %lu+%d / %lu", (unsigned long)offset, chunk_len, (unsigned long)s_reasm_total);
                    send_ack("{\"cmd\":\"wallpaper_ack\",\"status\":\"chunk\",\"off\":%lu}", (unsigned long)offset);

                    if (s_reasm_off >= s_reasm_total) {
                        ESP_LOGI(TAG, "Reasm complete, setting wallpaper...");
                        wallpaper_set_static((uint16_t *)s_reasm_buf, s_reasm_total);
                        cleanup_reasm();
                        s_uploading = false;
                        send_ack("{\"cmd\":\"wallpaper_ack\",\"status\":\"ok\"}");
                    }
                } else {
                    ESP_LOGE(TAG, "Chunk error: len=%d off=%lu total=%lu",
                             chunk_len, (unsigned long)offset, (unsigned long)s_reasm_total);
                    send_ack("{\"cmd\":\"wallpaper_ack\",\"status\":\"error\",\"msg\":\"chunk_bounds\"}");
                }
            } else {
                ESP_LOGE(TAG, "Reasm buffer not allocated");
                send_ack("{\"cmd\":\"wallpaper_ack\",\"status\":\"error\",\"msg\":\"no_buf\"}");
            }
        }
    }
    else if (strcmp(cmd_str, "wallpaper_gif_start") == 0) {
        const cJSON *frames = cJSON_GetObjectItem(root, "frames");
        if (frames && cJSON_IsNumber(frames)) {
            esp_err_t err = wallpaper_gif_start(frames->valueint);
            if (err == ESP_OK) {
                send_ack("{\"cmd\":\"wallpaper_ack\",\"status\":\"gif_start\",\"frames\":%d}",
                         frames->valueint);
            } else {
                send_ack("{\"cmd\":\"wallpaper_ack\",\"status\":\"error\",\"msg\":\"gif_start_fail\"}");
            }
        }
    }
    else if (strcmp(cmd_str, "wallpaper_gif_frame") == 0) {
        const cJSON *idx = cJSON_GetObjectItem(root, "idx");
        const cJSON *delay = cJSON_GetObjectItem(root, "delay");
        const cJSON *data = cJSON_GetObjectItem(root, "data");

        if (idx && cJSON_IsNumber(idx) && data && cJSON_IsString(data)) {
            int b64_len = strlen(data->valuestring);
            int max_decoded = (b64_len * 3) / 4 + 4;
            uint8_t *buf = heap_caps_malloc(max_decoded, MALLOC_CAP_SPIRAM);
            if (buf) {
                int decoded_len = base64_decode(data->valuestring, b64_len, buf, max_decoded);
                uint16_t delay_ms = (delay && cJSON_IsNumber(delay)) ? delay->valueint : 100;

                esp_err_t err = wallpaper_gif_add_frame(idx->valueint, (uint16_t *)buf,
                                                         decoded_len, delay_ms);
                if (err == ESP_OK) {
                    send_ack("{\"cmd\":\"wallpaper_ack\",\"status\":\"frame_ok\",\"idx\":%d}",
                             idx->valueint);
                } else {
                    send_ack("{\"cmd\":\"wallpaper_ack\",\"status\":\"error\",\"msg\":\"frame_fail\"}");
                }
                heap_caps_free(buf);
            }
        }
    }
    else if (strcmp(cmd_str, "wallpaper_gif_end") == 0) {
        wallpaper_gif_finish();
        send_ack("{\"cmd\":\"wallpaper_ack\",\"status\":\"gif_end\"}");
    }
    else if (strcmp(cmd_str, "wallpaper_clear") == 0) {
        wallpaper_clear();
        send_ack("{\"cmd\":\"wallpaper_ack\",\"status\":\"cleared\"}");
    }

    cJSON_Delete(root);
}
