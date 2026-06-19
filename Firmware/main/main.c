/**
 * AI Agent Deck V2.0 - Context-Aware Workflow Controller
 *
 * 功能:
 *   - BLE HID 键盘 (F13-F18)
 *   - BLE Profile 接收 (自动切换按键映射)
 *   - 实时 UI 显示当前 Profile
 *
 * 接线:
 *   屏幕: MOSI→GPIO11  SCLK→GPIO12  CS→GPIO10
 *         DC→GPIO9     RST→GPIO8    BL→GPIO21
 *   按键: ROW1→GPIO4   ROW2→GPIO5   ROW3→GPIO6
 *         COL1→GPIO7   COL2→GPIO15
 */

#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_system.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "driver/gpio.h"
#include "driver/uart.h"
#include "esp_timer.h"
#include "esp_hidd.h"
#include "esp_hid_gap.h"
#include "st7789.h"
#include "font5x7.h"
#include "profile_receiver.h"
#include "ui_components.h"
#include "ui.h"
#include "wallpaper.h"
#include "wifi_ctrl.h"
#include "cJSON.h"

/* WiFi 状态字符串 */
static const char* wifi_status_str(void)
{
    if (wifi_ctrl_is_connected()) return "Connected";
    return "Connecting...";
}

static const char *TAG = "AI_DECK";

/* ── 引脚定义 ────────────────────────────── */
#define PIN_MOSI  GPIO_NUM_11
#define PIN_SCLK  GPIO_NUM_12
#define PIN_CS    GPIO_NUM_10
#define PIN_DC    GPIO_NUM_9
#define PIN_RST   GPIO_NUM_8
#define PIN_BL    GPIO_NUM_21
#define ROW1_PIN  GPIO_NUM_4
#define ROW2_PIN  GPIO_NUM_5
#define ROW3_PIN  GPIO_NUM_6
#define COL1_PIN  GPIO_NUM_7
#define COL2_PIN  GPIO_NUM_15

/* ── 屏幕尺寸 ────────────────────────────── */
#define LCD_W  240
#define LCD_H  240

/* ── 按键颜色表 (每个按键独立颜色) ────────── */
static const uint16_t key_colors[PROFILE_MAX_KEYS] = {
    COLOR_GREEN, COLOR_PURPLE, COLOR_BLUE,
    COLOR_YELLOW, COLOR_RED, COLOR_DIM,
};

/* ── 按键矩阵 ────────────────────────────── */
static const gpio_num_t row_pins[] = {ROW1_PIN, ROW2_PIN, ROW3_PIN};
static const gpio_num_t col_pins[] = {COL1_PIN, COL2_PIN};
#define ROW_COUNT 3
#define COL_COUNT 2
static bool key_pressed[ROW_COUNT][COL_COUNT] = {0};

/* ── 按键消抖 ────────────────────────────── */
#define DEBOUNCE_MS  50

/* ── 待机动画状态 ────────────────────────── */
static bool screen_dirty = true;  /* 标记屏幕需要刷新 */
static volatile bool s_upload_in_progress = false; /* 壁纸上传中，暂停刷新 */

/* ── HID 修饰键定义 ──────────────────────── */
#define MOD_CTRL    0x01
#define MOD_SHIFT   0x02
#define MOD_ALT     0x04
#define MOD_WIN     0x08

/* ── F13-F18 HID 键码 (固定，PC 端翻译) ─── */
static const uint8_t fkey_codes[PROFILE_MAX_KEYS] = {
    0x68,  /* F13 */
    0x69,  /* F14 */
    0x6A,  /* F15 */
    0x6B,  /* F16 */
    0x6C,  /* F17 */
    0x6D,  /* F18 */
};

/* ── BLE HID 状态 ────────────────────────── */
static esp_hidd_dev_t *hid_dev = NULL;
static bool ble_connected = false;
static bool ble_advertising = false;

