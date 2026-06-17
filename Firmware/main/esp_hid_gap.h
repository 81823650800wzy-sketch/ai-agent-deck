/*
 * ESP HID GAP 处理 (从 ESP-IDF 示例移植)
 */

#ifndef _ESP_HID_GAP_H_
#define _ESP_HID_GAP_H_

#define HIDD_IDLE_MODE 0x00
#define HIDD_BLE_MODE 0x01

#include "esp_err.h"
#include "esp_log.h"
#include "esp_bt.h"
#include "esp_bt_defs.h"
#include "esp_bt_main.h"
#include "esp_gap_ble_api.h"
#include "esp_hid_common.h"

#ifdef __cplusplus
extern "C" {
#endif

esp_err_t esp_hid_gap_init(uint8_t mode);
esp_err_t esp_hid_gap_deinit(void);
esp_err_t esp_hid_ble_gap_adv_init(uint16_t appearance, const char *device_name);
esp_err_t esp_hid_ble_gap_adv_start(void);
void esp_hid_gap_event_handler(esp_gap_ble_cb_event_t event, esp_ble_gap_cb_param_t *param);

#ifdef __cplusplus
}
#endif

#endif /* _ESP_HID_GAP_H_ */
