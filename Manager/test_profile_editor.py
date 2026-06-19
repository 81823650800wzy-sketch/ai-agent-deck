"""
测试 Profile 编辑器
运行此脚本可以单独测试 Profile 编辑器功能
"""

import tkinter as tk
from tkinter import ttk
import sys
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from profile_manager import ProfileManager
from gui.profile_editor import ProfileEditorDialog, ProfileListDialog


def main():
    """主函数"""
    root = tk.Tk()
    root.title("Profile 编辑器测试")
    root.geometry("300x200")

    # 创建 Profile 管理器
    pm = ProfileManager()

    def open_editor():
        """打开编辑器"""
        editor = ProfileEditorDialog(root, pm, "VSCode")
        result = editor.show()
        if result:
            print(f"编辑完成: {result.name}")

    def open_list():
        """打开列表"""
        dialog = ProfileListDialog(root, pm)
        dialog.show()

    def create_new():
        """新建 Profile"""
        editor = ProfileEditorDialog(root, pm)
        result = editor.show()
        if result:
            print(f"新建 Profile: {result.name}")

    # 按钮
    ttk.Button(root, text="编辑 VSCode", command=open_editor).pack(pady=10)
    ttk.Button(root, text="新建 Profile", command=create_new).pack(pady=10)
    ttk.Button(root, text="Profile 列表", command=open_list).pack(pady=10)

    root.mainloop()


if __name__ == "__main__":
    main()
