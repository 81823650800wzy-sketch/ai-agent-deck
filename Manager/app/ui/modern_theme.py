"""
AI Agent Deck - 现代化主题
支持 Dark / Light / Neon 三套主题实时切换
"""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPalette, QFont, QLinearGradient, QPainter, QBrush
from PyQt5.QtWidgets import QApplication, QGraphicsDropShadowEffect


# ── 主题配置表 ──────────────────────────────────
THEME_CONFIGS = {
    "深色": {
        "PRIMARY": "#6C5CE7", "PRIMARY_HOVER": "#7E6FF0", "PRIMARY_PRESSED": "#5A4BD6",
        "BG_PRIMARY": "#0F0F1A", "BG_SECONDARY": "#1A1A2E", "BG_TERTIARY": "#16213E",
        "BG_CARD": "#1E1E3A", "BG_INPUT": "#252545",
        "TEXT_PRIMARY": "#FFFFFF", "TEXT_SECONDARY": "#B0B0CC", "TEXT_TERTIARY": "#6B6B8D",
        "TEXT_ACCENT": "#A29BFE",
        "SUCCESS": "#00D2FF", "WARNING": "#FECA57", "ERROR": "#FF6B6B", "INFO": "#48DBFB",
        "BORDER": "#2D2D5E", "BORDER_LIGHT": "#3D3D7E",
        "GRADIENT_START": "#6C5CE7", "GRADIENT_END": "#A29BFE",
    },
    "浅色": {
        "PRIMARY": "#2196F3", "PRIMARY_HOVER": "#42A5F5", "PRIMARY_PRESSED": "#1976D2",
        "BG_PRIMARY": "#F5F5F5", "BG_SECONDARY": "#FFFFFF", "BG_TERTIARY": "#E8E8E8",
        "BG_CARD": "#FFFFFF", "BG_INPUT": "#FAFAFA",
        "TEXT_PRIMARY": "#212121", "TEXT_SECONDARY": "#757575", "TEXT_TERTIARY": "#9E9E9E",
        "TEXT_ACCENT": "#1976D2",
        "SUCCESS": "#4CAF50", "WARNING": "#FF9800", "ERROR": "#F44336", "INFO": "#2196F3",
        "BORDER": "#E0E0E0", "BORDER_LIGHT": "#BDBDBD",
        "GRADIENT_START": "#2196F3", "GRADIENT_END": "#64B5F6",
    },
    "霓虹": {
        "PRIMARY": "#00FF00", "PRIMARY_HOVER": "#33FF33", "PRIMARY_PRESSED": "#00CC00",
        "BG_PRIMARY": "#0A0A0A", "BG_SECONDARY": "#111111", "BG_TERTIARY": "#1A1A1A",
        "BG_CARD": "#0D0D0D", "BG_INPUT": "#151515",
        "TEXT_PRIMARY": "#00FF00", "TEXT_SECONDARY": "#00CC00", "TEXT_TERTIARY": "#008800",
        "TEXT_ACCENT": "#FF00FF",
        "SUCCESS": "#00FF00", "WARNING": "#FFFF00", "ERROR": "#FF0000", "INFO": "#00FFFF",
        "BORDER": "#00FF00", "BORDER_LIGHT": "#003300",
        "GRADIENT_START": "#FF00FF", "GRADIENT_END": "#00FFFF",
    },
}

# 当前激活的主题名（模块级状态）
_current_theme_name = "深色"


class ModernColors:
    """现代配色方案 — 动态代理当前主题"""
    # 默认值（深色），实际运行时由 get_theme_colors() 覆盖
    PRIMARY = "#6C5CE7"
    PRIMARY_HOVER = "#7E6FF0"
    PRIMARY_PRESSED = "#5A4BD6"
    BG_PRIMARY = "#0F0F1A"
    BG_SECONDARY = "#1A1A2E"
    BG_TERTIARY = "#16213E"
    BG_CARD = "#1E1E3A"
    BG_INPUT = "#252545"
    TEXT_PRIMARY = "#FFFFFF"
    TEXT_SECONDARY = "#B0B0CC"
    TEXT_TERTIARY = "#6B6B8D"
    TEXT_ACCENT = "#A29BFE"
    SUCCESS = "#00D2FF"
    WARNING = "#FECA57"
    ERROR = "#FF6B6B"
    INFO = "#48DBFB"
    BORDER = "#2D2D5E"
    BORDER_LIGHT = "#3D3D7E"
    GRADIENT_START = "#6C5CE7"
    GRADIENT_END = "#A29BFE"


def set_theme(name: str):
    """切换当前主题，更新 ModernColors 类属性"""
    global _current_theme_name
    cfg = THEME_CONFIGS.get(name)
    if not cfg:
        return
    _current_theme_name = name
    for key, val in cfg.items():
        setattr(ModernColors, key, val)


def get_theme_names() -> list:
    """返回所有可用主题名"""
    return list(THEME_CONFIGS.keys())


