"""
测试固件烧录管理器对话框
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from PyQt5.QtWidgets import QApplication
from app.core.flash_manager import FlashManager
from app.ui.flash_dialog import FlashDialog


def main():
    """测试烧录对话框"""
    app = QApplication(sys.argv)

    # 设置样式
    from app.ui.modern_theme import apply_modern_style
    apply_modern_style(app)

    # 创建 FlashManager
    flash_manager = FlashManager()

    # 显示固件信息
    firmware_path = flash_manager.get_firmware_path()
    if firmware_path:
        print(f"固件路径: {firmware_path}")
        print(f"固件大小: {firmware_path.stat().st_size / 1024:.1f} KB")
    else:
        print("未找到固件文件")

    version = flash_manager.get_firmware_version()
    if version:
        print(f"固件版本: {version}")

    # 创建并显示对话框
    dialog = FlashDialog(flash_manager)
    dialog.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
