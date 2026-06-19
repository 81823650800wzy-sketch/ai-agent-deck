"""
AI Agent Deck - 崩溃处理器
捕获未处理异常，生成崩溃报告，显示错误对话框
支持主线程和子线程异常捕获
"""

import sys
import traceback
import logging
import platform
import threading
import faulthandler
import io
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger(__name__)

# 全局状态
_crash_dir: Optional[Path] = None
_restart_callback: Optional[Callable] = None


def get_crash_dir() -> Path:
    """获取崩溃报告目录"""
    global _crash_dir
    if _crash_dir is not None:
        return _crash_dir

    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Local" / "AI-Deck-Manager"
    else:
        base = Path.home() / ".ai-deck-manager"
    _crash_dir = base / "crashes"
    _crash_dir.mkdir(parents=True, exist_ok=True)
    return _crash_dir


def _collect_system_info() -> str:
    """收集系统信息用于崩溃报告"""
    info_lines = [
        "系统信息:",
        f"  操作系统: {platform.system()} {platform.release()} {platform.version()}",
        f"  架构: {platform.machine()}",
        f"  Python: {sys.version}",
        f"  可执行文件: {sys.executable}",
        f"  工作目录: {Path.cwd()}",
        f"  命令行参数: {sys.argv}",
        f"  线程数: {threading.active_count()}",
        f"  当前线程: {threading.current_thread().name}",
    ]

    # PyQt5 信息
    try:
        from PyQt5.QtCore import QT_VERSION_STR, PYQT_VERSION_STR
        info_lines.extend([
            f"  Qt版本: {QT_VERSION_STR}",
            f"  PyQt5版本: {PYQT_VERSION_STR}",
        ])
    except ImportError:
        pass

    # 内存信息（如果 psutil 可用）
    try:
        import psutil
        process = psutil.Process()
        mem = process.memory_info()
        info_lines.extend([
            f"  内存使用: {mem.rss / 1024 / 1024:.1f} MB",
            f"  CPU使用: {process.cpu_percent(interval=0.1)}%",
        ])
    except ImportError:
        pass

    return "\n".join(info_lines)


def _collect_recent_logs(lines: int = 50) -> str:
    """收集最近的日志"""
    try:
        log_dir = Path.home() / "AppData" / "Local" / "AI-Deck-Manager" / "logs"
        if sys.platform != "win32":
            log_dir = Path.home() / ".ai-deck-manager" / "logs"

        log_file = log_dir / "ai_deck.log"
        if log_file.exists():
            with open(log_file, "r", encoding="utf-8") as f:
                all_lines = f.readlines()
                recent = all_lines[-lines:] if len(all_lines) > lines else all_lines
                return "".join(recent)
    except Exception:
        pass
    return "(无法读取日志)"


def _save_crash_report(exc_type, exc_value, exc_tb, thread_name: str = "MainThread"):
    """保存崩溃报告到文件"""
    try:
        crash_dir = get_crash_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        crash_file = crash_dir / f"crash_{timestamp}.txt"

        with open(crash_file, "w", encoding="utf-8") as f:
            f.write("AI Agent Deck - 崩溃报告\n")
            f.write("=" * 60 + "\n\n")

            # 基本信息
            f.write(f"崩溃时间: {datetime.now().isoformat()}\n")
            f.write(f"崩溃线程: {thread_name}\n")
            f.write(f"异常类型: {exc_type.__name__}\n")
            f.write(f"异常信息: {str(exc_value)}\n\n")

            # 系统信息
            f.write(_collect_system_info())
            f.write("\n\n")

            # 异常详情
            f.write("异常详情:\n")
            f.write("-" * 60 + "\n")
            traceback.print_exception(exc_type, exc_value, exc_tb, file=f)

            # 调用栈
            f.write("\n\n调用栈:\n")
            f.write("-" * 60 + "\n")
            f.write("".join(traceback.format_tb(exc_tb)))

            # faulthandler 输出（如果可用）
            try:
                faulthandler_output = io.StringIO()
                faulthandler.dump_traceback(file=faulthandler_output)
                f.write("\n\n所有线程状态:\n")
                f.write("-" * 60 + "\n")
                f.write(faulthandler_output.getvalue())
            except Exception:
                pass

            # 最近日志
            f.write("\n\n最近日志:\n")
            f.write("-" * 60 + "\n")
            f.write(_collect_recent_logs())

        logger.error("崩溃报告已保存: %s", crash_file)
        return crash_file
    except Exception as e:
        logger.error("保存崩溃报告失败: %s", e)
        return None


