/**
 * ST7789 240x240 IPS 显示驱动 (完整版)
 * 适配: 1.54寸 IPS RGB 240x240 SPI 模块
 */
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_check.h"
#include "st7789.h"

static const char *TAG = "ST7789";
#define W  240
#define H  240

/* ST7789 命令 */
#define CMD_NOP       0x00
#define CMD_SWRESET   0x01
#define CMD_RDDID     0x04
#define CMD_RDDST     0x09
#define CMD_SLPIN     0x10
#define CMD_SLPOUT    0x11
#define CMD_PTLON     0x12
#define CMD_NORON     0x13
#define CMD_INVOFF    0x20
#define CMD_INVON     0x21
#define CMD_DISPOFF   0x28
#define CMD_DISPON    0x29
#define CMD_CASET     0x2A
#define CMD_RASET     0x2B
#define CMD_RAMWR     0x2C
#define CMD_RGBSET    0x2D
#define CMD_RAMRD     0x2E
#define CMD_PTLAR     0x30
#define CMD_VSCRDEF   0x33
#define CMD_MADCTL    0x36
#define CMD_VSCSAD    0x37
#define CMD_IDMOFF    0x38
#define CMD_IDMON     0x39
#define CMD_COLMOD    0x3A
#define CMD_RDID1     0xDA
#define CMD_RDID2     0xDB
#define CMD_RDID3     0xDC

/* ST7789 扩展命令 */
#define CMD_PWCTR1    0xC0
#define CMD_PWCTR2    0xC1
#define CMD_PWCTR3    0xC2
#define CMD_PWCTR4    0xC3
#define CMD_PWCTR5    0xC4
#define CMD_VMCTR1    0xC5
#define CMD_FRMCTR1   0xB1
#define CMD_FRMCTR2   0xB3
#define CMD_GMCTRP1   0xE0
#define CMD_GMCTRN1   0xE1
#define CMD_DGMEN     0xBA
#define CMD_PWCLT1    0xCB
#define CMD_PWCLT2    0xCF
#define CMD_PWCTR6    0xFC

/* 状态 */
static spi_device_handle_t g_spi;
static gpio_num_t g_dc, g_rst, g_bl;
static uint8_t g_rot;

/* ── 内部函数 ────────────────────────── */
static inline void dc_cmd(void)  { gpio_set_level(g_dc, 0); }
static inline void dc_data(void) { gpio_set_level(g_dc, 1); }

static void send_cmd(uint8_t cmd) {
    spi_transaction_t t = { .length = 8, .tx_buffer = &cmd };
    dc_cmd();
    spi_device_polling_transmit(g_spi, &t);
}

static void send_cmd_data(uint8_t cmd, const uint8_t *data, size_t len) {
    send_cmd(cmd);
    if (len > 0 && data) {
        spi_transaction_t t = { .length = len * 8, .tx_buffer = data };
        dc_data();
        spi_device_polling_transmit(g_spi, &t);
    }
}

/* 1.54" 240x240 面板在 ST7789 320-row GRAM 中的偏移 */
#define ROW_OFFSET  80    /* 可见行从 GRAM 第80行开始 */
#define COL_OFFSET  0     /* 列偏移 (有些模块需要40) */

static void set_window(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1) {
    uint8_t d[4];
    uint16_t cx0 = x0 + COL_OFFSET;
    uint16_t cx1 = x1 + COL_OFFSET;
    uint16_t cy0 = y0 + ROW_OFFSET;
    uint16_t cy1 = y1 + ROW_OFFSET;

    d[0]=cx0>>8; d[1]=cx0&0xFF; d[2]=cx1>>8; d[3]=cx1&0xFF;
    send_cmd_data(CMD_CASET, d, 4);
    d[0]=cy0>>8; d[1]=cy0&0xFF; d[2]=cy1>>8; d[3]=cy1&0xFF;
    send_cmd_data(CMD_RASET, d, 4);
    send_cmd(CMD_RAMWR);
}

static void hw_reset(void) {
    if (g_rst == GPIO_NUM_NC) return;
    gpio_set_level(g_rst, 0);
    vTaskDelay(pdMS_TO_TICKS(20));
    gpio_set_level(g_rst, 1);
    vTaskDelay(pdMS_TO_TICKS(150));
}

