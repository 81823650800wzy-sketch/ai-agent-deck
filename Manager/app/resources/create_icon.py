"""
创建应用图标
"""

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPixmap, QPainter, QBrush, QPen, QColor, QFont, QLinearGradient
from PyQt5.QtCore import Qt
import sys


def create_icon(size=256, output_path="icon.png"):
    """创建应用图标"""
    app = QApplication(sys.argv)

    # 创建画布
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # 绘制渐变背景
    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0, QColor("#6C5CE7"))
    gradient.setColorAt(1, QColor("#A29BFE"))

    painter.setBrush(QBrush(gradient))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(0, 0, size, size, size // 4, size // 4)

    # 绘制内部阴影效果
    inner_rect = size // 8
    painter.setBrush(QColor(0, 0, 0, 30))
    painter.drawRoundedRect(
        inner_rect, inner_rect,
        size - inner_rect * 2, size - inner_rect * 2,
        size // 5, size // 5
    )

    # 绘制文字 "AD"
    painter.setPen(QColor(Qt.white))
    font = QFont("Segoe UI", size // 3, QFont.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "AD")

    # 绘制装饰线条
    painter.setPen(QPen(QColor(255, 255, 255, 50), 2))
    line_y = size * 0.65
    painter.drawLine(size * 0.2, line_y, size * 0.8, line_y)

    painter.end()

    # 保存图标
    pixmap.save(output_path)
    print(f"Icon saved to {output_path}")

    return pixmap


if __name__ == "__main__":
    create_icon(256, "icon.png")
    create_icon(64, "icon_64.png")
    create_icon(32, "icon_32.png")
    create_icon(16, "icon_16.png")
