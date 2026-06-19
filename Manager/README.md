# AI Agent Deck Manager V2.0

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
│  (检测前台应用)    (匹配 Profile)    (BLE 发送)          │
│                                                         │
│  WorkflowManager (协调以上组件)                           │
│  pynput (监听 F13-F18 执行动作)                          │
└────────────────────────┬────────────────────────────────┘
                         │ BLE GATT
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
├── main.py               # 入口
├── workflow_manager.py   # 工作流协调器
├── window_detector.py    # 活动窗口检测
├── profile_manager.py    # Profile 管理
├── device_manager.py     # BLE 设备通信
├── test_workflow.py      # 端到端测试
├── profiles/             # Profile 配置文件 (自动生成)
│   ├── vscode.json
│   ├── blender.json
│   └── ...
├── gui/                  # GUI 模块
│   ├── __init__.py
│   ├── app.py            # 完整 GUI 应用
│   ├── main_window.py    # 主窗口
│   └── profile_editor.py # Profile 编辑器
├── scripts/              # 自定义脚本
├── requirements.txt      # Python 依赖
└── ai_deck_gui.py        # 旧版 GUI (保留)
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 测试链路 (不连接设备)

```bash
python test_workflow.py           # 单次测试
python test_workflow.py --monitor # 实时监控 (15秒)
```

### 3. 运行 (连接 ESP32)

```bash
python main.py                    # 默认 BLE 连接
python main.py --no-ble           # 离线模式 (仅窗口检测)
python main.py --scan             # 扫描 BLE 设备
python main.py --debug            # 调试日志
```

### 4. 测试 Profile 编辑器

```bash
python test_profile_editor.py     # 单独测试 Profile 编辑器
```

## 内置 Profile

| Profile | 应用 | K1 | K2 | K3 | K4 | K5 | K6 |
|---------|------|----|----|----|----|----|----|
| VSCode | Code.exe | Undo | Build | Debug | Review | Terminal | Explain |
| Blender | blender.exe | Bevel | Extrude | Grab | Modifier | Render | Explain |
| KiCad | kicad.exe | Route | Move | Rotate | DRC | Review | Annotate |
| Word | WINWORD.EXE | Save | Bold | Undo | Find | Print | AI Write |
| Chrome | chrome.exe | New Tab | Close | Reopen | Bookmark | DevTools | Find |
| Default | * | Copy | Paste | Undo | Save | Select | Close |

## 自定义 Profile

### 方式一: GUI 编辑器 (推荐)

运行 GUI 应用后，点击 "管理 Profile" 按钮，可以:
- 新建 Profile
- 编辑现有 Profile
- 删除 Profile
- 实时预览配置

### 方式二: 手动编辑 JSON

在 `profiles/` 目录下创建 JSON 文件:

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
- `key_combo`: 组合键 (如 `ctrl+z`, `ctrl+shift+b`, `f5`)
- `command`: 执行命令 (如 `cursor`, `start cmd`)
- `open_url`: 打开网页
- `script`: 运行 scripts/ 目录下的脚本

## BLE 通信协议

PC → ESP32 JSON 格式:

```json
{
  "cmd": "profile",
  "data": {
    "name": "VSCode",
    "keys": [
      {"id": "K1", "display": "Undo", "action": "ctrl+z"},
      {"id": "K2", "display": "Build", "action": "ctrl+shift+b"}
    ]
  }
}
```

ESP32 收到后:
1. 解析 JSON
2. 更新 `g_current_profile`
3. 刷新屏幕显示
4. 按键发送 F13-F18 到 PC

## 旧版 GUI

旧版 `ai_deck_gui.py` 仍可用，但已被新版 `main.py` 替代。
