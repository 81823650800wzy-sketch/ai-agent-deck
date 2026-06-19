"""
AI Agent Deck - 设备设置向导
集成 WiFi 配置、BLE 扫描、串口连接
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QProgressBar, QListWidget, QListWidgetItem,
    QGroupBox, QGridLayout, QTextEdit, QStackedWidget, QWidget,
    QMessageBox, QFrame
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor

from .modern_theme import ModernColors


class BLEScanWorker(QThread):
    """BLE 扫描线程"""
    found = pyqtSignal(str, str, int)  # name, address, rssi
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def run(self):
        try:
            import asyncio
            from bleak import BleakScanner

            async def _scan():
                devices = await BleakScanner.discover(timeout=10.0, return_adv=True)
                for addr, (dev, adv) in devices.items():
                    name = dev.name or "(unnamed)"
                    rssi = adv.rssi if hasattr(adv, 'rssi') else -100
                    self.found.emit(name, addr, rssi)

            asyncio.run(_scan())
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()


class SerialConfigWorker(QThread):
    """串口配置 WiFi 线程"""
    result = pyqtSignal(bool, str)  # success, message

    def __init__(self, port, ssid, password):
        super().__init__()
        self.port = port
        self.ssid = ssid
        self.password = password

    def run(self):
        try:
            import serial
            import json
            import time

            ser = serial.Serial(self.port, 115200, timeout=2)
            time.sleep(0.5)

            cmd = json.dumps({
                "cmd": "wifi_save",
                "ssid": self.ssid,
                "pass": self.password
            })
            ser.write((cmd + "\n").encode("utf-8"))
            ser.flush()

            deadline = time.time() + 5
            while time.time() < deadline:
                if ser.in_waiting:
                    data = ser.read(ser.in_waiting).decode("utf-8", errors="replace")
                    if "saved" in data or "ok" in data.lower():
                        ser.close()
                        self.result.emit(True, "WiFi 配置已保存！ESP32 将在重启后连接。")
                        return
                time.sleep(0.1)

            ser.close()
            self.result.emit(True, "配置已发送（未收到确认，可能已生效）")

        except ImportError:
            self.result.emit(False, "需要安装 pyserial: pip install pyserial")
        except Exception as e:
            self.result.emit(False, f"错误: {e}")


class SetupDialog(QDialog):
    """设备设置向导"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI Agent Deck - 设备设置")
        self.setMinimumSize(600, 500)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # 标题
        title = QLabel("设备设置向导")
        title.setStyleSheet(f"""
            font-size: 20px;
            font-weight: bold;
            color: {ModernColors.TEXT_PRIMARY};
        """)
        layout.addWidget(title)

        subtitle = QLabel("选择连接方式并配置设备")
        subtitle.setStyleSheet(f"color: {ModernColors.TEXT_SECONDARY}; font-size: 12px;")
        layout.addWidget(subtitle)

        # 步骤选择
        self.stack = QStackedWidget()
        self.stack.addWidget(self._create_step1_choose())
        self.stack.addWidget(self._create_step2_wifi())
        self.stack.addWidget(self._create_step3_ble())
        self.stack.addWidget(self._create_step4_done())
        layout.addWidget(self.stack)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.back_btn = QPushButton("上一步")
        self.back_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ModernColors.BG_INPUT};
                color: {ModernColors.TEXT_PRIMARY};
                border: 1px solid {ModernColors.BORDER};
                border-radius: 8px;
                padding: 10px 24px;
                font-size: 13px;
            }}
            QPushButton:hover {{ border-color: {ModernColors.PRIMARY}; }}
        """)
        self.back_btn.clicked.connect(self._go_back)
        self.back_btn.setVisible(False)
        btn_layout.addWidget(self.back_btn)

        self.next_btn = QPushButton("下一步")
        self.next_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ModernColors.PRIMARY};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {ModernColors.PRIMARY_HOVER}; }}
        """)
        self.next_btn.clicked.connect(self._go_next)
        btn_layout.addWidget(self.next_btn)

        layout.addLayout(btn_layout)

        self._current_step = 0

    def _create_step1_choose(self) -> QWidget:
        """步骤1：选择连接方式"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        label = QLabel("选择连接方式：")
        label.setStyleSheet(f"font-size: 14px; color: {ModernColors.TEXT_PRIMARY}; font-weight: bold;")
        layout.addWidget(label)

        # WiFi 选项
        wifi_card = self._create_option_card(
            "WiFi 连接（推荐）",
            "ESP32 连接家庭 WiFi，PC 通过网络通信\n支持 OTA 更新、日志查看、高速数据传输",
            "需要先通过串口配置 WiFi 凭据"
        )
        wifi_card.mousePressEvent = lambda e: self._select_mode("wifi")
        layout.addWidget(wifi_card)

        # BLE 选项
        ble_card = self._create_option_card(
            "BLE 蓝牙连接",
            "ESP32 通过蓝牙与 PC 通信\n无需 WiFi，适合移动使用",
            "速度较慢，不支持 OTA"
        )
        ble_card.mousePressEvent = lambda e: self._select_mode("ble")
        layout.addWidget(ble_card)

        # 串口选项
        serial_card = self._create_option_card(
            "USB 串口连接",
            "通过 USB 线连接 ESP32\n最稳定，适合开发调试",
            "需要 USB 线"
        )
        serial_card.mousePressEvent = lambda e: self._select_mode("serial")
        layout.addWidget(serial_card)

        layout.addStretch()
        return page

    def _create_option_card(self, title, desc, note) -> QFrame:
        """创建选项卡片"""
        card = QFrame()
        card.setCursor(Qt.PointingHandCursor)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {ModernColors.BG_CARD};
                border: 1px solid {ModernColors.BORDER};
                border-radius: 12px;
                padding: 16px;
            }}
            QFrame:hover {{
                border-color: {ModernColors.PRIMARY};
                background-color: {ModernColors.BG_TERTIARY};
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        t = QLabel(title)
        t.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {ModernColors.TEXT_PRIMARY};")
        layout.addWidget(t)

        d = QLabel(desc)
        d.setStyleSheet(f"font-size: 11px; color: {ModernColors.TEXT_SECONDARY};")
        layout.addWidget(d)

        n = QLabel(f"⚠ {note}")
        n.setStyleSheet(f"font-size: 10px; color: {ModernColors.TEXT_TERTIARY};")
        layout.addWidget(n)

        return card

    def _create_step2_wifi(self) -> QWidget:
        """步骤2：WiFi 配置"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        label = QLabel("配置 WiFi 连接")
        label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {ModernColors.TEXT_PRIMARY};")
        layout.addWidget(label)

        # 串口选择
        port_layout = QHBoxLayout()
        port_label = QLabel("串口:")
        port_label.setStyleSheet(f"color: {ModernColors.TEXT_SECONDARY};")
        port_layout.addWidget(port_label)

        self.port_combo = QComboBox()
        self.port_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {ModernColors.BG_INPUT};
                color: {ModernColors.TEXT_PRIMARY};
                border: 1px solid {ModernColors.BORDER};
                border-radius: 6px;
                padding: 8px;
            }}
        """)
        self._refresh_ports()
        port_layout.addWidget(self.port_combo)

        refresh_btn = QPushButton("刷新")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ModernColors.BG_INPUT};
                color: {ModernColors.TEXT_PRIMARY};
                border: 1px solid {ModernColors.BORDER};
                border-radius: 6px;
                padding: 8px 16px;
            }}
        """)
        refresh_btn.clicked.connect(self._refresh_ports)
        port_layout.addWidget(refresh_btn)
        layout.addLayout(port_layout)

        # WiFi SSID
        ssid_layout = QHBoxLayout()
        ssid_label = QLabel("WiFi 名称:")
        ssid_label.setStyleSheet(f"color: {ModernColors.TEXT_SECONDARY};")
        ssid_layout.addWidget(ssid_label)

        self.ssid_input = QLineEdit()
        self.ssid_input.setPlaceholderText("输入 WiFi 名称 (SSID)")
        self.ssid_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {ModernColors.BG_INPUT};
                color: {ModernColors.TEXT_PRIMARY};
                border: 1px solid {ModernColors.BORDER};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12px;
            }}
            QLineEdit:focus {{ border-color: {ModernColors.PRIMARY}; }}
        """)
        ssid_layout.addWidget(self.ssid_input)
        layout.addLayout(ssid_layout)

        # WiFi 密码
        pass_layout = QHBoxLayout()
        pass_label = QLabel("WiFi 密码:")
        pass_label.setStyleSheet(f"color: {ModernColors.TEXT_SECONDARY};")
        pass_layout.addWidget(pass_label)

        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("输入 WiFi 密码")
        self.pass_input.setEchoMode(QLineEdit.Password)
        self.pass_input.setStyleSheet(self.ssid_input.styleSheet())
        pass_layout.addWidget(self.pass_input)
        layout.addLayout(pass_layout)

        # 配置按钮
        self.config_btn = QPushButton("发送配置到 ESP32")
        self.config_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ModernColors.PRIMARY};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {ModernColors.PRIMARY_HOVER}; }}
            QPushButton:disabled {{ background-color: {ModernColors.BG_INPUT}; color: {ModernColors.TEXT_TERTIARY}; }}
        """)
        self.config_btn.clicked.connect(self._send_wifi_config)
        layout.addWidget(self.config_btn)

        # 状态
        self.wifi_status = QLabel("")
        self.wifi_status.setStyleSheet(f"color: {ModernColors.TEXT_SECONDARY}; font-size: 11px;")
        self.wifi_status.setWordWrap(True)
        layout.addWidget(self.wifi_status)

        layout.addStretch()
        return page

    def _create_step3_ble(self) -> QWidget:
        """步骤3：BLE 扫描"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        label = QLabel("扫描 BLE 设备")
        label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {ModernColors.TEXT_PRIMARY};")
        layout.addWidget(label)

        # 扫描按钮
        self.scan_btn = QPushButton("开始扫描 (10秒)")
        self.scan_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ModernColors.PRIMARY};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {ModernColors.PRIMARY_HOVER}; }}
        """)
        self.scan_btn.clicked.connect(self._start_ble_scan)
        layout.addWidget(self.scan_btn)

        # 进度条
        self.scan_progress = QProgressBar()
        self.scan_progress.setVisible(False)
        self.scan_progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {ModernColors.BG_INPUT};
                border: 1px solid {ModernColors.BORDER};
                border-radius: 4px;
                height: 8px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {ModernColors.PRIMARY};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(self.scan_progress)

        # 设备列表
        self.ble_list = QListWidget()
        self.ble_list.setMinimumHeight(200)
        self.ble_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {ModernColors.BG_INPUT};
                border: 1px solid {ModernColors.BORDER};
                border-radius: 8px;
                padding: 4px;
                color: {ModernColors.TEXT_PRIMARY};
            }}
            QListWidget::item {{
                padding: 8px;
                border-radius: 4px;
            }}
            QListWidget::item:selected {{
                background-color: {ModernColors.PRIMARY};
            }}
        """)
        layout.addWidget(self.ble_list)

        # 提示
        tip = QLabel("提示: 确保 ESP32 已通电，BLE 广播名称为 'AI Agent Deck'")
        tip.setStyleSheet(f"color: {ModernColors.TEXT_TERTIARY}; font-size: 10px;")
        tip.setWordWrap(True)
        layout.addWidget(tip)

        layout.addStretch()
        return page

    def _create_step4_done(self) -> QWidget:
        """步骤4：完成"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        self.done_icon = QLabel("✓")
        self.done_icon.setStyleSheet(f"font-size: 48px; color: {ModernColors.PRIMARY};")
        self.done_icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.done_icon)

        self.done_title = QLabel("设置完成")
        self.done_title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {ModernColors.TEXT_PRIMARY};")
        self.done_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.done_title)

        self.done_desc = QLabel("")
        self.done_desc.setStyleSheet(f"color: {ModernColors.TEXT_SECONDARY}; font-size: 12px;")
        self.done_desc.setAlignment(Qt.AlignCenter)
        self.done_desc.setWordWrap(True)
        layout.addWidget(self.done_desc)

        layout.addStretch()
        return page

    def _refresh_ports(self):
        """刷新串口列表"""
        self.port_combo.clear()
        try:
            import serial.tools.list_ports
            ports = serial.tools.list_ports.comports()
            for p in ports:
                self.port_combo.addItem(f"{p.device} - {p.description}", p.device)
        except ImportError:
            self.port_combo.addItem("需要安装 pyserial")

    def _select_mode(self, mode):
        """选择连接模式"""
        self._mode = mode
        if mode == "wifi":
            self.stack.setCurrentIndex(1)
        elif mode == "ble":
            self.stack.setCurrentIndex(2)
        elif mode == "serial":
            # 串口模式直接完成
            self._finish("串口模式已选择", "点击「启动」连接设备")
        self.back_btn.setVisible(True)

    def _go_back(self):
        """返回上一步"""
        self._current_step = 0
        self.stack.setCurrentIndex(0)
        self.back_btn.setVisible(False)

    def _go_next(self):
        """下一步"""
        if self.stack.currentIndex() == 0:
            return
        elif self.stack.currentIndex() == 1:
            # WiFi 配置页 - 检查输入
            if not self.ssid_input.text().strip():
                self.wifi_status.setText("请输入 WiFi 名称")
                return
            self._send_wifi_config()
        elif self.stack.currentIndex() == 2:
            # BLE 页 - 选择设备
            self._finish("BLE 模式已选择", "点击「启动」连接设备")
        elif self.stack.currentIndex() == 3:
            # 完成页
            self.accept()

    def _send_wifi_config(self):
        """发送 WiFi 配置"""
        port = self.port_combo.currentData()
        ssid = self.ssid_input.text().strip()
        password = self.pass_input.text()

        if not port:
            self.wifi_status.setText("请选择串口")
            return
        if not ssid:
            self.wifi_status.setText("请输入 WiFi 名称")
            return

        self.config_btn.setEnabled(False)
        self.wifi_status.setText("正在发送配置...")

        self._config_worker = SerialConfigWorker(port, ssid, password)
        self._config_worker.result.connect(self._on_config_result)
        self._config_worker.start()

    def _on_config_result(self, success, msg):
        """配置结果"""
        self.config_btn.setEnabled(True)
        self.wifi_status.setText(msg)
        if success:
            self._finish("WiFi 配置完成", f"ESP32 将连接到: {self.ssid_input.text()}\n请重启 ESP32，然后点击「启动」")

    def _start_ble_scan(self):
        """开始 BLE 扫描"""
        self.ble_list.clear()
        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("扫描中...")
        self.scan_progress.setVisible(True)
        self.scan_progress.setRange(0, 0)  # 不确定进度

        self._scan_worker = BLEScanWorker()
        self._scan_worker.found.connect(self._on_ble_found)
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_worker.error.connect(self._on_scan_error)
        self._scan_worker.start()

    def _on_ble_found(self, name, address, rssi):
        """发现 BLE 设备"""
        item = QListWidgetItem(f"{name}  ({address})  RSSI: {rssi}")
        item.setData(Qt.UserRole, address)

        # 高亮可能的设备
        if "AI" in name.upper() or "DECK" in name.upper() or "AGENT" in name.upper():
            item.setForeground(QColor(ModernColors.PRIMARY))
            item.setText(f"★ {item.text()}")

        self.ble_list.addItem(item)

    def _on_scan_finished(self):
        """扫描完成"""
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("重新扫描")
        self.scan_progress.setVisible(False)

        if self.ble_list.count() == 0:
            self.ble_list.addItem("未发现设备 - 确保 ESP32 已通电")

    def _on_scan_error(self, msg):
        """扫描错误"""
        self.ble_list.addItem(f"扫描错误: {msg}")

    def _finish(self, title, desc):
        """完成设置"""
        self.done_title.setText(title)
        self.done_desc.setText(desc)
        self.stack.setCurrentIndex(3)
        self.back_btn.setVisible(True)
        self.next_btn.setText("完成")

    def get_selected_mode(self) -> str:
        """获取选择的连接模式"""
        return getattr(self, '_mode', 'wifi')

    def get_selected_port(self) -> str:
        """获取选择的串口"""
        return self.port_combo.currentData()

    def get_selected_ble_address(self) -> str:
        """获取选择的 BLE 设备地址"""
        item = self.ble_list.currentItem()
        if item:
            return item.data(Qt.UserRole)
        return None
