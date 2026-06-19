# AI Agent Deck Manager v2.1.0

Context-Aware Workflow Controller — 桌面端管理软件

## 核心功能

**自动识别当前软件 → 自动切换 Profile → 屏幕实时反馈**

```
用户打开 VSCode
    ↓
设备自动切换: Programming Mode
    K1 Undo | K2 Build | K3 Debug | K4 Review | K5 Terminal | K6 Explain

用户切换 Blender
    ↓
设备自动切换: Blender Mode
    K1 Bevel | K2 Extrude | K3 Grab | K4 Modifier | K5 Render | K6 Explain
```

## 架构

```
┌─────────────────────────────────────────────────────────┐
│                      PC Manager                         │
│                                                         │
│  WindowDetector ──→ ProfileManager ──→ DeviceManager    │
│  (检测前台应用)    (匹配 Profile)    (BLE/串口/WiFi)     │
│                                                         │
│  WorkflowManager (协调以上组件)                           │
│  pynput (监听 F13-F18 执行动作)                          │
└────────────────────────┬────────────────────────────────┘
                         │ BLE GATT / Serial / WiFi TCP
                         ▼
┌─────────────────────────────────────────────────────────┐
│                     ESP32 Firmware                      │
│                                                         │
│  ProfileReceiver ──→ g_current_profile ──→ draw_ui()    │
│  (接收 JSON)        (全局按键映射)       (刷新屏幕)      │
│                                                         │
│  按键矩阵 ──→ send_keyboard_key(F13-F18) ──→ PC        │
└─────────────────────────────────────────────────────────┘
```

## 文件结构

```
Manager/
├── app/                    # 应用主模块
│   ├── main.py             # 应用入口 (含闪屏)
│   ├── version.py          # 版本兼容层
│   ├── utils/              # 工具模块
│   │   ├── version.py      # 版本单一真相源
│   │   ├── logger.py       # 日志框架
│   │   └── crash_handler.py # 崩溃处理
│   ├── core/               # 核心引擎
│   │   ├── engine.py       # 引擎
│   │   ├── device.py       # BLE/串口设备
│   │   ├── wifi_device.py  # WiFi 设备
│   │   ├── profile.py      # Profile 管理
│   │   ├── flash_manager.py # 固件烧录
│   │   └── wallpaper_manager.py
│   ├── ui/                 # PyQt5 UI
│   │   ├── modern_window.py # 主窗口
│   │   ├── modern_theme.py  # 主题系统
│   │   ├── modern_widgets.py # 自定义组件
│   │   ├── profile_editor.py # Profile 编辑器
│   │   ├── setup_dialog.py  # 设置向导
│   │   ├── about_dialog.py  # 关于对话框
│   │   └── log_panel.py     # 日志面板
│   ├── ai/                 # AI 推荐
│   └── data/               # 数据分析
├── firmware/               # 固件文件
│   ├── ai_agent_deck.bin
│   ├── bootloader.bin
│   └── version.json
├── profiles/               # Profile 配置
├── pyproject.toml          # Python 打包配置
├── LICENSE                 # MIT 许可证
├── requirements.txt        # 依赖
├── build.bat               # 构建脚本
├── start.bat               # 启动脚本
└── AI_Deck_Manager.spec    # PyInstaller 配置

installer/
├── AI_Deck_Manager.iss     # Inno Setup 安装包脚本
└── build_installer.bat     # 安装包构建脚本
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行应用

```bash
# 方式一: 直接运行
python run_app.py

# 方式二: 双击启动
start.bat

# 方式三: 模块方式
python -m app
```

### 3. 打包发布

```bash
# 构建 PyInstaller 包
build.bat
# → dist/AI_Deck_Manager/AI_Deck_Manager.exe

# 创建 Windows 安装包 (需要 Inno Setup 6)
cd installer
build_installer.bat
# → dist/AI_Deck_Manager_Setup_2.1.0.exe
```

## 功能特性

### 连接方式

| 方式 | 说明 | 适用场景 |
|------|------|----------|
| 串口 | USB 直连，最可靠 | 开发调试 |
| BLE | 蓝牙无线连接 | 日常使用 |
| WiFi | TCP 网络连接 | 远程控制 |

### 固件烧录

主界面点击"烧录固件"按钮，或使用命令行：

```bash
# 检测 ESP32
python -m esptool --chip esp32s3 --port COM7 chip_id

# 烧录固件
python -m esptool --chip esp32s3 --port COM7 --baud 460800 \
  write_flash --flash_mode dio --flash_size 8MB --flash_freq 80m \
  0x0 firmware/bootloader.bin \
  0x8000 firmware/partition-table.bin \
  0x10000 firmware/ota_data_initial.bin \
  0x20000 firmware/ai_agent_deck.bin
```

### Profile 管理

- **GUI 编辑器**: 点击"管理 Profile"按钮
- **手动编辑**: 在 `profiles/` 目录下创建 JSON 文件

```json
{
  "name": "MyApp",
  "process_names": ["myapp.exe"],
  "keys": [
    {"id": "K1", "display": "Action1", "action": "key_combo", "value": "ctrl+shift+a"},
    {"id": "K2", "display": "Action2", "action": "open_url", "value": "https://..."}
  ]
}
```

支持的动作类型:
- `key_combo`: 组合键 (如 `ctrl+z`, `f5`)
- `command`: 执行命令 (如 `notepad`)
- `open_url`: 打开网页
- `script`: 运行脚本

### 内置 Profile

| Profile | 应用 | K1 | K2 | K3 | K4 | K5 | K6 |
|---------|------|----|----|----|----|----|----|
| VSCode | code.exe | Undo | Build | Debug | Review | Terminal | Explain |
| Blender | blender.exe | Bevel | Extrude | Grab | Modifier | Render | Explain |
| KiCad | kicad.exe | Route | Move | Rotate | DRC | Review | Annotate |
| Word | WINWORD.EXE | Save | Bold | Undo | Find | Print | AI Write |
| Chrome | chrome.exe | New Tab | Close | Reopen | Bookmark | DevTools | Find |
| Default | * | Copy | Paste | Undo | Save | Select | Close |

## 日志和崩溃处理

### 日志位置

- Windows: `%USERPROFILE%\AppData\Local\AI-Deck-Manager\logs\`
- 自动轮转，最多 5 个 2MB 文件

### 崩溃报告

- Windows: `%USERPROFILE%\AppData\Local\AI-Deck-Manager\crashes\`
- 自动捕获未处理异常
- 包含系统信息、调用栈、日志

## 开发

### 依赖

```
pywin32>=306        # Windows API
psutil>=5.9.0       # 进程管理
pynput>=1.7.6       # 键盘监听
bleak>=0.21.0       # BLE 通信
PyQt5>=5.15.0       # GUI 框架
Pillow>=10.0.0      # 图像处理
pyserial>=3.5       # 串口通信
esptool>=4.7.0      # ESP32 烧录
```

### 运行测试

```bash
python test_crash_handler.py  # 测试崩溃处理器
```

## 许可证

MIT License - 详见 [LICENSE](LICENSE)
