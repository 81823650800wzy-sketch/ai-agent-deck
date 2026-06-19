/**
 * AI Agent Deck - 壁纸管理器实现
 * 支持静态图片和 GIF 动图，数据存储在 PSRAM
 */

#include <string.h>
#include <stdlib.h>
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

bool wallpaper_is_uploading(void) { return s_uploading; }

/* ── 初始化 ──────────────────────────────── */
esp_err_t wallpaper_init(void)
{
    memset(&s_wp, 0, sizeof(s_wp));
    s_wp.type = WP_TYPE_NONE;
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

/* ── 设置静态壁纸 ────────────────────────── */
esp_err_t wallpaper_set_static(const uint16_t *data, uint32_t len)
{
    if (len < WP_FRAME_SIZE) {
        ESP_LOGE(TAG, "Static image too small: %d < %d", len, WP_FRAME_SIZE);
        return ESP_ERR_INVALID_SIZE;
    }

    /* 释放旧壁纸 */
    free_static();
    free_gif();

    /* 分配 PSRAM */
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

    /* 释放旧壁纸 */
    free_static();
    free_gif();

    /* 分配帧数组 */
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

    /* 释放旧帧数据（如果重传） */
    if (s_wp.frames[frame_idx].pixels) {
        heap_caps_free(s_wp.frames[frame_idx].pixels);
    }

    /* 分配帧像素 */
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

    /* 检查所有帧是否已接收 */
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

/* ── 清除壁纸 ────────────────────────────── */
esp_err_t wallpaper_clear(void)
{
    free_static();
    free_gif();
    s_wp.type = WP_TYPE_NONE;
    ESP_LOGI(TAG, "Wallpaper cleared");
    return ESP_OK;
}

/* ── 帧更新（GIF 自动播放） ──────────────── */
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
        return true;  /* 需要重绘 */
    }

    return false;
}

/* ── 绘制壁纸到屏幕 ─────────────────────── */
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
            /* 无壁纸，不绘制（由主循环绘制默认渐变） */
            break;
    }
}

/* ── 串口命令解析 ────────────────────────── */

