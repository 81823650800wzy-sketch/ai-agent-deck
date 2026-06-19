"""
AI Agent Deck - ESP32 固件烧录管理器
支持串口烧录和 WiFi OTA 烧录
"""

import os
import sys
import time
import json
import base64
import logging
import threading
import subprocess
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class FlashMode(Enum):
    """烧录模式"""
    SERIAL = "serial"   # 串口烧录 (esptool)
    OTA = "ota"         # WiFi OTA 烧录


@dataclass
class FlashProgress:
    """烧录进度"""
    stage: str          # 当前阶段
    progress: float     # 0.0 - 1.0
    message: str        # 描述信息
    error: Optional[str] = None


class FlashManager:
    """
    ESP32 固件烧录管理器

    功能:
    - 串口烧录 (esptool)
    - WiFi OTA 烧录
    - 进度回调
    - 固件版本管理
    """

    # ESP32-S3 烧录参数
    CHIP = "esp32s3"
    BAUD = 460800
    FLASH_SIZE = "8MB"
    FLASH_MODE = "dio"
    FLASH_FREQ = "80m"

    # 分区地址
    BOOTLOADER_ADDR = 0x0
    PARTITION_ADDR = 0x8000
    OTA_DATA_ADDR = 0x10000
    APP_ADDR = 0x20000

    def __init__(self):
        self._firmware_dir = self._get_firmware_dir()
        self._progress_cb: Optional[Callable[[FlashProgress], None]] = None
        self._cancel_flag = False

    def _get_firmware_dir(self) -> Path:
        """获取固件目录"""
        # 优先使用打包后的资源目录
        if getattr(sys, 'frozen', False):
            base = Path(sys._MEIPASS)
        else:
            base = Path(__file__).parent.parent.parent
        return base / "firmware"

    def set_progress_callback(self, cb: Callable[[FlashProgress], None]):
        """设置进度回调"""
        self._progress_cb = cb

    def _report(self, stage: str, progress: float, message: str, error: str = None):
        """报告进度"""
        logger.info("[%s] %.0f%% %s", stage, progress * 100, message)
        if self._progress_cb:
            self._progress_cb(FlashProgress(stage, progress, message, error))

    def get_firmware_path(self) -> Optional[Path]:
        """获取固件文件路径"""
        path = self._firmware_dir / "ai_agent_deck.bin"
        if path.exists():
            return path
        # 尝试从项目目录查找
        project_firmware = Path(__file__).parent.parent.parent.parent / "Firmware" / "build" / "ai_agent_deck.bin"
        if project_firmware.exists():
            return project_firmware
        return None

    def get_firmware_version(self) -> Optional[str]:
        """获取固件版本"""
        version_file = self._firmware_dir / "version.json"
        if version_file.exists():
            try:
                with open(version_file, 'r') as f:
                    data = json.load(f)
                return data.get("version")
            except Exception:
                pass
        return None

    def cancel(self):
        """取消烧录"""
        self._cancel_flag = True

    def flash_serial(self, port: str, firmware_path: Path = None) -> bool:
        """
        串口烧录固件

        Args:
            port: 串口号 (如 COM7)
            firmware_path: 固件文件路径 (None 则使用默认)

        Returns:
            是否成功
        """
        self._cancel_flag = False

        if firmware_path is None:
            firmware_path = self.get_firmware_path()

        if not firmware_path or not firmware_path.exists():
            self._report("error", 0, "固件文件不存在", "找不到 ai_agent_deck.bin")
            return False

        self._report("prepare", 0, f"准备烧录: {firmware_path.name}")

        # 构建 esptool 命令
        cmd = [
            sys.executable, "-m", "esptool",
            "--chip", self.CHIP,
            "--port", port,
            "--baud", str(self.BAUD),
            "--before", "default_reset",
            "--after", "hard_reset",
            "write_flash",
            "--flash_mode", self.FLASH_MODE,
            "--flash_size", self.FLASH_SIZE,
            "--flash_freq", self.FLASH_FREQ,
            hex(self.BOOTLOADER_ADDR), str(self._firmware_dir / "bootloader.bin"),
            hex(self.PARTITION_ADDR), str(self._firmware_dir / "partition-table.bin"),
            hex(self.OTA_DATA_ADDR), str(self._firmware_dir / "ota_data_initial.bin"),
            hex(self.APP_ADDR), str(firmware_path),
        ]

        # 检查辅助文件是否存在
        for addr_name, path_str in [
            ("bootloader", self._firmware_dir / "bootloader.bin"),
            ("partition-table", self._firmware_dir / "partition-table.bin"),
            ("ota_data", self._firmware_dir / "ota_data_initial.bin"),
        ]:
            if not Path(path_str).exists():
                # 尝试从 Firmware/build 目录查找
                build_dir = Path(__file__).parent.parent.parent.parent / "Firmware" / "build"
                alt_path = build_dir / Path(path_str).name
                if alt_path.exists():
                    # 替换命令中的路径
                    cmd = [str(alt_path) if str(c) == str(path_str) else c for c in cmd]
                else:
                    self._report("error", 0, f"缺少文件: {Path(path_str).name}",
                                f"请先编译固件: idf.py build")
                    return False

        self._report("connecting", 0.1, f"连接 {port}...")

        try:
            # 使用 esptool Python API
            import esptool

            self._report("erasing", 0.2, "擦除 Flash...")

            # 构建参数列表
            args = [
                "--chip", self.CHIP,
                "--port", port,
                "--baud", str(self.BAUD),
                "--before", "default_reset",
                "--after", "hard_reset",
                "write_flash",
                "--flash_mode", self.FLASH_MODE,
                "--flash_size", self.FLASH_SIZE,
                "--flash_freq", self.FLASH_FREQ,
                hex(self.BOOTLOADER_ADDR), str(cmd[cmd.index(hex(self.BOOTLOADER_ADDR)) + 1]),
                hex(self.PARTITION_ADDR), str(cmd[cmd.index(hex(self.PARTITION_ADDR)) + 1]),
                hex(self.OTA_DATA_ADDR), str(cmd[cmd.index(hex(self.OTA_DATA_ADDR)) + 1]),
                hex(self.APP_ADDR), str(firmware_path),
            ]

            self._report("flashing", 0.3, "正在烧录...")

            # 调用 esptool
            esptool.main(args)

            self._report("done", 1.0, "烧录完成！设备将自动重启")
            return True

        except ImportError:
            self._report("error", 0, "esptool 未安装", "请运行: pip install esptool")
            return False
        except Exception as e:
            self._report("error", 0, f"烧录失败: {e}", str(e))
            return False

    def flash_ota(self, host: str, port: int = 3232, firmware_path: Path = None) -> bool:
        """
        WiFi OTA 烧录

        Args:
            host: ESP32 IP 地址
            port: OTA 端口 (默认 3232)
            firmware_path: 固件文件路径

        Returns:
            是否成功
        """
        self._cancel_flag = False

        if firmware_path is None:
            firmware_path = self.get_firmware_path()

        if not firmware_path or not firmware_path.exists():
            self._report("error", 0, "固件文件不存在")
            return False

        self._report("prepare", 0, f"WiFi OTA 烧录: {host}")

        try:
            # 使用 esptool OTA 功能
            import esptool

            args = [
                "--chip", self.CHIP,
                "--port", f"socket://{host}:3232",
                "--baud", "115200",
                "write_flash",
                "--flash_mode", self.FLASH_MODE,
                "--flash_size", self.FLASH_SIZE,
                hex(self.APP_ADDR), str(firmware_path),
            ]

            self._report("connecting", 0.2, f"连接 {host}...")
            esptool.main(args)

            self._report("done", 1.0, "OTA 烧录完成！")
            return True

        except ImportError:
            self._report("error", 0, "esptool 未安装", "请运行: pip install esptool")
            return False
        except Exception as e:
            self._report("error", 0, f"OTA 烧录失败: {e}", str(e))
            return False

    def detect_chip(self, port: str) -> Optional[dict]:
        """
        检测串口上的 ESP32 芯片

        Args:
            port: 串口号

        Returns:
            芯片信息字典，未检测到返回 None
        """
        try:
            import esptool
            import io
            import contextlib

            # 捕获 esptool 输出
            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                try:
                    args = ["--chip", "auto", "--port", port, "chip_id"]
                    esptool.main(args)
                except SystemExit:
                    pass

            output = f.getvalue()
            if "Chip ID" in output:
                return {"port": port, "output": output}
            return None

        except ImportError:
            logger.warning("esptool 未安装，无法检测芯片")
            return None
        except Exception as e:
            logger.debug("检测芯片失败: %s", e)
            return None


def copy_firmware_to_resources():
    """
    将编译好的固件复制到 Manager/firmware/ 目录
    用于打包和分发
    """
    import shutil

    src_dir = Path(__file__).parent.parent.parent.parent / "Firmware" / "build"
    dst_dir = Path(__file__).parent.parent.parent / "firmware"

    if not src_dir.exists():
        logger.error("固件编译目录不存在: %s", src_dir)
        return False

    dst_dir.mkdir(parents=True, exist_ok=True)

    files = [
        "ai_agent_deck.bin",
        "bootloader/bootloader.bin",
        "partition_table/partition-table.bin",
        "ota_data_initial.bin",
    ]

    for f in files:
        src = src_dir / f
        dst = dst_dir / Path(f).name
        if src.exists():
            shutil.copy2(src, dst)
            logger.info("复制固件: %s -> %s", src, dst)
        else:
            logger.warning("固件文件不存在: %s", src)

    # 保存版本信息
    version_info = {
        "version": "2.1.0",
        "build": "a16fe08",
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(dst_dir / "version.json", "w") as f:
        json.dump(version_info, f, indent=2)

    logger.info("固件复制完成")
    return True
