"""
AI Agent Deck - PC 端管理软件
功能：
  - 监听 AI Agent Deck 的 HID 按键事件
  - 根据配置执行相应操作（打开应用、运行脚本等）
  - 支持用户自定义按键映射

使用方法：
  1. 先连接 AI Agent Deck 蓝牙设备
  2. 运行此程序
  3. 按下设备按键即可触发对应操作
"""

import json
import os
import sys
import subprocess
import threading
from pathlib import Path

try:
    from pynput import keyboard
except ImportError:
    print("请先安装 pynput: pip install pynput")
    sys.exit(1)

# 配置文件路径
CONFIG_FILE = Path(__file__).parent / "config.json"
SCRIPTS_DIR = Path(__file__).parent / "scripts"


class AIDeckManager:
    def __init__(self):
        self.config = self.load_config()
        self.listener = None
        self.running = False

        # 创建脚本目录
        SCRIPTS_DIR.mkdir(exist_ok=True)

        # 初始化脚本文件
        self.init_scripts()

    def load_config(self):
        """加载配置文件"""
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"keys": {}, "scripts": {}}

    def save_config(self):
        """保存配置文件"""
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

    def init_scripts(self):
        """初始化脚本文件"""
        for script_name, script_info in self.config.get("scripts", {}).items():
            script_path = SCRIPTS_DIR / script_name
            if not script_path.exists():
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write(script_info.get("content", ""))
                print(f"  创建脚本: {script_path}")

    def execute_action(self, key_config):
        """执行按键对应的操作"""
        action = key_config.get("action")
        name = key_config.get("name", "Unknown")

        print(f"\n[触发] {name}")

        if action == "command":
            # 执行命令
            command = key_config.get("command")
            if command:
                print(f"  执行命令: {command}")
                try:
                    subprocess.Popen(command, shell=True)
                except Exception as e:
                    print(f"  错误: {e}")

        elif action == "script":
            # 执行脚本
            script_name = key_config.get("script")
            if script_name:
                script_path = SCRIPTS_DIR / script_name
                if script_path.exists():
                    print(f"  执行脚本: {script_path}")
                    try:
                        subprocess.Popen(str(script_path), shell=True)
                    except Exception as e:
                        print(f"  错误: {e}")
                else:
                    print(f"  脚本不存在: {script_path}")

        elif action == "open_url":
            # 打开 URL
            url = key_config.get("url")
            if url:
                print(f"  打开网址: {url}")
                os.startfile(url)

        elif action == "open_app":
            # 打开应用
            app_path = key_config.get("path")
            if app_path:
                print(f"  打开应用: {app_path}")
                try:
                    subprocess.Popen(app_path)
                except Exception as e:
                    print(f"  错误: {e}")

    def on_key_press(self, key):
        """键盘按键回调"""
        try:
            # 获取按键名称
            if hasattr(key, 'name'):
                key_name = key.name
            elif hasattr(key, 'char'):
                key_name = key.char
            else:
                return

            # 检查是否是 F13-F18
            f_keys = {
                'f13': 'F13', 'f14': 'F14', 'f15': 'F15',
                'f16': 'F16', 'f17': 'F17', 'f18': 'F18'
            }

            if key_name and key_name.lower() in f_keys:
                mapped_key = f_keys[key_name.lower()]
                key_config = self.config.get("keys", {}).get(mapped_key)

                if key_config:
                    # 在新线程中执行操作，避免阻塞监听
                    threading.Thread(
                        target=self.execute_action,
                        args=(key_config,),
                        daemon=True
                    ).start()

        except Exception as e:
            print(f"错误: {e}")

    def start(self):
        """启动监听"""
        print("=" * 50)
        print("  AI Agent Deck 管理软件")
        print("=" * 50)
        print(f"\n配置文件: {CONFIG_FILE}")
        print(f"脚本目录: {SCRIPTS_DIR}")
        print("\n已配置的按键:")

        for key, config in self.config.get("keys", {}).items():
            name = config.get("name", "未命名")
            desc = config.get("description", "")
            print(f"  {key}: {name} - {desc}")

        print("\n等待按键输入... (按 Ctrl+C 退出)")
        print("-" * 50)

        # 启动键盘监听
        self.running = True
        self.listener = keyboard.Listener(on_press=self.on_key_press)
        self.listener.start()

        try:
            while self.running:
                self.listener.join(timeout=0.1)
        except KeyboardInterrupt:
            print("\n\n正在退出...")
            self.stop()

    def stop(self):
        """停止监听"""
        self.running = False
        if self.listener:
            self.listener.stop()


def create_gui():
    """创建图形界面（可选）"""
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox

        class AIDeckGUI:
            def __init__(self):
                self.root = tk.Tk()
                self.root.title("AI Agent Deck 管理软件")
                self.root.geometry("600x500")

                self.manager = AIDeckManager()
                self.create_widgets()

            def create_widgets(self):
                # 标题
                title = ttk.Label(self.root, text="AI Agent Deck 管理软件", font=("Arial", 16))
                title.pack(pady=10)

                # 状态
                self.status_var = tk.StringVar(value="等待连接...")
                status = ttk.Label(self.root, textvariable=self.status_var)
                status.pack(pady=5)

                # 按键列表
                frame = ttk.LabelFrame(self.root, text="按键映射", padding=10)
                frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

                # 创建按键配置表格
                columns = ("按键", "名称", "操作", "说明")
                self.tree = ttk.Treeview(frame, columns=columns, show="headings")

                for col in columns:
                    self.tree.heading(col, text=col)
                    self.tree.column(col, width=100)

                # 加载配置
                for key, config in self.manager.config.get("keys", {}).items():
                    self.tree.insert("", tk.END, values=(
                        key,
                        config.get("name", ""),
                        config.get("action", ""),
                        config.get("description", "")
                    ))

                self.tree.pack(fill=tk.BOTH, expand=True)

                # 按钮
                btn_frame = ttk.Frame(self.root)
                btn_frame.pack(pady=10)

                ttk.Button(btn_frame, text="启动监听", command=self.start_listen).pack(side=tk.LEFT, padx=5)
                ttk.Button(btn_frame, text="停止监听", command=self.stop_listen).pack(side=tk.LEFT, padx=5)
                ttk.Button(btn_frame, text="编辑配置", command=self.edit_config).pack(side=tk.LEFT, padx=5)

            def start_listen(self):
                self.status_var.set("监听中... 按下 F13-F18 测试")
                threading.Thread(target=self.manager.start, daemon=True).start()

            def stop_listen(self):
                self.manager.stop()
                self.status_var.set("已停止")

            def edit_config(self):
                os.startfile(str(CONFIG_FILE))

            def run(self):
                self.root.mainloop()

        return AIDeckGUI()

    except ImportError:
        return None


def main():
    """主函数"""
    # 检查是否有 GUI 参数
    if "--gui" in sys.argv:
        gui = create_gui()
        if gui:
            gui.run()
            return

    # 默认使用命令行模式
    manager = AIDeckManager()
    manager.start()


if __name__ == "__main__":
    main()
