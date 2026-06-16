/**
 * 轻量级 GIF 解码器 (内存优化版)
 * 设计用于 ESP32-S3 PSRAM 环境
 * 一次解码一帧，输出 RGB565
 */
#pragma once
#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct gd_frame {
    uint16_t width;
    uint16_t height;
    uint16_t delay_ms;     /* 帧延迟 */
    uint16_t *pixels;      /* RGB565, 需要调用者 free */
    bool     is_disposal2; /* 是否需要恢复背景 */
} gd_frame_t;

typedef struct gd_gif gd_gif_t;

/**
 * 从内存缓冲区打开 GIF
 * @param data   GIF文件数据
 * @param size   数据大小
 * @return GIF句柄, 失败返回NULL
 */
gd_gif_t *gd_open_gif_from_memory(const uint8_t *data, uint32_t size);

/**
 * 解码下一帧
 * @param gif   GIF句柄
 * @param frame 输出帧数据 (pixels需要free)
 * @return 0=成功, -1=结束/错误
 */
int gd_decode_frame(gd_gif_t *gif, gd_frame_t *frame);

/**
 * 获取GIF信息
 */
void gd_get_info(gd_gif_t *gif, uint16_t *w, uint16_t *h, uint16_t *frame_count);

/**
 * 关闭GIF并释放资源
 */
void gd_close_gif(gd_gif_t *gif);

#ifdef __cplusplus
}
#endif
