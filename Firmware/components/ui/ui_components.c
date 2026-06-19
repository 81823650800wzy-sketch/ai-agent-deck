/**
 * AI Agent Deck - UI 组件
 * 高级 UI 绘制函数：动画、圆角矩形、图标等
 *
 * 注意: ui_color_lerp, ui_draw_gradient_h, ui_draw_gradient_v 在 ui.c 中定义
 */

#include <stdio.h>
#include <string.h>
#include <math.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "st7789.h"
#include "font5x7.h"
#include "ui.h"
#include "ui_components.h"

/* ── 颜色亮度调整 ────────────────────────── */
uint16_t ui_color_brightness(uint16_t color, uint8_t brightness)
{
    uint8_t r = (color >> 11) & 0x1F;
    uint8_t g = (color >> 5) & 0x3F;
    uint8_t b = color & 0x1F;

    r = (r * brightness) / 255;
    g = (g * brightness) / 255;
    b = (b * brightness) / 255;

    return (r << 11) | (g << 5) | b;
}

/* ── Bresenham 圆弧辅助 ──────────────────── */
static void _draw_circle_quarter(int16_t cx, int16_t cy, int16_t r, uint16_t color, bool fill)
{
    int16_t x = 0, y = r;
    int16_t d = 3 - 2 * r;

    while (x <= y) {
        if (fill) {
            /* 填充：画水平线 */
            st7789_fill_rect(cx - y, cy - x, cx + y, cy - x, color);
            st7789_fill_rect(cx - x, cy - y, cx + x, cy - y, color);
            st7789_fill_rect(cx - y, cy + x, cx + y, cy + x, color);
            st7789_fill_rect(cx - x, cy + y, cx + x, cy + y, color);
        } else {
            /* 边框：画像素点 */
            st7789_draw_pixel(cx + x, cy + y, color);
            st7789_draw_pixel(cx - x, cy + y, color);
            st7789_draw_pixel(cx + x, cy - y, color);
            st7789_draw_pixel(cx - x, cy - y, color);
            st7789_draw_pixel(cx + y, cy + x, color);
            st7789_draw_pixel(cx - y, cy + x, color);
            st7789_draw_pixel(cx + y, cy - x, color);
            st7789_draw_pixel(cx - y, cy - x, color);
        }
        if (d < 0) {
            d += 4 * x + 6;
        } else {
            d += 4 * (x - y) + 10;
            y--;
        }
        x++;
    }
}

/* ── 圆角矩形绘制（Bresenham 圆弧） ─────── */
void ui_draw_rounded_rect(int16_t x, int16_t y, int16_t w, int16_t h, int16_t r, uint16_t color)
{
    if (r < 1) { st7789_draw_rect(x, y, x + w - 1, y + h - 1, color); return; }
    if (r > w / 2) r = w / 2;
    if (r > h / 2) r = h / 2;

    /* 四条边 */
    st7789_fill_rect(x + r, y, x + w - r - 1, y, color);           /* 上 */
    st7789_fill_rect(x + r, y + h - 1, x + w - r - 1, y + h - 1, color); /* 下 */
    st7789_fill_rect(x, y + r, x, y + h - r - 1, color);           /* 左 */
    st7789_fill_rect(x + w - 1, y + r, x + w - 1, y + h - r - 1, color); /* 右 */

    /* 四个圆角 */
    _draw_circle_quarter(x + r, y + r, r, color, false);
    _draw_circle_quarter(x + w - r - 1, y + r, r, color, false);
    _draw_circle_quarter(x + r, y + h - r - 1, r, color, false);
    _draw_circle_quarter(x + w - r - 1, y + h - r - 1, r, color, false);
}

