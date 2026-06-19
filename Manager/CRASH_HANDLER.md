# 崩溃处理器使用说明

## 功能概述

崩溃处理器提供以下功能：

1. **全局异常捕获** - 捕获主线程未处理的异常
2. **线程异常捕获** - 捕获子线程中的异常
3. **崩溃报告生成** - 自动保存详细的崩溃信息
4. **错误对话框** - 显示用户友好的错误提示
5. **死锁检测** - 通过 faulthandler 检测死锁

## 崩溃报告内容

崩溃报告包含以下信息：

- 崩溃时间和线程
- 异常类型和消息
- 系统信息（OS、Python版本、Qt版本等）
- 完整的调用栈
- 所有线程状态（通过 faulthandler）
- 最近的应用日志

报告保存位置：
- Windows: `%USERPROFILE%\AppData\Local\AI-Deck-Manager\crashes\`
- Linux/Mac: `~/.ai-deck-manager/crashes/`

## 使用方法

### 基本使用

```python
from app.utils.crash_handler import setup_crash_handler

# 在应用启动时安装
setup_crash_handler()
```

### 手动触发崩溃报告

```python
from app.utils.crash_handler import manual_crash_report

# 用于调试或记录严重错误
manual_crash_report("发生了严重错误")
```

### 自定义重启逻辑

```python
from app.utils.crash_handler import set_restart_callback

def my_restart():
    # 自定义重启逻辑
    pass

set_restart_callback(my_restart)
```

## 测试

运行测试脚本验证功能：

```bash
python test_crash_handler.py
```

测试内容：
1. 手动崩溃报告生成
2. 未处理异常捕获
3. 线程异常捕获

## 配置选项

`setup_crash_handler()` 参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enable_faulthandler` | bool | True | 启用 faulthandler 用于死锁检测 |

## 注意事项

1. 崩溃处理器应在应用启动时尽早安装
2. 线程异常不会阻止程序退出，但会生成报告
3. faulthandler 在某些环境下可能不可用
4. 崩溃报告可能包含敏感信息，注意保护