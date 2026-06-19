"""
AI Agent Deck - ESP32 固件烧录管理器对话框
支持串口烧录和进度显示
"""

import sys
import logging
from pathlib import Path
from typing import Optional

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QProgressBar, QTextEdit, QGroupBox, QFileDialog,
    QFrame, QSizePolicy, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor

from .modern_theme import ModernColors, ModernFonts
from .modern_widgets import Card, GradientButton, OutlineButton, StatusIndicator

logger = logging.getLogger(__name__)


class FlashWorker(QThread):
    """烧录工作线程"""
    progress = pyqtSignal(str, float, str)  # stage, progress, message
    finished = pyqtSignal(bool, str)         # success, message
    log = pyqtSignal(str)                    # 日志输出

    def __init__(self, flash_manager, port: str, firmware_path: Path = None):
        super().__init__()
        self.flash_manager = flash_manager
        self.port = port
        self.firmware_path = firmware_path
        self._cancel = False

    def cancel(self):
        """取消烧录"""
        self._cancel = True
        self.flash_manager.cancel()

    def run(self):
        """执行烧录"""
        try:
            # 设置进度回调
            def on_progress(progress):
                if self._cancel:
                    return
                self.progress.emit(
                    progress.stage,
                    progress.progress,
                    progress.message
                )
                self.log.emit(f"[{progress.stage}] {progress.message}")
                if progress.error:
                    self.log.emit(f"  错误: {progress.error}")

            self.flash_manager.set_progress_callback(on_progress)

            # 执行串口烧录
            success = self.flash_manager.flash_serial(
                self.port,
                self.firmware_path
            )

            if success:
                self.finished.emit(True, "烧录完成！设备将自动重启")
            else:
                self.finished.emit(False, "烧录失败，请查看日志")

        except Exception as e:
            self.log.emit(f"异常: {e}")
            self.finished.emit(False, f"烧录异常: {e}")


class ChipDetectWorker(QThread):
    """芯片检测工作线程"""
    result = pyqtSignal(bool, str)  # success, message

    def __init__(self, flash_manager, port: str):
        super().__init__()
        self.flash_manager = flash_manager
        self.port = port

    def run(self):
        """检测芯片"""
        try:
            info = self.flash_manager.detect_chip(self.port)
            if info:
                self.result.emit(True, f"检测到 ESP32 设备\n{info.get('output', '')}")
            else:
                self.result.emit(False, "未检测到 ESP32 设备")
        except Exception as e:
            self.result.emit(False, f"检测失败: {e}")