def _show_crash_dialog(exc_type, exc_value, exc_tb, thread_name: str = "MainThread"):
    """显示崩溃对话框"""
    try:
        from PyQt5.QtWidgets import QApplication, QMessageBox
        from PyQt5.QtCore import Qt

        # 确保 QApplication 存在
        app = QApplication.instance()
        if app is None:
            return

        tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("AI Agent Deck - 程序错误")
        msg.setText(f"程序遇到了一个未处理的错误\n(线程: {thread_name})")
        msg.setInformativeText(
            "崩溃报告已保存到日志目录。\n"
            "您可以选择重启程序或查看详情。"
        )
        msg.setDetailedText(tb_str)
        msg.setStandardButtons(QMessageBox.Retry | QMessageBox.Close)
        msg.setDefaultButton(QMessageBox.Retry)

        ret = msg.exec_()
        if ret == QMessageBox.Retry:
            _restart_application()

    except Exception:
        pass


def _restart_application():
    """重启应用程序"""
    try:
        import subprocess
        logger.info("正在重启应用程序...")
        subprocess.Popen([sys.executable] + sys.argv)
        sys.exit(1)
    except Exception as e:
        logger.error("重启失败: %s", e)
        sys.exit(1)


def _global_exception_handler(exc_type, exc_value, exc_tb):
    """全局异常处理器（主线程）"""
    # KeyboardInterrupt 正常退出
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return

    logger.critical("未处理的异常", exc_info=(exc_type, exc_value, exc_tb))

    # 保存崩溃报告
    _save_crash_report(exc_type, exc_value, exc_tb, "MainThread")

    # 显示对话框
    _show_crash_dialog(exc_type, exc_value, exc_tb, "MainThread")


def _thread_exception_handler(args):
    """线程异常处理器"""
    exc_type = args.exc_type
    exc_value = args.exc_value
    exc_tb = args.exc_tb
    thread_name = args.thread.name if hasattr(args, 'thread') else "Unknown"

    logger.critical(
        "线程 '%s' 未处理的异常",
        thread_name,
        exc_info=(exc_type, exc_value, exc_tb)
    )

    # 保存崩溃报告
    _save_crash_report(exc_type, exc_value, exc_tb, thread_name)

    # 在主线程显示对话框
    try:
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, lambda: _show_crash_dialog(exc_type, exc_value, exc_tb, thread_name))
    except Exception:
        pass


def install_thread_exception_hook():
    """安装线程异常钩子"""
    threading.excepthook = _thread_exception_handler
    logger.info("线程异常钩子已安装")


def setup_crash_handler(enable_faulthandler: bool = True):
    """
    安装全局崩溃处理器

    Args:
        enable_faulthandler: 是否启用 faulthandler（用于死锁检测）
    """
    # 1. 主线程异常钩子
    sys.excepthook = _global_exception_handler
    logger.info("主线程异常钩子已安装")

    # 2. 线程异常钩子
    install_thread_exception_hook()

    # 3. faulthandler（用于死锁检测和段错误捕获）
    if enable_faulthandler:
        try:
            # 启用段错误时的 traceback 输出
            faulthandler.enable()
            logger.info("faulthandler 已启用")

            # 可选：设置超时检测死锁（开发模式下启用）
            # faulthandler.dump_traceback_later(timeout=30, repeat=True)
        except Exception as e:
            logger.warning("faulthandler 启用失败: %s", e)

    logger.info("崩溃处理器已安装完成")


def set_restart_callback(callback: Callable):
    """设置自定义重启回调"""
    global _restart_callback
    _restart_callback = callback


def manual_crash_report(message: str = "手动触发崩溃报告"):
    """手动触发崩溃报告（用于调试）"""
    try:
        raise RuntimeError(message)
    except RuntimeError:
        exc_type, exc_value, exc_tb = sys.exc_info()
        _save_crash_report(exc_type, exc_value, exc_tb, "Manual")
        logger.warning("手动崩溃报告已生成: %s", message)
