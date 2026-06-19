"""
AI Agent Deck - 完整 GUI 应用程序
启动、配置、测试一体化界面
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import json
import sys
from pathlib import Path
from typing import Optional, Callable

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflow_manager import WorkflowManager
from profile_manager import ProfileManager, Profile, KeyMapping

# 导入 Profile 编辑器
from .profile_editor import ProfileEditorDialog, ProfileListDialog


class LogHandler:
    """日志处理器，将日志输出到 Text 控件"""

    def __init__(self, text_widget: tk.Text):
        self.text_widget = text_widget
        self.text_widget.tag_configure("INFO", foreground="black")
        self.text_widget.tag_configure("OK", foreground="green")
        self.text_widget.tag_configure("FAIL", foreground="red")
        self.text_widget.tag_configure("WARN", foreground="orange")

    def write(self, message: str):
        """写入日志"""
        self.text_widget.insert(tk.END, message + "\n")
        self.text_widget.see(tk.END)

    def clear(self):
        """清空日志"""
        self.text_widget.delete(1.0, tk.END)


class AI_Deck_App:
    """
    AI Agent Deck 完整应用程序

    功能:
    - 设备连接管理
    - Profile 可视化
    - 按键测试
    - 日志显示
    - 配置管理
    """

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AI Agent Deck - 工作流控制器")
        self.root.geometry("800x600")
        self.root.minsize(800, 600)

        # 工作流管理器
        self.workflow: Optional[WorkflowManager] = None
        self.running = False

        # 状态变量
        self.device_status = tk.StringVar(value="未连接")
        self.current_app = tk.StringVar(value="无")
        self.current_profile = tk.StringVar(value="无")
        self.connection_mode = tk.StringVar(value="串口")

        # 初始化 UI
        self._setup_ui()

        # 日志重定向
        self._setup_log_redirect()

    def _setup_ui(self):
        """初始化界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ── 顶部工具栏 ──
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(toolbar, text="启动", command=self._on_start, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="停止", command=self._on_stop, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="测试连接", command=self._on_test, width=10).pack(side=tk.LEFT, padx=5)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        ttk.Label(toolbar, text="模式:").pack(side=tk.LEFT)
        mode_combo = ttk.Combobox(toolbar, textvariable=self.connection_mode,
                                  values=["串口", "BLE"], state="readonly", width=8)
        mode_combo.pack(side=tk.LEFT, padx=5)
        mode_combo.set("串口")

        # ── 主内容区域 ──
        content = ttk.Frame(main_frame)
        content.pack(fill=tk.BOTH, expand=True)

        # 左侧面板
        left_panel = ttk.Frame(content, width=250)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)

        # 设备状态
        device_frame = ttk.LabelFrame(left_panel, text="设备状态", padding="10")
        device_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(device_frame, text="连接状态:").pack(anchor=tk.W)
        ttk.Label(device_frame, textvariable=self.device_status, font=("", 12, "bold")).pack(anchor=tk.W)

        ttk.Label(device_frame, text="当前应用:").pack(anchor=tk.W, pady=(10, 0))
        ttk.Label(device_frame, textvariable=self.current_app, font=("", 10)).pack(anchor=tk.W)

        ttk.Label(device_frame, text="当前 Profile:").pack(anchor=tk.W, pady=(10, 0))
        ttk.Label(device_frame, textvariable=self.current_profile, font=("", 10, "bold")).pack(anchor=tk.W)

        # Profile 列表
        profile_frame = ttk.LabelFrame(left_panel, text="Profile 列表", padding="10")
        profile_frame.pack(fill=tk.BOTH, expand=True)

        self.profile_listbox = tk.Listbox(profile_frame, height=6)
        self.profile_listbox.pack(fill=tk.BOTH, expand=True)
        self.profile_listbox.bind('<<ListboxSelect>>', self._on_profile_select)

        # 右侧面板
        right_panel = ttk.Frame(content)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 上部：按键映射
        keys_frame = ttk.LabelFrame(right_panel, text="按键映射", padding="10")
        keys_frame.pack(fill=tk.X, pady=(0, 10))

        self.key_cards = []
        for row in range(3):
            for col in range(2):
                idx = row * 2 + col
                frame = ttk.Frame(keys_frame, relief=tk.RIDGE, borderwidth=1)
                frame.grid(row=row, column=col, padx=5, pady=5, sticky=tk.NSEW)

                ttk.Label(frame, text=f"K{idx+1}", font=("", 10), foreground="gray").pack(anchor=tk.W, padx=5, pady=(5, 0))
                name_label = ttk.Label(frame, text="未配置", font=("", 11, "bold"))
                name_label.pack(anchor=tk.W, padx=5)
                action_label = ttk.Label(frame, text="", font=("", 9), foreground="gray")
                action_label.pack(anchor=tk.W, padx=5, pady=(0, 5))

                self.key_cards.append({'name': name_label, 'action': action_label})

        keys_frame.columnconfigure(0, weight=1)
        keys_frame.columnconfigure(1, weight=1)
        for i in range(3):
            keys_frame.rowconfigure(i, weight=1)

        # 下部：测试区域
        test_frame = ttk.LabelFrame(right_panel, text="测试工具", padding="10")
        test_frame.pack(fill=tk.X, pady=(0, 10))

        test_btn_frame = ttk.Frame(test_frame)
        test_btn_frame.pack(fill=tk.X)

        ttk.Button(test_btn_frame, text="发送测试 Profile", command=self._on_send_test).pack(side=tk.LEFT, padx=5)
        ttk.Button(test_btn_frame, text="清空日志", command=self._on_clear_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(test_btn_frame, text="打开 Profile 文件夹", command=self._on_open_profiles).pack(side=tk.LEFT, padx=5)
        ttk.Button(test_btn_frame, text="管理 Profile", command=self._on_manage_profiles).pack(side=tk.LEFT, padx=5)

        # 底部：日志区域
        log_frame = ttk.LabelFrame(main_frame, text="日志", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 状态栏
        status_bar = ttk.Frame(main_frame)
        status_bar.pack(fill=tk.X, pady=(5, 0))

        ttk.Label(status_bar, text="AI Agent Deck v2.0").pack(side=tk.LEFT)
        ttk.Label(status_bar, text="串口模式").pack(side=tk.RIGHT)

    def _setup_log_redirect(self):
        """设置日志重定向"""
        self.log_handler = LogHandler(self.log_text)

        # 重定向 stdout
        import io
        self._stdout = sys.stdout
        sys.stdout = io.StringIO()

        # 定时更新日志
        self._update_log()

    def _update_log(self):
        """定时更新日志"""
        try:
            output = sys.stdout.getvalue()
            if output:
                self.log_handler.write(output)
                sys.stdout = io.StringIO()
        except:
            pass
        self.root.after(100, self._update_log)

    def _on_start(self):
        """启动工作流"""
        if self.running:
            messagebox.showwarning("警告", "工作流已在运行中")
            return

        try:
            use_ble = self.connection_mode.get() == "BLE"
            self.workflow = WorkflowManager(use_ble=use_ble)

            # 注册回调
            self.workflow.detector.on_change(self._on_app_changed)

            # 启动
            self.workflow.start()
            self.running = True

            self.device_status.set("已连接" if self.workflow.device.is_connected else "连接中...")
            self.log_handler.write("[OK] 工作流已启动\n")

            # 更新 Profile 列表
            self._update_profile_list()

        except Exception as e:
            self.log_handler.write(f"[FAIL] 启动失败: {e}\n")
            messagebox.showerror("错误", f"启动失败: {e}")

    def _on_stop(self):
        """停止工作流"""
        if not self.running:
            return

        try:
            if self.workflow:
                self.workflow.stop()
            self.running = False
            self.device_status.set("未连接")
            self.current_app.set("无")
            self.current_profile.set("无")
            self.log_handler.write("[OK] 工作流已停止\n")
        except Exception as e:
            self.log_handler.write(f"[FAIL] 停止失败: {e}\n")

    def _on_test(self):
        """测试连接"""
        try:
            use_ble = self.connection_mode.get() == "BLE"
            if use_ble:
                self.log_handler.write("[TEST] 测试 BLE 连接...\n")
                # TODO: 实现 BLE 测试
                self.log_handler.write("[WARN] BLE 测试功能待实现\n")
            else:
                self.log_handler.write("[TEST] 测试串口连接...\n")
                from device_manager import DeviceManagerSerial
                dm = DeviceManagerSerial()
                if dm.port:
                    dm.start()
                    if dm.is_connected:
                        self.log_handler.write(f"[OK] 串口连接成功: {dm.port}\n")
                        dm.stop()
                    else:
                        self.log_handler.write("[FAIL] 串口连接失败\n")
                else:
                    self.log_handler.write("[FAIL] 未找到串口设备\n")
        except Exception as e:
            self.log_handler.write(f"[FAIL] 测试失败: {e}\n")

    def _on_send_test(self):
        """发送测试 Profile"""
        if not self.running or not self.workflow:
            messagebox.showwarning("警告", "请先启动工作流")
            return

        try:
            # 创建测试 Profile
            test_profile = Profile(
                name="Test",
                keys=[
                    KeyMapping("K1", "Test-A", "key_combo", "ctrl+a"),
                    KeyMapping("K2", "Test-B", "key_combo", "ctrl+b"),
                    KeyMapping("K3", "Test-C", "key_combo", "ctrl+c"),
                    KeyMapping("K4", "Test-D", "key_combo", "ctrl+d"),
                    KeyMapping("K5", "Test-E", "key_combo", "ctrl+e"),
                    KeyMapping("K6", "Test-F", "key_combo", "ctrl+f"),
                ]
            )

            self.workflow.device.send_profile(test_profile)
            self.log_handler.write("[OK] 测试 Profile 已发送\n")

            # 更新显示
            self._update_key_display(test_profile.keys)

        except Exception as e:
            self.log_handler.write(f"[FAIL] 发送失败: {e}\n")

    def _on_clear_log(self):
        """清空日志"""
        self.log_handler.clear()

    def _on_open_profiles(self):
        """打开 Profile 文件夹"""
        import os
        profiles_dir = Path(__file__).parent.parent / "profiles"
        if profiles_dir.exists():
            os.startfile(str(profiles_dir))
        else:
            messagebox.showinfo("提示", f"Profile 文件夹不存在: {profiles_dir}")

    def _on_manage_profiles(self):
        """打开 Profile 管理对话框"""
        if not self.workflow:
            messagebox.showwarning("提示", "请先启动工作流")
            return

        dialog = ProfileListDialog(self.root, self.workflow.profiles)
        dialog.show()
        self._update_profile_list()

    def _on_profile_select(self, event):
        """Profile 列表选择"""
        selection = self.profile_listbox.curselection()
        if selection:
            profile_name = self.profile_listbox.get(selection[0])
            self.log_handler.write(f"[INFO] 选择 Profile: {profile_name}\n")

            # 加载并显示 Profile
            if self.workflow:
                profile = self.workflow.profiles.get_profile_by_name(profile_name)
                if profile:
                    self._update_key_display(profile.keys)

    def _on_app_changed(self, new_app, old_app):
        """应用切换回调"""
        if self.workflow:
            profile = self.workflow.profiles.get_profile_by_process(new_app.process_name)
            if profile:
                self.current_app.set(new_app.process_name)
                self.current_profile.set(profile.name)
                self._update_key_display(profile.keys)

    def _update_profile_list(self):
        """更新 Profile 列表"""
        self.profile_listbox.delete(0, tk.END)
        if self.workflow:
            for name in self.workflow.profiles.list_profiles():
                self.profile_listbox.insert(tk.END, name)

    def _update_key_display(self, keys: list):
        """更新按键显示"""
        for i, key in enumerate(keys):
            if i < len(self.key_cards):
                self.key_cards[i]['name'].config(text=key.display)
                self.key_cards[i]['action'].config(text=key.action)

    def run(self):
        """运行应用程序"""
        self.root.mainloop()

    def stop(self):
        """停止应用程序"""
        if self.running:
            self._on_stop()
        self.root.destroy()


def main():
    """主函数"""
    app = AI_Deck_App()
    app.run()


if __name__ == "__main__":
    main()