/* ── HID Report Map (键盘) ───────────────── */
static const uint8_t keyboard_report_map[] = {
    0x05, 0x01,        // Usage Page (Generic Desktop)
    0x09, 0x06,        // Usage (Keyboard)
    0xA1, 0x01,        // Collection (Application)
    0x85, 0x01,        //   Report ID (1)
    0x05, 0x07,        //   Usage Page (Kbrd/Keypad)
    0x19, 0xE0,        //   Usage Minimum (0xE0)
    0x29, 0xE7,        //   Usage Maximum (0xE7)
    0x15, 0x00,        //   Logical Minimum (0)
    0x25, 0x01,        //   Logical Maximum (1)
    0x75, 0x01,        //   Report Size (1)
    0x95, 0x08,        //   Report Count (8)
    0x81, 0x02,        //   Input (Data,Var,Abs)
    0x95, 0x01,        //   Report Count (1)
    0x75, 0x08,        //   Report Size (8)
    0x81, 0x03,        //   Input (Const,Var,Abs)
    0x95, 0x06,        //   Report Count (6)
    0x75, 0x08,        //   Report Size (8)
    0x15, 0x00,        //   Logical Minimum (0)
    0x25, 0x65,        //   Logical Maximum (101)
    0x05, 0x07,        //   Usage Page (Kbrd/Keypad)
    0x19, 0x00,        //   Usage Minimum (0x00)
    0x29, 0x65,        //   Usage Maximum (0x65)
    0x81, 0x00,        //   Input (Data,Array,Abs)
    0xC0,              // End Collection
};

static esp_hid_raw_report_map_t ble_report_maps[] = {
    {.data = keyboard_report_map, .len = sizeof(keyboard_report_map)},
};

static esp_hid_device_config_t ble_hid_config = {
    .vendor_id = 0x1234,
    .product_id = 0x5678,
    .version = 0x0100,
    .device_name = "AI Agent Deck",
    .manufacturer_name = "AI-Deck",
    .serial_number = "00000001",
    .report_maps = ble_report_maps,
    .report_maps_len = 1,
};

/* ── 字体绘制 ────────────────────────────── */
void draw_char(int16_t x, int16_t y, char c, uint16_t color, uint8_t scale)
{
    if (c < 32 || c > 127) c = '?';
    const uint8_t *glyph = font5x7[c - 32];
    for (int col = 0; col < 5; col++) {
        uint8_t line = glyph[col];
        for (int row = 0; row < 7; row++) {
            if (line & (1 << row)) {
                for (int sy = 0; sy < scale; sy++) {
                    for (int sx = 0; sx < scale; sx++) {
                        int16_t px = x + col * scale + sx;
                        int16_t py = y + row * scale + sy;
                        if (px >= 0 && px < LCD_W && py >= 0 && py < LCD_H) {
                            st7789_draw_pixel(px, py, color);
                        }
                    }
                }
            }
        }
    }
}

void draw_string(int16_t x, int16_t y, const char *str, uint16_t color, uint8_t scale)
{
    while (*str) {
        draw_char(x, y, *str, color, scale);
        x += 6 * scale;
        str++;
    }
}

int16_t string_width(const char *str, uint8_t scale)
{
    int16_t len = 0;
    while (*str) { len++; str++; }
    return len * 6 * scale;
}

void draw_string_centered(int16_t y, const char *str, uint16_t color, uint8_t scale)
{
    int16_t w = string_width(str, scale);
    draw_string((LCD_W - w) / 2, y, str, color, scale);
}

/* ── 初始化按键矩阵 ──────────────────────── */
static void matrix_init(void)
{
    for (int i = 0; i < ROW_COUNT; i++) {
        gpio_config_t io = {
            .pin_bit_mask = 1ULL << row_pins[i],
            .mode = GPIO_MODE_OUTPUT,
            .pull_up_en = GPIO_PULLUP_DISABLE,
            .pull_down_en = GPIO_PULLDOWN_DISABLE,
            .intr_type = GPIO_INTR_DISABLE,
        };
        gpio_config(&io);
        gpio_set_level(row_pins[i], 1);
    }
    for (int i = 0; i < COL_COUNT; i++) {
        gpio_config_t io = {
            .pin_bit_mask = 1ULL << col_pins[i],
            .mode = GPIO_MODE_INPUT,
            .pull_up_en = GPIO_PULLUP_ENABLE,
            .pull_down_en = GPIO_PULLDOWN_DISABLE,
            .intr_type = GPIO_INTR_DISABLE,
        };
        gpio_config(&io);
    }
}

static void matrix_scan(void)
{
    for (int r = 0; r < ROW_COUNT; r++) {
        gpio_set_level(row_pins[r], 0);
        esp_rom_delay_us(5);
        for (int c = 0; c < COL_COUNT; c++) {
            key_pressed[r][c] = (gpio_get_level(col_pins[c]) == 0);
        }
        gpio_set_level(row_pins[r], 1);
    }
}

