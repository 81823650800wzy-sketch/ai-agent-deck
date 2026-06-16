/**
 * AI Agent Deck - UI 框架实现 (伪3D版)
 * 参考 Neumorphism 设计风格
 */

#include <string.h>
#include <stdlib.h>
#include <math.h>
#include "ui.h"
#include "esp_log.h"

static const char *TAG = "UI";

/* ── 内部状态 ────────────────────────────── */
static int16_t screen_w, screen_h;
static ui_comp_t comp_pool[32];
static ui_anim_t anim_pool[16];
static uint16_t comp_idx = 0;
static uint16_t anim_idx = 0;

/* ── 初始化 ──────────────────────────────── */
void ui_init(int16_t w, int16_t h)
{
    screen_w = w;
    screen_h = h;
    comp_idx = 0;
    anim_idx = 0;
    memset(comp_pool, 0, sizeof(comp_pool));
    memset(anim_pool, 0, sizeof(anim_pool));
    ESP_LOGI(TAG, "UI initialized %dx%d", w, h);
}

void ui_clear(uint16_t color)
{
    st7789_fill_screen(color);
}

/* ── 组件分配 ────────────────────────────── */
static ui_comp_t *comp_alloc(void)
{
    if (comp_idx >= 32) {
        ESP_LOGE(TAG, "Component pool full!");
        return NULL;
    }
    ui_comp_t *c = &comp_pool[comp_idx++];
    memset(c, 0, sizeof(ui_comp_t));
    return c;
}

/* ── 组件创建 ────────────────────────────── */
ui_comp_t *ui_panel_3d_create(int16_t x, int16_t y, int16_t w, int16_t h, uint8_t depth)
{
    ui_comp_t *c = comp_alloc();
    if (!c) return NULL;
    c->type = UI_COMP_PANEL_3D;
    c->x = x; c->y = y; c->w = w; c->h = h;
    c->style.bg_color = UI_COLOR_BG;
    c->style.shadow_color = UI_COLOR_SHADOW;
    c->style.highlight_color = UI_COLOR_HIGHLIGHT;
    c->style.depth = depth;
    c->style.visible = true;
    c->dirty = true;
    return c;
}

ui_comp_t *ui_panel_inset_create(int16_t x, int16_t y, int16_t w, int16_t h, uint8_t depth)
{
    ui_comp_t *c = comp_alloc();
    if (!c) return NULL;
    c->type = UI_COMP_PANEL_INSET;
    c->x = x; c->y = y; c->w = w; c->h = h;
    c->style.bg_color = UI_COLOR_BG_DARK;
    c->style.shadow_color = UI_COLOR_SHADOW;
    c->style.highlight_color = UI_COLOR_HIGHLIGHT;
    c->style.depth = depth;
    c->style.visible = true;
    c->dirty = true;
    return c;
}

ui_comp_t *ui_button_3d_create(int16_t x, int16_t y, int16_t w, int16_t h, uint16_t color)
{
    ui_comp_t *c = comp_alloc();
    if (!c) return NULL;
    c->type = UI_COMP_BUTTON_3D;
    c->x = x; c->y = y; c->w = w; c->h = h;
    c->style.bg_color = color;
    c->style.shadow_color = ui_color_darken(color, 40);
    c->style.highlight_color = ui_color_brighten(color, 40);
    c->style.depth = 3;
    c->style.visible = true;
    c->dirty = true;
    return c;
}

ui_comp_t *ui_progress_3d_create(int16_t x, int16_t y, int16_t w, int16_t h, uint16_t fill_color)
{
    ui_comp_t *c = comp_alloc();
    if (!c) return NULL;
    c->type = UI_COMP_PROGRESS_3D;
    c->x = x; c->y = y; c->w = w; c->h = h;
    c->style.bg_color = UI_COLOR_BG_DARK;
    c->style.shadow_color = UI_COLOR_SHADOW;
    c->style.highlight_color = UI_COLOR_HIGHLIGHT;
    c->style.border_color = fill_color;
    c->style.depth = 2;
    c->style.visible = true;
    c->dirty = true;
    /* 存储进度值 */
    uint32_t *data = (uint32_t *)malloc(sizeof(uint32_t) * 2);
    if (data) {
        data[0] = 0;
        data[1] = fill_color;
        c->data = data;
    }
    return c;
}

ui_comp_t *ui_led_create(int16_t x, int16_t y, uint16_t color, bool on)
{
    ui_comp_t *c = comp_alloc();
    if (!c) return NULL;
    c->type = UI_COMP_LED;
    c->x = x; c->y = y; c->w = 12; c->h = 12;
    c->style.bg_color = color;
    c->style.visible = on;
    c->dirty = true;
    return c;
}

