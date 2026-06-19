"""
AI Agent Deck - 版本信息（兼容层）
实际数据来自 app/utils/version.py
"""

from .utils.version import (
    __version__,
    __version_info__,
    APP_NAME,
    APP_AUTHOR,
    APP_DESCRIPTION,
    APP_URL,
    FIRMWARE_VERSION,
    FIRMWARE_BUILD,
)

# 兼容旧接口
VERSION = __version_info__
VERSION_STR = __version__
ORG_NAME = APP_AUTHOR
FULL_VERSION = __version__
PRERELEASE = ""
APP_DISPLAY_NAME = APP_NAME
BUILD_NUMBER = FIRMWARE_BUILD
BUILD_DATE = ""


def get_version_display() -> str:
    """用于 UI 显示的版本字符串"""
    return f"v{FULL_VERSION}"


def get_version_info() -> dict:
    """返回完整版本信息字典"""
    return {
        "version": VERSION_STR,
        "full_version": FULL_VERSION,
        "prerelease": PRERELEASE,
        "app_name": APP_NAME,
        "display_name": APP_DISPLAY_NAME,
        "description": APP_DESCRIPTION,
        "build_number": BUILD_NUMBER,
        "build_date": BUILD_DATE,
        "firmware_version": FIRMWARE_VERSION,
        "firmware_build": FIRMWARE_BUILD,
    }
