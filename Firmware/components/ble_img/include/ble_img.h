#pragma once
#include <stdbool.h>
#include <stdint.h>

// 控制命令
#define CMD_SHOW_IMAGE   0x01
#define CMD_GIF_START    0x02
#define CMD_GIF_FRAME    0x03
#define CMD_GIF_END      0x04
#define CMD_SET_DELAY    0x05
#define CMD_CLEAR        0x06

// 状态码
#define STATUS_OK        0x00
#define STATUS_ERR_LEN   0x01
#define STATUS_ERR_SEQ   0x02
#define STATUS_ERR_STATE 0x03
#define STATUS_READY     0x04
#define STATUS_FRAME_ACK 0x05

// 回调
typedef void (*ble_ctrl_cb_t)(const uint8_t *data, uint16_t len);
typedef void (*ble_data_cb_t)(const uint8_t *data, uint16_t len);
typedef void (*ble_status_cb_t)(bool connected);

typedef struct {
    ble_ctrl_cb_t  on_ctrl;
    ble_data_cb_t  on_data;
    ble_status_cb_t on_status;
} ble_img_callbacks_t;

void ble_img_init(const ble_img_callbacks_t *cb);
bool ble_img_is_connected(void);