ui_comp_t *ui_gradient_create(int16_t x, int16_t y, int16_t w, int16_t h,
                               uint16_t color1, uint16_t color2, bool vertical)
{
    ui_comp_t *c = comp_alloc();
    if (!c) return NULL;
    c->type = UI_COMP_GRADIENT;
    c->x = x; c->y = y; c->w = w; c->h = h;
    c->style.bg_color = color1;
    c->style.gradient_color = color2;
    c->style.gradient = !vertical; /* horizontal */
    c->style.visible = true;
    c->dirty = true;
    return c;
}

/* ── 组件操作 ────────────────────────────── */
void ui_set_progress(ui_comp_t *comp, uint8_t value)
{
    if (!comp || !comp->data) return;
    uint32_t *data = (uint32_t *)comp->data;
    data[0] = value;
    comp->dirty = true;
}

void ui_set_led(ui_comp_t *comp, bool on)
{
    if (!comp) return;
    comp->style.visible = on;
    comp->dirty = true;
}

void ui_mark_dirty(ui_comp_t *comp)
{
    if (comp) comp->dirty = true;
}

/* ── 颜色工具 ────────────────────────────── */
uint16_t ui_color_lerp(uint16_t c1, uint16_t c2, uint8_t t)
{
    uint8_t r1 = (c1 >> 11) & 0x1F, g1 = (c1 >> 5) & 0x3F, b1 = c1 & 0x1F;
    uint8_t r2 = (c2 >> 11) & 0x1F, g2 = (c2 >> 5) & 0x3F, b2 = c2 & 0x1F;
    uint8_t r = r1 + ((int16_t)(r2 - r1) * t) / 255;
    uint8_t g = g1 + ((int16_t)(g2 - g1) * t) / 255;
    uint8_t b = b1 + ((int16_t)(b2 - b1) * t) / 255;
    return (r << 11) | (g << 5) | b;
}

uint16_t ui_color_brighten(uint16_t c, uint8_t amount)
{
    uint8_t r = ((c >> 11) & 0x1F) + amount;
    uint8_t g = ((c >> 5) & 0x3F) + amount;
    uint8_t b = (c & 0x1F) + amount;
    if (r > 31) r = 31;
    if (g > 63) g = 63;
    if (b > 31) b = 31;
    return (r << 11) | (g << 5) | b;
}

uint16_t ui_color_darken(uint16_t c, uint8_t amount)
{
    int16_t r = ((c >> 11) & 0x1F) - amount;
    int16_t g = ((c >> 5) & 0x3F) - amount;
    int16_t b = (c & 0x1F) - amount;
    if (r < 0) r = 0;
    if (g < 0) g = 0;
    if (b < 0) b = 0;
    return (r << 11) | (g << 5) | b;
}

/* ── 渐变绘制 ────────────────────────────── */
void ui_draw_gradient_h(int16_t x, int16_t y, int16_t w, int16_t h,
                         uint16_t c1, uint16_t c2)
{
    for (int16_t i = 0; i < w; i++) {
        uint8_t t = (w > 1) ? (i * 255) / (w - 1) : 0;
        st7789_fill_rect(x + i, y, x + i, y + h - 1, ui_color_lerp(c1, c2, t));
    }
}

void ui_draw_gradient_v(int16_t x, int16_t y, int16_t w, int16_t h,
                         uint16_t c1, uint16_t c2)
{
    for (int16_t i = 0; i < h; i++) {
        uint8_t t = (h > 1) ? (i * 255) / (h - 1) : 0;
        st7789_fill_rect(x, y + i, x + w - 1, y + i, ui_color_lerp(c1, c2, t));
    }
}

void ui_draw_gradient_rect(int16_t x, int16_t y, int16_t w, int16_t h,
                            uint16_t c1, uint16_t c2, uint16_t c3, uint16_t c4)
{
    /* 四角渐变 (双线性插值) */
    for (int16_t j = 0; j < h; j++) {
        uint8_t ty = (h > 1) ? (j * 255) / (h - 1) : 0;
        uint16_t left = ui_color_lerp(c1, c3, ty);
        uint16_t right = ui_color_lerp(c2, c4, ty);
        for (int16_t i = 0; i < w; i++) {
            uint8_t tx = (w > 1) ? (i * 255) / (w - 1) : 0;
            st7789_draw_pixel(x + i, y + j, ui_color_lerp(left, right, tx));
        }
    }
}

