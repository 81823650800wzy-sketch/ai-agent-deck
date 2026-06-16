# AI Agent Deck V1.0

桌面 AI 工作流控制终端 — 6键机械键盘 + OLED显示屏 + 摇杆 + BLE HID

## 项目简介

AI Agent Deck 是一款专为 AI 工作流设计的桌面硬件控制终端。在 AI 时代，用户频繁切换 ChatGPT、Claude、Cursor 等工具，需要一个专用物理设备来快速调用、监控和控制这些 AI 工具。

**核心特性**：
- 🔹 6个机械按键（一键触发 AI 工具快捷键）
- 🔹 1.54寸 IPS 显示屏（240×240，显示状态信息）
- 🔹 ALPS 摇杆（菜单导航）
- 🔹 BLE 5.0 HID（无线连接 PC）
- 🔹 1000mAh 电池（移动使用）
- 🔹 Pogo Pin 扩展接口（麦克风/摄像头/NFC 模块）

## 项目结构

```
D:\AI-Agent-Deck\
├── Docs/                          ← 项目文档
│   ├── 开发日志.md                ← 工作留痕
│   ├── 开发规划.md                ← 8周开发计划
│   └── Phase1-验证清单.md         ← Phase 1 验证清单
├── Firmware/                      ← ESP32-S3 固件
│   ├── CMakeLists.txt
│   ├── sdkconfig.defaults
│   ├── build.sh                   ← 构建脚本
│   ├── partitions.csv
│   ├── main/
│   │   ├── CMakeLists.txt
│   │   └── main.c                 ← 主程序 (Phase 1: 显示屏测试)
│   └── components/
│       ├── st7789/                ← 屏幕驱动
│       ├── ble_img/               ← BLE 图片传输服务
│       └── gifdec/                ← GIF 解码器
├── AndroidApp/                    ← Android APK 源码 (V2)
└── README.md                      ← 本文档
```

## 硬件接线

### ST7789 显示屏

| ESP32-S3 | ST7789 | 说明 |
|----------|--------|------|
| GPIO 11  | MOSI   | SPI 数据 |
| GPIO 12  | SCLK   | SPI 时钟 |
| GPIO 10  | CS     | 片选 |
| GPIO 9   | DC     | 数据/命令 |
| GPIO 8   | RST    | 复位 |
| GPIO 21  | BL     | 背光 |
| 3.3V     | VCC    | 电源 |
| GND      | GND    | 地 |

### 按键矩阵 (3×2)

| ESP32-S3 | 说明 |
|----------|------|
| GPIO 4   | ROW1 |
| GPIO 5   | ROW2 |
| GPIO 6   | ROW3 |
| GPIO 7   | COL1 |
| GPIO 15  | COL2 |

### 摇杆

| ESP32-S3 | 说明 |
|----------|------|
| GPIO 1   | VRx (ADC) |
| GPIO 2   | VRy (ADC) |
| GPIO 3   | SW (按键) |

## 快速开始

### 1. 构建固件

```bash
cd D:\AI-Agent-Deck\Firmware
bash build.sh build
```

### 2. 烧录固件

```bash
# 按住 BOOT 键插入 USB，然后执行：
bash build.sh flash COM3    # 替换 COM3 为实际端口
```

### 3. 串口监控

```bash
bash build.sh monitor COM3
```

### 4. 烧录+监控

```bash
bash build.sh flash_monitor COM3
```

## 开发阶段

| 阶段 | 内容 | 周期 | 状态 |
|------|------|------|------|
| Phase 1 | 开发板验证 | 第1-2周 | 🔄 进行中 |
| Phase 2 | 功能集成 | 第3-4周 | ⬜ 待开始 |
| Phase 3 | PCB设计 | 第5-6周 | ⬜ 待开始 |
| Phase 4 | 焊接调试 | 第7-8周 | ⬜ 待开始 |

## 技术规格

| 参数 | 值 |
|------|-----|
| MCU | ESP32-S3-WROOM-1-N8R8 |
| 主频 | 240MHz 双核 |
| Flash | 8MB |
| PSRAM | 8MB |
| 显示 | 1.54寸 IPS 240×240 ST7789 |
| 按键 | 6× Gateron G Pro 红轴 |
| 摇杆 | ALPS RKJXV122400R |
| 电池 | 503450 1000mAh LiPo |
| 连接 | BLE 5.0 HID |
| PCB | 90×90mm 4层板 |
| 成本 | 约232元/台 |

## 相关文档

- [开发日志](Docs/开发日志.md) - 工作留痕
- [开发规划](Docs/开发规划.md) - 8周开发计划
- [Phase 1 验证清单](Docs/Phase1-验证清单.md) - Phase 1 验证清单

## 许可证

MIT License
