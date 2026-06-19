"""
AI Agent Deck - 设备管理器
支持 BLE 和串口通信
"""

import asyncio
import json
import threading
import time
from typing import Optional, Callable
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class DeviceInfo:
    """设备信息"""
    name: str
    address: str
    rssi: int = 0
    connected: bool = False


class DeviceManager(ABC):
    """设备管理器基类"""

    @abstractmethod
    def start(self):
        """启动设备连接"""
        pass

    @abstractmethod
    def stop(self):
        """停止设备连接"""
        pass

    @abstractmethod
    def send_profile(self, profile) -> bool:
        """发送 Profile"""
        pass

    def send_profile_raw(self, json_str: str) -> bool:
        """发送原始 JSON 字符串到设备"""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """检查连接状态"""
        pass

    def on_connect(self, callback: Callable):
        """注册连接回调"""
        pass

    def on_disconnect(self, callback: Callable):
        """注册断开回调"""
        pass


class DeviceManagerBLE(DeviceManager):
    """
    BLE 设备管理器

    功能:
    - 自动扫描并连接 "AI Agent Deck"
    - 通过 GATT 发送 Profile JSON
    - 心跳保活 (5秒间隔)
    - 断线自动重连
    """

    PROFILE_SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
    PROFILE_CHAR_UUID = "12345678-1234-5678-1234-56789abcdef1"

    def __init__(self, device_name: str = "AI Agent Deck"):
        self.device_name = device_name
        self.connected = False
        self._client = None
        self._device_address = None

        # 异步事件循环
        self._loop = None
        self._thread = None
        self._running = False

        # 心跳
        self._heartbeat_interval = 5.0
        self._heartbeat_task = None

        # 回调
        self._on_connect_callback = None
        self._on_disconnect_callback = None

        # 重连配置
        self._reconnect_delay = 2.0
        self._max_reconnect_delay = 30.0

    def on_connect(self, callback: Callable):
        self._on_connect_callback = callback

    def on_disconnect(self, callback: Callable):
        self._on_disconnect_callback = callback

    def start(self):
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            self._loop.run_until_complete(self._main_loop())
        except Exception as e:
            print(f"[BLE] Event loop error: {e}")
        finally:
            self._loop.close()

    async def _main_loop(self):
        while self._running:
            try:
                # 扫描设备
                device = await self._scan_device()
                if not device:
                    await asyncio.sleep(self._reconnect_delay)
                    continue

                # 连接设备
                success = await self._connect_device(device)
                if not success:
                    await asyncio.sleep(self._reconnect_delay)
                    continue

                # 启动心跳
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

                # 等待断开
                await self._wait_for_disconnect()

            except Exception as e:
                print(f"[BLE] Main loop error: {e}")

            # 清理
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                self._heartbeat_task = None

            self.connected = False
            if self._on_disconnect_callback:
                self._on_disconnect_callback()

            if self._running:
                await asyncio.sleep(self._reconnect_delay)

    async def _scan_device(self):
        try:
            from bleak import BleakScanner
            devices = await BleakScanner.discover(timeout=5.0)

            for d in devices:
                name = d.name or ""
                if self.device_name in name:
                    return DeviceInfo(name=name, address=d.address, rssi=d.rssi)

            return None

        except Exception as e:
            print(f"[BLE] Scan error: {e}")
            return None

    async def _connect_device(self, device: DeviceInfo):
        try:
            from bleak import BleakClient

            self._client = BleakClient(
                device.address,
                disconnected_callback=self._on_ble_disconnect
            )

            success = await self._client.connect(timeout=10.0)
            if success:
                self.connected = True
                self._device_address = device.address

                # 等待 GATT 服务解析完成
                await asyncio.sleep(0.5)

                # 列出可用服务（调试）
                if hasattr(self._client, 'services'):
                    for svc in self._client.services:
                        print(f"[BLE] Service: {svc.uuid}")
                        for char in svc.characteristics:
                            print(f"  Char: {char.uuid} props={char.properties}")

                if self._on_connect_callback:
                    self._on_connect_callback()

                return True

            return False

        except Exception as e:
            print(f"[BLE] Connect error: {e}")
            return False

    def _on_ble_disconnect(self, client):
        self.connected = False

    async def _wait_for_disconnect(self):
        while self.connected and self._running:
            await asyncio.sleep(1.0)

            if self._client and not self._client.is_connected:
                self.connected = False
                break

    async def _heartbeat_loop(self):
        while self.connected:
            try:
                await asyncio.sleep(self._heartbeat_interval)

                if not self.connected:
                    break

                success = await self._send_ping()
                if not success:
                    self.connected = False
                    break

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[BLE] Heartbeat error: {e}")
                break

    async def _send_ping(self):
        try:
            ping_data = json.dumps({"cmd": "ping"}).encode("utf-8") + b"\n"
            return await self._send_data(ping_data)
        except Exception:
            return False

    async def _send_data(self, data: bytes, retries: int = 3):
        if not self._client or not self.connected:
            print(f"[BLE] Cannot send: client={self._client is not None}, connected={self.connected}")
            return False

        # 检查实际连接状态
        if hasattr(self._client, 'is_connected') and not self._client.is_connected:
            print("[BLE] Client disconnected, marking as not connected")
            self.connected = False
            return False

        for attempt in range(retries):
            try:
                # bleak 支持直接用 UUID 字符串写入
                await self._client.write_gatt_char(
                    self.PROFILE_CHAR_UUID, data, response=True
                )
                return True

            except Exception as e:
                print(f"[BLE] Send attempt {attempt+1}/{retries} failed: {type(e).__name__}: {e}")
                # 如果是连接错误，标记为断开
                if "disconnected" in str(e).lower() or "not connected" in str(e).lower():
                    self.connected = False
                    return False
                # 短暂等待后重试
                if attempt < retries - 1:
                    await asyncio.sleep(0.5)

        return False

    def send_profile(self, profile) -> bool:
        if not self.connected or not self._loop:
            print(f"[BLE] Cannot send profile: connected={self.connected}, loop={self._loop is not None}")
            return False

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

            future = asyncio.run_coroutine_threadsafe(
                self._send_data(data), self._loop
            )
            return future.result(timeout=15.0)  # 增加超时以适应重试

        except Exception as e:
            print(f"[BLE] Send profile error: {e}")
            return False

    def send_profile_raw(self, json_str: str) -> bool:
        """发送原始 JSON 到 ESP32"""
        if not self.connected or not self._loop:
            return False
        try:
            data = json_str.encode("utf-8") + b"\n"
            future = asyncio.run_coroutine_threadsafe(
                self._send_data(data), self._loop
            )
            return future.result(timeout=15.0)  # 增加超时以适应重试
        except Exception as e:
            print(f"[BLE] Send raw error: {e}")
            return False

    def stop(self):
        self._running = False

        if self._heartbeat_task:
            self._heartbeat_task.cancel()

        if self._client and self.connected:
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self._client.disconnect(), self._loop
                )
                future.result(timeout=3.0)
            except Exception:
                pass

        self.connected = False

    def is_connected(self) -> bool:
        # 双重检查：内部状态 + 实际 BLE 连接
        if not self.connected:
            return False
        if self._client and hasattr(self._client, 'is_connected'):
            try:
                if not self._client.is_connected:
                    self.connected = False
                    return False
            except:
                pass
        return True


