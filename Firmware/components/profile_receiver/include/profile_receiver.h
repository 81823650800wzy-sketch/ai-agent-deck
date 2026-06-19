/**
 * AI Agent Deck - Profile 接收器
 * 通过 BLE GATT 接收 PC Manager 发送的 Profile 数据
 */

#pragma once

#include "esp_err.h"
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ── 按键映射 ─────────────────────────────── */
#define PROFILE_MAX_KEYS    6
#define PROFILE_NAME_LEN    32
#define PROFILE_KEY_NAME_LEN 16

typedef struct {
    char id[4];                     /* K1-K6 */
    char display[PROFILE_KEY_NAME_LEN]; /* 显示名 */
    char action[32];                /* 动作描述 */
} profile_key_t;

typedef struct {
    char name[PROFILE_NAME_LEN];   /* Profile 名称 */
    int key_count;                  /* 按键数量 */
    profile_key_t keys[PROFILE_MAX_KEYS]; /* 按键映射 */
    bool valid;                     /* 数据有效标志 */
} current_profile_t;

/* ── 外部可访问的全局 Profile ────────────── */
extern current_profile_t g_current_profile;

/* ── 初始化 Profile 接收服务 ─────────────── */
esp_err_t profile_receiver_init(void);

/* ── GATTS 事件处理 (由 main.c 统一回调调用) ── */
void profile_gatts_handler(esp_gatts_cb_event_t event,
                            esp_gatt_if_t gatts_if,
                            esp_ble_gatts_cb_param_t *param);

/* ── 发送确认到 PC ───────────────────────── */
void profile_send_ack(const char *profile_name, int key_count);

/* ── 发送心跳响应 ─────────────────────────── */
void profile_send_pong(void);

/* ── 更新全局按键映射 ────────────────────── */
void profile_update_keymap(const current_profile_t *profile);

/* ── 刷新屏幕显示 ────────────────────────── */
void profile_refresh_display(void);

#ifdef __cplusplus
}
#endif
