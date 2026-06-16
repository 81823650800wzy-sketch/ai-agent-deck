/**
 * AI Agent Deck V1.0 - BLE HID 键盘 + UI 系统
 *
 * 功能:
 *   - BLE 无线键盘
 *   - 真实 AI 工具快捷键映射
 *   - 状态显示界面
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
#include "esp_hidd.h"
#include "esp_hid_gap.h"
#include "st7789.h"
#include "font5x7.h"

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

/* ── 按键矩阵 ────────────────────────────── */
static const gpio_num_t row_pins[] = {ROW1_PIN, ROW2_PIN, ROW3_PIN};
static const gpio_num_t col_pins[] = {COL1_PIN, COL2_PIN};
#define ROW_COUNT 3
#define COL_COUNT 2
static bool key_pressed[ROW_COUNT][COL_COUNT] = {0};

/* ── HID 修饰键定义 ──────────────────────── */
#define MOD_CTRL    0x01
#define MOD_SHIFT   0x02
#define MOD_ALT     0x04
#define MOD_WIN     0x08

/* ── 按键功能定义 ────────────────────────── */
typedef struct {
    const char *name;       /* 显示名称 */
    const char *app;        /* 目标应用 */
    uint8_t modifier;       /* HID 修饰键 */
    uint8_t keycode;        /* HID 键码 */
    uint16_t color;         /* UI 颜色 */
} key_func_t;