class ModernFonts:
    """现代字体"""
    FAMILY = "Segoe UI"
    FAMILY_MONO = "Cascadia Code"

    TITLE = QFont(FAMILY, 24, QFont.Bold)
    HEADER = QFont(FAMILY, 16, QFont.Bold)
    SUBHEADER = QFont(FAMILY, 12, QFont.Medium)
    BODY = QFont(FAMILY, 10)
    BODY_BOLD = QFont(FAMILY, 10, QFont.Bold)
    CAPTION = QFont(FAMILY, 9)
    MONO = QFont(FAMILY_MONO, 9)


def get_modern_stylesheet() -> str:
    """获取现代化样式表"""
    return f"""
    /* 主窗口 */
    QMainWindow {{
        background-color: {ModernColors.BG_PRIMARY};
        color: {ModernColors.TEXT_PRIMARY};
    }}

    QWidget {{
        background-color: transparent;
        color: {ModernColors.TEXT_PRIMARY};
        font-family: "Segoe UI", "Microsoft YaHei UI", sans-serif;
        font-size: 10px;
    }}

    /* 菜单栏 */
    QMenuBar {{
        background-color: {ModernColors.BG_SECONDARY};
        color: {ModernColors.TEXT_PRIMARY};
        border-bottom: 1px solid {ModernColors.BORDER};
        padding: 4px 8px;
    }}

    QMenuBar::item {{
        background-color: transparent;
        padding: 6px 12px;
        border-radius: 4px;
    }}

    QMenuBar::item:selected {{
        background-color: {ModernColors.BG_TERTIARY};
    }}

    QMenu {{
        background-color: {ModernColors.BG_CARD};
        color: {ModernColors.TEXT_PRIMARY};
        border: 1px solid {ModernColors.BORDER};
        border-radius: 8px;
        padding: 4px;
    }}

    QMenu::item {{
        padding: 8px 24px;
        border-radius: 4px;
    }}

    QMenu::item:selected {{
        background-color: {ModernColors.PRIMARY};
    }}

    /* 按钮 */
    QPushButton {{
        background-color: {ModernColors.PRIMARY};
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 8px;
        font-weight: bold;
        font-size: 11px;
    }}

    QPushButton:hover {{
        background-color: {ModernColors.PRIMARY_HOVER};
    }}

    QPushButton:pressed {{
        background-color: {ModernColors.PRIMARY_PRESSED};
    }}

    QPushButton:disabled {{
        background-color: {ModernColors.BG_TERTIARY};
        color: {ModernColors.TEXT_TERTIARY};
    }}

    /* 次要按钮 */
    QPushButton[secondary="true"] {{
        background-color: transparent;
        border: 1px solid {ModernColors.BORDER_LIGHT};
        color: {ModernColors.TEXT_PRIMARY};
    }}

    QPushButton[secondary="true"]:hover {{
        background-color: {ModernColors.BG_TERTIARY};
        border-color: {ModernColors.PRIMARY};
    }}

    /* 危险按钮 */
    QPushButton[danger="true"] {{
        background-color: {ModernColors.ERROR};
    }}

    QPushButton[danger="true"]:hover {{
        background-color: #FF5252;
    }}

    /* 分组框 */
    QGroupBox {{
        background-color: {ModernColors.BG_CARD};
        border: 1px solid {ModernColors.BORDER};
        border-radius: 12px;
        margin-top: 12px;
        padding: 16px;
        padding-top: 28px;
        font-weight: bold;
        font-size: 11px;
        color: {ModernColors.TEXT_PRIMARY};
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 16px;
        top: 4px;
        padding: 0 8px;
        color: {ModernColors.TEXT_ACCENT};
        background-color: {ModernColors.BG_CARD};
    }}

    /* 列表 */
    QListWidget {{
        background-color: {ModernColors.BG_INPUT};
        border: 1px solid {ModernColors.BORDER};
        border-radius: 8px;
        padding: 4px;
        outline: none;
    }}

    QListWidget::item {{
        padding: 10px 12px;
        border-radius: 6px;
        margin: 2px;
    }}

    QListWidget::item:selected {{
        background-color: {ModernColors.PRIMARY};
        color: white;
    }}

    QListWidget::item:hover {{
        background-color: {ModernColors.BG_TERTIARY};
    }}

    /* 文本框 */
    QTextEdit {{
        background-color: {ModernColors.BG_INPUT};
        color: {ModernColors.TEXT_PRIMARY};
        border: 1px solid {ModernColors.BORDER};
        border-radius: 8px;
        padding: 8px;
        font-family: "Cascadia Code", "Consolas", monospace;
        font-size: 11px;
        selection-background-color: {ModernColors.PRIMARY};
    }}

    /* 标签 */
    QLabel {{
        color: {ModernColors.TEXT_PRIMARY};
        background-color: transparent;
    }}

    QLabel[heading="true"] {{
        font-size: 24px;
        font-weight: bold;
        color: {ModernColors.TEXT_PRIMARY};
    }}

    QLabel[subheading="true"] {{
        font-size: 14px;
        font-weight: bold;
        color: {ModernColors.TEXT_PRIMARY};
    }}

    QLabel[caption="true"] {{
        font-size: 10px;
        color: {ModernColors.TEXT_SECONDARY};
    }}

    QLabel[accent="true"] {{
        color: {ModernColors.TEXT_ACCENT};
    }}

    QLabel[success="true"] {{
        color: {ModernColors.SUCCESS};
    }}

    QLabel[warning="true"] {{
        color: {ModernColors.WARNING};
    }}

    QLabel[error="true"] {{
        color: {ModernColors.ERROR};
    }}

    /* 下拉框 */
    QComboBox {{
        background-color: {ModernColors.BG_INPUT};
        color: {ModernColors.TEXT_PRIMARY};
        border: 1px solid {ModernColors.BORDER};
        border-radius: 8px;
        padding: 8px 12px;
        min-width: 100px;
    }}

    QComboBox:hover {{
        border-color: {ModernColors.PRIMARY};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {ModernColors.BG_CARD};
        color: {ModernColors.TEXT_PRIMARY};
        border: 1px solid {ModernColors.BORDER};
        border-radius: 8px;
        selection-background-color: {ModernColors.PRIMARY};
    }}

    /* 滚动条 */
    QScrollBar:vertical {{
        background-color: {ModernColors.BG_PRIMARY};
        width: 8px;
        border-radius: 4px;
    }}

    QScrollBar::handle:vertical {{
        background-color: {ModernColors.BORDER_LIGHT};
        border-radius: 4px;
        min-height: 40px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: {ModernColors.PRIMARY};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    /* 状态栏 */
    QStatusBar {{
        background-color: {ModernColors.BG_SECONDARY};
        color: {ModernColors.TEXT_SECONDARY};
        border-top: 1px solid {ModernColors.BORDER};
        padding: 4px 12px;
        font-size: 10px;
    }}

    /* 分隔线 */
    QFrame[frameShape="4"] {{
        color: {ModernColors.BORDER};
        max-height: 1px;
    }}

    /* 输入框 */
    QLineEdit {{
        background-color: {ModernColors.BG_INPUT};
        color: {ModernColors.TEXT_PRIMARY};
        border: 1px solid {ModernColors.BORDER};
        border-radius: 8px;
        padding: 8px 12px;
    }}

    QLineEdit:focus {{
        border-color: {ModernColors.PRIMARY};
    }}

    /* 复选框 */
    QCheckBox {{
        color: {ModernColors.TEXT_PRIMARY};
        spacing: 8px;
    }}

    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 1px solid {ModernColors.BORDER_LIGHT};
        background-color: {ModernColors.BG_INPUT};
    }}

    QCheckBox::indicator:checked {{
        background-color: {ModernColors.PRIMARY};
        border-color: {ModernColors.PRIMARY};
    }}

    /* 工具提示 */
    QToolTip {{
        background-color: {ModernColors.BG_CARD};
        color: {ModernColors.TEXT_PRIMARY};
        border: 1px solid {ModernColors.BORDER};
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 10px;
    }}
    """


