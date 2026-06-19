"""
AI Agent Deck - Profile 编辑器对话框
允许用户编辑 Profile 的按键映射配置
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from profile_manager import ProfileManager, Profile, KeyMapping


class ProfileEditorDialog:
    """
    Profile 编辑器对话框

    功能:
    - 编辑 Profile 名称
    - 管理进程名列表
    - 编辑 6 个按键的映射配置
    - 实时预览
    """

    def __init__(self, parent, profile_manager: ProfileManager, profile_name: str = None):
        """
        初始化编辑器

        Args:
            parent: 父窗口
            profile_manager: Profile 管理器实例
            profile_name: 要编辑的 Profile 名称，None 表示新建
        """
        self.parent = parent
        self.profile_manager = profile_manager
        self.profile_name = profile_name
        self.result = None  # 编辑结果

        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("编辑 Profile" if profile_name else "新建 Profile")
        self.dialog.geometry("600x700")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 居中显示
        self.dialog.geometry("+%d+%d" % (
            parent.winfo_rootx() + (parent.winfo_width() - 600) // 2,
            parent.winfo_rooty() + (parent.winfo_height() - 700) // 2
        ))

        # 加载现有 Profile 或创建新的
        if profile_name and profile_name in profile_manager.profiles:
            self.profile = profile_manager.profiles[profile_name]
            self.is_new = False
        else:
            self.profile = Profile(
                name="",
                process_names=[],
                keys=[KeyMapping(f"K{i+1}", "", "key_combo", "") for i in range(6)]
            )
            self.is_new = True

        # 初始化 UI
        self._setup_ui()
        self._load_profile_data()

    def _setup_ui(self):
        """初始化界面"""
        # 主框架
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ── 基本信息区域 ──
        info_frame = ttk.LabelFrame(main_frame, text="基本信息", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 10))

        # Profile 名称
        name_frame = ttk.Frame(info_frame)
        name_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(name_frame, text="Profile 名称:", width=12).pack(side=tk.LEFT)
        self.name_entry = ttk.Entry(name_frame)
        self.name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        # 进程名列表
        process_frame = ttk.Frame(info_frame)
        process_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Label(process_frame, text="进程名:", width=12).pack(side=tk.LEFT, anchor=tk.N)

        # 进程名列表和按钮
        process_list_frame = ttk.Frame(process_frame)
        process_list_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        self.process_listbox = tk.Listbox(process_list_frame, height=3)
        self.process_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)

        process_btn_frame = ttk.Frame(process_list_frame)
        process_btn_frame.pack(side=tk.LEFT, padx=(5, 0))

        ttk.Button(process_btn_frame, text="添加", command=self._add_process, width=6).pack(pady=2)
        ttk.Button(process_btn_frame, text="删除", command=self._delete_process, width=6).pack(pady=2)

        # ── 按键映射区域 ──
        keys_frame = ttk.LabelFrame(main_frame, text="按键映射", padding="10")
        keys_frame.pack(fill=tk.BOTH, expand=True)

        # 6 个按键编辑卡片
        self.key_widgets = []
        for i in range(6):
            card = self._create_key_card(keys_frame, i)
            self.key_widgets.append(card)

        # ── 底部按钮 ──
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(btn_frame, text="保存", command=self._on_save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self._on_cancel).pack(side=tk.RIGHT)
        ttk.Button(btn_frame, text="预览", command=self._on_preview).pack(side=tk.LEFT)

    def _create_key_card(self, parent, index: int) -> dict:
        """创建单个按键编辑卡片"""
        card_frame = ttk.Frame(parent, relief=tk.RIDGE, borderwidth=1)
        card_frame.pack(fill=tk.X, pady=3)

        # 按键 ID 标签
        ttk.Label(card_frame, text=f"K{index+1}", font=("", 10, "bold"), width=4).pack(side=tk.LEFT, padx=5)

        # 输入区域
        input_frame = ttk.Frame(card_frame)
        input_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)

        # 第一行：显示名称
        row1 = ttk.Frame(input_frame)
        row1.pack(fill=tk.X, pady=2)

        ttk.Label(row1, text="名称:", width=6).pack(side=tk.LEFT)
        display_entry = ttk.Entry(row1, width=15)
        display_entry.pack(side=tk.LEFT, padx=(0, 10))

        # 动作类型
        ttk.Label(row1, text="类型:", width=6).pack(side=tk.LEFT)
        action_var = tk.StringVar(value="key_combo")
        action_combo = ttk.Combobox(
            row1,
            textvariable=action_var,
            values=["key_combo", "open_url", "command", "script"],
            state="readonly",
            width=10
        )
        action_combo.pack(side=tk.LEFT, padx=(0, 10))

        # 第二行：动作值
        row2 = ttk.Frame(input_frame)
        row2.pack(fill=tk.X, pady=2)

        ttk.Label(row2, text="值:", width=6).pack(side=tk.LEFT)
        value_entry = ttk.Entry(row2)
        value_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        return {
            'display': display_entry,
            'action': action_var,
            'value': value_entry
        }

    def _load_profile_data(self):
        """加载 Profile 数据到界面"""
        # 名称
        self.name_entry.insert(0, self.profile.name)

        # 进程名
        for pname in self.profile.process_names:
            self.process_listbox.insert(tk.END, pname)

        # 按键映射
        for i, key in enumerate(self.profile.keys):
            if i < len(self.key_widgets):
                widget = self.key_widgets[i]
                widget['display'].insert(0, key.display)
                widget['action'].set(key.action)
                widget['value'].insert(0, key.value)

    def _add_process(self):
        """添加进程名"""
        dialog = tk.Toplevel(self.dialog)
        dialog.title("添加进程名")
        dialog.geometry("300x100")
        dialog.transient(self.dialog)
        dialog.grab_set()

        ttk.Label(dialog, text="请输入进程名 (例如: notepad.exe):").pack(pady=10)

        entry = ttk.Entry(dialog, width=30)
        entry.pack(pady=5)
        entry.focus_set()

        def on_ok():
            pname = entry.get().strip()
            if pname:
                self.process_listbox.insert(tk.END, pname)
            dialog.destroy()

        ttk.Button(dialog, text="确定", command=on_ok).pack(pady=10)

        # 绑定回车键
        entry.bind('<Return>', lambda e: on_ok())

    def _delete_process(self):
        """删除选中的进程名"""
        selection = self.process_listbox.curselection()
        if selection:
            self.process_listbox.delete(selection[0])

    def _on_save(self):
        """保存 Profile"""
        # 验证名称
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("错误", "请输入 Profile 名称")
            return

        # 检查名称是否重复（新建时）
        if self.is_new and name in self.profile_manager.profiles:
            messagebox.showerror("错误", f"Profile '{name}' 已存在")
            return

        # 收集进程名
        process_names = []
        for i in range(self.process_listbox.size()):
            process_names.append(self.process_listbox.get(i))

        # 收集按键映射
        keys = []
        for i, widget in enumerate(self.key_widgets):
            display = widget['display'].get().strip()
            action = widget['action'].get()
            value = widget['value'].get().strip()

            if not display:
                display = f"K{i+1}"
            if not value:
                value = ""

            keys.append(KeyMapping(
                id=f"K{i+1}",
                display=display,
                action=action,
                value=value
            ))

        # 创建 Profile 对象
        profile = Profile(
            name=name,
            process_names=process_names,
            keys=keys
        )

        # 保存到管理器
        self.profile_manager.add_profile(profile)
        self.result = profile

        messagebox.showinfo("成功", f"Profile '{name}' 已保存")
        self.dialog.destroy()

    def _on_cancel(self):
        """取消编辑"""
        self.dialog.destroy()

    def _on_preview(self):
        """预览当前配置"""
        preview_text = "=== Profile 预览 ===\n\n"

        # 名称
        name = self.name_entry.get().strip()
        preview_text += f"名称: {name or '(未设置)'}\n"

        # 进程名
        process_names = []
        for i in range(self.process_listbox.size()):
            process_names.append(self.process_listbox.get(i))
        preview_text += f"进程名: {', '.join(process_names) or '(无)'}\n\n"

        # 按键映射
        preview_text += "按键映射:\n"
        for i, widget in enumerate(self.key_widgets):
            display = widget['display'].get().strip() or f"K{i+1}"
            action = widget['action'].get()
            value = widget['value'].get().strip() or "(空)"
            preview_text += f"  K{i+1}: {display} [{action}] → {value}\n"

        # 显示预览窗口
        preview_window = tk.Toplevel(self.dialog)
        preview_window.title("预览")
        preview_window.geometry("400x300")
        preview_window.transient(self.dialog)

        text_widget = tk.Text(preview_window, font=("Consolas", 10))
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert(1.0, preview_text)
        text_widget.config(state=tk.DISABLED)

    def show(self) -> Optional[Profile]:
        """显示对话框并返回结果"""
        self.dialog.wait_window()
        return self.result


class ProfileListDialog:
    """
    Profile 列表管理对话框

    功能:
    - 显示所有 Profile
    - 新建、编辑、删除 Profile
    - 导入/导出 Profile
    """

    def __init__(self, parent, profile_manager: ProfileManager):
        self.parent = parent
        self.profile_manager = profile_manager
        self.selected_profile = None

        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Profile 管理")
        self.dialog.geometry("500x400")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 居中显示
        self.dialog.geometry("+%d+%d" % (
            parent.winfo_rootx() + (parent.winfo_width() - 500) // 2,
            parent.winfo_rooty() + (parent.winfo_height() - 400) // 2
        ))

        # 初始化 UI
        self._setup_ui()
        self._refresh_list()

    def _setup_ui(self):
        """初始化界面"""
        # 主框架
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        ttk.Label(main_frame, text="Profile 列表", font=("", 14, "bold")).pack(anchor=tk.W, pady=(0, 10))

        # Profile 列表
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        # 列表和滚动条
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.profile_listbox = tk.Listbox(
            list_frame,
            font=("", 11),
            yscrollcommand=scrollbar.set
        )
        self.profile_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.profile_listbox.yview)

        # 绑定双击事件
        self.profile_listbox.bind('<Double-Button-1>', self._on_double_click)

        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(btn_frame, text="新建", command=self._on_new).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="编辑", command=self._on_edit).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="删除", command=self._on_delete).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="关闭", command=self._on_close).pack(side=tk.RIGHT, padx=5)

        # 状态栏
        self.status_label = ttk.Label(main_frame, text="", foreground="gray")
        self.status_label.pack(anchor=tk.W, pady=(5, 0))

    def _refresh_list(self):
        """刷新 Profile 列表"""
        self.profile_listbox.delete(0, tk.END)
        for name in self.profile_manager.list_profiles():
            self.profile_listbox.insert(tk.END, name)

        self.status_label.config(text=f"共 {len(self.profile_manager.profiles)} 个 Profile")

    def _on_new(self):
        """新建 Profile"""
        editor = ProfileEditorDialog(self.dialog, self.profile_manager)
        result = editor.show()
        if result:
            self._refresh_list()

    def _on_edit(self):
        """编辑选中的 Profile"""
        selection = self.profile_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个 Profile")
            return

        profile_name = self.profile_listbox.get(selection[0])
        editor = ProfileEditorDialog(self.dialog, self.profile_manager, profile_name)
        result = editor.show()
        if result:
            self._refresh_list()

    def _on_delete(self):
        """删除选中的 Profile"""
        selection = self.profile_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个 Profile")
            return

        profile_name = self.profile_listbox.get(selection[0])

        # 确认删除
        if messagebox.askyesno("确认", f"确定要删除 Profile '{profile_name}' 吗？"):
            self.profile_manager.delete_profile(profile_name)
            self._refresh_list()
            messagebox.showinfo("成功", f"Profile '{profile_name}' 已删除")

    def _on_double_click(self, event):
        """双击编辑"""
        self._on_edit()

    def _on_close(self):
        """关闭对话框"""
        self.dialog.destroy()

    def show(self) -> Optional[str]:
        """显示对话框并返回选中的 Profile 名称"""
        self.dialog.wait_window()
        return self.selected_profile


# 测试代码
if __name__ == "__main__":
    root = tk.Tk()
    root.title("测试")
    root.geometry("200x100")

    pm = ProfileManager()

    def test_editor():
        editor = ProfileEditorDialog(root, pm, "VSCode")
        result = editor.show()
        if result:
            print(f"编辑完成: {result.name}")

    def test_list():
        dialog = ProfileListDialog(root, pm)
        dialog.show()

    ttk.Button(root, text="编辑器", command=test_editor).pack(pady=10)
    ttk.Button(root, text="列表", command=test_list).pack(pady=10)

    root.mainloop()