/* Base64 解码表 */
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
        /* 壁纸传输开始: {"cmd":"wallpaper_start","width":240,"height":240,"size":115200} */
        const cJSON *size = cJSON_GetObjectItem(root, "size");
        if (size && cJSON_IsNumber(size)) {
            ESP_LOGI(TAG, "Wallpaper upload start: %d bytes", size->valueint);
            s_uploading = true;
            printf("{\"cmd\":\"wallpaper_ack\",\"status\":\"ready\"}\n");
        }
    }
    else if (strcmp(cmd_str, "wallpaper_end") == 0) {
        /* 壁纸传输结束 */
        ESP_LOGI(TAG, "Wallpaper upload end");
        s_uploading = false;
        printf("{\"cmd\":\"wallpaper_ack\",\"status\":\"end\"}\n");
    }
    else if (strcmp(cmd_str, "wallpaper_set") == 0) {
        /* 静态壁纸（完整数据）: {"cmd":"wallpaper_set","data":"<base64>"} */
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
                    printf("{\"cmd\":\"wallpaper_ack\",\"status\":\"ok\"}\n");
                } else {
                    ESP_LOGE(TAG, "Image too small: %d < %d", decoded_len, WP_FRAME_SIZE);
                    printf("{\"cmd\":\"wallpaper_ack\",\"status\":\"error\",\"msg\":\"too_small\"}\n");
                }
                heap_caps_free(buf);
            }
        }
    }
    else if (strcmp(cmd_str, "wp_chunk") == 0) {
        /* 分块传输: {"cmd":"wp_chunk","off":0,"total":115200,"data":"<base64>"} */
        const cJSON *off = cJSON_GetObjectItem(root, "off");
        const cJSON *total = cJSON_GetObjectItem(root, "total");
        const cJSON *data = cJSON_GetObjectItem(root, "data");

        if (off && total && data && cJSON_IsNumber(off) && cJSON_IsNumber(total) && cJSON_IsString(data)) {
            static uint8_t *s_reasm_buf = NULL;
            static uint32_t s_reasm_total = 0;
            static uint32_t s_reasm_off = 0;

            uint32_t offset = off->valueint;
            uint32_t total_size = total->valueint;
            int b64_len = strlen(data->valuestring);
            /* 静态内部 RAM 缓冲区（避免 PSRAM 和栈问题） */
            static uint8_t chunk_buf[256];
            int max_decoded = sizeof(chunk_buf);

            /* 首个分块：分配重组缓冲区 */
            if (offset == 0 || s_reasm_buf == NULL) {
                if (s_reasm_buf) {
                    heap_caps_free(s_reasm_buf);
                    s_reasm_buf = NULL;
                }
                /* 只有合法的壁纸大小才分配（115200 = 240*240*2） */
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

            /* 解码到栈缓冲区，再复制到重组缓冲区 */
            if (s_reasm_buf) {
                int chunk_len = base64_decode(data->valuestring, b64_len,
                                               chunk_buf, max_decoded);
                if (chunk_len > 0 && offset + chunk_len <= s_reasm_total) {
                    memcpy(s_reasm_buf + offset, chunk_buf, chunk_len);
                    s_reasm_off = offset + chunk_len;
                    ESP_LOGI(TAG, "Chunk %lu+%d / %lu", (unsigned long)offset, chunk_len, (unsigned long)s_reasm_total);
                    printf("{\"cmd\":\"wallpaper_ack\",\"status\":\"chunk\",\"off\":%lu}\n", (unsigned long)offset);

                    /* 检查是否接收完成 */
                    if (s_reasm_off >= s_reasm_total) {
                        ESP_LOGI(TAG, "Reasm complete, setting wallpaper...");
                        wallpaper_set_static((uint16_t *)s_reasm_buf, s_reasm_total);
                        heap_caps_free(s_reasm_buf);
                        s_reasm_buf = NULL;
                        printf("{\"cmd\":\"wallpaper_ack\",\"status\":\"ok\"}\n");
                    }
                } else {
                    ESP_LOGE(TAG, "Chunk error: len=%d off=%lu total=%lu",
                             chunk_len, (unsigned long)offset, (unsigned long)s_reasm_total);
                }
            } else {
                ESP_LOGE(TAG, "Reasm buffer not allocated");
            }
        }
    }
    else if (strcmp(cmd_str, "wallpaper_gif_start") == 0) {
        /* GIF 开始: {"cmd":"wallpaper_gif_start","frames":N} */
        const cJSON *frames = cJSON_GetObjectItem(root, "frames");
        if (frames && cJSON_IsNumber(frames)) {
            wallpaper_gif_start(frames->valueint);
            printf("{\"cmd\":\"wallpaper_ack\",\"status\":\"gif_start\",\"frames\":%d}\n",
                   frames->valueint);
        }
    }
    else if (strcmp(cmd_str, "wallpaper_gif_frame") == 0) {
        /* GIF 帧: {"cmd":"wallpaper_gif_frame","idx":0,"delay":100,"data":"<base64>"} */
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
                    printf("{\"cmd\":\"wallpaper_ack\",\"status\":\"frame_ok\",\"idx\":%d}\n",
                           idx->valueint);
                }
                heap_caps_free(buf);
            }
        }
    }
    else if (strcmp(cmd_str, "wallpaper_gif_end") == 0) {
        /* GIF 完成: {"cmd":"wallpaper_gif_end"} */
        wallpaper_gif_finish();
        printf("{\"cmd\":\"wallpaper_ack\",\"status\":\"gif_end\"}\n");
    }
    else if (strcmp(cmd_str, "wallpaper_clear") == 0) {
        /* 清除壁纸: {"cmd":"wallpaper_clear"} */
        wallpaper_clear();
        printf("{\"cmd\":\"wallpaper_ack\",\"status\":\"cleared\"}\n");
    }

    cJSON_Delete(root);
}
