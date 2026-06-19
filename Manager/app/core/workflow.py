"""
AI Agent Deck - 工作流管理器
协调窗口检测、Profile 匹配、设备同步
"""

import time
import threading
from typing import Optional, Callable
from dataclasses import dataclass

from ..utils.logger import get_logger
from .device import DeviceManager, DeviceManagerBLE, DeviceManagerSerial
from .profile import ProfileManager, Profile

logger = get_logger("workflow")


@dataclass
class AppInfo:
    """应用信息"""
    process_name: str
    window_title: str
    process_path: str
    timestamp: float


class WindowDetector:
    """
    窗口检测器

    功能:
    - 检测前台窗口变化
    - 提取进程名、窗口标题
    - 触发回调
    """

    def __init__(self, poll_interval: float = 0.5):
        self.poll_interval = poll_interval
        self._callback: Optional[Callable] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._current_app: Optional[AppInfo] = None

    def on_change(self, callback: Callable):
        """注册变化回调"""
        self._callback = callback

    def start(self):
        """启动检测"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._detect_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """停止检测"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _detect_loop(self):
        """检测循环"""
        try:
            import win32gui
            import win32process
            import psutil
        except ImportError:
            logger.error("缺少依赖: pywin32, psutil")
            return

        while self._running:
            try:
                # 获取前台窗口
                hwnd = win32gui.GetForegroundWindow()
                if hwnd:
                    # 获取进程信息
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    process = psutil.Process(pid)
                    process_name = process.name()
                    window_title = win32gui.GetWindowText(hwnd)
                    process_path = process.exe()

                    # 检查是否变化
                    new_app = AppInfo(
                        process_name=process_name,
                        window_title=window_title,
                        process_path=process_path,
                        timestamp=time.time()
                    )

                    if (not self._current_app or
                            self._current_app.process_name != new_app.process_name):

                        old_app = self._current_app
                        self._current_app = new_app

                        if self._callback:
                            self._callback(new_app, old_app)

            except Exception as e:
                pass

            time.sleep(self.poll_interval)

    @property
    def current_app(self) -> Optional[AppInfo]:
        return self._current_app


class WorkflowManager:
    """
    工作流管理器

    流程:
    1. 检测当前窗口 (WindowDetector)
    2. 匹配 Profile (ProfileManager)
    3. 发送到 ESP32 (DeviceManager)
    4. 监听按键执行动作
    """

    def __init__(self, device: DeviceManager = None, use_ble: bool = False, com_port: str = None):
        self.detector = WindowDetector()
        self.profiles = ProfileManager()

        # 使用外部设备管理器或创建新的
        if device:
            self.device = device
        elif use_ble:
            self.device = DeviceManagerBLE()
        else:
            self.device = DeviceManagerSerial(port=com_port)

        self.current_profile: Optional[Profile] = None
        self.current_app: Optional[AppInfo] = None

        # 注册回调
        self.detector.on_change(self._on_app_changed)

    def _on_app_changed(self, new_app: AppInfo, old_app: Optional[AppInfo]):
        """应用切换回调"""
        # 匹配 Profile
        profile = self.profiles.get_profile_by_process(new_app.process_name)

        if profile and profile != self.current_profile:
            self._switch_profile(profile, new_app)

    def _switch_profile(self, profile: Profile, app: AppInfo):
        """切换到新 Profile"""
        self.current_profile = profile
        self.current_app = app

        # 发送到 ESP32
        self.device.send_profile(profile)

    def start(self):
        """启动工作流管理器"""
        # 启动设备连接
        self.device.start()

        # 启动窗口检测
        self.detector.start()

    def stop(self):
        """停止工作流管理器"""
        self.detector.stop()
        self.device.stop()