/* ── 伪3D 绘制原语 ──────────────────────── */
void ui_draw_3d_panel(int16_t x, int16_t y, int16_t w, int16_t h,
                       uint16_t bg, uint8_t depth, bool inset)
{
    if (depth == 0) depth = 1;
    if (depth > UI_DEPTH_LEVELS) depth = UI_DEPTH_LEVELS;

    uint16_t shadow = ui_color_darken(bg, 30 + depth * 8);
    uint16_t highlight = ui_color_brighten(bg, 25 + depth * 6);

    /* 背景 */
    st7789_fill_rect(x, y, x + w - 1, y + h - 1, bg);

    if (inset) {
        /* 内凹效果: 左上暗，右下亮 */
        for (int i = 0; i < depth; i++) {
            /* 上边 - 暗 */
            st7789_fill_rect(x + i, y + i, x + w - 2 - i, y + i, shadow);
            /* 左边 - 暗 */
            st7789_fill_rect(x + i, y + i, x + i, y + h - 2 - i, shadow);
            /* 下边 - 亮 */
            st7789_fill_rect(x + i + 1, y + h - 1 - i, x + w - 1 - i, y + h - 1 - i, highlight);
            /* 右边 - 亮 */
            st7789_fill_rect(x + w - 1 - i, y + i + 1, x + w - 1 - i, y + h - 1 - i, highlight);
        }
    } else {
        /* 外凸效果: 左上亮，右下暗 */
        for (int i = 0; i < depth; i++) {
            /* 上边 - 亮 */
            st7789_fill_rect(x + i, y + i, x + w - 2 - i, y + i, highlight);
            /* 左边 - 亮 */
            st7789_fill_rect(x + i, y + i, x + i, y + h - 2 - i, highlight);
            /* 下边 - 暗 */
            st7789_fill_rect(x + i + 1, y + h - 1 - i, x + w - 1 - i, y + h - 1 - i, shadow);
            /* 右边 - 暗 */
            st7789_fill_rect(x + w - 1 - i, y + i + 1, x + w - 1 - i, y + h - 1 - i, shadow);
        }
    }
}

void ui_draw_3d_button(int16_t x, int16_t y, int16_t w, int16_t h,
                        uint16_t color, bool pressed)
{
    uint16_t shadow = ui_color_darken(color, 50);
    uint16_t highlight = ui_color_brighten(color, 50);
    uint16_t bg = pressed ? ui_color_darken(color, 20) : color;

    /* 背景 */
    st7789_fill_rect(x, y, x + w - 1, y + h - 1, bg);

    if (pressed) {
        /* 按下状态: 内凹 */
        st7789_fill_rect(x, y, x + w - 2, y, shadow);
        st7789_fill_rect(x, y, x, y + h - 2, shadow);
        st7789_fill_rect(x + 1, y + h - 1, x + w - 1, y + h - 1, highlight);
        st7789_fill_rect(x + w - 1, y + 1, x + w - 1, y + h - 1, highlight);
    } else {
        /* 正常状态: 外凸 */
        st7789_fill_rect(x, y, x + w - 2, y, highlight);
        st7789_fill_rect(x, y, x, y + h - 2, highlight);
        st7789_fill_rect(x + 1, y + h - 1, x + w - 1, y + h - 1, shadow);
        st7789_fill_rect(x + w - 1, y + 1, x + w - 1, y + h - 1, shadow);
    }
}

void ui_draw_3d_progress(int16_t x, int16_t y, int16_t w, int16_t h,
                          uint16_t fill_color, uint8_t value)
{
    /* 内凹轨道 */
    ui_draw_3d_panel(x, y, w, h, UI_COLOR_BG_DARK, 2, true);

    /* 填充条 */
    int16_t fill_w = ((w - 4) * value) / 100;
    if (fill_w > 0) {
        uint16_t fill_start = ui_color_darken(fill_color, 20);
        uint16_t fill_end = ui_color_brighten(fill_color, 30);
        ui_draw_gradient_h(x + 2, y + 2, fill_w, h - 4, fill_start, fill_end);

        /* 高光条 */
        st7789_fill_rect(x + 2, y + 2, x + 2 + fill_w - 1, y + 2,
                         ui_color_brighten(fill_color, 60));
    }
}

void ui_draw_led(int16_t x, int16_t y, uint16_t color, bool on)
{
    if (!on) {
        /* 关闭状态: 暗灰色 */
        st7789_fill_rect(x, y, x + 11, y + 11, RGB565(30, 30, 40));
        return;
    }

    /* 外圈暗 */
    st7789_fill_rect(x, y, x + 11, y + 11, ui_color_darken(color, 60));
    /* 内圈亮 */
    st7789_fill_rect(x + 2, y + 2, x + 9, y + 9, color);
    /* 高光点 */
    st7789_fill_rect(x + 3, y + 3, x + 5, y + 5, ui_color_brighten(color, 80));
}

