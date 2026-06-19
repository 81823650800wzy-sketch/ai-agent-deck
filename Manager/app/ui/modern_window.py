"""
AI Agent Deck - 现代化主窗口
专业级桌面应用界面
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QListWidget, QTextEdit,
    QComboBox, QGroupBox, QGridLayout, QStatusBar, QMenuBar,
    QAction, QMessageBox, QFileDialog, QSplitter, QApplication,
    QGraphicsDropShadowEffect, QScrollArea, QSizePolicy, QLineEdit,
    QDialog
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve, QThread
from PyQt5.QtGui import QFont, QColor, QIcon, QPixmap, QPainter, QBrush, QPen

from typing import Optional
import time

from ..version import get_version_display
from ..core.engine import Engine, EngineState, EngineConfig, TransportMode
from ..core.profile import Profile, KeyMapping
from ..core.wallpaper_manager import WallpaperManager
from ..log import get_logger, setup_ui_bridge
from .modern_theme import ModernColors, ModernFonts, apply_modern_style, create_shadow_effect, get_theme_names, set_theme
from .setup_dialog import SetupDialog
from .log_panel import LogPanel

logger = get_logger("ui")


class ScreenPreview(QWidget):
    """ESP32 屏幕实时预览（240x240 缩放到 180x180）"""

    screen_clicked = pyqtSignal(int)  # 点击切换界面

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(150, 150)
        self.setMaximumSize(250, 250)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.current_screen = 0
        self._screens = ["KEYS", "STATUS", "WALLPAPER"]

    def set_screen(self, idx: int):
        self.current_screen = idx
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 使用实际 widget 尺寸
        w = self.width() - 1
        h = self.height() - 1

        # 背景
        painter.setBrush(QColor(ModernColors.BG_INPUT))
        painter.setPen(QColor(ModernColors.BORDER))
        painter.drawRoundedRect(0, 0, w, h, 8, 8)

        # 模拟 ESP32 屏幕内容
        s = self.current_screen
        pw, ph = w, h
        sx = pw / 240  # 缩放比
        sy = ph / 240

        # 壁纸渐变背景
        for yy in range(0, ph, 3):
            t = yy / ph
            r = int(8 + 10 * t)
            g = int(10 + 8 * t)
            b = int(25 + 7 * t)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(r, g, b))
            painter.drawRect(0, yy, pw, 3)

        # 标题栏
        painter.setBrush(QColor(16, 18, 36, 200))
        painter.drawRoundedRect(int(4*sx), int(3*sy), int(232*sx), int(24*sy), 6, 6)
        painter.setPen(QColor(200, 210, 235))
        painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
        painter.drawText(int(4*sx), int(3*sy), int(232*sx), int(24*sy),
                         Qt.AlignCenter, self._screens[s])

        if s == 0:  # KEYS
            colors = [
                QColor(72, 199, 142), QColor(139, 92, 246), QColor(59, 130, 246),
                QColor(245, 158, 11), QColor(239, 68, 68), QColor(100, 115, 150)
            ]
            names = ["Copy", "Paste", "Undo", "Save", "All", "Close"]
            gap = int(5 * sx)
            cw = int((232 - 4*gap) / 3)
            ch = int(50 * sy)
            for i in range(6):
                r, c = divmod(i, 3)
                x = int(4*sx) + gap + c * (cw + gap)
                y = int(32*sy) + gap + r * (ch + gap)
                # 玻璃卡片
                painter.setBrush(QColor(16, 18, 36, 160))
                painter.setPen(QColor(50, 60, 100))
                painter.drawRoundedRect(x, y, cw, ch, 5, 5)
                # 顶部指示条
                painter.setPen(Qt.NoPen)
                painter.setBrush(colors[i])
                painter.drawRect(x + 6, y + 1, cw - 12, 2)
                # 文字
                painter.setPen(QColor(200, 210, 235))
                painter.setFont(QFont("Segoe UI", 6))
                painter.drawText(x, y + int(18*sy), cw, 12, Qt.AlignCenter, names[i])

        elif s == 1:  # STATUS
            labels = ["BLE", "Profile", "Keys", "RAM", "PSRAM"]
            values = ["Connected", "Default", "6/6", "280 KB", "8189 KB"]
            gap = int(4 * sy)
            rh = int(20 * sy)
            for i in range(5):
                y = int(32*sy) + i * (rh + gap)
                painter.setBrush(QColor(16, 18, 36, 160))
                painter.setPen(QColor(50, 60, 100))
                painter.drawRoundedRect(int(8*sx), y, int(224*sx), rh, 3, 3)
                painter.setPen(QColor(90, 105, 140))
                painter.setFont(QFont("Segoe UI", 5))
                painter.drawText(int(14*sx), y + 2, 60, rh - 4, Qt.AlignVCenter, labels[i])
                painter.setPen(QColor(200, 210, 235))
                painter.drawText(int(80*sx), y + 2, int(140*sx), rh - 4, Qt.AlignVCenter | Qt.AlignRight, values[i])

        elif s == 2:  # WALLPAPER
            painter.setPen(QColor(200, 210, 235))
            painter.setFont(QFont("Segoe UI", 6))
            painter.drawText(int(20*sx), int(50*sy), int(200*sx), 20, Qt.AlignCenter, "Wallpaper Preview")
            painter.setPen(QColor(90, 105, 140))
            painter.drawText(int(20*sx), int(80*sy), int(200*sx), 60, Qt.AlignCenter | Qt.TextWordWrap,
                             "Upload via App\nPNG/JPG/GIF supported")

        # 页码
        painter.setPen(QColor(90, 105, 140))
        painter.setFont(QFont("Segoe UI", 5))
        painter.drawText(int(160*sx), int(10*sy), 30, 12, Qt.AlignRight, f"{s+1}/3")

        painter.end()

    def mousePressEvent(self, event):
        """点击切换界面"""
        x = event.x()
        if x < self.width() // 3:
            self.screen_clicked.emit(0)
        elif x < self.width() * 2 // 3:
            self.screen_clicked.emit(1)
        else:
            self.screen_clicked.emit(2)
from .modern_widgets import (
    Card, StatusIndicator, GradientButton, OutlineButton,
    KeyCard, ProfileCard, AppIcon, IconButton
)


class _UploadWorker(QThread):
    """后台上传线程，避免阻塞 GUI"""
    finished = pyqtSignal(bool, str)  # (success, message)
    progress = pyqtSignal(int, int)   # (current, total)

    def __init__(self, mgr, upload_type, serial_conn=None, parent=None):
        super().__init__(parent)
        self.mgr = mgr
        self.upload_type = upload_type  # "static" or "gif"
        self.serial_conn = serial_conn

    def run(self):
        try:
            if self.upload_type == "gif":
                ok = self.mgr.upload_gif()
            else:
                # 串口模式：不用 ack_func（接收线程会处理 ACK）
                # 改用固定延迟，让 ESP32 有时间处理
                ok = self.mgr.upload_static(ack_func=None)
            self.finished.emit(ok, "上传成功" if ok else "上传失败")
        except Exception as e:
            self.finished.emit(False, f"上传异常: {e}")


class ModernMainWindow(QMainWindow):
    """
    现代化主窗口

    特点:
    - 深色主题
    - 圆角卡片
    - 渐变按钮
    - 清晰的文字
    - 专业的布局
    """

    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)
    device_connect_signal = pyqtSignal()
    device_disconnect_signal = pyqtSignal()
    app_change_signal = pyqtSignal(str, str)  # new_app, old_app
    profile_change_signal = pyqtSignal(str)   # profile_name
    device_data_signal = pyqtSignal(dict)     # ESP32 response data
    status_msg_signal = pyqtSignal(str)       # WiFi/BLE status

    def __init__(self, engine: Optional[Engine] = None):
        super().__init__()

        self.engine = engine or Engine()
        self.key_cards = []
        self.profile_cards = []

        # 壁纸管理器
        self.wallpaper_mgr = WallpaperManager()

        # 设置引擎的壁纸管理器引用（用于 ACK 通知）
        self.engine._wallpaper_mgr = self.wallpaper_mgr

        self._setup_window()
        self._setup_ui()
        self._setup_connections()
        self._start_update_timer()

        # 初始加载 Profile 列表
        self._update_profile_list()

        # 初始化系统托盘
        self._tray_icon = None
        self._init_system_tray()

    def _setup_window(self):
        """设置窗口属性"""
        self.setWindowTitle("AI Agent Deck")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)

        # 设置窗口图标
        self._set_window_icon()

    def _set_window_icon(self):
        """设置窗口图标"""
        # 创建应用图标
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制渐变背景
        from PyQt5.QtGui import QLinearGradient
        gradient = QLinearGradient(0, 0, 64, 64)
        gradient.setColorAt(0, QColor(ModernColors.GRADIENT_START))
        gradient.setColorAt(1, QColor(ModernColors.GRADIENT_END))

        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, 64, 64, 16, 16)

        # 绘制文字
        painter.setPen(QColor(Qt.white))
        painter.setFont(QFont("Segoe UI", 20, QFont.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "AD")

        painter.end()

        self.setWindowIcon(QIcon(pixmap))

    def _setup_ui(self):
        """初始化界面"""
        # 中央部件
        central = QWidget()
        self.setCentralWidget(central)

        # 主布局
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 顶部栏
        top_bar = self._create_top_bar()
        main_layout.addWidget(top_bar)

        # 内容区域
        content = self._create_content()
        main_layout.addWidget(content)

        # 状态栏
        self._setup_status_bar()

    def _create_top_bar(self) -> QWidget:
        """创建顶部栏"""
        top_bar = QFrame()
        top_bar.setFixedHeight(60)
        top_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {ModernColors.BG_SECONDARY};
                border-bottom: 1px solid {ModernColors.BORDER};
            }}
        """)

        layout = QHBoxLayout(top_bar)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(16)

        # 应用图标和标题
        app_icon = AppIcon(36)
        layout.addWidget(app_icon)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(0)

        title = QLabel("AI Agent Deck")
        title.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {ModernColors.TEXT_PRIMARY};
        """)
        title_layout.addWidget(title)

        subtitle = QLabel("工作流控制器")
        subtitle.setStyleSheet(f"""
            font-size: 10px;
            color: {ModernColors.TEXT_SECONDARY};
        """)
        title_layout.addWidget(subtitle)

        layout.addLayout(title_layout)
        layout.addStretch()

        # 状态指示器
        self.status_indicator = StatusIndicator("设备未连接", "offline")
        layout.addWidget(self.status_indicator)

        # 控制按钮
        setup_btn = OutlineButton("⚙ 设置")
        setup_btn.setFixedWidth(80)
        setup_btn.clicked.connect(self._open_setup)
        layout.addWidget(setup_btn)

        self.start_btn = GradientButton("启动")
        self.start_btn.setFixedWidth(100)
        self.start_btn.clicked.connect(self._on_start)
        layout.addWidget(self.start_btn)

        self.stop_btn = OutlineButton("停止")
        self.stop_btn.setFixedWidth(100)
        self.stop_btn.clicked.connect(self._on_stop)
        self.stop_btn.setEnabled(False)
        layout.addWidget(self.stop_btn)

        return top_bar

    def _create_content(self) -> QWidget:
        """创建内容区域（使用 QSplitter 支持拖动调整大小）"""
        content = QWidget()
        layout = QHBoxLayout(content)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(0)

        # 主水平分割器：左侧面板 | 右侧面板
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setHandleWidth(8)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {ModernColors.BG_TERTIARY};
                margin: 2px 4px;
                border-radius: 2px;
            }}
            QSplitter::handle:hover {{
                background-color: {ModernColors.PRIMARY};
            }}
            QSplitter::handle:pressed {{
                background-color: {ModernColors.PRIMARY_HOVER};
            }}
        """)

        # 左侧面板
        left_panel = self._create_left_panel()
        self.main_splitter.addWidget(left_panel)

        # 右侧垂直分割器：上半区(屏幕+按键) | 下半区(日志)
        self.right_splitter = QSplitter(Qt.Vertical)
        self.right_splitter.setHandleWidth(8)
        self.right_splitter.setChildrenCollapsible(False)
        self.right_splitter.setStyleSheet(self.main_splitter.styleSheet())

        # 上半区：屏幕预览 + 按键映射
        top_area = self._create_top_area()
        self.right_splitter.addWidget(top_area)

        # 下半区：日志
        log_area = self._create_log_area()
        self.right_splitter.addWidget(log_area)

        # 设置初始比例：上半区 60%，日志 40%
        self.right_splitter.setSizes([400, 300])

        self.main_splitter.addWidget(self.right_splitter)

        # 设置初始比例：左侧 280px，右侧剩余
        self.main_splitter.setSizes([280, 920])
        # 设置右侧上下比例：上半区 55%，日志 45%
        self.right_splitter.setSizes([440, 360])

        layout.addWidget(self.main_splitter)

        return content

    def _create_left_panel(self) -> QWidget:
        """创建左侧面板"""
        panel = QWidget()
        panel.setMinimumWidth(180)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # 设备状态卡片
        device_card = Card("设备状态")

        # 当前应用
        self.app_label = QLabel("当前应用: 无")
        self.app_label.setStyleSheet(f"""
            font-size: 12px;
            color: {ModernColors.TEXT_SECONDARY};
            padding: 8px 0;
        """)
        device_card.add_widget(self.app_label)

        # 当前 Profile
        self.profile_label = QLabel("当前 Profile: 无")
        self.profile_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: bold;
            color: {ModernColors.TEXT_PRIMARY};
            padding: 8px 0;
        """)
        device_card.add_widget(self.profile_label)

        # 通信模式
        mode_layout = QHBoxLayout()
        mode_label = QLabel("通信模式:")
        mode_label.setStyleSheet(f"color: {ModernColors.TEXT_SECONDARY};")
        mode_layout.addWidget(mode_label)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["串口", "BLE", "WiFi"])
        self.mode_combo.setCurrentText("串口")
        mode_layout.addWidget(self.mode_combo)

        device_card.add_layout(mode_layout)

        # WiFi IP 地址输入（手动指定 ESP32 IP）
        wifi_layout = QHBoxLayout()
        wifi_label = QLabel("ESP32 IP:")
        wifi_label.setStyleSheet(f"color: {ModernColors.TEXT_SECONDARY};")
        wifi_layout.addWidget(wifi_label)

        self.wifi_ip_input = QLineEdit()
        self.wifi_ip_input.setPlaceholderText("自动发现 (或手动输入 IP)")
        self.wifi_ip_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {ModernColors.BG_INPUT};
                color: {ModernColors.TEXT_PRIMARY};
                border: 1px solid {ModernColors.BORDER};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11px;
            }}
            QLineEdit:focus {{
                border-color: {ModernColors.PRIMARY};
            }}
        """)
        wifi_layout.addWidget(self.wifi_ip_input)

        device_card.add_layout(wifi_layout)

        # 快速操作按钮
        quick_layout = QHBoxLayout()

        quick_scan_btn = OutlineButton("🔍 扫描设备")
        quick_scan_btn.setFixedHeight(32)
        quick_scan_btn.clicked.connect(self._quick_scan)
        quick_layout.addWidget(quick_scan_btn)

        quick_setup_btn = OutlineButton("⚙ 一键配网")
        quick_setup_btn.setFixedHeight(32)
        quick_setup_btn.clicked.connect(self._open_setup)
        quick_layout.addWidget(quick_setup_btn)

        device_card.add_layout(quick_layout)

        # 连接状态详情
        self.connection_detail = QLabel("")
        self.connection_detail.setStyleSheet(f"""
            color: {ModernColors.TEXT_TERTIARY};
            font-size: 10px;
            padding: 4px;
            background-color: {ModernColors.BG_INPUT};
            border-radius: 4px;
        """)
        self.connection_detail.setWordWrap(True)
        device_card.add_widget(self.connection_detail)

        layout.addWidget(device_card)

        # Profile 列表卡片
        profile_card = Card("Profile 列表")

        self.profile_list = QListWidget()
        self.profile_list.setMinimumHeight(200)
        self.profile_list.currentTextChanged.connect(self._on_profile_select)
        profile_card.add_widget(self.profile_list)

        # 添加/删除按钮
        profile_btn_layout = QHBoxLayout()

        add_profile_btn = OutlineButton("添加")
        add_profile_btn.clicked.connect(self._on_add_profile)
        profile_btn_layout.addWidget(add_profile_btn)

        del_profile_btn = OutlineButton("删除")
        del_profile_btn.setProperty("danger", True)
        del_profile_btn.clicked.connect(self._on_delete_profile)
        profile_btn_layout.addWidget(del_profile_btn)

        profile_card.add_layout(profile_btn_layout)

        layout.addWidget(profile_card)

        # 主题选择
        theme_card = Card("主题")

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(get_theme_names())
        self.theme_combo.setCurrentText("深色")
        self.theme_combo.currentTextChanged.connect(self._on_theme_change)
        theme_card.add_widget(self.theme_combo)

        layout.addWidget(theme_card)

        layout.addStretch()

        return panel

    def _create_top_area(self) -> QWidget:
        """创建上半区：ESP32 屏幕控制 + 按键映射"""
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(10)

        # 左列：ESP32 屏幕预览 + 控制（最小宽度，可伸缩）
        screen_col = QWidget()
        screen_col.setMinimumWidth(180)
        screen_col.setMaximumWidth(300)
        screen_layout = QVBoxLayout(screen_col)
        screen_layout.setContentsMargins(0, 0, 0, 0)
        screen_layout.setSpacing(8)

        # 屏幕预览
        self.screen_preview = ScreenPreview()
        self.screen_preview.screen_clicked.connect(self._on_screen_click)
        screen_layout.addWidget(self.screen_preview)

        # 屏幕切换按钮（紧凑）
        nav_layout = QHBoxLayout()
        for text, sid in [("按键", 0), ("状态", 1), ("壁纸", 2)]:
            btn = OutlineButton(text)
            btn.setFixedHeight(30)
            btn.clicked.connect(lambda checked, s=sid: self._send_screen_cmd("switch", s))
            nav_layout.addWidget(btn)
        screen_layout.addLayout(nav_layout)

        # 壁纸操作（紧凑）
        wp_layout = QHBoxLayout()
        load_btn = OutlineButton("选图")
        load_btn.setFixedHeight(30)
        load_btn.clicked.connect(self._on_load_wallpaper)
        wp_layout.addWidget(load_btn)

        upload_btn = GradientButton("上传")
        upload_btn.setFixedHeight(30)
        upload_btn.clicked.connect(self._on_upload_wallpaper)
        wp_layout.addWidget(upload_btn)

        clear_btn = OutlineButton("清除")
        clear_btn.setFixedHeight(30)
        clear_btn.clicked.connect(self._on_clear_wallpaper)
        wp_layout.addWidget(clear_btn)
        screen_layout.addLayout(wp_layout)

        # 壁纸缩略图预览
        self.wallpaper_preview = QLabel("无壁纸")
        self.wallpaper_preview.setFixedHeight(60)
        self.wallpaper_preview.setAlignment(Qt.AlignCenter)
        self.wallpaper_preview.setStyleSheet(f"""
            background-color: {ModernColors.BG_INPUT};
            border: 1px dashed {ModernColors.BORDER};
            border-radius: 6px;
            color: {ModernColors.TEXT_TERTIARY};
            font-size: 10px;
        """)
        screen_layout.addWidget(self.wallpaper_preview)

        self.wallpaper_status = QLabel("未加载壁纸")
        self.wallpaper_status.setStyleSheet(f"color: {ModernColors.TEXT_TERTIARY}; font-size: 10px;")
        screen_layout.addWidget(self.wallpaper_status)

        screen_layout.addStretch()
        layout.addWidget(screen_col)

        # 右列：按键映射（占据剩余空间）
        keys_card = Card("按键映射")

        keys_grid = QGridLayout()
        keys_grid.setSpacing(8)

        self.key_cards = []
        for row in range(3):
            for col in range(2):
                idx = row * 2 + col
                key_id = f"K{idx + 1}"
                card = KeyCard(key_id)
                card.setMinimumSize(120, 80)  # 最小尺寸，允许伸缩
                keys_grid.addWidget(card, row, col)
                self.key_cards.append(card)

        keys_card.add_layout(keys_grid)

        # 测试按钮放在按键卡片内
        test_layout = QHBoxLayout()
        test_profile_btn = OutlineButton("发送测试")
        test_profile_btn.setFixedHeight(28)
        test_profile_btn.clicked.connect(self._on_send_test)
        test_layout.addWidget(test_profile_btn)

        test_key_btn = OutlineButton("测试按键")
        test_key_btn.setFixedHeight(28)
        test_key_btn.clicked.connect(self._on_test_key)
        test_layout.addWidget(test_key_btn)
        keys_card.add_layout(test_layout)

        layout.addWidget(keys_card)

        return panel

    def _create_log_area(self) -> QWidget:
        """创建下半区：增强日志面板"""
        self.log_panel = LogPanel()
        # 将 LogPanel 桥接到 Python 日志系统
        setup_ui_bridge(self.log_panel)
        return self.log_panel

    def _setup_status_bar(self):
        """设置状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # 状态信息
        self.status_label = QLabel("就绪")
        self.status_bar.addWidget(self.status_label)

        # 版本信息
        version_label = QLabel(get_version_display())
        version_label.setStyleSheet(f"color: {ModernColors.TEXT_TERTIARY};")
        self.status_bar.addPermanentWidget(version_label)

    def _setup_connections(self):
        """设置信号连接"""
        # 引擎事件 → 信号（线程安全）
        self.engine.on('state_change', lambda s: self.status_signal.emit(f"引擎状态: {s.value}"))
        self.engine.on('device_connect', lambda: self.device_connect_signal.emit())
        self.engine.on('device_disconnect', lambda: self.device_disconnect_signal.emit())
        self.engine.on('app_change', lambda new, old: self.app_change_signal.emit(
            new.process_name, old.process_name if old else ""))
        self.engine.on('profile_change', lambda p: self.profile_change_signal.emit(p.name))
        self.engine.on('error', lambda e: self.log_signal.emit(f"[ERROR] {e}"))
        self.engine.on('status', lambda m: self.status_msg_signal.emit(m))
        self.engine.on('device_data', lambda d: self.device_data_signal.emit(d))

        # 信号 → UI 更新（主线程）
        self.log_signal.connect(self._append_log)
        self.status_signal.connect(self.status_label.setText)
        self.device_connect_signal.connect(self._on_device_connect)
        self.device_disconnect_signal.connect(self._on_device_disconnect)
        self.app_change_signal.connect(self._on_app_change_safe)
        self.profile_change_signal.connect(self._on_profile_change_safe)
        self.status_msg_signal.connect(self._on_status_msg)
        self.device_data_signal.connect(self._on_device_data)

    def _start_update_timer(self):
        """启动更新定时器"""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_status)
        self.update_timer.start(500)

    def _open_setup(self):
        """打开设置向导"""
        dialog = SetupDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            mode = dialog.get_selected_mode()
            # 根据设置更新界面
            if mode == "wifi":
                self.mode_combo.setCurrentText("WiFi")
            elif mode == "ble":
                self.mode_combo.setCurrentText("BLE")
            else:
                self.mode_combo.setCurrentText("串口")

            # 如果选择了串口，更新引擎配置
            port = dialog.get_selected_port()
            if port and mode == "串口":
                self.engine.config.com_port = port

            self._log(f"[设置] 已选择: {mode}")

    def _quick_scan(self):
        """快速扫描 BLE 设备"""
        self._log("[扫描] 正在扫描 BLE 设备...")
        self.connection_detail.setText("扫描中...")

        import threading
        def _scan():
            try:
                import asyncio
                from bleak import BleakScanner

                async def _do_scan():
                    devices = await BleakScanner.discover(timeout=8.0, return_adv=True)
                    results = []
                    for addr, (dev, adv) in devices.items():
                        name = dev.name or "(unnamed)"
                        rssi = adv.rssi if hasattr(adv, 'rssi') else -100
                        results.append((name, addr, rssi))
                    return results

                results = asyncio.run(_do_scan())

                if results:
                    # 找到最可能的设备
                    candidates = [r for r in results if any(k in r[0].upper() for k in ["AI", "DECK", "AGENT", "ESP"])]
                    if candidates:
                        name, addr, rssi = candidates[0]
                        self.connection_detail.setText(f"找到: {name}\n{addr} (RSSI: {rssi})")
                        self._log(f"[扫描] 找到设备: {name} ({addr})")
                    else:
                        self.connection_detail.setText(f"发现 {len(results)} 个设备\n未找到 AI Agent Deck")
                        self._log(f"[扫描] 发现 {len(results)} 个设备，未找到 AI Agent Deck")
                else:
                    self.connection_detail.setText("未发现设备\n确保 ESP32 已通电")
                    self._log("[扫描] 未发现设备")

            except Exception as e:
                self.connection_detail.setText(f"扫描失败: {e}")
                self._log(f"[扫描] 错误: {e}")

        threading.Thread(target=_scan, daemon=True).start()

    def _on_start(self):
        """启动引擎（后台线程，避免 UI 卡死）"""
        if self.engine.is_running():
            self._log("[WARN] 引擎已在运行")
            return

        # 根据下拉框设置传输模式
        mode_text = self.mode_combo.currentText()
        if mode_text == "WiFi":
            self.engine.config.transport = TransportMode.WIFI
            manual_ip = self.wifi_ip_input.text().strip()
            self.engine.config.wifi_host = manual_ip if manual_ip else None
        elif mode_text == "BLE":
            self.engine.config.transport = TransportMode.BLE
        else:
            self.engine.config.transport = TransportMode.SERIAL

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_indicator.set_status("connecting", "连接中...")
        self._log(f"[OK] 引擎启动中... 模式: {mode_text}")

        # 后台启动引擎
        import threading
        def _start():
            try:
                self.engine.start()
                QTimer.singleShot(0, self._update_profile_list)
                QTimer.singleShot(0, lambda: self._log("[OK] 引擎已就绪"))
            except Exception as e:
                QTimer.singleShot(0, lambda: self._log(f"[ERROR] 启动失败: {e}"))
                QTimer.singleShot(0, lambda: self.start_btn.setEnabled(True))

        threading.Thread(target=_start, daemon=True).start()

    def _on_stop(self):
        """停止引擎"""
        try:
            self.engine.stop()
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.status_indicator.set_status("offline", "设备未连接")
            self._log("[OK] 引擎已停止")
        except Exception as e:
            self._log(f"[ERROR] 停止失败: {e}")

    def _on_profile_select(self, name: str):
        """Profile 选择"""
        if not self.engine.profiles:
            return
        profile = self.engine.profiles.get_profile_by_name(name)
        if profile:
            self._update_key_display(profile.keys)

    def _on_theme_change(self, name: str):
        """主题切换"""
        app = QApplication.instance()
        if app:
            apply_modern_style(app, name)
            self._log(f"[THEME] 切换主题: {name}")

    def _on_load_wallpaper(self):
        """选择壁纸图片"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择壁纸图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif);;所有文件 (*)"
        )
        if not file_path:
            return

        img = self.wallpaper_mgr.load_image(file_path)
        if img:
            # 预览缩略图
            pixmap = self.wallpaper_mgr.get_preview_pixmap(size=60)
            if pixmap:
                self.wallpaper_preview.setPixmap(pixmap)
            else:
                self.wallpaper_preview.setText("预览不可用")

            # 状态
            frames = self.wallpaper_mgr.current_frames
            if frames:
                self.wallpaper_status.setText(f"已加载: {len(frames)} 帧 GIF")
            else:
                self.wallpaper_status.setText("已加载: 静态图片")
            self._log(f"[WALLPAPER] 已加载: {file_path}")
        else:
            self._log("[WALLPAPER] 加载失败，请安装 Pillow: pip install Pillow")

    def _on_upload_wallpaper(self):
        """上传壁纸到 ESP32（后台线程）"""
        if not self.engine.is_running():
            QMessageBox.warning(self, "警告", "请先启动引擎")
            return

        if not self.wallpaper_mgr.current_image:
            QMessageBox.warning(self, "警告", "请先选择图片")
            return

        # 设置发送函数
        self.wallpaper_mgr.set_send_func(self._send_to_device)

        # 禁用按钮防止重复上传
        self.sender().setEnabled(False)
        self.wallpaper_status.setText("上传中...")

        # 获取串口连接（用于 ACK 等待）
        serial_conn = None
        if self.engine.workflow and self.engine.workflow.device:
            dev = self.engine.workflow.device
            if hasattr(dev, '_serial'):
                serial_conn = dev._serial

        # 后台线程上传
        upload_type = "gif" if self.wallpaper_mgr.current_frames else "static"
        self._upload_worker = _UploadWorker(self.wallpaper_mgr, upload_type, serial_conn)
        self._upload_worker.finished.connect(self._on_upload_done)
        self._upload_worker.progress.connect(self._on_upload_progress)
        self._upload_worker.start()

        self._log(f"[WALLPAPER] 开始上传 ({upload_type})...")

    def _on_upload_done(self, success: bool, msg: str):
        """上传完成回调"""
        self._log(f"[WALLPAPER] {msg}")
        self.wallpaper_status.setText("✓ 已上传" if success else "✗ 上传失败")
        # 重新启用上传按钮
        for btn in self.findChildren(QPushButton):
            if btn.text() == "上传":
                btn.setEnabled(True)
                break

    def _on_upload_progress(self, current: int, total: int):
        """上传进度"""
        pct = int(current * 100 / total) if total > 0 else 0
        self.wallpaper_status.setText(f"上传中... {pct}%")

    def _on_clear_wallpaper(self):
        """清除壁纸"""
        self.wallpaper_mgr.clear_wallpaper()
        self.wallpaper_preview.clear()
        self.wallpaper_preview.setText("无壁纸")
        self.wallpaper_status.setText("未加载")
        self._log("[WALLPAPER] 已清除")

    def _send_screen_cmd(self, action: str, screen_id: int = None):
        """发送屏幕控制命令到 ESP32"""
        import json
        cmd = {"cmd": "screen", "action": action}
        if screen_id is not None:
            cmd["id"] = screen_id
        json_str = json.dumps(cmd)
        success = self._send_to_device(json_str)
        if success:
            self._log(f"[SCREEN] {action}" + (f" -> {screen_id}" if screen_id is not None else ""))
            # 更新预览
            if screen_id is not None:
                self.screen_preview.set_screen(screen_id)
            elif action == "next":
                self.screen_preview.set_screen((self.screen_preview.current_screen + 1) % 3)
            elif action == "prev":
                self.screen_preview.set_screen((self.screen_preview.current_screen - 1) % 3)
        else:
            self._log("[SCREEN] 发送失败")

    def _on_screen_click(self, screen_id: int):
        """点击预览切换界面"""
        self._send_screen_cmd("switch", screen_id)

    def _send_to_device(self, json_str: str) -> bool:
        """发送 JSON 到设备（串口或 BLE）"""
        if not self.engine.workflow or not self.engine.workflow.device:
            return False
        try:
            return self.engine.workflow.device.send_profile_raw(json_str)
        except Exception as e:
            self._log(f"[WALLPAPER] 发送失败: {e}")
            return False

    def _on_add_profile(self):
        """打开 Profile 管理器"""
        try:
            from .profile_editor import ProfileListManager
            pm = self.engine.profiles if self.engine else None
            dlg = ProfileListManager(profile_manager=pm, parent=self)
            dlg.profile_changed.connect(self._refresh_profile_list)
            dlg.exec_()
        except Exception as e:
            self._log(f"[ERROR] 打开 Profile 管理器失败: {e}")

    def _on_delete_profile(self):
        """删除 Profile"""
        current = self.profile_list.currentItem()
        if current:
            name = current.text()
            reply = QMessageBox.question(
                self,
                "确认删除",
                f"确定要删除 Profile '{name}' 吗?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.engine.profiles.delete_profile(name)
                self._update_profile_list()
                self._log(f"[OK] 已删除 Profile: {name}")

    def _on_send_test(self):
        """发送测试 Profile"""
        if not self.engine.is_running():
            QMessageBox.warning(self, "警告", "请先启动引擎")
            return

        test_profile = Profile(
            name="Test",
            keys=[
                KeyMapping("K1", "测试-A", "key_combo", "ctrl+a"),
                KeyMapping("K2", "测试-B", "key_combo", "ctrl+b"),
                KeyMapping("K3", "测试-C", "key_combo", "ctrl+c"),
                KeyMapping("K4", "测试-D", "key_combo", "ctrl+d"),
                KeyMapping("K5", "测试-E", "key_combo", "ctrl+e"),
                KeyMapping("K6", "测试-F", "key_combo", "ctrl+f"),
            ]
        )

        success = self.engine.send_profile(test_profile)
        if success:
            self._log("[OK] 测试 Profile 已发送")
            self._update_key_display(test_profile.keys)
        else:
            self._log("[ERROR] 发送失败")

    def _on_test_key(self):
        """测试按键"""
        self._log("[TEST] 按下 ESP32 上的按键进行测试...")

    def _on_clear_log(self):
        """清空日志"""
        self.log_panel.clear()

    def _on_export_log(self):
        """导出日志"""
        self.log_panel._export_log()

    def _on_state_change(self, state: EngineState):
        """引擎状态变化"""
        self.status_signal.emit(f"引擎状态: {state.value}")

    def _on_device_connect(self):
        """设备连接（主线程）"""
        self.status_indicator.set_status("online", "设备已连接")
        self._log("[OK] 设备已连接")

    def _on_device_disconnect(self):
        """设备断开（主线程）"""
        self.status_indicator.set_status("offline", "设备已断开")
        self._log("[WARN] 设备已断开")

    def _on_app_change_safe(self, new_name: str, old_name: str):
        """应用切换（主线程，已解包数据）"""
        self.app_label.setText(f"当前应用: {new_name}")
        self._log(f"[APP] 切换: {old_name or 'N/A'} → {new_name}")

    def _on_profile_change_safe(self, profile_name: str):
        """Profile 切换（主线程，已解包数据）"""
        self.profile_label.setText(f"当前 Profile: {profile_name}")
        # 更新按键显示
        if self.engine.profiles:
            profile = self.engine.profiles.get_profile_by_name(profile_name)
            if profile:
                self._update_key_display(profile.keys)
        self._log(f"[PROFILE] 切换: {profile_name}")

    def _on_error(self, error: str):
        """错误"""
        self._log(f"[ERROR] {error}")

    def _on_status_msg(self, msg: str):
        """WiFi/BLE 状态消息"""
        self._log(f"[WiFi] {msg}")
        self.status_label.setText(msg)
        self.connection_detail.setText(msg)

    def _on_device_data(self, data: dict):
        """ESP32 响应数据"""
        cmd = data.get("cmd", "unknown")
        if cmd == "pong":
            self.log_panel.log_ok("Pong 收到", "ESP32")
        elif cmd == "profile_ack":
            name = data.get("profile", "?")
            keys = data.get("keys", 0)
            self.log_panel.log_ok(f"Profile 确认: {name} ({keys}键)", "ESP32")
        elif cmd == "screen_ack":
            sid = data.get("id", "?")
            sname = data.get("name", "?")
            self.log_panel.log_ok(f"屏幕切换: {sname} ({sid})", "ESP32")
        elif cmd == "wifi_status":
            ip = data.get("ip", "?")
            connected = data.get("connected", False)
            self.log_panel.log_info(f"WiFi: {ip} (连接: {connected})", "ESP32")
        elif cmd == "ota_ack":
            status = data.get("status", "?")
            msg = data.get("msg", "")
            self.log_panel.log_info(f"OTA: {status} {msg}", "ESP32")
        else:
            import json
            detail = json.dumps(data, ensure_ascii=False, indent=2)
            self.log_panel.log_info(f"响应: {cmd}", "ESP32", detail)

    def _update_profile_list(self):
        """更新 Profile 列表"""
        self.profile_list.clear()
        if self.engine.profiles:
            for name in self.engine.profiles.list_profiles():
                self.profile_list.addItem(name)

    def _refresh_profile_list(self):
        """刷新 Profile 列表（Profile 编辑器回调）"""
        self._update_profile_list()

    def _update_key_display(self, keys: list):
        """更新按键显示"""
        for i, key in enumerate(keys):
            if i < len(self.key_cards):
                self.key_cards[i].update_key(key.display, key.action)

    def _update_status(self):
        """更新状态"""
        if self.engine.is_running():
            connected = self.engine.is_connected()
            if connected:
                self.status_indicator.set_status("online", "设备已连接")
            else:
                self.status_indicator.set_status("connecting", "连接中...")

    def _log(self, message: str, level: str = "INFO", tag: str = "", detail: str = ""):
        """添加日志（可从任意线程调用）"""
        # 发射信号到主线程处理
        self.log_signal.emit(message)

    def _process_log(self, message: str, level: str = "INFO", tag: str = "", detail: str = ""):
        """处理日志（仅在主线程调用）"""
        # 解析日志级别和标签
        if not level or level == "INFO":
            if "[OK]" in message:
                level = "OK"
            elif "[ERROR]" in message or "[FAIL]" in message:
                level = "ERROR"
            elif "[WARN]" in message:
                level = "WARN"
            elif "[DEBUG]" in message:
                level = "DEBUG"

        # 提取标签
        if not tag:
            import re
            m = re.search(r'\[([A-Z]+)\]', message)
            if m:
                tag = m.group(1)

        # 清理消息
        clean_msg = message
        for prefix in ["[OK]", "[ERROR]", "[WARN]", "[DEBUG]", "[INFO]"]:
            clean_msg = clean_msg.replace(prefix, "").strip()

        self.log_panel.log(clean_msg, level, tag, detail)

    def _append_log(self, message: str):
        """追加日志（信号槽，仅在主线程调用）"""
        self._process_log(message)

    def closeEvent(self, event):
        """关闭事件 - 最小化到托盘"""
        if self._tray_icon and self._tray_icon.isVisible():
            self.hide()
            self._tray_icon.showMessage(
                "AI Agent Deck",
                "程序已最小化到系统托盘",
                QSystemTrayIcon.Information,
                2000
            )
            event.ignore()
        else:
            self._cleanup_and_exit()
            event.accept()

    def _cleanup_and_exit(self):
        """清理并退出"""
        try:
            if self._tray_icon:
                self._tray_icon.hide()
            if self.engine.is_running():
                self.engine.stop()
            import time
            time.sleep(0.3)
        except Exception:
            pass

    def _init_system_tray(self):
        """初始化系统托盘图标"""
        self._tray_icon = None
        try:
            from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
            from PyQt5.QtGui import QIcon

            if not QSystemTrayIcon.isSystemTrayAvailable():
                return

            # 创建托盘图标
            tray_icon = self._create_tray_icon()
            self._tray_icon = QSystemTrayIcon(tray_icon, self)

            # 托盘菜单
            tray_menu = QMenu()

            show_action = QAction("显示主窗口", self)
            show_action.triggered.connect(self._show_from_tray)
            tray_menu.addAction(show_action)

            tray_menu.addSeparator()

            flash_action = QAction("烧录固件...", self)
            flash_action.triggered.connect(self._on_flash_firmware)
            tray_menu.addAction(flash_action)

            tray_menu.addSeparator()

            about_action = QAction("关于", self)
            about_action.triggered.connect(self._show_about)
            tray_menu.addAction(about_action)

            quit_action = QAction("退出", self)
            quit_action.triggered.connect(self._force_quit)
            tray_menu.addAction(quit_action)

            self._tray_icon.setContextMenu(tray_menu)
            self._tray_icon.activated.connect(self._on_tray_activated)
            self._tray_icon.show()

        except Exception as e:
            self._log(f"[WARN] 系统托盘初始化失败: {e}")

    def _create_tray_icon(self):
        """创建托盘图标"""
        from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor
        from PyQt5.QtCore import Qt

        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor("#1a1a2e"))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#0f3460"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(4, 4, 56, 56, 12, 12)

        from PyQt5.QtGui import QFont
        painter.setPen(QColor("#e94560"))
        painter.setFont(QFont("Segoe UI", 20, QFont.Bold))
        painter.drawText(4, 4, 56, 56, Qt.AlignCenter, "AD")
        painter.end()

        return QIcon(pixmap)

    def _on_tray_activated(self, reason):
        """托盘图标激活"""
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_from_tray()

    def _show_from_tray(self):
        """从托盘恢复显示"""
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _force_quit(self):
        """强制退出"""
        self._cleanup_and_exit()
        from PyQt5.QtWidgets import QApplication
        QApplication.quit()

    def _show_about(self):
        """显示关于对话框"""
        from ..version import get_version_info, get_version_display
        from PyQt5.QtWidgets import QMessageBox

        info = get_version_info()
        QMessageBox.about(
            self,
            "关于 AI Agent Deck",
            f"<h2>{info['app_name']}</h2>"
            f"<p>版本: {get_version_display()}</p>"
            f"<p>固件版本: v{info.get('firmware_version', 'N/A')} ({info.get('firmware_build', '')})</p>"
            f"<br>"
            f"<p>{info['description']}</p>"
            f"<br>"
            f"<p>基于 ESP32-S3 的上下文感知工作流控制器</p>"
            f"<p>自动检测当前应用，智能切换按键映射</p>"
            f"<br>"
            f"<p><a href='https://github.com/81823650800wzy-sketch/ai-agent-deck'>"
            f"GitHub 仓库</a></p>"
        )

    def _on_flash_firmware(self):
        """打开固件烧录对话框"""
        try:
            from ..core.flash_manager import FlashManager
            flash_mgr = FlashManager()

            fw_path = flash_mgr.get_firmware_path()
            if not fw_path:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "烧录固件", "未找到固件文件。\n请先编译固件或运行 build.bat 打包。")
                return

            # 检测串口
            import serial.tools.list_ports
            ports = serial.tools.list_ports.comports()
            esp_ports = [p for p in ports if 'CP210' in p.description or 'CH340' in p.description or 'USB' in p.description]

            if not esp_ports:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "烧录固件", "未检测到 ESP32 设备。\n请检查 USB 连接。")
                return

            # 选择串口
            from PyQt5.QtWidgets import QInputDialog
            port_names = [f"{p.device} ({p.description})" for p in esp_ports]
            port_str, ok = QInputDialog.getItem(self, "选择串口", "ESP32 串口:", port_names, 0, False)

            if not ok:
                return

            port = port_str.split(" ")[0]

            # 确认烧录
            from PyQt5.QtWidgets import QMessageBox
            ret = QMessageBox.question(
                self, "确认烧录",
                f"即将烧录固件到 {port}\n\n"
                f"固件: {fw_path.name}\n"
                f"大小: {fw_path.stat().st_size / 1024:.1f} KB\n\n"
                f"烧录过程中请勿断开连接。继续？",
                QMessageBox.Yes | QMessageBox.No
            )

            if ret != QMessageBox.Yes:
                return

            # 执行烧录（后台线程）
            def do_flash():
                def on_progress(p):
                    self.status_signal.emit(f"[烧录] {p.message}")
                    if p.error:
                        self.log_signal.emit("ERROR", f"[烧录] {p.error}")

                flash_mgr.set_progress_callback(on_progress)
                success = flash_mgr.flash_serial(port, fw_path)
                if success:
                    self.status_signal.emit("固件烧录完成")
                else:
                    self.status_signal.emit("固件烧录失败")

            import threading
            threading.Thread(target=do_flash, daemon=True).start()

        except Exception as e:
            self._log(f"[ERROR] 固件烧录失败: {e}")
