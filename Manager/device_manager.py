"""
AI Agent Deck - BLE 设备通信管理器
通过 BLE GATT 与 ESP32 通信，发送 Profile 数据，心跳保活
"""

import asyncio
import json
import struct
import threading
import time
from typing import Callable, Optional
from dataclasses import dataclass

try:
    from bleak import BleakClient, BleakScanner
    from bleak.backends.characteristic import BleakGATTCharacteristic
except ImportError:
    BleakClient = None
    BleakScanner = None
    print("[DeviceManager] bleak 未安装: pip install bleak")


@dataclass
class DeviceInfo:
    """BLE 设备信息"""
    name: str
    address: str
    rssi: int = 0


class DeviceManager:
    """
    BLE 设备通信管理器

    功能:
    - 自动扫描并连接 "AI Agent Deck"
    - 通过 GATT 发送 Profile JSON
    - 心跳保活 (5 秒 ping)
    - 断线自动重连
    """

    # GATT UUID (与 ESP32 固件一致)
    PROFILE_SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
    PROFILE_CHAR_UUID = "12345678-1234-5678-1234-56789abcdef1"

    def __init__(self, device_name: str = "AI Agent Deck"):
        self.device_name = device_name
        self.connected = False
        self._client: Optional[BleakClient] = None
        self._device_address: Optional[str] = None

        # 异步事件循环
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

        # 心跳
        self._heartbeat_interval = 5.0  # 秒
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._last_pong = 0.0

        # 回调
        self._on_connect: Optional[Callable] = None
        self._on_disconnect: Optional[Callable] = None

        # 重连配置
        self._reconnect_delay = 2.0
        self._max_reconnect_delay = 30.0

    def on_connect(self, callback: Callable):
        """注册连接成功回调"""
        self._on_connect = callback

    def on_disconnect(self, callback: Callable):
        """注册断开连接回调"""
        self._on_disconnect = callback

    def start(self):
        """启动 BLE 管理器 (在后台线程运行异步事件循环)"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print("[DeviceManager] BLE 管理器已启动")

    def _run_loop(self):
        """在后台线程运行异步事件循环"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            self._loop.run_until_complete(self._main_loop())
        except Exception as e:
            print(f"[DeviceManager] 事件循环异常: {e}")
        finally:
            self._loop.close()

    async def _main_loop(self):
        """主循环：扫描 → 连接 → 保持连接"""
        while self._running:
            try:
                # 扫描设备
                device = await self._scan_device()
                if not device:
                    print(f"[DeviceManager] 未找到 {self.device_name}，{self._reconnect_delay}秒后重试...")
                    await asyncio.sleep(self._reconnect_delay)
                    continue

                # 连接设备
                success = await self._connect_device(device)
                if not success:
                    await asyncio.sleep(self._reconnect_delay)
                    continue

                # 连接成功，启动心跳
                self._last_pong = time.time()
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

                # 等待断开连接
                await self._wait_for_disconnect()

            except Exception as e:
                print(f"[DeviceManager] 主循环异常: {e}")

            # 断开连接后清理
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                self._heartbeat_task = None

            self.connected = False
            if self._on_disconnect:
                self._on_disconnect()

            # 指数退避重连
            if self._running:
                print(f"[DeviceManager] {self._reconnect_delay}秒后尝试重连...")
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 1.5, self._max_reconnect_delay)

    async def _scan_device(self) -> Optional[DeviceInfo]:
        """扫描目标 BLE 设备"""
        print(f"[DeviceManager] 正在扫描 {self.device_name}...")

        try:
            devices = await BleakScanner.discover(timeout=5.0)

            for d in devices:
                name = d.name or ""
                if self.device_name in name:
                    print(f"[DeviceManager] [OK] 找到设备: {name} [{d.address}]")
                    return DeviceInfo(name=name, address=d.address, rssi=d.rssi)

            return None

        except Exception as e:
            print(f"[DeviceManager] 扫描异常: {e}")
            return None

    async def _connect_device(self, device: DeviceInfo) -> bool:
        """连接 BLE 设备"""
        print(f"[DeviceManager] 正在连接 {device.name} [{device.address}]...")

        try:
            self._client = BleakClient(
                device.address,
                disconnected_callback=self._on_ble_disconnect
            )

            success = await self._client.connect(timeout=10.0)
            if success:
                self.connected = True
                self._device_address = device.address
                self._reconnect_delay = 2.0  # 重置重连延迟

                print(f"[DeviceManager] [OK] 已连接: {device.name}")

                # 打印 MTU
                mtu = self._client.mtu_size
                print(f"[DeviceManager] MTU: {mtu}")

                if self._on_connect:
                    self._on_connect()

                return True
            else:
                print(f"[DeviceManager] [FAIL] 连接失败")
                return False

        except Exception as e:
            print(f"[DeviceManager] 连接异常: {e}")
            return False

    def _on_ble_disconnect(self, client: BleakClient):
        """BLE 断开回调 (由 bleak 调用)"""
        print(f"[DeviceManager] BLE 连接断开")
        self.connected = False

    async def _wait_for_disconnect(self):
        """等待连接断开"""
        while self.connected and self._running:
            await asyncio.sleep(1.0)

            # 检查连接状态
            if self._client and not self._client.is_connected:
                self.connected = False
                break

    async def _heartbeat_loop(self):
        """心跳保活循环"""
        print(f"[DeviceManager] 心跳已启动 (间隔 {self._heartbeat_interval}秒)")

        while self.connected:
            try:
                await asyncio.sleep(self._heartbeat_interval)

                if not self.connected:
                    break

                # 发送 ping
                success = await self._send_ping()
                if success:
                    self._last_pong = time.time()
                else:
                    print("[DeviceManager] 心跳失败，准备断开")
                    self.connected = False
                    break

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[DeviceManager] 心跳异常: {e}")
                break

    async def _send_ping(self) -> bool:
        """发送 ping 命令"""
        try:
            ping_data = json.dumps({"cmd": "ping"}).encode("utf-8") + b"\n"
            return await self._send_data(ping_data)
        except Exception:
            return False

    async def _send_data(self, data: bytes) -> bool:
        """通过 GATT 发送数据"""
        if not self._client or not self.connected:
            return False

        try:
            # 查找 Profile 特征值
            char = self._client.services.get_characteristic(self.PROFILE_CHAR_UUID)
            if not char:
                print(f"[DeviceManager] 未找到特征值: {self.PROFILE_CHAR_UUID}")
                return False

            # 分块发送 (MTU 限制)
            mtu = self._client.mtu_size - 3  # ATT 头部占 3 字节
            offset = 0

            while offset < len(data):
                chunk = data[offset:offset + mtu]

                if offset + mtu < len(data):
                    # 使用 Prepare Write (长写入)
                    await self._client.write_gatt_char(char, chunk, response=True)
                else:
                    # 最后一块，直接写入
                    await self._client.write_gatt_char(char, chunk, response=True)

                offset += mtu

            return True

        except Exception as e:
            print(f"[DeviceManager] 发送失败: {e}")
            return False

    def send_profile(self, profile):
        """发送 Profile 到 ESP32 (同步接口)"""
        if not self.connected or not self._loop:
            print("[DeviceManager] 设备未连接")
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

            # 在异步事件循环中执行
            future = asyncio.run_coroutine_threadsafe(
                self._send_data(data), self._loop
            )
            success = future.result(timeout=5.0)

            if success:
                print(f"[DeviceManager] [OK] 已发送: {profile.name} ({len(data)} 字节)")
            else:
                print(f"[DeviceManager] [FAIL] 发送失败")

            return success

        except Exception as e:
            print(f"[DeviceManager] [FAIL] 发送异常: {e}")
            return False

    def stop(self):
        """停止 BLE 管理器"""
        print("[DeviceManager] 正在停止...")
        self._running = False

        # 取消心跳任务
        if self._heartbeat_task:
            self._heartbeat_task.cancel()

        # 断开连接
        if self._client and self.connected:
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self._client.disconnect(), self._loop
                )
                future.result(timeout=3.0)
            except Exception:
                pass

        self.connected = False
        print("[DeviceManager] 已停止")

    @property
    def is_connected(self) -> bool:
        return self.connected

    @property
    def battery_level(self) -> int:
        """获取电池电量 (预留接口)"""
        # TODO: 实现电池电量读取
        return -1