/* ── BLE 事件处理 ────────────────────────── */
static void gap_event_handler(esp_gap_ble_cb_event_t event, esp_ble_gap_cb_param_t *param)
{
    /* 安全相关事件 */
    if (event == ESP_GAP_BLE_SEC_REQ_EVT) {
        esp_ble_gap_security_rsp(param->ble_security.ble_req.bd_addr, true);
    } else if (event == ESP_GAP_BLE_NC_REQ_EVT) {
        esp_ble_confirm_reply(param->ble_security.ble_req.bd_addr, true);
    }

    /* 转发给 GAP 模块处理广播事件 */
    esp_hid_gap_event_handler(event, param);
}

static void ble_hidd_event_callback(void *handler_args, esp_event_base_t base, int32_t id, void *event_data)
{
    esp_hidd_event_t event = (esp_hidd_event_t)id;
    esp_hidd_event_data_t *param = (esp_hidd_event_data_t *)event_data;

    switch (event) {
        case ESP_HIDD_START_EVENT:
            esp_hid_ble_gap_adv_start();
            ble_advertising = true;
            break;
        case ESP_HIDD_CONNECT_EVENT:
            ble_connected = true;
            ble_advertising = false;
            break;
        case ESP_HIDD_DISCONNECT_EVENT:
            ble_connected = false;
            esp_hid_ble_gap_adv_start();
            ble_advertising = true;
            break;
        default:
            break;
    }
}

/* ── 统一 GATTS 回调 (HID + Profile) ─────── */
static void unified_gatts_handler(esp_gatts_cb_event_t event,
                                   esp_gatt_if_t gatts_if,
                                   esp_ble_gatts_cb_param_t *param)
{
    /* 调试: 打印所有事件 */
    if (event == ESP_GATTS_WRITE_EVT || event == ESP_GATTS_READ_EVT ||
        event == ESP_GATTS_CONNECT_EVT || event == ESP_GATTS_DISCONNECT_EVT ||
        event == ESP_GATTS_MTU_EVT) {
        ESP_LOGI("UNIFIED", "Event=%d gatts_if=%d", event, gatts_if);
    }

    /* 先转发给 HID 处理 */
    esp_hidd_gatts_event_handler(event, gatts_if, param);

    /* 再转发给 Profile 处理 */
    profile_gatts_handler(event, gatts_if, param);
}

/* ── 初始化 BLE HID ──────────────────────── */
static void ble_hid_init(void)
{
    esp_hid_gap_init(HIDD_BLE_MODE);
    esp_ble_gap_register_callback(gap_event_handler);
    esp_hid_ble_gap_adv_init(ESP_HID_APPEARANCE_KEYBOARD, ble_hid_config.device_name);
    esp_ble_gatts_register_callback(unified_gatts_handler);
    esp_hidd_dev_init(&ble_hid_config, ESP_HID_TRANSPORT_BLE, ble_hidd_event_callback, &hid_dev);
}

/* ── 发送按键 (F13-F18) ──────────────────── */
/* 返回 true 表示已通过 BLE 发送，false 表示未连接 */
static bool send_keyboard_key(uint8_t modifier, uint8_t keycode)
{
    if (!ble_connected || !hid_dev) return false;

    uint8_t buffer[8] = {modifier, 0, keycode, 0, 0, 0, 0, 0};
    esp_hidd_dev_input_set(hid_dev, 0, 1, buffer, 8);
    vTaskDelay(pdMS_TO_TICKS(30));
    memset(buffer, 0, sizeof(buffer));
    esp_hidd_dev_input_set(hid_dev, 0, 1, buffer, 8);
    return true;
}

/* ═══════════════════════════════════════════════
 *  UI 绘制 — 多界面液态玻璃系统
 * ═══════════════════════════════════════════════ */

/* ── 屏幕管理器 ──────────────────────────── */
#define SCREEN_COUNT    3
static int current_screen = 0;
static int last_screen = -1;        /* 上一次绘制的界面，用于避免重绘 */
static bool wallpaper_dirty = true; /* 壁纸是否需要重绘 */

/* 屏幕名称 */
static const char *screen_names[SCREEN_COUNT] = {
    "KEYS", "STATUS", "WALLPAPER"
};

