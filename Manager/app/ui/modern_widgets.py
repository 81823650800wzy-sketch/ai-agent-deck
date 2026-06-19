"""
AI Agent Deck - 现代化组件
自定义 UI 组件
"""

from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsDropShadowEffect, QWidget, QSizePolicy
)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, QSize
from PyQt5.QtGui import (
    QColor, QPainter, QPainterPath, QLinearGradient,
    QFont, QIcon, QPixmap, QBrush, QPen
)

from .modern_theme import ModernColors, ModernFonts


class Card(QFrame):
    """现代化卡片"""

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.title = title
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(f"""
            Card {{
                background-color: {ModernColors.BG_CARD};
                border: 1px solid {ModernColors.BORDER};
                border-radius: 12px;
                padding: 16px;
            }}
        """)

        # 添加阴影
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 50))
        self.setGraphicsEffect(shadow)

        # 布局
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(12)

        # 标题
        if self.title:
            title_label = QLabel(self.title)
            title_label.setProperty("subheading", True)
            title_label.setStyleSheet(f"""
                font-size: 14px;
                font-weight: bold;
                color: {ModernColors.TEXT_PRIMARY};
                padding-bottom: 8px;
                border-bottom: 1px solid {ModernColors.BORDER};
            """)
            self.layout.addWidget(title_label)

    def add_widget(self, widget):
        self.layout.addWidget(widget)

    def add_layout(self, layout):
        self.layout.addLayout(layout)


class StatusIndicator(QWidget):
    """状态指示器"""

    def __init__(self, text: str = "", status: str = "offline", parent=None):
        super().__init__(parent)
        self.text = text
        self.status = status
        self.setMinimumHeight(28)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 状态颜色
        colors = {
            "online": ModernColors.SUCCESS,
            "offline": ModernColors.TEXT_TERTIARY,
            "warning": ModernColors.WARNING,
            "error": ModernColors.ERROR,
            "connecting": ModernColors.PRIMARY
        }
        color = colors.get(self.status, ModernColors.TEXT_TERTIARY)

        # 绘制状态点
        dot_size = 8
        dot_x = 4
        dot_y = (self.height() - dot_size) // 2

        painter.setBrush(QColor(color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(dot_x, dot_y, dot_size, dot_size)

        # 绘制文字
        painter.setPen(QColor(ModernColors.TEXT_PRIMARY))
        painter.setFont(ModernFonts.BODY)
        painter.drawText(
            dot_x + dot_size + 8, 0,
            self.width() - dot_x - dot_size - 8, self.height(),
            Qt.AlignVCenter | Qt.AlignLeft,
            self.text
        )

        painter.end()

    def set_status(self, status: str, text: str = None):
        self.status = status
        if text:
            self.text = text
        self.update()


class IconButton(QPushButton):
    """图标按钮"""

    def __init__(self, icon_char: str, tooltip: str = "", size: int = 36, parent=None):
        super().__init__(parent)
        self.icon_char = icon_char
        self.tooltip = tooltip
        self.btn_size = size
        self._setup_ui()

    def _setup_ui(self):
        self.setFixedSize(self.btn_size, self.btn_size)
        self.setToolTip(self.tooltip)
        self.setCursor(Qt.PointingHandCursor)

        self.setStyleSheet(f"""
            IconButton {{
                background-color: {ModernColors.BG_TERTIARY};
                border: 1px solid {ModernColors.BORDER};
                border-radius: {self.btn_size // 2}px;
                font-size: 14px;
                color: {ModernColors.TEXT_PRIMARY};
            }}
            IconButton:hover {{
                background-color: {ModernColors.PRIMARY};
                border-color: {ModernColors.PRIMARY};
            }}
            IconButton:pressed {{
                background-color: {ModernColors.PRIMARY_PRESSED};
            }}
        """)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QColor(ModernColors.TEXT_PRIMARY))
        painter.setFont(QFont("Segoe MDL2 Assets", 12))
        painter.drawText(self.rect(), Qt.AlignCenter, self.icon_char)
        painter.end()


class GradientButton(QPushButton):
    """渐变按钮"""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self._setup_ui()

    def _setup_ui(self):
        self.setMinimumHeight(36)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            GradientButton {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {ModernColors.GRADIENT_START},
                    stop:1 {ModernColors.GRADIENT_END}
                );
                color: white;
                border: none;
                border-radius: 22px;
                font-size: 13px;
                font-weight: bold;
                padding: 0 24px;
            }}
            GradientButton:hover {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {ModernColors.PRIMARY_HOVER},
                    stop:1 {ModernColors.GRADIENT_END}
                );
            }}
            GradientButton:pressed {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {ModernColors.PRIMARY_PRESSED},
                    stop:1 {ModernColors.GRADIENT_END}
                );
            }}
            GradientButton:disabled {{
                background: {ModernColors.BG_TERTIARY};
                color: {ModernColors.TEXT_TERTIARY};
            }}
        """)


class OutlineButton(QPushButton):
    """轮廓按钮"""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self._setup_ui()

    def _setup_ui(self):
        self.setMinimumHeight(36)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            OutlineButton {{
                background-color: transparent;
                color: {ModernColors.TEXT_PRIMARY};
                border: 1px solid {ModernColors.BORDER_LIGHT};
                border-radius: 22px;
                font-size: 13px;
                font-weight: bold;
                padding: 0 24px;
            }}
            OutlineButton:hover {{
                background-color: {ModernColors.BG_TERTIARY};
                border-color: {ModernColors.PRIMARY};
                color: {ModernColors.PRIMARY};
            }}
            OutlineButton:pressed {{
                background-color: {ModernColors.BG_INPUT};
            }}
        """)