class DeviceManagerSerial:
    """
    串口设备管理器 (备用)
    当 BLE 不可用时使用串口通信
    """

    def __init__(self, port: str = None, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.connected = False
        self._serial = None

        try:
            import serial
            import serial.tools.list_ports
            self._serial_module = serial
        except ImportError:
            self._serial_module = None
            print("[DeviceManagerSerial] pyserial 未安装")

    def _auto_detect_port(self) -> Optional[str]:
        """自动检测 ESP32 串口"""
        if not self._serial_module:
            return None

        ports = self._serial_module.tools.list_ports.comports()
        for p in ports:
            # 优先查找 CP2102 (ESP32-S3 常用)
            if 'CP210' in p.description:
                return p.device
        for p in ports:
            # 其次查找 CH340
            if 'CH340' in p.description:
                return p.device
        for p in ports:
            # 最后查找任何 USB 串口
            if 'USB' in p.description or 'Serial' in p.description:
                return p.device
        return None

    def start(self):
        """启动串口连接"""
        if not self.port:
            self.port = self._auto_detect_port()

        if self.port:
            try:
                self._serial = self._serial_module.Serial(self.port, self.baudrate, timeout=1)
                self.connected = True
                print(f"[DeviceManagerSerial] [OK] 已连接: {self.port}")
            except Exception as e:
                print(f"[DeviceManagerSerial] 连接失败: {e}")
        else:
            print("[DeviceManagerSerial] 未找到串口")

    def send_profile(self, profile) -> bool:
        """发送 Profile (串口)"""
        if not self.connected or not self._serial:
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

            self._serial.write(data)
            self._serial.flush()
            print(f"[DeviceManagerSerial] [OK] 已发送: {profile.name}")
            return True

        except Exception as e:
            print(f"[DeviceManagerSerial] [FAIL] 发送失败: {e}")
            return False

    def stop(self):
        """停止串口连接"""
        if self._serial:
            self._serial.close()
        self.connected = False

    @property
    def is_connected(self) -> bool:
        return self.connected