def apply_modern_style(app: QApplication, theme_name: str = None):
    """应用现代化样式，可选指定主题名"""
    if theme_name:
        set_theme(theme_name)

    # 设置样式表
    app.setStyleSheet(get_modern_stylesheet())

    # 设置调色板
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(ModernColors.BG_PRIMARY))
    palette.setColor(QPalette.WindowText, QColor(ModernColors.TEXT_PRIMARY))
    palette.setColor(QPalette.Base, QColor(ModernColors.BG_INPUT))
    palette.setColor(QPalette.AlternateBase, QColor(ModernColors.BG_TERTIARY))
    palette.setColor(QPalette.ToolTipBase, QColor(ModernColors.BG_CARD))
    palette.setColor(QPalette.ToolTipText, QColor(ModernColors.TEXT_PRIMARY))
    palette.setColor(QPalette.Text, QColor(ModernColors.TEXT_PRIMARY))
    palette.setColor(QPalette.Button, QColor(ModernColors.PRIMARY))
    palette.setColor(QPalette.ButtonText, QColor(Qt.white))
    palette.setColor(QPalette.BrightText, QColor(Qt.red))
    palette.setColor(QPalette.Link, QColor(ModernColors.PRIMARY))
    palette.setColor(QPalette.Highlight, QColor(ModernColors.PRIMARY))
    palette.setColor(QPalette.HighlightedText, QColor(Qt.white))
    app.setPalette(palette)


def create_shadow_effect(blur_radius=20, offset_y=4, color="#000000", opacity=50):
    """创建阴影效果"""
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(blur_radius)
    shadow.setOffset(0, offset_y)
    shadow.setColor(QColor(color))
    shadow.setColor(QColor(0, 0, 0, opacity))
    return shadow
