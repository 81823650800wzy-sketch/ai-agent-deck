"""
AI Agent Deck - WiFi 设备管理器
通过 TCP 连接 ESP32，支持 mDNS 自动发现
"""

import socket
import json
import threading
import time
from typing import Optional, Callable

from ..log import get_logger

logger = get_logger("wifi")


class WiFiDeviceManager:
    """
    WiFi 设备管理器

    功能:
    - mDNS 自动发现 ai-deck.local
    - TCP 连接 ESP32 (端口 8080)
    - 发送 Profile / 壁纸 / 屏幕控制命令
    - OTA 固件更新
    """

    def __init__(self, host: str = None, port: int = 8080):
        self.host = host
        self.port = port
        self.connected = False
        self._socket: Optional[socket.socket] = None
        self._recv_thread: Optional[threading.Thread] = None
        self._running = False

        # 回调
        self._on_connect_callback = None
        self._on_disconnect_callback = None
        self._on_data_callback = None
        self._on_status_callback = None  # 状态回调（用于 UI 显示）

    def on_connect(self, callback: Callable):
        self._on_connect_callback = callback

    def on_disconnect(self, callback: Callable):
        self._on_disconnect_callback = callback

    def on_data(self, callback: Callable):
        """注册数据接收回调（用于日志、ACK 等）"""
        self._on_data_callback = callback

    def on_status(self, callback: Callable):
        """注册状态回调（用于 UI 显示连接进度）"""
        self._on_status_callback = callback

    def _emit_status(self, msg: str):
        """发送状态消息"""
        logger.info(msg)
        if self._on_status_callback:
            self._on_status_callback(msg)

    def discover(self, timeout: float = 5.0) -> Optional[str]:
        """
        通过 mDNS 发现设备
        返回设备 IP 地址，未找到返回 None
        """
        self._emit_status("正在搜索设备...")

        try:
            from zeroconf import Zeroconf, ServiceBrowser, ServiceStateChange

            found_ip = None
            event = threading.Event()

            def on_service_change(zc, svc_type, name, state_change):
                nonlocal found_ip
                if state_change == ServiceStateChange.Added:
                    info = zc.get_service_info(svc_type, name)
                    if info and info.addresses:
                        found_ip = socket.inet_ntoa(info.addresses[0])
                        event.set()

            zc = Zeroconf()
            browser = ServiceBrowser(zc, "_ai-deck._tcp.local.", handlers=[on_service_change])

            event.wait(timeout=timeout)
            browser.cancel()
            zc.close()

            if found_ip:
                self._emit_status(f"发现设备: {found_ip}")
                self.host = found_ip
            else:
                self._emit_status("mDNS 未发现设备，尝试 DNS...")
                found_ip = self._dns_resolve("ai-deck.local")

            return found_ip

        except ImportError:
            self._emit_status("zeroconf 未安装，使用 DNS 解析...")
            return self._dns_resolve("ai-deck.local")

        except Exception as e:
            self._emit_status(f"mDNS 错误: {e}，尝试 DNS...")
            return self._dns_resolve("ai-deck.local")

    def _dns_resolve(self, hostname: str) -> Optional[str]:
        """DNS 回退"""
        try:
            ip = socket.gethostbyname(hostname)
            logger.info(f"DNS 解析: {hostname} -> {ip}")
            self.host = ip
            return ip
        except socket.gaierror:
            return None

    def start(self):
        """启动连接"""
        if self._running:
            return

        self._running = True
        self._recv_thread = threading.Thread(target=self._connect_loop, daemon=True)
        self._recv_thread.start()

    def _connect_loop(self):
        """连接循环（自动重连）"""
        while self._running:
            # 自动发现
            if not self.host:
                ip = self.discover()
                if not ip:
                    self._emit_status("未找到设备，3秒后重试...")
                    time.sleep(3)
                    continue

            # 连接
            try:
                self._emit_status(f"连接 {self.host}:{self.port}...")
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._socket.settimeout(5.0)
                self._socket.connect((self.host, self.port))
                self._socket.settimeout(None)  # 非阻塞模式

                self.connected = True
                self._emit_status(f"已连接: {self.host}:{self.port}")

                if self._on_connect_callback:
                    self._on_connect_callback()

                # 接收循环
                self._recv_loop()

            except ConnectionRefusedError:
                self._emit_status("连接被拒绝，ESP32 可能未启动 TCP 服务器")
                time.sleep(5)
            except TimeoutError:
                self._emit_status("连接超时，检查网络...")
                time.sleep(3)
            except OSError as e:
                self._emit_status(f"连接错误: {e}")
                time.sleep(3)

            finally:
                self._cleanup()

    def _recv_loop(self):
        """数据接收循环"""
        buf = b""
        while self._running and self.connected:
            try:
                data = self._socket.recv(4096)
                if not data:
                    logger.warning("远端关闭连接")
                    break

                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    if line and self._on_data_callback:
                        try:
                            msg = json.loads(line.decode("utf-8"))
                            self._on_data_callback(msg)
                        except json.JSONDecodeError:
                            pass  # 忽略非 JSON 数据

            except (ConnectionResetError, OSError):
                break

    def _cleanup(self):
        """清理连接"""
        self.connected = False
        if self._socket:
            try:
                self._socket.close()
            except:
                pass
            self._socket = None

        if self._on_disconnect_callback:
            self._on_disconnect_callback()

    def stop(self):
        """停止连接"""
        self._running = False
        self._cleanup()

    def send(self, data: dict) -> bool:
        """发送 JSON 命令"""
        if not self.connected or not self._socket:
            return False
        try:
            json_str = json.dumps(data, ensure_ascii=False) + "\n"
            self._socket.sendall(json_str.encode("utf-8"))
            return True
        except Exception as e:
            logger.error(f"WiFi 发送异常: {e}")
            self.connected = False
            return False

    def send_profile(self, profile) -> bool:
        """发送 Profile"""
        return self.send({
            "cmd": "profile",
            "data": {
                "name": profile.name,
                "keys": [
                    {"id": k.id, "display": k.display, "action": k.action}
                    for k in profile.keys
                ]
            }
        })

    def send_profile_raw(self, json_str: str) -> bool:
        """发送原始 JSON"""
        if not self.connected or not self._socket:
            return False
        try:
            data = json_str.encode("utf-8") + b"\n"
            self._socket.sendall(data)
            return True
        except Exception as e:
            logger.error(f"WiFi 发送原始数据异常: {e}")
            self.connected = False
            return False

    def send_screen_cmd(self, action: str, screen_id: int = None) -> bool:
        """发送屏幕控制命令"""
        cmd = {"cmd": "screen", "action": action}
        if screen_id is not None:
            cmd["id"] = screen_id
        return self.send(cmd)

    def send_wallpaper_chunk(self, offset: int, total: int, data_b64: str) -> bool:
        """发送壁纸数据块"""
        return self.send({
            "cmd": "wp_chunk",
            "off": offset,
            "total": total,
            "data": data_b64
        })

    def is_connected(self) -> bool:
        return self.connected

    # ── OTA 功能 ────────────────────────────

    def ota_update(self, firmware_path: str, progress_cb: Callable = None) -> bool:
        """
        OTA 固件更新
        @param firmware_path: .bin 固件文件路径
        @param progress_cb: 进度回调 (bytes_sent, total_bytes)
        """
        import base64

        with open(firmware_path, "rb") as f:
            fw_data = f.read()

        total = len(fw_data)
        chunk_size = 4096  # 每块 4KB

        # 1. 开始 OTA
        if not self.send({"cmd": "ota_begin", "size": total}):
            logger.error("OTA 启动失败")
            return False

        time.sleep(0.5)  # 等待 ESP32 准备

        # 2. 分块发送
        offset = 0
        while offset < total:
            end = min(offset + chunk_size, total)
            chunk = fw_data[offset:end]
            b64_chunk = base64.b64encode(chunk).decode("ascii")

            if not self.send({"cmd": "ota_data", "data": b64_chunk}):
                logger.error(f"OTA 传输失败: offset={offset}")
                return False

            offset = end
            if progress_cb:
                progress_cb(offset, total)

            time.sleep(0.05)  # 控制发送速率

        # 3. 完成
        time.sleep(0.5)
        if not self.send({"cmd": "ota_end"}):
            logger.error("OTA 完成命令发送失败")
            return False

        logger.info("OTA 更新已发送，设备将重启")
        return True
