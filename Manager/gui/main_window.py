"""
AI Agent Deck - 主窗口
设备状态、Profile 显示、按键映射可视化
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from typing import Optional, Callable


class MainWindow:
    """
    主窗口类

    功能:
    - 设备连接状态显示
    - 当前 Profile 可视化
    - 按键映射编辑 (预留)
    - 使用统计 (预留)
    """

    def __init__(self, workflow_manager=None):
        self.workflow = workflow_manager
        self.root = tk.Tk()
        self.root.title("AI Agent Deck")
        self.root.geometry("400x500")
        self.root.resizable(False, False)

        # 状态变量
        self.device_status = tk.StringVar(value="未连接")
        self.profile_name = tk.StringVar(value="无")
        self.app_name = tk.StringVar(value="无")

        # 初始化 UI
        self._setup_ui()

        # 更新定时器
        self._update_timer = None

    def _setup_ui(self):
        """初始化界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ── 设备状态区域 ──
        device_frame = ttk.LabelFrame(main_frame, text="设备状态", padding="10")
        device_frame.pack(fill=tk.X, pady=(0, 10))

        # 连接状态
        status_frame = ttk.Frame(device_frame)
        status_frame.pack(fill=tk.X)

        ttk.Label(status_frame, text="连接状态:").pack(side=tk.LEFT)
        self.status_label = ttk.Label(
            status_frame,
            textvariable=self.device_status,
            foreground="gray"
        )
        self.status_label.pack(side=tk.LEFT, padx=(5, 0))

        # 连接/断开按钮
        self.connect_btn = ttk.Button(
            status_frame,
            text="连接",
            command=self._on_connect_click,
            width=8
        )
        self.connect_btn.pack(side=tk.RIGHT)

        # ── 当前应用区域 ──
        app_frame = ttk.LabelFrame(main_frame, text="当前应用", padding="10")
        app_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(app_frame, text="应用程序:").pack(anchor=tk.W)
        ttk.Label(
            app_frame,
            textvariable=self.app_name,
            font=("", 12, "bold")
        ).pack(anchor=tk.W)

        ttk.Label(app_frame, text="当前 Profile:").pack(anchor=tk.W, pady=(10, 0))
        ttk.Label(
            app_frame,
            textvariable=self.profile_name,
            font=("", 12, "bold")
        ).pack(anchor=tk.W)

        # ── 按键映射区域 ──
        keys_frame = ttk.LabelFrame(main_frame, text="按键映射", padding="10")
        keys_frame.pack(fill=tk.BOTH, expand=True)

        # 按键网格 (2列 x 3行)
        self.key_labels = []
        for row in range(3):
            for col in range(2):
                idx = row * 2 + col
                frame = ttk.Frame(keys_frame, relief=tk.RIDGE, borderwidth=1)
                frame.grid(row=row, column=col, padx=5, pady=5, sticky=tk.NSEW)

                # 按键 ID
                ttk.Label(
                    frame,
                    text=f"K{idx+1}",
                    font=("", 10),
                    foreground="gray"
                ).pack(anchor=tk.W, padx=5, pady=(5, 0))

                # 按键名称
                name_label = ttk.Label(
                    frame,
                    text="未配置",
                    font=("", 11, "bold")
                )
                name_label.pack(anchor=tk.W, padx=5)

                # 动作描述
                action_label = ttk.Label(
                    frame,
                    text="",
                    font=("", 9),
                    foreground="gray"
                )
                action_label.pack(anchor=tk.W, padx=5, pady=(0, 5))

                self.key_labels.append({
                    'name': name_label,
                    'action': action_label
                })

        # 配置网格权重
        keys_frame.columnconfigure(0, weight=1)
        keys_frame.columnconfigure(1, weight=1)
        for i in range(3):
            keys_frame.rowconfigure(i, weight=1)

        # ── 底部状态栏 ──
        status_bar = ttk.Frame(main_frame)
        status_bar.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(
            status_bar,
            text="AI Agent Deck v2.0",
            foreground="gray"
        ).pack(side=tk.LEFT)

        # 扫描按钮
        ttk.Button(
            status_bar,
            text="扫描设备",
            command=self._on_scan_click,
            width=10
        ).pack(side=tk.RIGHT)

    def _on_connect_click(self):
        """连接/断开按钮点击"""
        if not self.workflow:
            return

        if self.workflow.device.is_connected:
            # 断开连接
            self.workflow.device.stop()
            self.connect_btn.config(text="连接")
        else:
            # 连接设备
            self.workflow.device.start()
            self.connect_btn.config(text="断开")

    def _on_scan_click(self):
        """扫描设备"""
        # TODO: 实现设备扫描对话框
        messagebox.showinfo("扫描", "正在扫描 BLE 设备...\n请查看控制台输出")

    def update_device_status(self, connected: bool):
        """更新设备连接状态"""
        if connected:
            self.device_status.set("已连接")
            self.status_label.config(foreground="green")
            self.connect_btn.config(text="断开")
        else:
            self.device_status.set("未连接")
            self.status_label.config(foreground="gray")
            self.connect_btn.config(text="连接")

    def update_app_info(self, app_name: str, profile_name: str):
        """更新当前应用信息"""
        self.app_name.set(app_name)
        self.profile_name.set(profile_name)

    def update_key_mapping(self, keys: list):
        """
        更新按键映射显示

        Args:
            keys: KeyMapping 对象列表，每个包含 id, display, action
        """
        for i, key in enumerate(keys):
            if i < len(self.key_labels):
                self.key_labels[i]['name'].config(text=key.display)
                self.key_labels[i]['action'].config(text=key.action)

    def start_update_loop(self):
        """启动状态更新循环"""
        def update():
            if self.workflow:
                # 更新设备状态
                self.update_device_status(self.workflow.device.is_connected)

                # 更新当前应用
                if self.workflow.current_app:
                    self.update_app_info(
                        self.workflow.current_app.process_name,
                        self.workflow.current_profile.name if self.workflow.current_profile else "无"
                    )

                # 更新按键映射
                if self.workflow.current_profile:
                    self.update_key_mapping(self.workflow.current_profile.keys)

            # 每 500ms 更新一次
            self._update_timer = self.root.after(500, update)

        update()

    def run(self):
        """运行主窗口"""
        self.start_update_loop()
        self.root.mainloop()

    def stop(self):
        """停止主窗口"""
        if self._update_timer:
            self.root.after_cancel(self._update_timer)
        self.root.destroy()