/* ── 壁纸绘制 ────────────────────────────── */
static void draw_default_wallpaper(void)
{
    for (int16_t y = 0; y < LCD_H; y++) {
        uint8_t t = (y * 255) / LCD_H;
        uint16_t c = ui_color_lerp(RGB565(8, 10, 25), RGB565(18, 8, 32), t);
        st7789_fill_rect(0, y, LCD_W - 1, y, c);
    }
    for (int16_t gx = 0; gx < LCD_W; gx += 20) {
        for (int16_t gy = 0; gy < LCD_H; gy += 20) {
            st7789_draw_pixel(gx, gy, RGB565(25, 30, 55));
        }
    }
}

static void draw_wallpaper(void)
{
    if (!wallpaper_dirty) return;

    wallpaper_t *wp = wallpaper_get();
    if (wp->type != WP_TYPE_NONE) {
        wallpaper_draw();
    } else {
        draw_default_wallpaper();
    }
    wallpaper_dirty = false;
}

/* ── 液态玻璃组件 ────────────────────────── */

/* 25% 透明度玻璃背景色（深色壁纸上近似效果） */
#define GLASS_BG        RGB565(16, 18, 36)
#define GLASS_BORDER    RGB565(50, 60, 100)
#define GLASS_HIGHLIGHT RGB565(70, 85, 140)
#define GLASS_SHADOW    RGB565(25, 30, 55)
#define TEXT_PRIMARY     RGB565(200, 210, 235)
#define TEXT_DIM         RGB565(90, 105, 140)
#define TEXT_ACCENT      RGB565(160, 155, 254)

/* 玻璃面板（通用） */
static void draw_glass_panel(int x, int y, int w, int h, int r)
{
    ui_fill_rounded_rect(x, y, w, h, r, GLASS_BG);
    /* 顶高光 */
    ui_draw_gradient_h(x + r, y + 1, w - 2 * r, 1, GLASS_HIGHLIGHT, GLASS_SHADOW);
    /* 底暗边 */
    ui_draw_gradient_h(x + r, y + h - 2, w - 2 * r, 1, GLASS_SHADOW, RGB565(18, 22, 42));
}

/* ── 标题栏 ──────────────────────────────── */
void draw_header(void)
{
    draw_glass_panel(4, 3, LCD_W - 8, 24, 12);

    const char *title = screen_names[current_screen];
    draw_string_centered(9, title, TEXT_PRIMARY, 2);

    /* 页码指示器 */
    char page[16];
    snprintf(page, sizeof(page), "%d/%d", current_screen + 1, SCREEN_COUNT);
    int16_t pw = string_width(page, 1);
    draw_string(LCD_W - pw - 10, 11, page, TEXT_DIM, 1);

    /* BLE 状态点 */
    uint16_t c = ble_connected ? RGB565(72, 199, 142) : RGB565(80, 90, 120);
    st7789_fill_rect(8, 11, 12, 15, c);

    /* WiFi 状态点 */
    uint16_t wc = wifi_ctrl_is_connected() ? RGB565(72, 199, 142) : RGB565(80, 90, 120);
    st7789_fill_rect(16, 11, 20, 15, wc);
}

/* ── 底栏 ────────────────────────────────── */
void draw_footer(void)
{
    draw_glass_panel(4, LCD_H - 22, LCD_W - 8, 19, 10);

    /* 左：Profile */
    if (g_current_profile.valid) {
        draw_string(10, LCD_H - 16, g_current_profile.name, TEXT_DIM, 1);
    }

    /* 右：按键数 */
    char ks[8];
    snprintf(ks, sizeof(ks), "%dK", g_current_profile.key_count);
    int16_t kw = string_width(ks, 1);
    draw_string(LCD_W - kw - 10, LCD_H - 16, ks, TEXT_DIM, 1);
}

/* ═══════════════════════════════════════════════
 *  SCREEN 0: 按键卡片（液态玻璃，3列2行布局）
 * ═══════════════════════════════════════════════ */

/* 卡片布局参数 */
#define CARD_COLS   3
#define CARD_ROWS   2
#define CARD_GAP    6
#define CARD_H      55