/* ── ST7789 完整初始化序列 ──────────── */
esp_err_t st7789_init(const st7789_config_t *cfg) {
    ESP_RETURN_ON_FALSE(cfg, ESP_ERR_INVALID_ARG, TAG, "null config");
    g_dc=cfg->pin_dc; g_rst=cfg->pin_rst; g_bl=cfg->pin_bl;

    gpio_config_t io = { .mode=GPIO_MODE_OUTPUT,
        .pull_up_en=GPIO_PULLUP_DISABLE, .pull_down_en=GPIO_PULLDOWN_DISABLE,
        .intr_type=GPIO_INTR_DISABLE };

    io.pin_bit_mask = 1ULL<<cfg->pin_dc;  gpio_config(&io);
    if (cfg->pin_rst!=GPIO_NUM_NC) { io.pin_bit_mask=1ULL<<cfg->pin_rst; gpio_config(&io); gpio_set_level(cfg->pin_rst,1); }
    if (cfg->pin_bl!=GPIO_NUM_NC)  { io.pin_bit_mask=1ULL<<cfg->pin_bl;  gpio_config(&io); gpio_set_level(cfg->pin_bl,1); }

    /* SPI 初始化 — 用较低速度保证杜邦线稳定 */
    spi_bus_config_t bus = { .mosi_io_num=cfg->pin_mosi, .miso_io_num=-1,
        .sclk_io_num=cfg->pin_sclk, .quadwp_io_num=-1, .quadhd_io_num=-1,
        .max_transfer_sz=W*H*2+8 };
    ESP_RETURN_ON_ERROR(spi_bus_initialize(cfg->spi_host, &bus, SPI_DMA_CH_AUTO), TAG, "SPI bus");

    int clk = cfg->spi_clock_hz > 0 ? cfg->spi_clock_hz : 27000000; /* 默认27MHz */
    spi_device_interface_config_t dev = { .clock_speed_hz=clk,
        .mode=0, .spics_io_num=cfg->pin_cs, .queue_size=7,
        .flags=SPI_DEVICE_HALFDUPLEX };
    ESP_RETURN_ON_ERROR(spi_bus_add_device(cfg->spi_host, &dev, &g_spi), TAG, "SPI dev");

    ESP_LOGI(TAG, "SPI initialized at %d Hz", clk);

    /* ── 硬件复位 ── */
    hw_reset();

    /* ── 软件复位 ── */
    send_cmd(CMD_SWRESET);
    vTaskDelay(pdMS_TO_TICKS(200));

    /* ── 退出睡眠 ── */
    send_cmd(CMD_SLPOUT);
    vTaskDelay(pdMS_TO_TICKS(120));

    /* ── 像素格式: 16-bit RGB565 ── */
    {
        uint8_t d = 0x55;
        send_cmd_data(CMD_COLMOD, &d, 1);
    }
    vTaskDelay(pdMS_TO_TICKS(10));

    /* ── 显示方向: 正常 (依模块调整) ── */
    st7789_set_rotation(0);

    /* ── 帧速率控制 ── */
    {
        uint8_t d[] = { 0x01, 0x2C, 0x2D }; /* 119Hz */
        send_cmd_data(CMD_FRMCTR2, d, 3);
    }

    /* ── 反相控制 ── */
    {
        uint8_t d[] = { 0x01, 0x2C, 0x2D };
        send_cmd_data(CMD_FRMCTR1, d, 3);
    }

    /* ── 显示反转控制 ── */
    {
        uint8_t d[] = { 0x01, 0x2C, 0x2D, 0x33, 0x33 };
        send_cmd_data(CMD_DGMEN, d, 5);
    }

    /* ── 电源控制 ── */
    {
        uint8_t d1[] = { 0x19 };
        send_cmd_data(CMD_PWCTR1, d1, 1);
    }
    {
        uint8_t d2[] = { 0x0C };
        send_cmd_data(CMD_PWCTR2, d2, 1);
    }
    {
        uint8_t d3[] = { 0x12 };
        send_cmd_data(CMD_PWCTR3, d3, 1);
    }

    /* ── VCOM 控制 ── */
    {
        uint8_t d[] = { 0x35, 0x3E };
        send_cmd_data(CMD_VMCTR1, d, 2);
    }

    /* ── 电源控制 4 ── */
    {
        uint8_t d[] = { 0x33 };
        send_cmd_data(CMD_PWCTR4, d, 1);
    }

    /* ── 正极性 Gamma ── */
    {
        uint8_t d[] = { 0xD0, 0x04, 0x0D, 0x11, 0x13, 0x2B,
                        0x3F, 0x54, 0x4C, 0x18, 0x0D, 0x0B,
                        0x1F, 0x23 };
        send_cmd_data(CMD_GMCTRP1, d, 14);
    }

    /* ── 负极性 Gamma ── */
    {
        uint8_t d[] = { 0xD0, 0x04, 0x0C, 0x11, 0x13, 0x2C,
                        0x3F, 0x44, 0x51, 0x2F, 0x1F, 0x1F,
                        0x20, 0x23 };
        send_cmd_data(CMD_GMCTRN1, d, 14);
    }

    /* ── 反转关闭 ── */
    send_cmd(CMD_INVOFF);

    /* ── 正常显示模式 ── */
    send_cmd(CMD_NORON);
    vTaskDelay(pdMS_TO_TICKS(10));

    /* ── 空闲模式关闭 ── */
    send_cmd(CMD_IDMOFF);

    /* ── 局部显示关闭 ── */
    send_cmd(CMD_PTLON);
    send_cmd(CMD_NORON);

    /* ── 开显示 ── */
    send_cmd(CMD_DISPON);
    vTaskDelay(pdMS_TO_TICKS(200));

    /* ── 清屏 ── */
    st7789_fill_screen(ST7789_COLOR_BLACK);

    ESP_LOGI(TAG, "ST7789 init OK %dx%d", W, H);
    return ESP_OK;
}

