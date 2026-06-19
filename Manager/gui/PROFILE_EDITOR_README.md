# Profile 编辑器

## 功能概述

Profile 编辑器是 AI Agent Deck Manager 的 GUI 组件，允许用户可视化编辑按键映射配置。

## 主要功能

### 1. Profile 列表管理 (`ProfileListDialog`)

- 显示所有 Profile 列表
- 新建 Profile
- 编辑现有 Profile
- 删除 Profile
- 双击快速编辑

### 2. Profile 编辑器 (`ProfileEditorDialog`)

- 编辑 Profile 名称
- 管理进程名列表（添加/删除）
- 编辑 6 个按键的映射配置
  - 显示名称
  - 动作类型（key_combo, open_url, command, script）
  - 动作值
- 实时预览功能

## 文件结构

```
gui/
├── __init__.py           # 模块导出
├── app.py                # 完整 GUI 应用
├── main_window.py        # 主窗口
└── profile_editor.py     # Profile 编辑器
```

## 使用方法

### 方法一: 通过主应用

1. 运行主应用:
   ```bash
   python main.py
   ```

2. 点击 "管理 Profile" 按钮

3. 在弹出的对话框中:
   - 点击 "新建" 创建新 Profile
   - 选择现有 Profile 并点击 "编辑"
   - 选择 Profile 并点击 "删除"

### 方法二: 编程方式

```python
from profile_manager import ProfileManager, Profile, KeyMapping
from gui.profile_editor import ProfileEditorDialog, ProfileListDialog

# 创建 Profile 管理器
pm = ProfileManager()

# 创建新 Profile
new_profile = Profile(
    name="MyApp",
    process_names=["myapp.exe"],
    keys=[
        KeyMapping("K1", "保存", "key_combo", "ctrl+s"),
        KeyMapping("K2", "复制", "key_combo", "ctrl+c"),
        # ... 更多按键
    ]
)

# 保存到管理器
pm.add_profile(new_profile)
```

## 支持的动作类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `key_combo` | 组合键 | `ctrl+z`, `ctrl+shift+b`, `f5` |
| `open_url` | 打开网页 | `https://example.com` |
| `command` | 执行命令 | `cursor`, `start cmd` |
| `script` | 运行脚本 | `scripts/my_script.py` |

## 界面预览

### Profile 列表对话框

```
┌─────────────────────────────────────┐
│ Profile 管理                        │
├─────────────────────────────────────┤
│ ┌─────────────────────────────────┐ │
│ │ Blender                         │ │
│ │ Chrome                          │ │
│ │ Default                         │ │
│ │ KiCad                           │ │
│ │ VSCode                          │ │
│ │ Word                            │ │
│ └─────────────────────────────────┘ │
├─────────────────────────────────────┤
│ [新建] [编辑] [删除]        [关闭] │
│ 共 6 个 Profile                     │
└─────────────────────────────────────┘
```

### Profile 编辑器对话框

```
┌─────────────────────────────────────┐
│ 编辑 Profile                        │
├─────────────────────────────────────┤
│ 基本信息                            │
│ Profile 名称: [VSCode          ]   │
│ 进程名:       [Code.exe        ]   │
│               [添加] [删除]         │
├─────────────────────────────────────┤
│ 按键映射                            │
│ K1 [Undo    ] [key_combo v] [ctrl+z]│
│ K2 [Build   ] [key_combo v] [ctrl+…]│
│ K3 [Debug   ] [key_combo v] [f5    ]│
│ K4 [Review  ] [key_combo v] [ctrl+…]│
│ K5 [Terminal] [key_combo v] [ctrl+…]│
│ K6 [Explain ] [key_combo v] [ctrl+…]│
├─────────────────────────────────────┤
│ [预览]                      [取消][保存]│
└─────────────────────────────────────┘
```

## 技术实现

- 使用 tkinter 构建 GUI
- 模块化设计，易于扩展
- 支持 Profile 的 CRUD 操作
- 实时预览配置效果
- 数据持久化到 JSON 文件

## 依赖

- Python 3.10+
- tkinter (Python 标准库)
- profile_manager 模块

## 注意事项

1. Profile 名称必须唯一
2. 进程名区分大小写（匹配时自动转小写）
3. 通配符 `*` 用于匹配所有未配置的应用
4. 修改后自动保存到 `profiles/` 目录
