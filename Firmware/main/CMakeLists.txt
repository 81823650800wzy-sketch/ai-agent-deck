idf_component_register(
    SRCS "main.c" "esp_hid_gap.c"
    INCLUDE_DIRS "."
    REQUIRES
        driver
        nvs_flash
        spi_flash
        esp_hid
        bt
        st7789
        ble_img
        gifdec
        ui
)