void ui_fill_rounded_rect(int16_t x, int16_t y, int16_t w, int16_t h, int16_t r, uint16_t color)
{
    if (r < 1) { st7789_fill_rect(x, y, x + w - 1, y + h - 1, color); return; }
    if (r > w / 2) r = w / 2;
    if (r > h / 2) r = h / 2;

    /* 中间区域（三块矩形覆盖主体） */
    st7789_fill_rect(x + r, y, x + w - r - 1, y + h - 1, color);   /* 中间横条 */
    st7789_fill_rect(x, y + r, x + r - 1, y + h - r - 1, color);   /* 左竖条 */
    st7789_fill_rect(x + w - r, y + r, x + w - 1, y + h - r - 1, color); /* 右竖条 */

    /* 四个圆角填充 */
    _draw_circle_quarter(x + r, y + r, r, color, true);
    _draw_circle_quarter(x + w - r - 1, y + r, r, color, true);
    _draw_circle_quarter(x + r, y + h - r - 1, r, color, true);
    _draw_circle_quarter(x + w - r - 1, y + h - r - 1, r, color, true);
}

/* ── 进度条绘制 ──────────────────────────── */
void ui_draw_progress_bar(int16_t x, int16_t y, int16_t w, int16_t h,
                          uint8_t progress, uint16_t color, uint16_t bg_color)
{
    /* 背景 */
    ui_fill_rounded_rect(x, y, w, h, h / 2, bg_color);

    /* 进度 */
    int16_t fill_w = (w * progress) / 100;
    if (fill_w > h) {  /* 确保最小宽度 */
        ui_fill_rounded_rect(x, y, fill_w, h, h / 2, color);
    }
}

/* ── 电池图标绘制 ────────────────────────── */
void ui_draw_battery_icon(int16_t x, int16_t y, uint8_t level, bool charging)
{
    int16_t w = 20;
    int16_t h = 10;
    int16_t cap_w = 3;

    /* 电池外壳 */
    st7789_draw_rect(x, y, x + w - 1, y + h - 1, COLOR_TEXT);

    /* 电池帽 */
    st7789_fill_rect(x + w, y + 2, x + w + cap_w - 1, y + h - 3, COLOR_TEXT);

    /* 电量指示 */
    uint16_t color;
    if (level > 60) {
        color = COLOR_GREEN;
    } else if (level > 20) {
        color = COLOR_YELLOW;
    } else {
        color = COLOR_RED;
    }

    int16_t fill_w = ((w - 4) * level) / 100;
    if (fill_w > 0) {
        st7789_fill_rect(x + 2, y + 2, x + 2 + fill_w - 1, y + h - 3, color);
    }

    /* 充电指示 (闪电符号) */
    if (charging) {
        /* 简化的闪电符号 */
        st7789_draw_pixel(x + w / 2, y + 3, COLOR_YELLOW);
        st7789_draw_pixel(x + w / 2 - 1, y + 4, COLOR_YELLOW);
        st7789_draw_pixel(x + w / 2, y + 5, COLOR_YELLOW);
        st7789_draw_pixel(x + w / 2 + 1, y + 6, COLOR_YELLOW);
    }
}

/* ── BLE 状态图标绘制 ────────────────────── */
void ui_draw_ble_icon(int16_t x, int16_t y, bool connected, bool advertising)
{
    if (connected) {
        /* 已连接：实心蓝牙标志 + 高光 */
        ui_fill_rounded_rect(x, y, 10, 10, 2, COLOR_GREEN);
        st7789_draw_pixel(x + 3, y + 3, COLOR_BG);
        st7789_draw_pixel(x + 5, y + 5, COLOR_BG);
        st7789_draw_pixel(x + 7, y + 7, COLOR_BG);
    } else if (advertising) {
        /* 广播中：脉冲动画 */
        static uint8_t pulse = 0;
        pulse = (pulse + 1) % 4;
        uint16_t c = ui_color_brightness(COLOR_YELLOW, 128 + pulse * 42);
        ui_fill_rounded_rect(x, y, 10, 10, 2, c);
    } else {
        /* 未连接：暗色轮廓 */
        ui_draw_rounded_rect(x, y, 10, 10, 2, COLOR_DIM);
    }
}