class KeyCard(QFrame):
    """按键卡片"""

    def __init__(self, key_id: str, parent=None):
        super().__init__(parent)
        self.key_id = key_id
        self._setup_ui()

    def _setup_ui(self):
        self.setMinimumSize(120, 80)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            KeyCard {{
                background-color: {ModernColors.BG_INPUT};
                border: 1px solid {ModernColors.BORDER};
                border-radius: 10px;
            }}
            KeyCard:hover {{
                border-color: {ModernColors.PRIMARY};
                background-color: {ModernColors.BG_TERTIARY};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        # 按键 ID
        self.id_label = QLabel(self.key_id)
        self.id_label.setStyleSheet(f"""
            font-family: "Cascadia Code", "Consolas", monospace;
            font-size: 10px;
            font-weight: bold;
            color: {ModernColors.TEXT_ACCENT};
        """)
        layout.addWidget(self.id_label)

        # 显示名称
        self.name_label = QLabel("未配置")
        self.name_label.setStyleSheet(f"""
            font-size: 11px;
            font-weight: bold;
            color: {ModernColors.TEXT_PRIMARY};
        """)
        self.name_label.setWordWrap(True)
        layout.addWidget(self.name_label)

        # 动作
        self.action_label = QLabel("")
        self.action_label.setStyleSheet(f"""
            font-size: 9px;
            color: {ModernColors.TEXT_TERTIARY};
        """)
        self.action_label.setWordWrap(True)
        layout.addWidget(self.action_label)

    def update_key(self, name: str = "", action: str = ""):
        self.name_label.setText(name or "未配置")
        self.action_label.setText(action)

    def set_active(self, active: bool):
        if active:
            self.setStyleSheet(f"""
                KeyCard {{
                    background-color: {ModernColors.PRIMARY};
                    border: 2px solid {ModernColors.PRIMARY};
                    border-radius: 10px;
                }}
            """)
            self.name_label.setStyleSheet(f"""
                font-size: 12px;
                font-weight: bold;
                color: white;
            """)
        else:
            self._setup_ui()


class ProfileCard(QFrame):
    """Profile 卡片"""

    def __init__(self, name: str, description: str = "", parent=None):
        super().__init__(parent)
        self.name = name
        self.description = description
        self._setup_ui()

    def _setup_ui(self):
        self.setFixedHeight(60)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            ProfileCard {{
                background-color: {ModernColors.BG_INPUT};
                border: 1px solid {ModernColors.BORDER};
                border-radius: 8px;
            }}
            ProfileCard:hover {{
                border-color: {ModernColors.PRIMARY};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        # 图标
        icon_label = QLabel("⌨")
        icon_label.setStyleSheet("font-size: 20px;")
        layout.addWidget(icon_label)

        # 信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        name_label = QLabel(self.name)
        name_label.setStyleSheet(f"""
            font-size: 12px;
            font-weight: bold;
            color: {ModernColors.TEXT_PRIMARY};
        """)
        info_layout.addWidget(name_label)

        desc_label = QLabel(self.description)
        desc_label.setStyleSheet(f"""
            font-size: 10px;
            color: {ModernColors.TEXT_SECONDARY};
        """)
        info_layout.addWidget(desc_label)

        layout.addLayout(info_layout)
        layout.addStretch()

    def set_selected(self, selected: bool):
        if selected:
            self.setStyleSheet(f"""
                ProfileCard {{
                    background-color: {ModernColors.PRIMARY};
                    border: 2px solid {ModernColors.PRIMARY};
                    border-radius: 8px;
                }}
            """)
        else:
            self._setup_ui()


class AppIcon(QWidget):
    """应用图标"""

    def __init__(self, size: int = 64, parent=None):
        super().__init__(parent)
        self.icon_size = size
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制背景圆形
        gradient = QLinearGradient(0, 0, self.icon_size, self.icon_size)
        gradient.setColorAt(0, QColor(ModernColors.GRADIENT_START))
        gradient.setColorAt(1, QColor(ModernColors.GRADIENT_END))

        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, self.icon_size, self.icon_size)

        # 绘制图标文字
        painter.setPen(QColor(Qt.white))
        painter.setFont(QFont("Segoe UI", self.icon_size // 3, QFont.Bold))
        painter.drawText(self.rect(), Qt.AlignCenter, "AD")

        painter.end()