void st7789_backlight(bool l) { if (g_bl!=GPIO_NUM_NC) gpio_set_level(g_bl, l?1:0); }

void st7789_fill_screen(uint16_t c) { st7789_fill_rect(0,0,W-1,H-1,c); }

void st7789_fill_rect(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1, uint16_t color) {
    if (x0>x1) { uint16_t t=x0; x0=x1; x1=t; }
    if (y0>y1) { uint16_t t=y0; y0=y1; y1=t; }
    if (x1>=W) x1=W-1;
    if (y1>=H) y1=H-1;
    set_window(x0,y0,x1,y1);

    uint32_t n = (uint32_t)(x1-x0+1)*(y1-y0+1);
    #define CHUNK 4096
    static uint16_t buf[CHUNK];
    size_t fill = n<CHUNK?n:CHUNK;
    for (size_t i=0; i<fill; i++) buf[i]=color;
    dc_data();
    spi_transaction_t t = {};
    while (n>0) {
        size_t c = n<CHUNK?n:CHUNK;
        t.length=c*16; t.tx_buffer=buf;
        spi_device_polling_transmit(g_spi, &t);
        n-=c;
    }
}

void st7789_draw_pixel(uint16_t x, uint16_t y, uint16_t c) {
    if (x>=W||y>=H) return;
    set_window(x,y,x,y);
    dc_data();
    spi_transaction_t t = { .length=16, .tx_buffer=&c };
    spi_device_polling_transmit(g_spi, &t);
}

void st7789_draw_hline(uint16_t x0, uint16_t x1, uint16_t y, uint16_t c) {
    if (y>=H) return;
    if (x0>x1) { uint16_t t=x0; x0=x1; x1=t; }
    if (x1>=W) x1=W-1;
    st7789_fill_rect(x0,y,x1,y,c);
}

void st7789_draw_vline(uint16_t x, uint16_t y0, uint16_t y1, uint16_t c) {
    if (x>=W) return;
    if (y0>y1) { uint16_t t=y0; y0=y1; y1=t; }
    if (y1>=H) y1=H-1;
    st7789_fill_rect(x,y0,x,y1,c);
}

void st7789_draw_rect(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1, uint16_t c) {
    if (x0>x1) { uint16_t t=x0; x0=x1; x1=t; }
    if (y0>y1) { uint16_t t=y0; y0=y1; y1=t; }
    st7789_draw_hline(x0,x1,y0,c); st7789_draw_hline(x0,x1,y1,c);
    st7789_draw_vline(x0,y0,y1,c); st7789_draw_vline(x1,y0,y1,c);
}

void st7789_draw_bitmap(uint16_t x, uint16_t y, uint16_t w, uint16_t h, const uint16_t *bmp) {
    if (!bmp||x>=W||y>=H) return;
    if (x+w>W) w=W-x;
    if (y+h>H) h=H-y;
    set_window(x,y,x+w-1,y+h-1);
    dc_data();
    spi_transaction_t t = { .length=(size_t)w*h*16, .tx_buffer=bmp };
    spi_device_polling_transmit(g_spi, &t);
}

void st7789_set_rotation(uint8_t r) {
    g_rot=r&3;
    uint8_t m;

    /* 1.54寸 IPS 模块方向配置
     * Bit 7: MY (行地址顺序)
     * Bit 6: MX (列地址顺序)
     * Bit 5: MV (行/列交换)
     * Bit 3: RGB/BGR (0=RGB, 1=BGR)
     *
     * 0x40 = MX (水平镜像，修正文字方向)
     */
    switch(g_rot) {
    case 0: m=0x40; break;  /* 竖向 + MX */
    case 1: m=0x70; break;  /* 横屏 + MX + MV */
    case 2: m=0xD0; break;  /* 竖向翻转 + MX + MY */
    case 3: m=0xB0; break;  /* 横屏翻转 + MX + MY + MV */
    }

    send_cmd_data(CMD_MADCTL, &m, 1);
}

void st7789_set_madctl(uint8_t val) {
    uint8_t d = val;
    send_cmd_data(CMD_MADCTL, &d, 1);
    g_rot = 0;  /* 手动MADCTL时，rotation状态重置 */
}

void st7789_set_invert(bool inv) {
    send_cmd(inv ? CMD_INVON : CMD_INVOFF);
}

void st7789_get_size(uint16_t *w, uint16_t *h) {
    if (g_rot&1) { *w=H; *h=W; } else { *w=W; *h=H; }
}