/* ── 信号强度图标绘制 ────────────────────── */
void ui_draw_signal_icon(int16_t x, int16_t y, int8_t rssi)
{
    /* 信号强度等级: 0-4 */
    int level;
    if (rssi > -50) level = 4;
    else if (rssi > -60) level = 3;
    else if (rssi > -70) level = 2;
    else if (rssi > -80) level = 1;
    else level = 0;

    /* 绘制信号条 */
    for (int i = 0; i < 4; i++) {
        int16_t bar_h = 3 + i * 2;
        int16_t bar_y = y + 10 - bar_h;

        uint16_t color = (i < level) ? COLOR_GREEN : COLOR_DIM;
        st7789_fill_rect(x + i * 3, bar_y, x + i * 3 + 2, y + 10, color);
    }
}

/* ── 按键按下动画（非阻塞版） ────────────── */
void ui_animate_key_press(int16_t x, int16_t y, int16_t w, int16_t h, uint16_t color)
{
    /* 仅做一次高亮闪烁，由主循环负责恢复 */
    st7789_fill_rect(x, y, x + w - 1, y + h - 1, color);
    /* 边框加亮 */
    ui_draw_rounded_rect(x, y, w, h, 4, ui_color_brighten(color, 60));
}

/* ── Profile 切换动画 ────────────────────── */
void ui_animate_profile_switch(void)
{
    /* 从左向右滑动效果 */
    for (int16_t x = -LCD_W; x < 0; x += 20) {
        st7789_fill_screen(COLOR_BG);
        /* TODO: 绘制旧界面和新界面 */
        vTaskDelay(pdMS_TO_TICKS(16));
    }
}

/* ── 状态栏绘制 ──────────────────────────── */
void ui_draw_status_bar(int16_t y, const char *left_text, const char *right_text,
                        uint16_t color, uint16_t bg_color)
{
    /* 背景 */
    st7789_fill_rect(0, y, LCD_W - 1, y + 15, bg_color);

    /* 左侧文本 */
    if (left_text) {
        draw_string(4, y + 4, left_text, color, 1);
    }

    /* 右侧文本 */
    if (right_text) {
        int16_t tw = string_width(right_text, 1);
        draw_string(LCD_W - tw - 4, y + 4, right_text, color, 1);
    }
}

/* ── 信息卡片绘制 ────────────────────────── */
void ui_draw_info_card(int16_t x, int16_t y, int16_t w, int16_t h,
                       const char *title, const char *value, uint16_t color)
{
    /* 背景 */
    ui_fill_rounded_rect(x, y, w, h, 4, COLOR_CARD);

    /* 边框 */
    ui_draw_rounded_rect(x, y, w, h, 4, color);

    /* 标题 */
    if (title) {
        int16_t tw = string_width(title, 1);
        draw_string(x + (w - tw) / 2, y + 6, title, COLOR_DIM, 1);
    }

    /* 值 */
    if (value) {
        int16_t tw = string_width(value, 1);
        draw_string(x + (w - tw) / 2, y + 20, value, COLOR_TEXT, 1);
    }
}

/* ── 加载动画 ────────────────────────────── */
void ui_draw_loading(int16_t cx, int16_t cy, int16_t radius, uint16_t color)
{
    static int angle = 0;

    /* 绘制旋转点 */
    for (int i = 0; i < 8; i++) {
        int a = (angle + i * 45) % 360;
        float rad = a * 3.14159f / 180.0f;

        int16_t px = cx + (int16_t)(radius * cosf(rad));
        int16_t py = cy + (int16_t)(radius * sinf(rad));

        /* 渐变透明度 */
        uint8_t brightness = 255 - (i * 32);
        uint16_t c = ui_color_brightness(color, brightness);

        st7789_fill_rect(px - 1, py - 1, px + 1, py + 1, c);
    }

    angle = (angle + 15) % 360;
}
