"""AI Agent Deck - 工具模块"""
from .version import __version__, APP_NAME, APP_AUTHOR
from .logger import setup_logging, get_logger
from .crash_handler import setup_crash_handler, manual_crash_report, set_restart_callback
