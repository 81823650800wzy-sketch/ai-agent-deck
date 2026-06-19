"""
AI Agent Deck - 关于对话框
自定义深色主题样式，展示应用信息和系统环境
"""

import platform
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QWidget,
)
from PyQt5.QtCore import Qt, QT_VERSION_STR
from PyQt5.QtGui import QColor, QPainter, QLinearGradient

from .modern_theme import ModernColors
from .modern_widgets import AppIcon
from ..version import (
    __version__, APP_NAME, APP_DESCRIPTION, APP_URL,
    FIRMWARE_VERSION, FIRMWARE_BUILD,
)


# ── 渐变头部（纯绘制层，不干扰子控件）──────────

class _GradientHeader(QWidget):
    """渐变色头部背景"""

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # 主渐变
        g = QLinearGradient(0, 0, self.width(), self.height())
        g.setColorAt(0, QColor(ModernColors.GRADIENT_START))
        g.setColorAt(1, QColor(ModernColors.GRADIENT_END))
        p.fillRect(self.rect(), g)

        # 装饰性半透明光斑
        p.setBrush(QColor(255, 255, 255, 15))
        p.setPen(Qt.NoPen)
        p.drawEllipse(self.width() - 100, -50, 220, 220)
        p.drawEllipse(-40, self.height() - 70, 160, 160)

        p.end()


# ── 关于对话框 ──────────────────────────────────

class AboutDialog(QDialog):
    """自定义「关于」对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于 AI Agent Deck")
        self.setFixedSize(440, 520)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._build_ui()

    # ── UI 构建 ──────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 渐变头部
        root.addWidget(self._make_header())

        # 信息区域
        body = QWidget()
        body.setStyleSheet(f"background: {ModernColors.BG_PRIMARY};")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(28, 20, 28, 20)
        bl.setSpacing(14)

        # 项目描述
        bl.addWidget(self._centered_label(
            APP_DESCRIPTION, ModernColors.TEXT_SECONDARY, 12,
        ))

        # 功能亮点
        bl.addWidget(self._centered_label(
            "自动检测当前应用 · 智能切换按键映射\n"
            "ESP32-S3 硬件控制 · BLE / WiFi / 串口通信",
            ModernColors.TEXT_TERTIARY, 11,
        ))

        bl.addWidget(self._separator())

        # 系统信息表
        info_items = [
            ("固件版本", f"v{FIRMWARE_VERSION} ({FIRMWARE_BUILD})"),
            ("Python", platform.python_version()),
            ("Qt", QT_VERSION_STR),
            ("操作系统", f"{platform.system()} {platform.release()}"),
        ]
        for key, val in info_items:
            bl.addLayout(self._info_row(key, val))

        bl.addWidget(self._separator())

        # 外部链接
        links = QHBoxLayout()
        links.setAlignment(Qt.AlignCenter)
        links.setSpacing(24)
        links.addWidget(self._link("GitHub 仓库", APP_URL))
        links.addWidget(self._link("报告问题", f"{APP_URL}/issues"))
        bl.addLayout(links)

        # 版权
        bl.addWidget(self._centered_label(
            "MIT License · Copyright 2024 AI Agent Deck Team",
            ModernColors.TEXT_TERTIARY, 10,
        ))

        bl.addStretch()

        # 关闭按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.setFixedSize(100, 36)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: {ModernColors.PRIMARY};
                color: white; border: none;
                border-radius: 18px;
                font-size: 13px; font-weight: bold;
            }}
            QPushButton:hover {{ background: {ModernColors.PRIMARY_HOVER}; }}
            QPushButton:pressed {{ background: {ModernColors.PRIMARY_PRESSED}; }}
        """)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        btn_row.addStretch()
        bl.addLayout(btn_row)

        root.addWidget(body)

    # ── 辅助工厂方法 ─────────────────────────

    @staticmethod
    def _make_header() -> QWidget:
        """构建渐变头部"""
        h = _GradientHeader()
        h.setFixedHeight(200)
        hl = QVBoxLayout(h)
        hl.setAlignment(Qt.AlignCenter)
        hl.setSpacing(8)

        # 应用图标
        hl.addWidget(AppIcon(64), alignment=Qt.AlignCenter)

        # 应用名称
        hl.addWidget(AboutDialog._centered_label(
            APP_NAME, "#ffffff", 20, bold=True,
        ))

        # 版本号
        hl.addWidget(AboutDialog._centered_label(
            f"v{__version__}", "rgba(255,255,255,0.8)", 12,
        ))
        return h

    @staticmethod
    def _centered_label(text: str, color: str, size: int,
                        bold: bool = False) -> QLabel:
        lbl = QLabel(text)
        weight = "bold" if bold else "normal"
        lbl.setStyleSheet(
            f"color: {color}; font-size: {size}px; font-weight: {weight};"
        )
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setWordWrap(True)
        return lbl

    @staticmethod
    def _separator() -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.HLine)
        f.setStyleSheet(f"color: {ModernColors.BORDER};")
        return f

    @staticmethod
    def _info_row(key: str, val: str) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)

        k = QLabel(key)
        k.setFixedWidth(80)
        k.setStyleSheet(
            f"color: {ModernColors.TEXT_TERTIARY}; font-size: 11px;"
        )
        row.addWidget(k)

        v = QLabel(val)
        v.setStyleSheet(
            f"color: {ModernColors.TEXT_PRIMARY}; font-size: 11px;"
            f"font-family: 'Cascadia Code','Consolas',monospace;"
        )
        row.addWidget(v)
        return row

    @staticmethod
    def _link(text: str, url: str) -> QLabel:
        lbl = QLabel(
            f'<a href="{url}" style="color:{ModernColors.TEXT_ACCENT};'
            f'text-decoration:none;">{text}</a>'
        )
        lbl.setOpenExternalLinks(True)
        lbl.setStyleSheet("font-size: 11px;")
        return lbl
