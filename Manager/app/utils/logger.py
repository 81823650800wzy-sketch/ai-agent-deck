"""
AI Agent Deck - 日志框架
支持控制台 + 文件输出，自动轮转
"""

import logging
import logging.handlers
import sys
from pathlib import Path


def get_log_dir() -> Path:
    """获取日志目录（跨平台）"""
    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Local" / "AI-Deck-Manager"
    else:
        base = Path.home() / ".ai-deck-manager"
    log_dir = base / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


class QtLogHandler(logging.Handler):
    """将日志转发到 Qt 信号（用于 UI 日志面板）"""

    def __init__(self, signal=None):
        super().__init__()
        self._signal = signal

    def set_signal(self, signal):
        self._signal = signal

    def emit(self, record):
        if self._signal:
            msg = self.format(record)
            try:
                self._signal.emit(record.levelname, msg)
            except Exception:
                pass


# 全局 Qt 日志处理器实例
_qt_handler = QtLogHandler()


def setup_logging(level=logging.DEBUG, log_to_file=True):
    """
    配置全局日志

    Args:
        level: 日志级别
        log_to_file: 是否输出到文件
    """
    root = logging.getLogger()
    root.setLevel(level)

    # 清除已有处理器
    root.handlers.clear()

    # 格式
    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-7s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    detailed_fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-7s %(name)s (%(filename)s:%(lineno)d): %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 控制台处理器
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    root.addHandler(console)

    # 文件处理器（轮转，最多 5 个 2MB 文件）
    if log_to_file:
        log_dir = get_log_dir()
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "ai_deck.log",
            maxBytes=2 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_fmt)
        root.addHandler(file_handler)

    # Qt 信号处理器
    _qt_handler.setLevel(logging.DEBUG)
    _qt_handler.setFormatter(fmt)
    root.addHandler(_qt_handler)

    logging.info("日志系统初始化完成 (级别=%s, 文件=%s)", level, log_to_file)


def get_logger(name: str) -> logging.Logger:
    """获取命名日志器"""
    return logging.getLogger(name)


def set_qt_signal(signal):
    """设置 Qt 信号，将日志转发到 UI"""
    _qt_handler.set_signal(signal)


def setup_ui_bridge(log_panel):
    """
    将 LogPanel 桥接到 Python 日志系统

    创建一个 logging.Handler，将日志消息转发到 LogPanel 控件
    """
    class LogPanelHandler(logging.Handler):
        def __init__(self, panel):
            super().__init__()
            self._panel = panel
            self._level_map = {
                'DEBUG': 'DEBUG',
                'INFO': 'INFO',
                'WARNING': 'WARN',
                'ERROR': 'ERROR',
                'CRITICAL': 'ERROR',
            }

        def emit(self, record):
            try:
                msg = self.format(record)
                level = self._level_map.get(record.levelname, 'INFO')
                tag = record.name or 'root'

                # 使用 QTimer 在 Qt 主线程中更新 UI
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, lambda: self._panel.add_log(level, tag, msg))
            except Exception:
                pass

    handler = LogPanelHandler(log_panel)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(
        "%(message)s"
    ))

    # 添加到根日志器
    logging.getLogger().addHandler(handler)