class FlashDialog(QDialog):
    """
    ESP32 固件烧录管理器对话框

    功能:
    - 选择串口
    - 选择固件文件
    - 检测芯片
    - 执行烧录
    - 显示进度和日志
    """

    def __init__(self, flash_manager, parent=None):
        super().__init__(parent)
        self.flash_manager = flash_manager
        self.flash_worker: Optional[FlashWorker] = None
        self.detect_worker: Optional[ChipDetectWorker] = None

        self._setup_ui()
        self._load_ports()
        self._load_default_firmware()

    def _setup_ui(self):
        """初始化界面"""
        self.setWindowTitle("ESP32 固件烧录管理器")
        self.setMinimumSize(600, 500)
        self.resize(700, 600)

        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 标题
        title_layout = QHBoxLayout()
        title = QLabel("ESP32 固件烧录")
        title.setFont(ModernFonts.HEADER)
        title.setStyleSheet(f"color: {ModernColors.TEXT_PRIMARY};")
        title_layout.addWidget(title)

        title_layout.addStretch()

        # 状态指示器
        self.status_indicator = StatusIndicator("就绪", "idle")
        title_layout.addWidget(self.status_indicator)

        layout.addLayout(title_layout)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet(f"color: {ModernColors.BORDER};")
        layout.addWidget(separator)

        # 串口和固件选择区域
        config_group = QGroupBox("配置")
        config_layout = QVBoxLayout(config_group)

        # 串口选择
        port_layout = QHBoxLayout()
        port_label = QLabel("串口:")
        port_label.setFixedWidth(60)
        port_label.setStyleSheet(f"color: {ModernColors.TEXT_SECONDARY};")
        port_layout.addWidget(port_label)

        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(150)
        port_layout.addWidget(self.port_combo)

        refresh_btn = OutlineButton("刷新")
        refresh_btn.setFixedWidth(60)
        refresh_btn.clicked.connect(self._load_ports)
        port_layout.addWidget(refresh_btn)

        detect_btn = OutlineButton("检测")
        detect_btn.setFixedWidth(60)
        detect_btn.clicked.connect(self._detect_chip)
        port_layout.addWidget(detect_btn)

        port_layout.addStretch()
        config_layout.addLayout(port_layout)

        # 固件选择
        firmware_layout = QHBoxLayout()
        firmware_label = QLabel("固件:")
        firmware_label.setFixedWidth(60)
        firmware_label.setStyleSheet(f"color: {ModernColors.TEXT_SECONDARY};")
        firmware_layout.addWidget(firmware_label)

        self.firmware_path_label = QLabel("未选择固件文件")
        self.firmware_path_label.setStyleSheet(f"""
            color: {ModernColors.TEXT_PRIMARY};
            background-color: {ModernColors.BG_INPUT};
            border: 1px solid {ModernColors.BORDER};
            border-radius: 6px;
            padding: 8px 12px;
        """)
        firmware_layout.addWidget(self.firmware_path_label)

        browse_btn = OutlineButton("浏览")
        browse_btn.setFixedWidth(60)
        browse_btn.clicked.connect(self._browse_firmware)
        firmware_layout.addWidget(browse_btn)

        config_layout.addLayout(firmware_layout)

        # 固件信息
        self.firmware_info_label = QLabel("")
        self.firmware_info_label.setStyleSheet(f"""
            color: {ModernColors.TEXT_TERTIARY};
            font-size: 10px;
            padding: 4px 0;
        """)
        config_layout.addWidget(self.firmware_info_label)

        layout.addWidget(config_group)

        # 进度区域
        progress_group = QGroupBox("烧录进度")
        progress_layout = QVBoxLayout(progress_group)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        progress_layout.addWidget(self.progress_bar)

        # 进度状态
        self.progress_label = QLabel("等待烧录...")
        self.progress_label.setStyleSheet(f"""
            color: {ModernColors.TEXT_SECONDARY};
            font-size: 11px;
        """)
        progress_layout.addWidget(self.progress_label)

        layout.addWidget(progress_group)

        # 日志区域
        log_group = QGroupBox("日志")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(ModernFonts.MONO)
        self.log_text.setMinimumHeight(150)
        log_layout.addWidget(self.log_text)

        # 日志控制按钮
        log_controls = QHBoxLayout()
        log_controls.addStretch()

        clear_log_btn = OutlineButton("清空日志")
        clear_log_btn.setFixedWidth(80)
        clear_log_btn.clicked.connect(self.log_text.clear)
        log_controls.addWidget(clear_log_btn)

        log_layout.addLayout(log_controls)
        layout.addWidget(log_group)

        # 操作按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_btn = OutlineButton("取消")
        self.cancel_btn.setFixedWidth(100)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_flash)
        button_layout.addWidget(self.cancel_btn)

        self.flash_btn = GradientButton("开始烧录")
        self.flash_btn.setFixedWidth(120)
        self.flash_btn.clicked.connect(self._start_flash)
        button_layout.addWidget(self.flash_btn)

        close_btn = OutlineButton("关闭")
        close_btn.setFixedWidth(80)
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def _load_ports(self):
        """加载可用串口列表"""
        self.port_combo.clear()

        try:
            import serial.tools.list_ports
            ports = serial.tools.list_ports.comports()

            for port in sorted(ports):
                # 显示端口名和描述
                desc = port.description if port.description else "未知设备"
                self.port_combo.addItem(f"{port.device} - {desc}", port.device)

            if self.port_combo.count() == 0:
                self.port_combo.addItem("未检测到串口", None)
                self._log("未检测到可用串口，请检查设备连接")
            else:
                self._log(f"检测到 {self.port_combo.count()} 个串口")

        except ImportError:
            self.port_combo.addItem("pyserial 未安装", None)
            self._log("错误: 请安装 pyserial: pip install pyserial")

    def _load_default_firmware(self):
        """加载默认固件路径"""
        firmware_path = self.flash_manager.get_firmware_path()
        if firmware_path:
            self._set_firmware_path(firmware_path)
        else:
            self.firmware_path_label.setText("未找到默认固件，请手动选择")

    def _browse_firmware(self):
        """浏览选择固件文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择固件文件",
            "",
            "固件文件 (*.bin);;所有文件 (*.*)"
        )

        if file_path:
            self._set_firmware_path(Path(file_path))

    def _set_firmware_path(self, path: Path):
        """设置固件路径"""
        self.firmware_path = path
        self.firmware_path_label.setText(str(path))

        # 显示固件信息
        if path.exists():
            size_kb = path.stat().st_size / 1024
            version = self.flash_manager.get_firmware_version()
            info = f"大小: {size_kb:.1f} KB"
            if version:
                info += f" | 版本: {version}"
            self.firmware_info_label.setText(info)
            self._log(f"已选择固件: {path.name} ({size_kb:.1f} KB)")
        else:
            self.firmware_info_label.setText("文件不存在!")
            self.firmware_info_label.setStyleSheet(f"color: {ModernColors.ERROR};")

    def _detect_chip(self):
        """检测串口上的 ESP32 芯片"""
        port = self.port_combo.currentData()
        if not port:
            self._log("请先选择串口")
            return

        self._log(f"正在检测 {port} 上的 ESP32 芯片...")
        self.status_indicator.set_status("connecting", "检测中...")

        # 禁用按钮
        self.detect_worker = ChipDetectWorker(self.flash_manager, port)
        self.detect_worker.result.connect(self._on_detect_result)
        self.detect_worker.start()

    def _on_detect_result(self, success: bool, message: str):
        """检测结果回调"""
        if success:
            self._log(f"检测成功: {message}")
            self.status_indicator.set_status("online", "已连接")
        else:
            self._log(f"检测失败: {message}")
            self.status_indicator.set_status("offline", "未连接")

    def _start_flash(self):
        """开始烧录"""
        # 检查串口
        port = self.port_combo.currentData()
        if not port:
            QMessageBox.warning(self, "错误", "请选择串口")
            return

        # 检查固件
        if not hasattr(self, 'firmware_path') or not self.firmware_path:
            QMessageBox.warning(self, "错误", "请选择固件文件")
            return

        if not self.firmware_path.exists():
            QMessageBox.warning(self, "错误", "固件文件不存在")
            return

        # 确认烧录
        reply = QMessageBox.question(
            self,
            "确认烧录",
            f"即将烧录固件到 {port}\n\n"
            f"固件: {self.firmware_path.name}\n\n"
            f"请确保设备已连接并进入下载模式。\n\n"
            f"是否继续？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # 更新 UI 状态
        self._set_flashing_state(True)
        self._log("=" * 50)
        self._log(f"开始烧录: {self.firmware_path.name} -> {port}")
        self._log("=" * 50)

        # 启动烧录线程
        self.flash_worker = FlashWorker(
            self.flash_manager,
            port,
            self.firmware_path
        )
        self.flash_worker.progress.connect(self._on_flash_progress)
        self.flash_worker.finished.connect(self._on_flash_finished)
        self.flash_worker.log.connect(self._log)
        self.flash_worker.start()

    def _cancel_flash(self):
        """取消烧录"""
        if self.flash_worker and self.flash_worker.isRunning():
            self.flash_worker.cancel()
            self._log("正在取消烧录...")

    def _on_flash_progress(self, stage: str, progress: float, message: str):
        """烧录进度回调"""
        self.progress_bar.setValue(int(progress * 100))
        self.progress_label.setText(message)

        # 更新状态指示器
        if stage == "connecting":
            self.status_indicator.set_status("connecting", "连接中...")
        elif stage in ["erasing", "flashing"]:
            self.status_indicator.set_status("online", "烧录中...")

    def _on_flash_finished(self, success: bool, message: str):
        """烧录完成回调"""
        self._set_flashing_state(False)

        if success:
            self.progress_bar.setValue(100)
            self.progress_label.setText("烧录完成!")
            self.status_indicator.set_status("online", "完成")
            self._log(message)
            QMessageBox.information(self, "成功", message)
        else:
            self.progress_label.setText("烧录失败")
            self.status_indicator.set_status("offline", "失败")
            self._log(f"错误: {message}")
            QMessageBox.critical(self, "失败", message)

    def _set_flashing_state(self, is_flashing: bool):
        """设置烧录状态"""
        self.flash_btn.setEnabled(not is_flashing)
        self.cancel_btn.setEnabled(is_flashing)
        self.port_combo.setEnabled(not is_flashing)

    def _log(self, message: str):
        """添加日志"""
        self.log_text.append(message)
        # 滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def closeEvent(self, event):
        """关闭事件"""
        if self.flash_worker and self.flash_worker.isRunning():
            reply = QMessageBox.question(
                self,
                "确认关闭",
                "烧录正在进行中，确定要关闭吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.flash_worker.cancel()
                self.flash_worker.wait(3000)  # 等待 3 秒
            else:
                event.ignore()
                return

        event.accept()
