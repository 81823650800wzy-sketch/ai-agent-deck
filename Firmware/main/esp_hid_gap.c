/*
 * ESP HID GAP 处理 (从 ESP-IDF 示例移植)
 */

#include <string.h>
#include "esp_hid_gap.h"

static const char *TAG = "ESP_HID_GAP";

static esp_ble_adv_params_t hid_adv_params = {
    .adv_int_min        = 0x20,
    .adv_int_max        = 0x30,
    .adv_type           = ADV_TYPE_IND,
    .own_addr_type      = BLE_ADDR_TYPE_PUBLIC,
    .channel_map        = ADV_CHNL_ALL,
    .adv_filter_policy  = ADV_FILTER_ALLOW_SCAN_ANY_CON_ANY,
};

esp_err_t esp_hid_gap_init(uint8_t mode)
{
    ESP_LOGI(TAG, "Initializing GAP (mode=%d)", mode);

    if (mode != HIDD_BLE_MODE) {
        ESP_LOGE(TAG, "Only BLE mode supported");
        return ESP_ERR_INVALID_ARG;
    }

    /* 释放经典蓝牙内存 */
    ESP_ERROR_CHECK(esp_bt_controller_mem_release(ESP_BT_MODE_CLASSIC_BT));

    /* 初始化蓝牙控制器 */
    esp_bt_controller_config_t bt_cfg = BT_CONTROLLER_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_bt_controller_init(&bt_cfg));
    ESP_ERROR_CHECK(esp_bt_controller_enable(ESP_BT_MODE_BLE));

    /* 初始化 Bluedroid */
    ESP_ERROR_CHECK(esp_bluedroid_init());
    ESP_ERROR_CHECK(esp_bluedroid_enable());

    ESP_LOGI(TAG, "GAP initialized");
    return ESP_OK;
}

esp_err_t esp_hid_gap_deinit(void)
{
    ESP_ERROR_CHECK(esp_bluedroid_disable());
    ESP_ERROR_CHECK(esp_bluedroid_deinit());
    ESP_ERROR_CHECK(esp_bt_controller_disable());
    ESP_ERROR_CHECK(esp_bt_controller_deinit());
    ESP_LOGI(TAG, "GAP deinitialized");
    return ESP_OK;
}

esp_err_t esp_hid_ble_gap_adv_init(uint16_t appearance, const char *device_name)
{
    ESP_LOGI(TAG, "Setting device name: %s", device_name);
    ESP_ERROR_CHECK(esp_ble_gap_set_device_name(device_name));

    /* 配置安全参数 - 允许配对 */
    esp_ble_auth_req_t auth_req = ESP_LE_AUTH_BOND;     /* 配对后绑定 */
    esp_ble_io_cap_t iocap = ESP_IO_CAP_NONE;           /* 无输入输出能力 */
    uint8_t key_size = 16;
    uint8_t init_key = ESP_BLE_ENC_KEY_MASK | ESP_BLE_ID_KEY_MASK;
    uint8_t rsp_key = ESP_BLE_ENC_KEY_MASK | ESP_BLE_ID_KEY_MASK;

    ESP_ERROR_CHECK(esp_ble_gap_set_security_param(ESP_BLE_SM_AUTHEN_REQ_MODE, &auth_req, sizeof(auth_req)));
    ESP_ERROR_CHECK(esp_ble_gap_set_security_param(ESP_BLE_SM_IOCAP_MODE, &iocap, sizeof(iocap)));
    ESP_ERROR_CHECK(esp_ble_gap_set_security_param(ESP_BLE_SM_MAX_KEY_SIZE, &key_size, sizeof(key_size)));
    ESP_ERROR_CHECK(esp_ble_gap_set_security_param(ESP_BLE_SM_SET_INIT_KEY, &init_key, sizeof(init_key)));
    ESP_ERROR_CHECK(esp_ble_gap_set_security_param(ESP_BLE_SM_SET_RSP_KEY, &rsp_key, sizeof(rsp_key)));

    /* 配置广播数据 */
    esp_ble_adv_data_t adv_data = {
        .set_scan_rsp        = false,
        .include_name        = true,
        .include_txpower     = true,
        .min_interval        = 0x0006,
        .max_interval        = 0x0010,
        .appearance          = appearance,
        .manufacturer_len    = 0,
        .p_manufacturer_data = NULL,
        .service_data_len    = 0,
        .p_service_data      = NULL,
        .service_uuid_len    = 0,
        .p_service_uuid      = NULL,
        .flag                = (ESP_BLE_ADV_FLAG_GEN_DISC | ESP_BLE_ADV_FLAG_BREDR_NOT_SPT),
    };
    ESP_ERROR_CHECK(esp_ble_gap_config_adv_data(&adv_data));

    ESP_LOGI(TAG, "Adv initialized (appearance=0x%04X)", appearance);
    return ESP_OK;
}

esp_err_t esp_hid_ble_gap_adv_start(void)
{
    ESP_LOGI(TAG, "Starting advertising");
    return esp_ble_gap_start_advertising(&hid_adv_params);
}
