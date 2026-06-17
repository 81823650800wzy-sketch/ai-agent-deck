"""
AI Agent Deck - 设备通信管理器
通过串口与 ESP32 通信，发送 Profile 数据
"""

import json
import threading
import time

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    serial = None
    print("[DeviceManager] pyserial 未安装: pip install pyserial")


class DeviceManager:
    """设备通信管理器 (串口)"""

    def __init__(self, port: str = None, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.connected = False
        self._serial = None
        self._thread: threading.Thread | None = None
        self._running = False

    def _auto_detect_port(self) -> str | None:
        """自动检测 ESP32 串口"""
        if not serial:
            return None
        ports = serial.tools.list_ports.comports()
        for p in ports:
            if 'CH340' in p.description or 'CP210' in p.description or 'USB' in p.description:
                return p.device
        return None

    def start(self):
        if self._running:
            return
        self._running = True

        if not self.port:
            self.port = self._auto_detect_port()

        if self.port:
            print(f"[DeviceManager] 串口: {self.port}")
            self._connect()
        else:
            print("[DeviceManager] 未找到串口")

    def _connect(self):
        """连接串口"""
        if not serial:
            return
        try:
            self._serial = serial.Serial(self.port, self.baudrate, timeout=1)
            self.connected = True
            print(f"[DeviceManager] ✅ 已连接: {self.port}")
        except Exception as e:
            print(f"[DeviceManager] 连接失败: {e}")

    def stop(self):
        self._running = False
        if self._serial:
            self._serial.close()
            self._serial = None
        self.connected = False

    def connect_async(self):
        """兼容旧接口"""
        pass

    def send_profile(self, profile):
        """发送 Profile 到 ESP32"""
        if not self.connected or not self._serial:
            print("[DeviceManager] 设备未连接")
            return

        try:
            payload = {
                "cmd": "profile",
                "data": {
                    "name": profile.name,
                    "keys": [
                        {"id": k.id, "display": k.display, "action": k.action}
                        for k in profile.keys
                    ]
                }
            }
            json_str = json.dumps(payload, ensure_ascii=False)
            data = json_str.encode("utf-8") + b"\n"

            self._serial.write(data)
            self._serial.flush()
            print(f"[DeviceManager] ✅ 已发送: {profile.name} ({len(data)} 字节)")

        except Exception as e:
            print(f"[DeviceManager] ❌ 发送失败: {e}")
            self.connected = False

    @property
    def is_connected(self) -> bool:
        return self.connected
