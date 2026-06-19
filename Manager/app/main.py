"""
AI Agent Deck - 应用程序入口
现代化桌面应用
"""

import sys
import logging
from pathlib import Path

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont, QPixmap, QPainter, QColor, QLinearGradient
from PyQt5.QtCore import Qt

from .utils.version import __version__, APP_NAME, APP_AUTHOR
from .utils.logger import setup_logging, get_logger, set_qt_signal
from .utils.crash_handler import setup_crash_handler
from .core.engine import Engine, EngineConfig, TransportMode
from .ui.modern_theme import apply_modern_style

logger = logging.getLogger(__name__)


def _create_splash_pixmap() -> QPixmap:
    """创建启动画面"""
    from PyQt5.QtGui import QFont as QF
    w, h = 400, 300
    pixmap = QPixmap(w, h)
    pixmap.fill(QColor("#1a1a2e"))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # 渐变背景
    gradient = QLinearGradient(0, 0, w, h)
    gradient.setColorAt(0, QColor("#1a1a2e"))
    gradient.setColorAt(1, QColor("#16213e"))
    painter.fillRect(0, 0, w, h, gradient)

    # 图标
    painter.setBrush(QColor("#0f3460"))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(160, 40, 80, 80)

    painter.setPen(QColor("#e94560"))
    icon_font = QF("Segoe UI", 24, QF.Bold)
    painter.setFont(icon_font)
    painter.drawText(160, 40, 80, 80, Qt.AlignCenter, "AD")

    # 标题
    painter.setPen(QColor("#ffffff"))
    title_font = QF("Segoe UI", 18, QF.Bold)
    painter.setFont(title_font)
    painter.drawText(0, 140, w, 40, Qt.AlignHCenter, APP_NAME)

    # 版本
    painter.setPen(QColor("#a0a0a0"))
    ver_font = QF("Segoe UI", 10)
    painter.setFont(ver_font)
    painter.drawText(0, 175, w, 25, Qt.AlignHCenter, f"v{__version__}")

    # 加载提示
    painter.setPen(QColor("#606060"))
    load_font = QF("Segoe UI", 9)
    painter.setFont(load_font)
    painter.drawText(0, h - 40, w, 25, Qt.AlignHCenter, "正在初始化...")

    painter.end()
    return pixmap


def main():
    """主函数"""

    # 1. 初始化日志系统
    setup_logging(level=logging.DEBUG, log_to_file=True)
    logger.info("%s v%s 启动中...", APP_NAME, __version__)

    # 2. 安装崩溃处理器
    setup_crash_handler()

    # 3. 高 DPI 支持
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # 4. 创建应用程序
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setOrganizationName(APP_AUTHOR)
    app.setQuitOnLastWindowClosed(False)  # 支持最小化到托盘

    # 5. 设置默认字体
    font = QFont("Microsoft YaHei UI", 10)
    font.setHintingPreference(QFont.PreferFullHinting)
    app.setFont(font)

    # 6. 应用现代化样式
    apply_modern_style(app)

    # 7. 显示启动画面
    splash = None
    try:
        from PyQt5.QtWidgets import QSplashScreen
        splash_pix = _create_splash_pixmap()
        splash = QSplashScreen(splash_pix)
        splash.show()
        app.processEvents()
        logger.info("启动画面已显示")
    except Exception as e:
        logger.warning("启动画面创建失败: %s", e)

    # 8. 创建引擎
    try:
        config = EngineConfig(
            transport=TransportMode.SERIAL,
            com_port=None,
            wifi_host=None,
            wifi_port=8080,
            poll_interval=0.5,
            heartbeat_interval=5.0,
            auto_reconnect=True
        )
        engine = Engine(config)
        logger.info("引擎初始化完成")
    except Exception as e:
        logger.error("引擎初始化失败: %s", e)
        if splash:
            splash.close()
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.critical(None, "启动错误", f"引擎初始化失败:\n{e}")
        sys.exit(1)

    # 9. 创建主窗口
    try:
        from .ui.modern_window import ModernMainWindow
        window = ModernMainWindow(engine)

        # 连接日志信号
        if hasattr(window, 'log_signal'):
            set_qt_signal(window.log_signal)

        window.show()
        logger.info("主窗口已显示")

        if splash:
            splash.finish(window)

    except Exception as e:
        logger.error("主窗口创建失败: %s", e)
        if splash:
            splash.close()
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.critical(None, "启动错误", f"主窗口创建失败:\n{e}")
        sys.exit(1)

    # 10. 运行应用程序
    logger.info("应用程序就绪")
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