static void draw_key_card(int x, int y, int w, int h, int key_index, bool pressed)
{
    if (key_index >= g_current_profile.key_count) return;

    const profile_key_t *key = &g_current_profile.keys[key_index];
    uint16_t accent = key_colors[key_index % PROFILE_MAX_KEYS];

    if (pressed) {
        ui_fill_rounded_rect(x, y, w, h, 10, accent);
        ui_draw_gradient_h(x + 2, y + 1, w - 4, 1,
                            ui_color_brighten(accent, 60), accent);
    } else {
        draw_glass_panel(x, y, w, h, 10);
        /* accent 顶部指示条 */
        st7789_fill_rect(x + 8, y + 1, x + w - 8, y + 2, accent);
    }

    uint16_t tc = pressed ? RGB565(255, 255, 255) : TEXT_PRIMARY;
    uint16_t dc = pressed ? RGB565(220, 220, 255) : TEXT_DIM;

    /* K 标签（左上角小字） */
    draw_string(x + 6, y + 8, key->id, dc, 1);
    /* 名称（居中大字） */
    int16_t tw = string_width(key->display, 1);
    draw_string(x + (w - tw) / 2, y + 24, key->display, tc, 1);
    /* 动作（居中小字） */
    int16_t aw = string_width(key->action, 1);
    if (aw > w - 8) aw = w - 8;
    draw_string(x + (w - aw) / 2, y + 38, key->action, dc, 1);
}

/* 物理矩阵位置查找表（idx -> row, col） */
static const struct { uint8_t r, c; } key_pos[PROFILE_MAX_KEYS] = {
    {0, 0}, {0, 1}, {1, 0}, {1, 1}, {2, 0}, {2, 1}
};

static void draw_screen_keys(void)
{
    int key_count = g_current_profile.key_count;
    int card_w = (LCD_W - CARD_GAP * (CARD_COLS + 1)) / CARD_COLS;
    int start_x = CARD_GAP;
    int start_y = 32;

    for (int lr = 0; lr < CARD_ROWS; lr++) {
        for (int lc = 0; lc < CARD_COLS; lc++) {
            int idx = lr * CARD_COLS + lc;
            if (idx < key_count) {
                int x = start_x + lc * (card_w + CARD_GAP);
                int y = start_y + lr * (CARD_H + CARD_GAP);
                bool pressed = key_pressed[key_pos[idx].r][key_pos[idx].c];
                draw_key_card(x, y, card_w, CARD_H, idx, pressed);
            }
        }
    }
}

/* ═══════════════════════════════════════════════
 *  SCREEN 1: 设备状态
 * ═══════════════════════════════════════════════ */

static void draw_info_row(int x, int y, int w, const char *label, const char *value, uint16_t val_color)
{
    draw_string(x, y, label, TEXT_DIM, 1);
    int16_t vw = string_width(value, 1);
    draw_string(x + w - vw, y, value, val_color, 1);
}

static void draw_screen_status(void)
{
    int x = 10, y = 34, w = LCD_W - 20, row_h = 22;

    /* 大字运行时间（居中） */
    int64_t sec = esp_timer_get_time() / 1000000;
    int hrs = (sec / 3600) % 24;
    int mins = (sec / 60) % 60;
    int secs = sec % 60;
    char clock_str[16];
    snprintf(clock_str, sizeof(clock_str), "%02d:%02d:%02d", hrs, mins, secs);

    /* 时钟玻璃面板 */
    draw_glass_panel(20, y, LCD_W - 40, 36, 10);
    draw_string_centered(y + 10, clock_str, TEXT_PRIMARY, 3);  /* 3x 缩放大字 */
    y += 42;

    /* 状态行 */
    static const struct { const char *label; const char *value; uint16_t color; } rows[] = {
        {"BLE",      NULL, 0},  /* 动态 */
        {"WiFi",     NULL, 0},  /* 动态 */
        {"Profile",  NULL, 0},  /* 动态 */
        {"Keys",     NULL, 0},  /* 动态 */
        {"RAM",      NULL, 0},  /* 动态 */
        {"PSRAM",    NULL, 0},  /* 动态 */
    };

    /* BLE */
    draw_glass_panel(x, y, w, row_h, 6);
    draw_info_row(x + 6, y + 6, w - 12, "BLE",
                  ble_connected ? "Connected" : "Searching",
                  ble_connected ? RGB565(72, 199, 142) : RGB565(245, 158, 11));
    y += row_h + 3;

    /* WiFi */
    draw_glass_panel(x, y, w, row_h, 6);
    bool wifi_ok = wifi_ctrl_is_connected();
    char wifi_ip[16];
    wifi_ctrl_get_ip(wifi_ip, sizeof(wifi_ip));
    draw_info_row(x + 6, y + 6, w - 12, "WiFi",
                  wifi_ok ? wifi_ip : "Connecting...",
                  wifi_ok ? RGB565(72, 199, 142) : RGB565(245, 158, 11));
    y += row_h + 3;

    /* Profile */
    draw_glass_panel(x, y, w, row_h, 6);
    draw_info_row(x + 6, y + 6, w - 12, "Profile",
                  g_current_profile.valid ? g_current_profile.name : "None", TEXT_PRIMARY);
    y += row_h + 3;

    /* 按键数 */
    draw_glass_panel(x, y, w, row_h, 6);
    char kn[16];
    snprintf(kn, sizeof(kn), "%d / %d", g_current_profile.key_count, PROFILE_MAX_KEYS);
    draw_info_row(x + 6, y + 6, w - 12, "Keys", kn, TEXT_PRIMARY);
    y += row_h + 3;

    /* 内存 */
    draw_glass_panel(x, y, w, row_h, 6);
    char mem[16];
    snprintf(mem, sizeof(mem), "%lu KB", (unsigned long)(esp_get_free_heap_size() / 1024));
    draw_info_row(x + 6, y + 6, w - 12, "RAM", mem, TEXT_ACCENT);
    y += row_h + 3;

    /* PSRAM */
    draw_glass_panel(x, y, w, row_h, 6);
    char psram[16];
    snprintf(psram, sizeof(psram), "%lu KB", (unsigned long)(heap_caps_get_free_size(MALLOC_CAP_SPIRAM) / 1024));
    draw_info_row(x + 6, y + 6, w - 12, "PSRAM", psram, TEXT_ACCENT);
}