/* ── 组件绘制 ────────────────────────────── */
void ui_draw_comp(ui_comp_t *comp)
{
    if (!comp || !comp->style.visible) return;

    switch (comp->type) {
        case UI_COMP_PANEL_3D:
            ui_draw_3d_panel(comp->x, comp->y, comp->w, comp->h,
                            comp->style.bg_color, comp->style.depth, false);
            break;

        case UI_COMP_PANEL_INSET:
            ui_draw_3d_panel(comp->x, comp->y, comp->w, comp->h,
                            comp->style.bg_color, comp->style.depth, true);
            break;

        case UI_COMP_BUTTON_3D:
            ui_draw_3d_button(comp->x, comp->y, comp->w, comp->h,
                             comp->style.bg_color, false);
            break;

        case UI_COMP_PROGRESS_3D:
            if (comp->data) {
                uint32_t *data = (uint32_t *)comp->data;
                ui_draw_3d_progress(comp->x, comp->y, comp->w, comp->h,
                                   data[1], data[0]);
            }
            break;

        case UI_COMP_LED:
            ui_draw_led(comp->x, comp->y, comp->style.bg_color, comp->style.visible);
            break;

        case UI_COMP_GRADIENT:
            if (comp->style.gradient) {
                ui_draw_gradient_h(comp->x, comp->y, comp->w, comp->h,
                                  comp->style.bg_color, comp->style.gradient_color);
            } else {
                ui_draw_gradient_v(comp->x, comp->y, comp->w, comp->h,
                                  comp->style.bg_color, comp->style.gradient_color);
            }
            break;

        default:
            st7789_fill_rect(comp->x, comp->y,
                            comp->x + comp->w - 1, comp->y + comp->h - 1,
                            comp->style.bg_color);
            break;
    }

    comp->dirty = false;
}

void ui_update(void)
{
    for (int i = 0; i < comp_idx; i++) {
        if (comp_pool[i].dirty) {
            ui_draw_comp(&comp_pool[i]);
        }
    }
}

/* ── 动画系统 ────────────────────────────── */
float ui_ease_func(ui_ease_t type, float t)
{
    switch (type) {
        case EASE_LINEAR:
            return t;
        case EASE_IN_OUT:
            return t < 0.5f ? 2.0f * t * t : 1.0f - (-2.0f * t + 2.0f) * (-2.0f * t + 2.0f) / 2.0f;
        case EASE_BOUNCE: {
            if (t < 1.0f / 2.75f) {
                return 7.5625f * t * t;
            } else if (t < 2.0f / 2.75f) {
                t -= 1.5f / 2.75f;
                return 7.5625f * t * t + 0.75f;
            } else if (t < 2.5f / 2.75f) {
                t -= 2.25f / 2.75f;
                return 7.5625f * t * t + 0.9375f;
            } else {
                t -= 2.625f / 2.75f;
                return 7.5625f * t * t + 0.984375f;
            }
        }
        case EASE_ELASTIC: {
            if (t == 0.0f || t == 1.0f) return t;
            return -(float)pow(2, 10 * (t - 1)) * (float)sin((t - 1.1f) * 5 * 3.14159f);
        }
        default:
            return t;
    }
}

ui_anim_t *ui_anim_create(float *value, float to, uint16_t duration_ms, ui_ease_t ease)
{
    if (anim_idx >= 16) return NULL;
    ui_anim_t *a = &anim_pool[anim_idx++];
    a->value = value;
    a->from = *value;
    a->to = to;
    a->duration_ms = duration_ms;
    a->elapsed_ms = 0;
    a->ease = ease;
    a->active = true;
    a->loop = false;
    return a;
}

void ui_anim_update(uint16_t delta_ms)
{
    for (int i = 0; i < anim_idx; i++) {
        ui_anim_t *a = &anim_pool[i];
        if (!a->active || !a->value) continue;

        a->elapsed_ms += delta_ms;
        if (a->elapsed_ms >= a->duration_ms) {
            if (a->loop) {
                a->elapsed_ms = 0;
                float temp = a->from;
                a->from = a->to;
                a->to = temp;
            } else {
                *a->value = a->to;
                a->active = false;
            }
        } else {
            float t = (float)a->elapsed_ms / a->duration_ms;
            float eased = ui_ease_func(a->ease, t);
            *a->value = a->from + (a->to - a->from) * eased;
        }
    }
}

void ui_anim_stop(ui_anim_t *anim)
{
    if (anim) anim->active = false;
}
