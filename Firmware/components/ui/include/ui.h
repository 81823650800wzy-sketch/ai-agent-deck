/**
 * AI Agent Deck - UI 框架 (伪3D版)
 * 参考 Neumorphism / Glassmorphism 设计风格
 *
 * 特性:
 *   - 伪3D 效果 (阴影 + 高光 + 内凹/外凸)
 *   - 渐变背景 (模拟光照方向)
 *   - 动画系统 (缓动函数)
 */

#pragma once
#include <stdint.h>
#include <stdbool.h>
#include "st7789.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ── 颜色主题 (Neumorphism 风格) ─────────── */
#define UI_COLOR_BG           RGB565(40, 45, 65)      /* 主背景 */
#define UI_COLOR_BG_DARK      RGB565(30, 35, 55)      /* 深色背景 */
#define UI_COLOR_SHADOW       RGB565(20, 25, 40)      /* 阴影色 */
#define UI_COLOR_HIGHLIGHT    RGB565(60, 68, 100)      /* 高光色 */
#define UI_COLOR_ACCENT       RGB565(240, 131, 58)     /* 橙色强调 */
#define UI_COLOR_ACCENT_CYAN  RGB565(13, 188, 170)     /* 青色强调 */
#define UI_COLOR_TEXT         RGB565(200, 210, 235)     /* 主文字 */
#define UI_COLOR_TEXT_DIM     RGB565(100, 115, 150)     /* 暗文字 */
#define UI_COLOR_GREEN        RGB565(72, 199, 142)      /* 绿色状态 */
#define UI_COLOR_RED          RGB565(239, 68, 68)       /* 红色警告 */
#define UI_COLOR_PURPLE       RGB565(139, 92, 246)      /* 紫色 */
#define UI_COLOR_BLUE         RGB565(59, 130, 246)      /* 蓝色 */
#define UI_COLOR_ORANGE       RGB565(245, 158, 11)      /* 橙色 */

/* ── 伪3D 效果参数 ──────────────────────── */
#define UI_SHADOW_OFFSET    3       /* 阴影偏移量 */
#define UI_HIGHLIGHT_SIZE   2       /* 高光宽度 */
#define UI_DEPTH_LEVELS     5       /* 深度层级 */

/* ── 组件类型 ────────────────────────────── */
typedef enum {
    UI_COMP_RECT,           /* 普通矩形 */
    UI_COMP_PANEL_3D,       /* 伪3D面板 (外凸) */
    UI_COMP_PANEL_INSET,    /* 伪3D面板 (内凹) */
    UI_COMP_BUTTON_3D,      /* 伪3D按钮 */
    UI_COMP_PROGRESS_3D,    /* 伪3D进度条 */
    UI_COMP_LED,            /* 状态指示灯 */
    UI_COMP_GRADIENT,       /* 渐变面板 */
} ui_comp_type_t;

/* ── 缓动函数类型 ────────────────────────── */
typedef enum {
    EASE_LINEAR,
    EASE_IN_OUT,
    EASE_BOUNCE,
    EASE_ELASTIC,
} ui_ease_t;

/* ── 样式结构 ────────────────────────────── */
typedef struct {
    uint16_t bg_color;          /* 背景色 */
    uint16_t shadow_color;      /* 阴影色 */
    uint16_t highlight_color;   /* 高光色 */
    uint16_t border_color;      /* 边框色 */
    uint8_t  depth;             /* 3D深度 (0-5) */
    uint8_t  radius;            /* 圆角 (0=直角) */
    bool     gradient;          /* 是否渐变 */
    uint16_t gradient_color;    /* 渐变目标色 */
    bool     visible;
} ui_style_t;

/* ── 组件结构 ────────────────────────────── */
typedef struct ui_comp {
    ui_comp_type_t type;
    int16_t x, y, w, h;
    ui_style_t style;
    bool dirty;
    void *data;
    void (*on_draw)(struct ui_comp *comp);
} ui_comp_t;

/* ── 动画结构 ────────────────────────────── */
typedef struct {
    float *value;               /* 目标值指针 */
    float from, to;             /* 起始/结束值 */
    uint16_t duration_ms;
    uint16_t elapsed_ms;
    ui_ease_t ease;
    bool active;
    bool loop;                  /* 是否循环 */
} ui_anim_t;

/* ── API ─────────────────────────────────── */

/* 初始化 */
void ui_init(int16_t w, int16_t h);
void ui_clear(uint16_t color);

/* 组件创建 */
ui_comp_t *ui_panel_3d_create(int16_t x, int16_t y, int16_t w, int16_t h, uint8_t depth);
ui_comp_t *ui_panel_inset_create(int16_t x, int16_t y, int16_t w, int16_t h, uint8_t depth);
ui_comp_t *ui_button_3d_create(int16_t x, int16_t y, int16_t w, int16_t h, uint16_t color);
ui_comp_t *ui_progress_3d_create(int16_t x, int16_t y, int16_t w, int16_t h, uint16_t fill_color);
ui_comp_t *ui_led_create(int16_t x, int16_t y, uint16_t color, bool on);
ui_comp_t *ui_gradient_create(int16_t x, int16_t y, int16_t w, int16_t h,
                               uint16_t color1, uint16_t color2, bool vertical);

/* 组件操作 */
void ui_set_progress(ui_comp_t *comp, uint8_t value);
void ui_set_led(ui_comp_t *comp, bool on);
void ui_mark_dirty(ui_comp_t *comp);

/* 绘制 */
void ui_draw_comp(ui_comp_t *comp);
void ui_update(void);

/* 渐变绘制 */
void ui_draw_gradient_h(int16_t x, int16_t y, int16_t w, int16_t h,
                         uint16_t c1, uint16_t c2);
void ui_draw_gradient_v(int16_t x, int16_t y, int16_t w, int16_t h,
                         uint16_t c1, uint16_t c2);
void ui_draw_gradient_rect(int16_t x, int16_t y, int16_t w, int16_t h,
                            uint16_t c1, uint16_t c2, uint16_t c3, uint16_t c4);

/* 伪3D 绘制原语 */
void ui_draw_3d_panel(int16_t x, int16_t y, int16_t w, int16_t h,
                       uint16_t bg, uint8_t depth, bool inset);
void ui_draw_3d_button(int16_t x, int16_t y, int16_t w, int16_t h,
                        uint16_t color, bool pressed);
void ui_draw_3d_progress(int16_t x, int16_t y, int16_t w, int16_t h,
                          uint16_t fill_color, uint8_t value);
void ui_draw_led(int16_t x, int16_t y, uint16_t color, bool on);

/* 颜色工具 */
uint16_t ui_color_lerp(uint16_t c1, uint16_t c2, uint8_t t);
uint16_t ui_color_brighten(uint16_t c, uint8_t amount);
uint16_t ui_color_darken(uint16_t c, uint8_t amount);

/* 动画 */
ui_anim_t *ui_anim_create(float *value, float to, uint16_t duration_ms, ui_ease_t ease);
void ui_anim_update(uint16_t delta_ms);
void ui_anim_stop(ui_anim_t *anim);
float ui_ease_func(ui_ease_t type, float t);

#ifdef __cplusplus
}
#endif