/* ═══════════════════════════════════════════════
 *  SCREEN 2: 壁纸管理
 * ═══════════════════════════════════════════════ */

static void draw_screen_wallpaper(void)
{
    int x = 10, y = 34, w = LCD_W - 20;

    /* 壁纸状态 */
    draw_glass_panel(x, y, w, 22, 6);
    wallpaper_t *wp = wallpaper_get();
    const char *wp_type = "None";
    uint16_t wp_color = TEXT_DIM;
    if (wp->type == WP_TYPE_STATIC) { wp_type = "Static"; wp_color = RGB565(72, 199, 142); }
    else if (wp->type == WP_TYPE_GIF) { wp_type = "GIF"; wp_color = RGB565(245, 158, 11); }
    draw_info_row(x + 6, y + 6, w - 12, "Type", wp_type, wp_color);
    y += 26;

    /* GIF 帧信息 */
    if (wp->type == WP_TYPE_GIF) {
        draw_glass_panel(x, y, w, 22, 6);
        char fi[24];
        snprintf(fi, sizeof(fi), "%d / %d", wp->current_frame + 1, wp->frame_count);
        draw_info_row(x + 6, y + 6, w - 12, "Frame", fi, TEXT_PRIMARY);
        y += 26;

        draw_glass_panel(x, y, w, 22, 6);
        draw_info_row(x + 6, y + 6, w - 12, "Playing",
                      wp->playing ? "Yes" : "No", wp->playing ? RGB565(72, 199, 142) : TEXT_DIM);
        y += 26;
    }

    /* 提示文字 */
    y += 8;
    draw_glass_panel(x, y, w, 60, 6);
    draw_string(x + 10, y + 10, "Upload via App:", TEXT_DIM, 1);
    draw_string(x + 10, y + 24, "1. Select image", TEXT_DIM, 1);
    draw_string(x + 10, y + 38, "2. Click Upload", TEXT_DIM, 1);
    draw_string(x + 10, y + 52, "PNG/JPG/GIF", TEXT_DIM, 1);
}

/* ═══════════════════════════════════════════════
 *  主 UI 入口 + 屏幕切换
 * ═══════════════════════════════════════════════ */

void draw_ui(void)
{
    bool full_redraw = (current_screen != last_screen);

    /* 切换界面时：强制清屏 + 重绘壁纸 + 全部内容 */
    if (full_redraw) {
        st7789_fill_screen(COLOR_BG);  /* 清除旧界面残留 */
        wallpaper_dirty = true;        /* 强制重绘壁纸 */
        last_screen = current_screen;
    }

    draw_wallpaper();
    draw_header();

    switch (current_screen) {
        case 0: draw_screen_keys(); break;
        case 1: draw_screen_status(); break;
        case 2: draw_screen_wallpaper(); break;
        default: draw_screen_keys(); break;
    }

    draw_footer();
}

