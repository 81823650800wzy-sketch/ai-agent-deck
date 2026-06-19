# ESP32 固件烧录管理器使用指南

## 功能概述

ESP32 固件烧录管理器是一个图形化工具，用于将固件烧录到 ESP32-S3 设备。

## 启动方式

### 方式一：从主程序启动

1. 运行主程序：`python main.py` 或双击 `start.bat`
2. 在左侧面板点击"烧录固件"按钮

### 方式二：独立启动

```bash
python flash.py
```

或双击 `flash.bat`

## 使用步骤

### 1. 连接设备

使用 USB 线将 ESP32-S3 开发板连接到电脑。

### 2. 选择串口

- 程序会自动检测可用串口
- 从下拉列表选择正确的串口（通常是 COM7）
- 点击"刷新"按钮更新串口列表
- 点击"检测"按钮验证设备连接

### 3. 选择固件

- 默认会自动加载 `firmware/` 目录下的固件
- 点击"浏览"按钮可以选择其他固件文件
- 支持 `.bin` 格式的固件文件

### 4. 开始烧录

- 点击"开始烧录"按钮
- 在确认对话框中点击"是"
- 等待烧录完成

### 5. 烧录过程

烧录过程分为以下阶段：

1. **准备** - 检查固件文件
2. **连接** - 连接到串口
3. **擦除** - 擦除 Flash
4. **烧录** - 写入固件
5. **完成** - 设备自动重启

## 进度和日志

- 进度条显示烧录进度
- 日志区域显示详细信息
- 可以点击"清空日志"按钮清除日志

## 取消烧录

在烧录过程中，可以点击"取消"按钮停止烧录。

## 固件文件

默认固件位置：`firmware/`

| 文件 | 说明 |
|------|------|
| ai_agent_deck.bin | 主固件 |
| bootloader.bin | 引导程序 |
| partition-table.bin | 分区表 |
| ota_data_initial.bin | OTA 数据 |
| version.json | 版本信息 |

## 常见问题

### Q: 找不到串口

A: 检查以下几点：
- USB 线是否连接好
- 驱动是否安装（CP2102 或 CH340）
- 设备管理器中是否显示串口

### Q: 烧录失败

A: 尝试以下方法：
- 检查串口是否被其他程序占用
- 降低波特率（修改 flash_manager.py 中的 BAUD 值）
- 按住 BOOT 按钮再烧录

### Q: 固件文件不存在

A: 检查以下几点：
- `firmware/` 目录是否存在
- 固件文件是否完整
- 点击"浏览"手动选择固件文件

## 技术细节

### 烧录参数

| 参数 | 值 |
|------|-----|
| 芯片 | ESP32-S3 |
| 波特率 | 460800 |
| Flash 大小 | 8MB |
| Flash 模式 | DIO |
| Flash 频率 | 80MHz |

### 分区地址

| 分区 | 地址 |
|------|------|
| bootloader | 0x0 |
| partition-table | 0x8000 |
| ota_data | 0x10000 |
| app | 0x20000 |

## 更新固件

### 从源码编译

```bash
cd D:\AI-Agent-Deck\Firmware
idf.py build
```

### 复制固件

```bash
cd D:\AI-Agent-Deck\Manager
python -c "from app.core.flash_manager import copy_firmware_to_resources; copy_firmware_to_resources()"
```

## 相关文件

- `app/core/flash_manager.py` - 烧录管理器核心
- `app/ui/flash_dialog.py` - 烧录对话框 UI
- `firmware/` - 固件文件目录
