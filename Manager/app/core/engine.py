"""
AI Agent Deck - 核心引擎
管理所有组件的生命周期
"""

import asyncio
import threading
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
from enum import Enum

from .device import DeviceManager, DeviceManagerSerial
from .wifi_device import WiFiDeviceManager
from .profile import ProfileManager, Profile
from .workflow import WorkflowManager


class EngineState(Enum):
    """引擎状态"""
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class TransportMode(Enum):
    """传输模式"""
    SERIAL = "serial"
    BLE = "ble"
    WIFI = "wifi"


@dataclass
class EngineConfig:
    """引擎配置"""
    transport: TransportMode = TransportMode.WIFI  # 默认 WiFi
    com_port: Optional[str] = None
    wifi_host: Optional[str] = None  # ESP32 IP (NULL 时自动发现)
    wifi_port: int = 8080
    poll_interval: float = 0.5
    heartbeat_interval: float = 5.0
    auto_reconnect: bool = True


class Engine:
    """
    核心引擎

    管理:
    - 设备连接
    - Profile 管理
    - 工作流协调
    - 事件分发
    """

    def __init__(self, config: Optional[EngineConfig] = None):
        self.config = config or EngineConfig()
        self.state = EngineState.IDLE

        # 组件
        self.device: Optional[DeviceManager] = None
        self.profiles: Optional[ProfileManager] = None
        self.workflow: Optional[WorkflowManager] = None

        # 预加载 Profile（不依赖 start()）
        try:
            self.profiles = ProfileManager()
        except Exception as e:
            print(f"[Engine] Pre-load profiles failed: {e}")

        # 待发送的 Profile（设备连接后自动发送）
        self._pending_profile: Optional[Profile] = None

        # 壁纸管理器引用（用于 ACK 通知）
        self._wallpaper_mgr = None

        # 事件回调
        self._callbacks: Dict[str, list] = {
            'state_change': [],
            'device_connect': [],
            'device_disconnect': [],
            'app_change': [],
            'profile_change': [],
            'key_press': [],
            'error': [],
            'status': [],  # WiFi/BLE 状态消息
            'device_data': [],  # ESP32 响应数据
        }

        # 线程锁
        self._lock = threading.Lock()

    def on(self, event: str, callback: Callable):
        """注册事件回调"""
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def _emit(self, event: str, *args, **kwargs):
        """触发事件"""
        for callback in self._callbacks.get(event, []):
            try:
                callback(*args, **kwargs)
            except RuntimeError as e:
                # Qt 对象已删除，忽略
                if "deleted" in str(e).lower():
                    continue
                print(f"[Engine] Callback error: {e}")
            except Exception as e:
                print(f"[Engine] Callback error: {e}")

    def start(self):
        """启动引擎"""
        if self.state != EngineState.IDLE:
            return

        self.state = EngineState.STARTING
        self._emit('state_change', self.state)

        try:
            # 初始化组件
            self._init_components()

            # 启动工作流
            self.workflow.start()

            self.state = EngineState.RUNNING
            self._emit('state_change', self.state)

        except Exception as e:
            self.state = EngineState.ERROR
            self._emit('error', str(e))
            self._emit('state_change', self.state)

    def stop(self):
        """停止引擎"""
        if self.state != EngineState.RUNNING:
            return

        self.state = EngineState.STOPPING
        self._emit('state_change', self.state)

        try:
            if self.workflow:
                self.workflow.stop()

            self.state = EngineState.IDLE
            self._emit('state_change', self.state)

        except Exception as e:
            self.state = EngineState.ERROR
            self._emit('error', str(e))
            self._emit('state_change', self.state)

    def _init_components(self):
        """初始化组件"""
        # Profile 管理器（如果已预加载则跳过）
        if not self.profiles:
            self.profiles = ProfileManager()

        # 设备管理器
        if self.config.transport == TransportMode.WIFI:
            self.device = WiFiDeviceManager(
                host=self.config.wifi_host,
                port=self.config.wifi_port
            )
        elif self.config.transport == TransportMode.BLE:
            from .device import DeviceManagerBLE
            self.device = DeviceManagerBLE()
        else:
            self.device = DeviceManagerSerial(port=self.config.com_port)

        self.device.on_connect(self._on_device_connected)
        self.device.on_disconnect(lambda: self._emit('device_disconnect'))

        # WiFi 状态回调
        if hasattr(self.device, 'on_status'):
            self.device.on_status(lambda msg: self._emit('status', msg))

        # 串口数据回调（显示 ESP32 响应）
        if hasattr(self.device, 'on_data'):
            self.device.on_data(self._on_device_data)

        # 工作流管理器 (共享设备管理器)
        self.workflow = WorkflowManager(device=self.device)

        # 注册回调
        self.workflow.detector.on_change(self._on_app_changed)

    def _on_device_data(self, data: dict):
        """设备数据回调（ESP32 响应）"""
        self._emit('device_data', data)

        # 如果是壁纸 ACK，通知壁纸管理器
        cmd = data.get("cmd", "")
        if cmd == "wallpaper_ack" and self._wallpaper_mgr:
            status = data.get("status", "")
            offset = data.get("off", -1)
            if status == "chunk":
                self._wallpaper_mgr.signal_ack(offset)
            elif status == "ok":
                self._wallpaper_mgr.signal_ack(999999)  # 完成信号

    def _on_device_connected(self):
        """设备连接成功回调"""
        self._emit('device_connect')

        # 发送待发送的 Profile
        if self._pending_profile and self.workflow and self.workflow.device:
            import threading
            # 延迟发送，等待 GATT 服务就绪
            def _delayed_send():
                import time
                time.sleep(1.0)  # 等待 BLE 服务发现完成
                if self._pending_profile and self.workflow.device.is_connected():
                    success = self.workflow.device.send_profile(self._pending_profile)
                    if success:
                        print(f"[Engine] Pending profile sent: {self._pending_profile.name}")
                        self._pending_profile = None
                    else:
                        print(f"[Engine] Failed to send pending profile")

            threading.Thread(target=_delayed_send, daemon=True).start()

    def _on_app_changed(self, new_app, old_app):
        """应用切换回调"""
        self._emit('app_change', new_app, old_app)

        # 匹配 Profile
        profile = self.profiles.get_profile_by_process(new_app.process_name)
        if profile:
            # 只在 Profile 变化时才发送
            if self.workflow and self.workflow.current_profile == profile:
                return

            self._emit('profile_change', profile)

            # 发送到设备（先检查连接状态）
            if self.workflow and self.workflow.device:
                if not self.workflow.device.is_connected():
                    self._pending_profile = profile
                    print(f"[Engine] Device not connected, will send when ready: {profile.name}")
                    return

                success = self.workflow.device.send_profile(profile)
                if success:
                    print(f"[Engine] Profile sent: {profile.name}")
                    self._pending_profile = None
                    if self.workflow:
                        self.workflow.current_profile = profile
                else:
                    self._pending_profile = profile
                    print(f"[Engine] Failed to send profile: {profile.name}")
                    self._emit('error', f"发送 Profile 失败: {profile.name}")

    def send_profile(self, profile: Profile) -> bool:
        """发送 Profile 到设备"""
        if not self.workflow or not self.workflow.device:
            return False

        return self.workflow.device.send_profile(profile)

    def get_current_profile(self) -> Optional[Profile]:
        """获取当前 Profile"""
        if self.workflow:
            return self.workflow.current_profile
        return None

    def get_current_app(self):
        """获取当前应用"""
        if self.workflow:
            return self.workflow.current_app
        return None

    def is_connected(self) -> bool:
        """检查设备是否连接"""
        if self.workflow and self.workflow.device:
            return self.workflow.device.is_connected()
        return False

    def is_running(self) -> bool:
        """检查引擎是否运行"""
        return self.state == EngineState.RUNNING