/* 屏幕切换命令解析 (非 static，供 wifi_ctrl 调用) */
void screen_parse_cmd(const char *json_str)
{
    cJSON *root = cJSON_Parse(json_str);
    if (!root) return;

    const cJSON *action = cJSON_GetObjectItem(root, "action");
    if (!action || !cJSON_IsString(action)) { cJSON_Delete(root); return; }

    const char *act = action->valuestring;
    if (strcmp(act, "switch") == 0) {
        const cJSON *id = cJSON_GetObjectItem(root, "id");
        if (id && cJSON_IsNumber(id)) {
            int new_id = id->valueint;
            if (new_id >= 0 && new_id < SCREEN_COUNT) {
                current_screen = new_id;
                wallpaper_dirty = true;
                screen_dirty = true;
                ESP_LOGI(TAG, "Screen -> %d (%s)", current_screen, screen_names[current_screen]);
            }
        }
    } else if (strcmp(act, "next") == 0) {
        current_screen = (current_screen + 1) % SCREEN_COUNT;
        wallpaper_dirty = true;
        screen_dirty = true;
        ESP_LOGI(TAG, "Screen -> %d (%s)", current_screen, screen_names[current_screen]);
    } else if (strcmp(act, "prev") == 0) {
        current_screen = (current_screen - 1 + SCREEN_COUNT) % SCREEN_COUNT;
        wallpaper_dirty = true;
        screen_dirty = true;
        ESP_LOGI(TAG, "Screen -> %d (%s)", current_screen, screen_names[current_screen]);
    } else if (strcmp(act, "get") == 0) {
        printf("{\"cmd\":\"screen_ack\",\"id\":%d,\"name\":\"%s\"}\n",
               current_screen, screen_names[current_screen]);
    }

    cJSON_Delete(root);
}

/* ── 将矩阵位置映射到 Profile 按键索引 ──── */
static int matrix_to_key_index(int row, int col)
{
    return row * COL_COUNT + col;  /* 0-5 */
}

/* ── 串口命令处理 (接收 PC Manager 的 Profile) ── */
static void serial_cmd_task(void *arg)
{
    char line[8192];  /* 增大缓冲区以容纳壁纸数据块 */
    int pos = 0;

    ESP_LOGI(TAG, "Serial command task started");

    while (1) {
        int c = fgetc(stdin);
        if (c == EOF) {
            vTaskDelay(pdMS_TO_TICKS(10));
            continue;
        }

        if (c == '\n' || c == '\r') {
            if (pos > 0 && pos < (int)sizeof(line)) {
                line[pos] = '\0';

                /* 跳过前导非 JSON 字符（UART 首字节损坏 workaround） */
                char *json_start = strchr(line, '{');
                if (!json_start) {
                    pos = 0;
                    continue;
                }

                ESP_LOGI(TAG, "Serial cmd: %d bytes", pos);

                /* 解析 JSON 命令 */
                if (strstr(json_start, "\"cmd\"")) {
                    if (strstr(json_start, "\"profile\"")) {
                        ESP_LOGI(TAG, "Parsing profile JSON...");
                        extern void parse_profile_json(const char *json_str);
                        parse_profile_json(json_start);
                    } else if (strstr(json_start, "\"wallpaper") ||
                               strstr(json_start, "\"wp_")) {
                        ESP_LOGI(TAG, "Parsing wallpaper cmd...");
                        wallpaper_parse_cmd(json_start);
                        wallpaper_dirty = true;
                        screen_dirty = true;
                    } else if (strstr(json_start, "\"screen\"")) {
                        ESP_LOGI(TAG, "Parsing screen cmd...");
                        screen_parse_cmd(json_start);
                    } else if (strstr(json_start, "\"ping\"")) {
                        ESP_LOGI(TAG, "Pong");
                        printf("{\"cmd\": \"pong\"}\n");
                    } else {
                        ESP_LOGI(TAG, "Unknown cmd: %.*s", pos > 40 ? 40 : pos, json_start);
                    }
                }
                pos = 0;
            } else {
                pos = 0;
            }
        } else if (pos < (int)sizeof(line) - 1) {
            line[pos++] = (char)c;
        }
    }
}

/* ── 壁纸 ACK 回调：WiFi 通道通过 TCP 发送 ── */
extern bool wifi_ctrl_send(const char *data, size_t len);
extern bool wifi_ctrl_has_client(void);