class DeviceManagerSerial(DeviceManager):
    """
    串口设备管理器

    功能:
    - 自动检测 ESP32 串口
    - 通过串口发送 Profile JSON
    - 后台接收线程读取 ESP32 响应
    - 心跳保活
    """

    def __init__(self, port: str = None, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.connected = False
        self._serial = None
        self._on_connect_callback = None
        self._on_disconnect_callback = None
        self._on_data_callback = None
        self._recv_thread = None
        self._running = False

        try:
            import serial
            import serial.tools.list_ports
            self._serial_module = serial
        except ImportError:
            self._serial_module = None

    def on_connect(self, callback: Callable):
        self._on_connect_callback = callback

    def on_disconnect(self, callback: Callable):
        self._on_disconnect_callback = callback

    def on_data(self, callback: Callable):
        """注册数据接收回调"""
        self._on_data_callback = callback

    def _auto_detect_port(self) -> Optional[str]:
        if not self._serial_module:
            return None

        ports = self._serial_module.tools.list_ports.comports()
        for p in ports:
            if 'CP210' in p.description:
                return p.device
        for p in ports:
            if 'CH340' in p.description:
                return p.device
        for p in ports:
            if 'USB' in p.description or 'Serial' in p.description:
                return p.device
        return None

    def start(self):
        if not self.port:
            self.port = self._auto_detect_port()

        if self.port:
            try:
                self._serial = self._serial_module.Serial(
                    self.port, self.baudrate, timeout=0.1,
                    write_timeout=2
                )
                # 禁用 DTR/RTS（避免 ESP32 复位）
                self._serial.dtr = False
                self._serial.rts = False

                # 等待 ESP32 启动完成
                time.sleep(3.0)

                # 清空缓冲区（丢弃启动日志）
                self._serial.reset_input_buffer()
                self._serial.reset_output_buffer()

                self.connected = True
                self._running = True

                # 启动接收线程
                self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
                self._recv_thread.start()

                if self._on_connect_callback:
                    self._on_connect_callback()

                print(f"[Serial] Connected to {self.port}")

                # 发送 ping 测试连接
                self._serial.write(b'{"cmd":"ping"}\n')
                self._serial.flush()

            except Exception as e:
                print(f"[Serial] Connect error: {e}")

    def _recv_loop(self):
        """后台接收线程 - 读取 ESP32 的所有输出"""
        buf = b""
        while self._running and self.connected:
            try:
                if not self._serial or not self._serial.is_open:
                    print("[Serial] Port closed, exiting recv loop")
                    self.connected = False
                    break

                data = self._serial.read(self._serial.in_waiting or 1)
                if data:
                    buf += data
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        line_str = line.decode("utf-8", errors="replace").strip()
                        if line_str:
                            print(f"[Serial] RX: {line_str}")
                            if self._on_data_callback:
                                try:
                                    msg = json.loads(line_str)
                                    self._on_data_callback(msg)
                                except json.JSONDecodeError:
                                    pass
                else:
                    time.sleep(0.05)

            except Exception as e:
                if self._running:
                    print(f"[Serial] Recv error: {e}")
                    self.connected = False
                break

        # 通知断开
        if self._on_disconnect_callback:
            self._on_disconnect_callback()
        print("[Serial] Recv thread exited")

    def send_profile(self, profile) -> bool:
        if not self.connected or not self._serial:
            print(f"[Serial] Cannot send: connected={self.connected}, serial={self._serial is not None}")
            return False

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

            print(f"[Serial] TX: {json_str[:100]}...")
            self._serial.write(data)
            self._serial.flush()
            return True

        except Exception as e:
            print(f"[Serial] Send error: {e}")
            return False

    def send_profile_raw(self, json_str: str) -> bool:
        """发送原始 JSON 到 ESP32"""
        if not self.connected or not self._serial:
            return False
        try:
            data = json_str.encode("utf-8") + b"\n"
            print(f"[Serial] TX raw: {json_str[:100]}...")
            self._serial.write(data)
            self._serial.flush()
            return True
        except Exception as e:
            print(f"[Serial] Send raw error: {e}")
            return False

    def stop(self):
        self._running = False
        self.connected = False

        if self._serial and self._serial.is_open:
            try:
                self._serial.close()
            except:
                pass

        if self._on_disconnect_callback:
            self._on_disconnect_callback()

    def is_connected(self) -> bool:
        if not self.connected:
            return False
        if self._serial and not self._serial.is_open:
            self.connected = False
            return False
        return True
