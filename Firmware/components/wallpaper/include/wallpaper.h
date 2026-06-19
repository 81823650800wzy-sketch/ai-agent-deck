/**
 * AI Agent Deck - 壁纸管理器
 * 支持静态图片和 GIF 动图壁纸
 * 数据存储在 PSRAM 中
 */

#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ── 壁纸类型 ─────────────────────────────── */
typedef enum {
    WP_TYPE_NONE = 0,       /* 无壁纸（显示默认渐变） */
    WP_TYPE_STATIC,         /* 静态图片 */
    WP_TYPE_GIF,            /* GIF 动图 */
} wallpaper_type_t;

/* ── 壁纸配置 ─────────────────────────────── */
#define WP_WIDTH    240
#define WP_HEIGHT   240
#define WP_BPP      2       /* RGB565 = 2 bytes per pixel */
#define WP_FRAME_SIZE   (WP_WIDTH * WP_HEIGHT * WP_BPP)  /* 115200 bytes */

/* ── GIF 帧信息 ───────────────────────────── */
typedef struct {
    uint16_t *pixels;       /* RGB565 像素数据 (PSRAM) */
    uint16_t delay_ms;      /* 帧延迟 */
} wp_gif_frame_t;

/* ── 壁纸数据 ─────────────────────────────── */
typedef struct {
    wallpaper_type_t type;

    /* 静态图片 */
    uint16_t *static_pixels;    /* RGB565, PSRAM 分配 */

    /* GIF 动图 */
    wp_gif_frame_t *frames;     /* 帧数组 (PSRAM) */
    uint16_t frame_count;
    uint16_t current_frame;
    int64_t last_frame_time;    /* 上次帧切换时间 (ms) */
    bool playing;               /* 是否正在播放 */
} wallpaper_t;

/* ── ACK 回调类型 ─────────────────────────── */
typedef void (*wp_ack_callback_t)(const char *data, int len);

/* ── API ──────────────────────────────────── */

/**
 * 设置 ACK 响应回调（串口/WiFi/BLE 各自设置）
 * 未设置时默认使用 printf (串口)
 */
void wallpaper_set_ack_callback(wp_ack_callback_t cb);

/**
 * 初始化壁纸系统
 */
esp_err_t wallpaper_init(void);

/**
 * 获取当前壁纸
 */
wallpaper_t *wallpaper_get(void);

/**
 * 设置静态壁纸 (从 RGB565 数据)
 * @param data  RGB565 像素数据 (240*240*2 字节)
 * @param len   数据长度
 */
esp_err_t wallpaper_set_static(const uint16_t *data, uint32_t len);

/**
 * 开始 GIF 壁纸传输
 * @param frame_count  总帧数
 */
esp_err_t wallpaper_gif_start(uint16_t frame_count);

/**
 * 添加 GIF 帧
 * @param frame_idx  帧索引
 * @param data       RGB565 像素数据
 * @param len        数据长度
 * @param delay_ms   帧延迟
 */
esp_err_t wallpaper_gif_add_frame(uint16_t frame_idx, const uint16_t *data,
                                   uint32_t len, uint16_t delay_ms);

/**
 * 完成 GIF 传输并开始播放
 */
esp_err_t wallpaper_gif_finish(void);

/**
 * 清除壁纸（恢复默认渐变）
 */
esp_err_t wallpaper_clear(void);

/**
 * 壁纸帧更新（主循环调用）
 * 对于 GIF，自动根据延迟切换帧
 * @return true 如果需要重绘
 */
bool wallpaper_update(void);

/**
 * 将当前壁纸帧绘制到屏幕
 */
void wallpaper_draw(void);

/**
 * 从串口命令加载壁纸
 * ACK 通过 wallpaper_set_ack_callback 设置的回调发送
 * @param json_str  JSON 命令字符串
 */
void wallpaper_parse_cmd(const char *json_str);

/**
 * 是否正在上传壁纸（主循环应暂停 SPI 刷新）
 */
bool wallpaper_is_uploading(void);

#ifdef __cplusplus
}
#endif