static void wallpaper_ack_to_wifi(const char *data, int len)
{
    /* 优先发到 WiFi 客户端 */
    if (wifi_ctrl_has_client()) {
        wifi_ctrl_send(data, len);
    }
    /* 同时输出到串口（调试/日志） */
    printf("%s", data);
}

/* ── 主函数 ──────────────────────────────── */
void app_main(void)
{
    /* NVS 初始化 */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    /* WiFi 初始化 (TCP 服务器 + mDNS) */
    wifi_ctrl_init(NULL, NULL);  /* 从 NVS 读取凭据 */

    /* 屏幕初始化 */
    st7789_config_t lcd_cfg = {
        .spi_host = SPI3_HOST,
        .pin_mosi = PIN_MOSI, .pin_sclk = PIN_SCLK,
        .pin_cs = PIN_CS, .pin_dc = PIN_DC,
        .pin_rst = PIN_RST, .pin_bl = PIN_BL,
        .spi_clock_hz = 40 * 1000 * 1000,
    };
    ESP_ERROR_CHECK(st7789_init(&lcd_cfg));
    st7789_backlight(true);

    /* 按键初始化 */
    matrix_init();

    /* BLE HID 初始化 */
    ble_hid_init();

    /* Profile 接收服务初始化 */
    profile_receiver_init();

    /* 壁纸系统初始化 */
    wallpaper_init();
    wallpaper_set_ack_callback(wallpaper_ack_to_wifi);

    /* 不重新安装 UART 驱动（避免与控制台冲突） */
    /* 首字节损坏问题通过 strchr(workaround) 解决 */

    /* 绘制界面 */
    draw_ui();

    /* 启动串口命令处理任务 */
    xTaskCreate(serial_cmd_task, "serial_cmd", 8192, NULL, 5, NULL);

    ESP_LOGI(TAG, "AI Agent Deck V2.0 started");
    ESP_LOGI(TAG, "BLE device: %s", ble_hid_config.device_name);
    ESP_LOGI(TAG, "Profile: %s", g_current_profile.name);

    /* 主循环 */
    int loop_count = 0;
    static bool last_key[ROW_COUNT][COL_COUNT] = {0};
    static int64_t key_debounce[ROW_COUNT][COL_COUNT] = {0};
    static int fast_scan = 0;

    while (1) {
        /* 自适应采样率 */
        vTaskDelay(pdMS_TO_TICKS(fast_scan > 0 ? 5 : 20));
        if (fast_scan > 0) fast_scan--;

        matrix_scan();
        int64_t now = esp_timer_get_time() / 1000;  /* 毫秒 */

        /* 检测按键（带消抖） */
        for (int r = 0; r < ROW_COUNT; r++) {
            for (int c = 0; c < COL_COUNT; c++) {
                bool cur = key_pressed[r][c];
                bool prev = last_key[r][c];

                /* 消抖：状态变化后 50ms 内忽略 */
                if (cur != prev) {
                    if ((now - key_debounce[r][c]) < DEBOUNCE_MS) {
                        key_pressed[r][c] = prev;  /* 保持上一个状态 */
                        continue;
                    }
                    key_debounce[r][c] = now;
                }

                /* 检测按下边沿 */
                if (key_pressed[r][c] && !last_key[r][c]) {
                    int idx = matrix_to_key_index(r, c);
                    if (idx < g_current_profile.key_count) {
                        const profile_key_t *kf = &g_current_profile.keys[idx];
                        ESP_LOGI(TAG, "[KEY] %s -> %s (%s)",
                                 kf->id, kf->display, kf->action);

                        /* 尝试发送 F13-F18 到 PC（无论是否成功都继续） */
                        bool sent = send_keyboard_key(0x00, fkey_codes[idx]);
                        if (!sent) {
                            ESP_LOGW(TAG, "BLE not connected, key local only");
                        }
                        fast_scan = 20;

                        /* 标记屏幕需要刷新（非阻塞动画） */
                        screen_dirty = true;
                    }
                }
                last_key[r][c] = key_pressed[r][c];
            }
        }

        /* 壁纸 GIF 帧更新 */
        if (!wallpaper_is_uploading()) {
            if (wallpaper_update()) {
                wallpaper_dirty = true;
                screen_dirty = true;
            }
        }

        /* 刷新显示 (10Hz 或有事件时)，上传期间暂停避免 SPI 冲突 */
        loop_count++;
        if (!wallpaper_is_uploading() && (loop_count % 10 == 0 || screen_dirty)) {
            draw_ui();
            screen_dirty = false;
        }
    }
}
