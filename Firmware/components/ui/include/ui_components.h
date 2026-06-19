/**
 * AI Agent Deck - UI 组件头文件
 */

#pragma once

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ── 屏幕尺寸 ────────────────────────────── */
#ifndef LCD_W
#define LCD_W  240
#endif

#ifndef LCD_H
#define LCD_H  240
#endif

/* ── 颜色定义 ────────────────────────────── */
#define COLOR_BG        RGB565(15, 20, 35)
#define COLOR_CARD      RGB565(25, 32, 55)
#define COLOR_HEADER    RGB565(30, 40, 70)
#define COLOR_BORDER    RGB565(50, 60, 100)
#define COLOR_ACCENT    RGB565(240, 131, 58)
#define COLOR_CYAN      RGB565(13, 148, 136)
#define COLOR_TEXT      RGB565(200, 210, 235)
#define COLOR_DIM       RGB565(100, 115, 150)
#define COLOR_GREEN     RGB565(72, 199, 142)
#define COLOR_RED       RGB565(239, 68, 68)
#define COLOR_YELLOW    RGB565(245, 158, 11)
#define COLOR_PURPLE    RGB565(139, 92, 246)
#define COLOR_BLUE      RGB565(59, 130, 246)

/* ── 颜色工具 ────────────────────────────── */

/**
 * 线性插值混合两个颜色
 * @param c1 颜色1
 * @param c2 颜色2
 * @param t 插值因子 (0-255)
 * @return 混合后的颜色
 */
uint16_t ui_color_lerp(uint16_t c1, uint16_t c2, uint8_t t);

/**
 * 调整颜色亮度
 * @param color 原始颜色
 * @param brightness 亮度 (0-255)
 * @return 调整后的颜色
 */
uint16_t ui_color_brightness(uint16_t color, uint8_t brightness);

/* ── 渐变绘制 ────────────────────────────── */

/**
 * 绘制水平渐变矩形
 */
void ui_draw_gradient_h(int16_t x, int16_t y, int16_t w, int16_t h, uint16_t c1, uint16_t c2);

/**
 * 绘制垂直渐变矩形
 */
void ui_draw_gradient_v(int16_t x, int16_t y, int16_t w, int16_t h, uint16_t c1, uint16_t c2);

/* ── 圆角矩形绘制 ────────────────────────── */

/**
 * 绘制圆角矩形边框
 */
void ui_draw_rounded_rect(int16_t x, int16_t y, int16_t w, int16_t h, int16_t r, uint16_t color);

/**
 * 绘制填充圆角矩形
 */
void ui_fill_rounded_rect(int16_t x, int16_t y, int16_t w, int16_t h, int16_t r, uint16_t color);

/* ── 进度条绘制 ──────────────────────────── */

/**
 * 绘制进度条
 * @param x, y, w, h 位置和尺寸
 * @param progress 进度 (0-100)
 * @param color 进度条颜色
 * @param bg_color 背景颜色
 */
void ui_draw_progress_bar(int16_t x, int16_t y, int16_t w, int16_t h,
                          uint8_t progress, uint16_t color, uint16_t bg_color);

/* ── 图标绘制 ────────────────────────────── */

/**
 * 绘制电池图标
 * @param x, y 位置
 * @param level 电量 (0-100)
 * @param charging 是否充电中
 */
void ui_draw_battery_icon(int16_t x, int16_t y, uint8_t level, bool charging);

/**
 * 绘制 BLE 状态图标
 * @param x, y 位置
 * @param connected 是否已连接
 * @param advertising 是否广播中
 */
void ui_draw_ble_icon(int16_t x, int16_t y, bool connected, bool advertising);

/**
 * 绘制信号强度图标
 * @param x, y 位置
 * @param rssi 信号强度 (dBm)
 */
void ui_draw_signal_icon(int16_t x, int16_t y, int8_t rssi);

/* ── 动画效果 ────────────────────────────── */

/**
 * 按键按下动画
 * @param x, y, w, h 按键位置和尺寸
 * @param color 按键颜色
 */
void ui_animate_key_press(int16_t x, int16_t y, int16_t w, int16_t h, uint16_t color);

/**
 * Profile 切换动画
 */
void ui_animate_profile_switch(void);

/* ── 状态栏绘制 ──────────────────────────── */

/**
 * 绘制状态栏
 * @param y Y坐标
 * @param left_text 左侧文本
 * @param right_text 右侧文本
 * @param color 文本颜色
 * @param bg_color 背景颜色
 */
void ui_draw_status_bar(int16_t y, const char *left_text, const char *right_text,
                        uint16_t color, uint16_t bg_color);

/* ── 信息卡片绘制 ────────────────────────── */

/**
 * 绘制信息卡片
 * @param x, y, w, h 位置和尺寸
 * @param title 标题
 * @param value 值
 * @param color 边框颜色
 */
void ui_draw_info_card(int16_t x, int16_t y, int16_t w, int16_t h,
                       const char *title, const char *value, uint16_t color);

/* ── 加载动画 ────────────────────────────── */

/**
 * 绘制加载动画
 * @param cx, cy 中心位置
 * @param radius 半径
 * @param color 颜色
 */
void ui_draw_loading(int16_t cx, int16_t cy, int16_t radius, uint16_t color);

/* ── 字体绘制函数 (由 main.c 提供) ───────── */
/* 注意: 这些函数在 main.c 中定义，ui_components.c 中使用 */
void draw_char(int16_t x, int16_t y, char c, uint16_t color, uint8_t scale);
void draw_string(int16_t x, int16_t y, const char *str, uint16_t color, uint8_t scale);
int16_t string_width(const char *str, uint8_t scale);
void draw_string_centered(int16_t y, const char *str, uint16_t color, uint8_t scale);

#ifdef __cplusplus
}
#endif
