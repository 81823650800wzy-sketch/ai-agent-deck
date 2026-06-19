"""
AI Agent Deck - 主窗口
专业桌面应用程序界面
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QListWidget, QTextEdit,
    QComboBox, QGroupBox, QGridLayout, QStatusBar, QMenuBar,
    QAction, QMessageBox, QFileDialog, QSplitter
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette

from typing import Optional

from ..core.engine import Engine, EngineState, EngineConfig
from ..core.profile import Profile, KeyMapping
from .theme import ThemeManager


class KeyCard(QFrame):
    """按键卡片"""

    def __init__(self, key_id: str, parent=None):
        super().__init__(parent)
        self.key_id = key_id
        self._setup_ui()

    def _setup_ui(self):
        """初始化界面"""
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(1)
        self.setFixedSize(120, 80)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # 按键 ID
        self.id_label = QLabel(self.key_id)
        self.id_label.setFont(QFont("Consolas", 10, QFont.Bold))
        self.id_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.id_label)

        # 显示名称
        self.name_label = QLabel("未配置")
        self.name_label.setFont(QFont("Segoe UI", 10))
        self.name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.name_label)

        # 动作
        self.action_label = QLabel("")
        self.action_label.setFont(QFont("Segoe UI", 8))
        self.action_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.action_label)

    def update_key(self, key: Optional[KeyMapping]):
        """更新按键显示"""
        if key:
            self.name_label.setText(key.display)
            self.action_label.setText(key.action)
        else:
            self.name_label.setText("未配置")
            self.action_label.setText("")


class MainWindow(QMainWindow):
    """
    主窗口

    功能:
    - 设备连接管理
    - Profile 可视化
    - 按键测试
    - 日志显示
    - 主题切换
    """

    # 信号
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)

    def __init__(self, engine: Optional[Engine] = None):
        super().__init__()

        # 引擎
        self.engine = engine or Engine()
        self.theme_manager = ThemeManager()

        # 初始化 UI
        self._setup_ui()
        self._setup_menu()
        self._setup_status_bar()
        self._setup_connections()

        # 应用主题
        self._apply_theme()

        # 定时器
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_status)
        self._update_timer.start(500)

    def _setup_ui(self):
        """初始化界面"""
        self.setWindowTitle("AI Agent Deck - 工作流控制器")
        self.setMinimumSize(900, 600)

        # 中央部件
        central = QWidget()
        self.setCentralWidget(central)

        # 主布局
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 左侧面板
        left_panel = self._create_left_panel()
        main_layout.addWidget(left_panel)

        # 右侧面板
        right_panel = self._create_right_panel()
        main_layout.addWidget(right_panel)

    def _create_left_panel(self) -> QWidget:
        """创建左侧面板"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Box)
        panel.setFixedWidth(250)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 设备状态
        device_group = QGroupBox("设备状态")
        device_layout = QVBoxLayout()

        self.status_label = QLabel("未连接")
        self.status_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        device_layout.addWidget(self.status_label)

        self.app_label = QLabel("当前应用: 无")
        device_layout.addWidget(self.app_label)

        self.profile_label = QLabel("当前 Profile: 无")
        self.profile_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        device_layout.addWidget(self.profile_label)

        device_group.setLayout(device_layout)
        layout.addWidget(device_group)

        # 控制按钮
        control_group = QGroupBox("控制")
        control_layout = QVBoxLayout()

        self.start_btn = QPushButton("启动")
        self.start_btn.clicked.connect(self._on_start)
        control_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self._on_stop)
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)

        self.test_btn = QPushButton("测试连接")
        self.test_btn.clicked.connect(self._on_test)
        control_layout.addWidget(self.test_btn)

        control_group.setLayout(control_layout)
        layout.addWidget(control_group)

        # Profile 列表
        profile_group = QGroupBox("Profile 列表")
        profile_layout = QVBoxLayout()

        self.profile_list = QListWidget()
        self.profile_list.currentTextChanged.connect(self._on_profile_select)
        profile_layout.addWidget(self.profile_list)

        profile_group.setLayout(profile_layout)
        layout.addWidget(profile_group)

        # 主题选择
        theme_group = QGroupBox("主题")
        theme_layout = QVBoxLayout()

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(self.theme_manager.list_themes())
        self.theme_combo.currentTextChanged.connect(self._on_theme_change)
        theme_layout.addWidget(self.theme_combo)

        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)

        return panel

    def _create_right_panel(self) -> QWidget:
        """创建右侧面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 按键映射
        keys_group = QGroupBox("按键映射")
        keys_layout = QGridLayout()
        keys_layout.setSpacing(10)

        self.key_cards = []
        for row in range(3):
            for col in range(2):
                idx = row * 2 + col
                key_id = f"K{idx + 1}"
                card = KeyCard(key_id)
                keys_layout.addWidget(card, row, col)
                self.key_cards.append(card)

        keys_group.setLayout(keys_layout)
        layout.addWidget(keys_group)

        # 日志区域
        log_group = QGroupBox("日志")
        log_layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)

        # 日志按钮
        log_btn_layout = QHBoxLayout()

        clear_btn = QPushButton("清空日志")
        clear_btn.clicked.connect(self._on_clear_log)
        log_btn_layout.addWidget(clear_btn)

        test_profile_btn = QPushButton("发送测试 Profile")
        test_profile_btn.clicked.connect(self._on_send_test)
        log_btn_layout.addWidget(test_profile_btn)

        log_layout.addLayout(log_btn_layout)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        return panel

    def _setup_menu(self):
        """设置菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件")

        import_action = QAction("导入 Profile", self)
        import_action.triggered.connect(self._on_import_profile)
        file_menu.addAction(import_action)

        export_action = QAction("导出 Profile", self)
        export_action.triggered.connect(self._on_export_profile)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 视图菜单
        view_menu = menubar.addMenu("视图")

        themes = self.theme_manager.list_themes()
        for theme_name in themes:
            action = QAction(theme_name, self)
            action.triggered.connect(lambda checked, name=theme_name: self._on_theme_change(name))
            view_menu.addAction(action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助")

        about_action = QAction("关于", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _setup_status_bar(self):
        """设置状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.status_bar.showMessage("就绪")

    def _setup_connections(self):
        """设置信号连接"""
        # 引擎事件
        self.engine.on('state_change', self._on_state_change)
        self.engine.on('device_connect', self._on_device_connect)
        self.engine.on('device_disconnect', self._on_device_disconnect)
        self.engine.on('app_change', self._on_app_change)
        self.engine.on('profile_change', self._on_profile_change)
        self.engine.on('error', self._on_error)

        # 信号
        self.log_signal.connect(self._append_log)
        self.status_signal.connect(self.status_bar.showMessage)

    def _apply_theme(self):
        """应用主题"""
        stylesheet = self.theme_manager.get_stylesheet()
        self.setStyleSheet(stylesheet)

    def _on_start(self):
        """启动引擎"""
        try:
            self.engine.start()
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self._log("[OK] 引擎已启动")
        except Exception as e:
            self._log(f"[FAIL] 启动失败: {e}")

    def _on_stop(self):
        """停止引擎"""
        try:
            self.engine.stop()
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self._log("[OK] 引擎已停止")
        except Exception as e:
            self._log(f"[FAIL] 停止失败: {e}")

    def _on_test(self):
        """测试连接"""
        self._log("[TEST] 测试连接...")
        # TODO: 实现连接测试

    def _on_profile_select(self, name: str):
        """Profile 选择"""
        profile = self.engine.profiles.get_profile_by_name(name)
        if profile:
            self._update_key_display(profile.keys)

    def _on_theme_change(self, name: str):
        """主题切换"""
        self.theme_manager.set_theme(name)
        self._apply_theme()
        self._log(f"[THEME] 切换主题: {name}")

    def _on_clear_log(self):
        """清空日志"""
        self.log_text.clear()

    def _on_send_test(self):
        """发送测试 Profile"""
        if not self.engine.is_running():
            QMessageBox.warning(self, "警告", "请先启动引擎")
            return

        test_profile = Profile(
            name="Test",
            keys=[
                KeyMapping("K1", "Test-A", "key_combo", "ctrl+a"),
                KeyMapping("K2", "Test-B", "key_combo", "ctrl+b"),
                KeyMapping("K3", "Test-C", "key_combo", "ctrl+c"),
                KeyMapping("K4", "Test-D", "key_combo", "ctrl+d"),
                KeyMapping("K5", "Test-E", "key_combo", "ctrl+e"),
                KeyMapping("K6", "Test-F", "key_combo", "ctrl+f"),
            ]
        )

        success = self.engine.send_profile(test_profile)
        if success:
            self._log("[OK] 测试 Profile 已发送")
        else:
            self._log("[FAIL] 发送失败")

    def _on_import_profile(self):
        """导入 Profile"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入 Profile", "", "JSON Files (*.json)"
        )
        if file_path:
            profile = self.engine.profiles.import_profile(file_path)
            if profile:
                self._update_profile_list()
                self._log(f"[OK] 导入 Profile: {profile.name}")
            else:
                self._log("[FAIL] 导入失败")

    def _on_export_profile(self):
        """导出 Profile"""
        if not self.profile_list.currentItem():
            QMessageBox.warning(self, "警告", "请选择要导出的 Profile")
            return

        name = self.profile_list.currentItem().text()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出 Profile", f"{name}.json", "JSON Files (*.json)"
        )
        if file_path:
            self.engine.profiles.export_profile(name, file_path)
            self._log(f"[OK] 导出 Profile: {name}")

    def _on_about(self):
        """关于"""
        QMessageBox.about(
            self,
            "关于 AI Agent Deck",
            "AI Agent Deck v2.0\n\n"
            "桌面 AI 工作流控制终端\n\n"
            "功能:\n"
            "- 自动感知工作场景\n"
            "- 智能按键映射\n"
            "- 个人工作流数据库"
        )

    def _on_state_change(self, state: EngineState):
        """引擎状态变化"""
        self.status_signal.emit(f"引擎状态: {state.value}")

    def _on_device_connect(self):
        """设备连接"""
        self.status_label.setText("已连接")
        self.status_label.setStyleSheet("color: green")
        self._log("[OK] 设备已连接")

    def _on_device_disconnect(self):
        """设备断开"""
        self.status_label.setText("未连接")
        self.status_label.setStyleSheet("color: red")
        self._log("[WARN] 设备已断开")

    def _on_app_change(self, new_app, old_app):
        """应用切换"""
        self.app_label.setText(f"当前应用: {new_app.process_name}")
        self._log(f"[APP] 切换: {old_app.process_name if old_app else 'N/A'} → {new_app.process_name}")

    def _on_profile_change(self, profile: Profile):
        """Profile 切换"""
        self.profile_label.setText(f"当前 Profile: {profile.name}")
        self._update_key_display(profile.keys)
        self._log(f"[PROFILE] 切换: {profile.name}")

    def _on_error(self, error: str):
        """错误"""
        self._log(f"[ERROR] {error}")

    def _update_profile_list(self):
        """更新 Profile 列表"""
        self.profile_list.clear()
        if self.engine.profiles:
            for name in self.engine.profiles.list_profiles():
                self.profile_list.addItem(name)

    def _update_key_display(self, keys: list):
        """更新按键显示"""
        for i, key in enumerate(keys):
            if i < len(self.key_cards):
                self.key_cards[i].update_key(key)

    def _update_status(self):
        """更新状态"""
        if self.engine.is_running():
            connected = self.engine.is_connected()
            self.status_label.setText("已连接" if connected else "连接中...")

    def _log(self, message: str):
        """添加日志"""
        self.log_signal.emit(message)

    def _append_log(self, message: str):
        """追加日志"""
        self.log_text.append(message)

    def closeEvent(self, event):
        """关闭事件"""
        if self.engine.is_running():
            self.engine.stop()
        event.accept()