/* 测试用普通字母键 */
static const key_func_t key_funcs[ROW_COUNT][COL_COUNT] = {
    /* Row 1 */
    {{"Key1", "Test-A",   0x00, 0x04, COLOR_GREEN},   // 'a'
     {"Key2", "Test-B",   0x00, 0x05, COLOR_PURPLE}},  // 'b'

    /* Row 2 */
    {{"Key3", "Test-C",   0x00, 0x06, COLOR_BLUE},    // 'c'
     {"Key4", "Test-D",   0x00, 0x07, COLOR_YELLOW}},  // 'd'

    /* Row 3 */
    {{"Key5", "Test-E",   0x00, 0x08, COLOR_RED},     // 'e'
     {"Key6", "Test-F",   0x00, 0x09, COLOR_DIM}},    // 'f'
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
    0x95, 0x05,        //   Report Count (5)
    0x75, 0x01,        //   Report Size (1)
    0x05, 0x08,        //   Usage Page (LEDs)
    0x19, 0x01,        //   Usage Minimum (Num Lock)
    0x29, 0x05,        //   Usage Maximum (Kana)
    0x91, 0x02,        //   Output (Data,Var,Abs)
    0x95, 0x01,        //   Report Count (1)
    0x75, 0x03,        //   Report Size (3)
    0x91, 0x03,        //   Output (Const,Var,Abs)
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
static void draw_char(int16_t x, int16_t y, char c, uint16_t color, uint8_t scale)
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

static void draw_string(int16_t x, int16_t y, const char *str, uint16_t color, uint8_t scale)
{
    while (*str) {
        draw_char(x, y, *str, color, scale);
        x += 6 * scale;
        str++;
    }
}

static int16_t string_width(const char *str, uint8_t scale)
{
    int16_t len = 0;
    while (*str) { len++; str++; }
    return len * 6 * scale;
}

static void draw_string_centered(int16_t y, const char *str, uint16_t color, uint8_t scale)
{
    int16_t w = string_width(str, scale);
    draw_string((LCD_W - w) / 2, y, str, color, scale);
}

/* ── 颜色工具 ────────────────────────────── */
static uint16_t color_lerp(uint16_t c1, uint16_t c2, uint8_t t)
{
    uint8_t r1 = (c1 >> 11) & 0x1F, g1 = (c1 >> 5) & 0x3F, b1 = c1 & 0x1F;
    uint8_t r2 = (c2 >> 11) & 0x1F, g2 = (c2 >> 5) & 0x3F, b2 = c2 & 0x1F;
    uint8_t r = r1 + ((int16_t)(r2 - r1) * t) / 255;
    uint8_t g = g1 + ((int16_t)(g2 - g1) * t) / 255;
    uint8_t b = b1 + ((int16_t)(b2 - b1) * t) / 255;
    return (r << 11) | (g << 5) | b;
}

static void draw_gradient_h(int16_t x, int16_t y, int16_t w, int16_t h, uint16_t c1, uint16_t c2)
{
    if (x < 0) { w += x; x = 0; }
    if (y < 0) { h += y; y = 0; }
    if (x + w > LCD_W) w = LCD_W - x;
    if (y + h > LCD_H) h = LCD_H - y;
    if (w <= 0 || h <= 0) return;
    for (int16_t i = 0; i < w; i++) {
        uint8_t t = (w > 1) ? (i * 255) / (w - 1) : 0;
        st7789_fill_rect(x + i, y, x + i, y + h - 1, color_lerp(c1, c2, t));
    }
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
    if (event == ESP_GAP_BLE_SEC_REQ_EVT) {
        esp_ble_gap_security_rsp(param->ble_security.ble_req.bd_addr, true);
    } else if (event == ESP_GAP_BLE_NC_REQ_EVT) {
        esp_ble_confirm_reply(param->ble_security.ble_req.bd_addr, true);
    }
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

/* ── 初始化 BLE HID ──────────────────────── */
static void ble_hid_init(void)
{
    esp_hid_gap_init(HIDD_BLE_MODE);
    esp_ble_gap_register_callback(gap_event_handler);
    esp_hid_ble_gap_adv_init(ESP_HID_APPEARANCE_KEYBOARD, ble_hid_config.device_name);
    esp_ble_gatts_register_callback(esp_hidd_gatts_event_handler);
    esp_hidd_dev_init(&ble_hid_config, ESP_HID_TRANSPORT_BLE, ble_hidd_event_callback, &hid_dev);
}

/* ── 发送按键 ────────────────────────────── */
static void send_keyboard_key(uint8_t modifier, uint8_t keycode)
{
    if (!ble_connected || !hid_dev) return;

    uint8_t buffer[8] = {modifier, 0, keycode, 0, 0, 0, 0, 0};
    esp_hidd_dev_input_set(hid_dev, 0, 1, buffer, 8);
    vTaskDelay(pdMS_TO_TICKS(30));
    memset(buffer, 0, sizeof(buffer));
    esp_hidd_dev_input_set(hid_dev, 0, 1, buffer, 8);
}

/* ── UI 绘制 ─────────────────────────────── */

/* 绘制顶部状态栏 */
static void draw_header(void)
{
    st7789_fill_rect(0, 0, LCD_W - 1, 35, COLOR_HEADER);
    draw_gradient_h(0, 0, LCD_W, 3, COLOR_ACCENT, COLOR_CYAN);
    draw_string_centered(8, "AI AGENT DECK", COLOR_TEXT, 2);

    /* BLE 状态指示 */
    if (ble_connected) {
        st7789_fill_rect(LCD_W - 20, 8, LCD_W - 8, 20, COLOR_GREEN);
    } else if (ble_advertising) {
        static bool blink = false;
        blink = !blink;
        st7789_fill_rect(LCD_W - 20, 8, LCD_W - 8, 20, blink ? COLOR_YELLOW : COLOR_BG);
    }
}

/* 绘制快捷键卡片 */
static void draw_key_card(int x, int y, int w, int h, const key_func_t *key, bool pressed)
{
    /* 背景 */
    uint16_t bg = pressed ? key->color : COLOR_CARD;
    st7789_fill_rect(x, y, x + w - 1, y + h - 1, bg);

    /* 边框 */
    st7789_draw_rect(x, y, x + w - 1, y + h - 1, key->color);
    if (pressed) {
        st7789_draw_rect(x + 1, y + 1, x + w - 2, y + h - 2, key->color);
    }

    /* 按键名称 */
    uint16_t text_col = pressed ? COLOR_BG : COLOR_TEXT;
    uint16_t dim_col = pressed ? COLOR_BG : COLOR_DIM;

    int16_t tw = string_width(key->name, 1);
    draw_string(x + (w - tw) / 2, y + 8, key->name, text_col, 1);

    /* 快捷键说明 */
    char shortcut[16] = "";
    if (key->modifier & MOD_CTRL) strcat(shortcut, "C+");
    if (key->modifier & MOD_SHIFT) strcat(shortcut, "S+");
    if (key->modifier & MOD_ALT) strcat(shortcut, "A+");
    if (key->modifier & MOD_WIN) strcat(shortcut, "W+");
    /* 添加键名 */
    char key_str[2] = {0};
    if (key->keycode >= 0x04 && key->keycode <= 0x1D) {
        key_str[0] = 'a' + (key->keycode - 0x04);
    } else if (key->keycode == 0x28) {
        strcpy(key_str, "N");  /* Enter */
    } else if (key->keycode == 0x2C) {
        strcpy(key_str, "_");  /* Space */
    } else if (key->keycode == 0x0F) {
        strcpy(key_str, "H");  /* Voice (Win+H) */
    } else {
        snprintf(key_str, sizeof(key_str), "%c", 'A' + (key->keycode % 26));
    }
    strcat(shortcut, key_str);

    tw = string_width(shortcut, 1);
    draw_string(x + (w - tw) / 2, y + 22, shortcut, dim_col, 1);

    /* 应用名称 */
    tw = string_width(key->app, 1);
    draw_string(x + (w - tw) / 2, y + 34, key->app, dim_col, 1);
}

/* 绘制底部状态栏 */
static void draw_footer(void)
{
    st7789_fill_rect(0, LCD_H - 20, LCD_W - 1, LCD_H - 1, COLOR_HEADER);
    st7789_draw_hline(0, LCD_W - 1, LCD_H - 20, COLOR_BORDER);

    const char *status = ble_connected ? "CONNECTED" : "SEARCHING...";
    uint16_t color = ble_connected ? COLOR_GREEN : COLOR_DIM;
    draw_string_centered(LCD_H - 14, status, color, 1);
}

/* 绘制主界面 */
static void draw_ui(void)
{
    st7789_fill_screen(COLOR_BG);
    draw_header();

    /* 按键卡片布局 */
    int card_w = 95;
    int card_h = 50;
    int gap = 8;
    int start_x = (LCD_W - card_w * 2 - gap) / 2;
    int start_y = 45;

    for (int r = 0; r < ROW_COUNT; r++) {
        for (int c = 0; c < COL_COUNT; c++) {
            int x = start_x + c * (card_w + gap);
            int y = start_y + r * (card_h + 8);
            draw_key_card(x, y, card_w, card_h, &key_funcs[r][c], key_pressed[r][c]);
        }
    }

    draw_footer();
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

    /* 绘制界面 */
    draw_ui();

    ESP_LOGI(TAG, "AI Agent Deck started");
    ESP_LOGI(TAG, "BLE device: %s", ble_hid_config.device_name);

    /* 主循环 */
    int loop_count = 0;
    static bool last_key[ROW_COUNT][COL_COUNT] = {0};
    static int fast_scan = 0;

    while (1) {
        /* 自适应采样率 */
        vTaskDelay(pdMS_TO_TICKS(fast_scan > 0 ? 5 : 20));
        if (fast_scan > 0) fast_scan--;

        matrix_scan();

        /* 检测按键 */
        for (int r = 0; r < ROW_COUNT; r++) {
            for (int c = 0; c < COL_COUNT; c++) {
                if (key_pressed[r][c] && !last_key[r][c]) {
                    const key_func_t *kf = &key_funcs[r][c];
                    ESP_LOGI(TAG, "[KEY] %s -> %s", kf->name, kf->app);
                    send_keyboard_key(kf->modifier, kf->keycode);
                    fast_scan = 20;
                }
                last_key[r][c] = key_pressed[r][c];
            }
        }

        /* 刷新显示 (10Hz) */
        loop_count++;
        if (loop_count % 10 == 0) {
            draw_header();

            /* 刷新按键卡片 */
            int card_w = 95, card_h = 50, gap = 8;
            int start_x = (LCD_W - card_w * 2 - gap) / 2;
            int start_y = 45;

            for (int r = 0; r < ROW_COUNT; r++) {
                for (int c = 0; c < COL_COUNT; c++) {
                    int x = start_x + c * (card_w + gap);
                    int y = start_y + r * (card_h + 8);
                    draw_key_card(x, y, card_w, card_h, &key_funcs[r][c], key_pressed[r][c]);
                }
            }

            draw_footer();
        }
    }
}
