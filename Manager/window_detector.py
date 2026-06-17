"""
AI Agent Deck - 活动窗口检测器
实时检测当前前台应用，用于自动切换 Profile
"""

import time
import threading
from dataclasses import dataclass

try:
    import win32gui
    import win32process
    import ctypes
    import ctypes.wintypes
    import psutil
except ImportError:
    print("请安装依赖: pip install pywin32 psutil")
    raise

# 使用 ctypes 获取前台窗口线程/进程ID (兼容性更好)
_user32 = ctypes.windll.user32


@dataclass
class ApplicationInfo:
    """当前应用信息"""
    process_name: str       # 进程名 (Code.exe)
    window_title: str       # 窗口标题
    pid: int                # 进程ID
    timestamp: float        # 检测时间戳

    def __str__(self):
        return f"{self.process_name} | {self.window_title[:40]}"


class WindowDetector:
    """Windows 活动窗口检测器"""

    def __init__(self, poll_interval: float = 0.5):
        self.poll_interval = poll_interval
        self._current: ApplicationInfo | None = None
        self._callbacks: list = []
        self._running = False
        self._thread: threading.Thread | None = None

    def on_change(self, callback):
        """注册应用切换回调"""
        self._callbacks.append(callback)

    def get_current_application(self) -> ApplicationInfo | None:
        """获取当前前台应用信息"""
        try:
            hwnd = _user32.GetForegroundWindow()
            if not hwnd:
                return None

            pid = ctypes.wintypes.DWORD()
            _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            pid = pid.value
            if not pid:
                return None

            process = psutil.Process(pid)
            process_name = process.name()

            length = _user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            _user32.GetWindowTextW(hwnd, buf, length + 1)
            window_title = buf.value

            return ApplicationInfo(
                process_name=process_name,
                window_title=window_title,
                pid=pid,
                timestamp=time.time()
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
            return None

    def _poll_loop(self):
        """轮询循环"""
        while self._running:
            app = self.get_current_application()
            if app and app != self._current:
                old = self._current
                self._current = app
                for cb in self._callbacks:
                    try:
                        cb(app, old)
                    except Exception as e:
                        print(f"[WindowDetector] 回调错误: {e}")
            time.sleep(self.poll_interval)

    def start(self):
        """启动检测"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        print(f"[WindowDetector] 启动 (轮询间隔: {self.poll_interval}s)")

    def stop(self):
        """停止检测"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        print("[WindowDetector] 已停止")

    @property
    def current(self) -> ApplicationInfo | None:
        return self._current
