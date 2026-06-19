"""
AI Agent Deck - 应用程序入口
现代化桌面应用
"""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from .core.engine import Engine, EngineConfig, TransportMode
from .ui.modern_window import ModernMainWindow
from .ui.modern_theme import apply_modern_style


def main():
    """主函数"""
    # 高 DPI 支持
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # 创建应用程序
    app = QApplication(sys.argv)
    app.setApplicationName("AI Agent Deck")
    app.setApplicationVersion("2.0.0")
    app.setOrganizationName("AI Agent Deck")

    # 设置默认字体
    font = QFont("Segoe UI", 10)
    font.setHintingPreference(QFont.PreferFullHinting)
    app.setFont(font)

    # 应用现代化样式
    apply_modern_style(app)

    # 创建引擎
    config = EngineConfig(
        transport=TransportMode.SERIAL,  # 默认串口（最可靠）
        com_port=None,
        wifi_host=None,
        wifi_port=8080,
        poll_interval=0.5,
        heartbeat_interval=5.0,
        auto_reconnect=True
    )
    engine = Engine(config)

    # 创建主窗口
    window = ModernMainWindow(engine)
    window.show()

    # 运行应用程序
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
