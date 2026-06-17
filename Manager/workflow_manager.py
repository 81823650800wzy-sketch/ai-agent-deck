"""
AI Agent Deck - 工作流管理器
协调 窗口检测 → Profile 匹配 → 设备同步 的完整链路
"""

import json
import os
import subprocess
import threading
import time
from pathlib import Path

from window_detector import WindowDetector, ApplicationInfo
from profile_manager import ProfileManager, Profile, KeyMapping
from device_manager import DeviceManager

try:
    from pynput import keyboard as pynput_keyboard
except ImportError:
    pynput_keyboard = None
    print("[WorkflowManager] pynput 未安装，按键监听不可用")


class WorkflowManager:
    """
    核心工作流管理器

    流程:
    1. 检测当前窗口 (WindowDetector)
    2. 匹配 Profile (ProfileManager)
    3. 发送到 ESP32 (DeviceManager)
    4. 监听按键执行动作
    """

    def __init__(self, com_port: str = None):
        self.detector = WindowDetector(poll_interval=0.5)
        self.profiles = ProfileManager()
        self.device = DeviceManager()

        self.current_profile: Profile | None = None
        self.current_app: ApplicationInfo | None = None

        self._key_listener = None
        self._key_map: dict[str, KeyMapping] = {}

        # 注册回调
        self.detector.on_change(self._on_app_changed)

        print("[WorkflowManager] 初始化完成")
        print(f"[WorkflowManager] 已加载 {len(self.profiles.profiles)} 个 Profile:")
        for name in self.profiles.list_profiles():
            print(f"  - {name}")

    def _on_app_changed(self, new_app: ApplicationInfo, old_app: ApplicationInfo | None):
        """应用切换回调"""
        print(f"\n[Workflow] 应用切换: {old_app.process_name if old_app else 'N/A'} → {new_app.process_name}")

        # 匹配 Profile
        profile = self.profiles.get_profile_by_process(new_app.process_name)

        if profile and profile != self.current_profile:
            self._switch_profile(profile, new_app)
        elif not profile:
            print(f"[Workflow] 无匹配 Profile: {new_app.process_name}")

    def _switch_profile(self, profile: Profile, app: ApplicationInfo):
        """切换到新 Profile"""
        print(f"[Workflow] ✅ 切换 Profile: {profile.name}")
        print(f"[Workflow] 按键映射:")
        for k in profile.keys:
            print(f"  {k.id}: {k.display} ({k.action})")

        self.current_profile = profile
        self.current_app = app

        # 更新按键映射
        self._key_map = {k.id: k for k in profile.keys}

        # 发送到 ESP32
        self.device.send_profile(profile)

    def _start_key_listener(self):
        """启动全局按键监听"""
        if not pynput_keyboard:
            print("[WorkflowManager] pynput 不可用，跳过按键监听")
            return

        def on_press(key):
            try:
                # 检测 F13-F18 (设备发送的功能键)
                if hasattr(key, 'vk'):
                    F_KEYS = {
                        124: "K1",  # F13
                        125: "K2",  # F14
                        126: "K3",  # F15
                        127: "K4",  # F16
                        128: "K5",  # F17
                        129: "K6",  # F18
                    }
                    key_id = F_KEYS.get(key.vk)
                    if key_id and key_id in self._key_map:
                        self._execute_action(self._key_map[key_id])
                        return

                # 也支持数字键 1-6 作为备用
                if hasattr(key, 'char') and key.char in '123456':
                    idx = int(key.char) - 1
                    if self.current_profile and idx < len(self.current_profile.keys):
                        self._execute_action(self.current_profile.keys[idx])
            except Exception as e:
                print(f"[Workflow] 按键处理错误: {e}")

        self._key_listener = pynput_keyboard.Listener(on_press=on_press)
        self._key_listener.start()
        print("[WorkflowManager] 按键监听已启动 (F13-F18 / 1-6)")

    def _execute_action(self, key: KeyMapping):
        """执行按键动作"""
        print(f"[Workflow] 执行: {key.id} → {key.display} ({key.action}: {key.value})")

        try:
            if key.action == "key_combo":
                # 使用 pynput 发送组合键
                self._send_key_combo(key.value)
            elif key.action == "open_url":
                os.startfile(key.value)
            elif key.action == "command":
                subprocess.Popen(key.value, shell=True)
            elif key.action == "script":
                script_path = Path(__file__).parent / "scripts" / key.value
                if script_path.exists():
                    subprocess.Popen(str(script_path), shell=True)
        except Exception as e:
            print(f"[Workflow] 执行失败: {e}")

    def _send_key_combo(self, combo: str):
        """发送组合键 (如 'ctrl+z', 'ctrl+shift+b')"""
        if not pynput_keyboard:
            return

        controller = pynput_keyboard.Controller()
        parts = combo.lower().split("+")

        KEY_MAP = {
            "ctrl": pynput_keyboard.Key.ctrl_l,
            "shift": pynput_keyboard.Key.shift_l,
            "alt": pynput_keyboard.Key.alt_l,
            "win": pynput_keyboard.Key.cmd_l,
            "enter": pynput_keyboard.Key.enter,
            "tab": pynput_keyboard.Key.tab,
            "esc": pynput_keyboard.Key.esc,
            "space": pynput_keyboard.Key.space,
            "backspace": pynput_keyboard.Key.backspace,
            "delete": pynput_keyboard.Key.delete,
            "f1": pynput_keyboard.Key.f1,
            "f5": pynput_keyboard.Key.f5,
            "f8": pynput_keyboard.Key.f8,
            "f9": pynput_keyboard.Key.f9,
            "f12": pynput_keyboard.Key.f12,
            "`": pynput_keyboard.KeyCode.from_char('`'),
        }

        # 收集修饰键和普通键
        modifiers = []
        normal_keys = []
        for part in parts:
            part = part.strip()
            if part in ("ctrl", "shift", "alt", "win"):
                modifiers.append(KEY_MAP[part])
            elif part in KEY_MAP:
                normal_keys.append(KEY_MAP[part])
            elif len(part) == 1:
                normal_keys.append(pynput_keyboard.KeyCode.from_char(part))

        # 按下所有键
        for mod in modifiers:
            controller.press(mod)
        for key in normal_keys:
            controller.press(key)
        for key in reversed(normal_keys):
            controller.release(key)
        for mod in reversed(modifiers):
            controller.release(mod)

    def start(self):
        """启动工作流管理器"""
        print("\n" + "=" * 50)
        print("  AI Agent Deck - Context-Aware Workflow")
        print("=" * 50)

        # 启动设备连接
        self.device.start()

        # 启动按键监听
        self._start_key_listener()

        # 启动窗口检测
        self.detector.start()

        print("\n[WorkflowManager] ✅ 已启动，等待应用切换...")
        print("[WorkflowManager] 打开 VSCode / Blender / KiCad 试试！\n")

    def stop(self):
        """停止工作流管理器"""
        print("\n[WorkflowManager] 正在停止...")
        self.detector.stop()
        self.device.stop()
        if self._key_listener:
            self._key_listener.stop()
        print("[WorkflowManager] 已停止")

    def run_forever(self):
        """阻塞运行"""
        self.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
