/**
 * ST7789 240x240 IPS 显示驱动
 * 适配: 1.54寸 IPS RGB 240×240 SPI 模块
 */

#pragma once
#include <stdint.h>
#include "driver/spi_master.h"
#include "driver/gpio.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ── 颜色定义 ───────────────────────── */
#define ST7789_COLOR_BLACK   0x0000
#define ST7789_COLOR_WHITE   0xFFFF
#define ST7789_COLOR_RED     0xF800
#define ST7789_COLOR_GREEN   0x07E0
#define ST7789_COLOR_BLUE    0x001F
#define ST7789_COLOR_YELLOW  0xFFE0
#define ST7789_COLOR_CYAN    0x07FF
#define ST7789_COLOR_MAGENTA 0xF81F
#define ST7789_COLOR_GRAY    0x8410
#define RGB565(r,g,b) ((((r)&0xF8)<<8)|(((g)&0xFC)<<3)|((b)>>3))

/* ── 配置结构体 ─────────────────────── */
typedef struct {
    spi_host_device_t spi_host;
    gpio_num_t pin_mosi, pin_sclk, pin_cs, pin_dc, pin_rst, pin_bl;
    int spi_clock_hz;
} st7789_config_t;

/* ── API ────────────────────────────── */
esp_err_t st7789_init(const st7789_config_t *config);
void st7789_backlight(bool level);
void st7789_fill_screen(uint16_t color);
void st7789_fill_rect(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1, uint16_t color);
void st7789_draw_pixel(uint16_t x, uint16_t y, uint16_t color);
void st7789_draw_bitmap(uint16_t x, uint16_t y, uint16_t w, uint16_t h, const uint16_t *bitmap);
void st7789_draw_hline(uint16_t x0, uint16_t x1, uint16_t y, uint16_t color);
void st7789_draw_vline(uint16_t x, uint16_t y0, uint16_t y1, uint16_t color);
void st7789_draw_rect(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1, uint16_t color);
void st7789_set_rotation(uint8_t rotation);
void st7789_get_size(uint16_t *w, uint16_t *h);
void st7789_set_madctl(uint8_t val);
void st7789_set_invert(bool inv);

#ifdef __cplusplus
}
#endif