class KeyEditDialog:
    """
    按键编辑对话框 (预留)
    """

    def __init__(self, parent, key_mapping=None):
        self.result = None

        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("编辑按键")
        self.dialog.geometry("300x200")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 居中显示
        self.dialog.geometry("+%d+%d" % (
            parent.winfo_rootx() + 50,
            parent.winfo_rooty() + 50
        ))

        # 初始化 UI
        self._setup_ui(key_mapping)

    def _setup_ui(self, key_mapping):
        """初始化对话框界面"""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 按键 ID
        ttk.Label(main_frame, text="按键 ID:").pack(anchor=tk.W)
        self.id_entry = ttk.Entry(main_frame)
        self.id_entry.pack(fill=tk.X, pady=(0, 10))

        # 显示名称
        ttk.Label(main_frame, text="显示名称:").pack(anchor=tk.W)
        self.name_entry = ttk.Entry(main_frame)
        self.name_entry.pack(fill=tk.X, pady=(0, 10))

        # 动作类型
        ttk.Label(main_frame, text="动作类型:").pack(anchor=tk.W)
        self.action_var = tk.StringVar(value="key_combo")
        action_combo = ttk.Combobox(
            main_frame,
            textvariable=self.action_var,
            values=["key_combo", "open_url", "command", "script"],
            state="readonly"
        )
        action_combo.pack(fill=tk.X, pady=(0, 10))

        # 动作值
        ttk.Label(main_frame, text="动作值:").pack(anchor=tk.W)
        self.value_entry = ttk.Entry(main_frame)
        self.value_entry.pack(fill=tk.X, pady=(0, 10))

        # 填充现有数据
        if key_mapping:
            self.id_entry.insert(0, key_mapping.id)
            self.name_entry.insert(0, key_mapping.display)
            self.action_var.set(key_mapping.action)
            self.value_entry.insert(0, key_mapping.value if hasattr(key_mapping, 'value') else "")

        # 按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(btn_frame, text="确定", command=self._on_ok).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(btn_frame, text="取消", command=self._on_cancel).pack(side=tk.RIGHT)

    def _on_ok(self):
        """确定按钮"""
        self.result = {
            'id': self.id_entry.get(),
            'display': self.name_entry.get(),
            'action': self.action_var.get(),
            'value': self.value_entry.get()
        }
        self.dialog.destroy()

    def _on_cancel(self):
        """取消按钮"""
        self.dialog.destroy()

    def show(self) -> Optional[dict]:
        """显示对话框并返回结果"""
        self.dialog.wait_window()
        return self.result
