#!/usr/bin/env python3
"""
AI Agent Deck - WiFi 配置工具
通过串口或 BLE 设置 ESP32 的 WiFi 凭据

用法:
  python setup_wifi.py --ssid "你的WiFi" --pass "密码"
  python setup_wifi.py --port COM7 --ssid "你的WiFi" --pass "密码"
"""

import argparse
import json
import time
import sys


def setup_via_serial(ssid: str, password: str, port: str = None):
    """通过串口发送 WiFi 凭据"""
    try:
        import serial
        import serial.tools.list_ports
    except ImportError:
        print("❌ 需要安装 pyserial: pip install pyserial")
        return False

    # 自动检测串口
    if not port:
        ports = serial.tools.list_ports.comports()
        for p in ports:
            if 'CP210' in p.description or 'CH340' in p.description:
                port = p.device
                break

    if not port:
        print("❌ 未找到 ESP32 串口，请指定 --port")
        return False

    print(f"📡 连接到: {port}")

    try:
        ser = serial.Serial(port, 115200, timeout=2)
        time.sleep(0.5)

        # 发送 WiFi 配置命令
        cmd = json.dumps({
            "cmd": "wifi_save",
            "ssid": ssid,
            "pass": password
        })
        ser.write((cmd + "\n").encode("utf-8"))
        ser.flush()

        print(f"📤 已发送 WiFi 配置: SSID={ssid}")

        # 等待响应
        deadline = time.time() + 5
        while time.time() < deadline:
            if ser.in_waiting:
                data = ser.read(ser.in_waiting).decode("utf-8", errors="replace")
                print(f"📥 ESP32: {data.strip()}")
                if "saved" in data or "ok" in data.lower():
                    print("✅ WiFi 凭据已保存！ESP32 将在下次启动时连接。")
                    ser.close()
                    return True
            time.sleep(0.1)

        print("⚠️ 未收到确认，但凭据可能已保存。请重启 ESP32 验证。")
        ser.close()
        return True

    except Exception as e:
        print(f"❌ 串口错误: {e}")
        return False


def setup_via_ble(ssid: str, password: str, device_name: str = "AI Agent Deck"):
    """通过 BLE 发送 WiFi 凭据"""
    try:
        from bleak import BleakScanner, BleakClient
    except ImportError:
        print("❌ 需要安装 bleak: pip install bleak")
        return False

    PROFILE_CHAR_UUID = "12345678-1234-5678-1234-56789abcdef1"

    import asyncio

    async def _send():
        print(f"🔍 扫描 BLE 设备: {device_name}")
        devices = await BleakScanner.discover(timeout=5.0)

        target = None
        for d in devices:
            if device_name in (d.name or ""):
                target = d
                break

        if not target:
            print(f"❌ 未找到 BLE 设备: {device_name}")
            return False

        print(f"📡 连接到: {target.name} ({target.address})")

        async with BleakClient(target.address) as client:
            if not client.is_connected:
                print("❌ BLE 连接失败")
                return False

            cmd = json.dumps({
                "cmd": "wifi_save",
                "ssid": ssid,
                "pass": password
            })
            data = cmd.encode("utf-8") + b"\n"
            await client.write_gatt_char(PROFILE_CHAR_UUID, data, response=True)

            print(f"📤 已发送 WiFi 配置: SSID={ssid}")
            print("✅ WiFi 凭据已发送！ESP32 将在下次启动时连接。")
            return True

    return asyncio.run(_send())


def main():
    parser = argparse.ArgumentParser(description="AI Agent Deck WiFi 配置工具")
    parser.add_argument("--ssid", required=True, help="WiFi SSID")
    parser.add_argument("--pass", dest="password", required=True, help="WiFi 密码")
    parser.add_argument("--port", default=None, help="串口号 (自动检测)")
    parser.add_argument("--ble", action="store_true", help="使用 BLE 而非串口")
    parser.add_argument("--device", default="AI Agent Deck", help="BLE 设备名")

    args = parser.parse_args()

    print("=" * 50)
    print("  AI Agent Deck - WiFi 配置工具")
    print("=" * 50)
    print(f"  SSID: {args.ssid}")
    print(f"  方式: {'BLE' if args.ble else '串口'}")
    print("=" * 50)

    if args.ble:
        success = setup_via_ble(args.ssid, args.password, args.device)
    else:
        success = setup_via_serial(args.ssid, args.password, args.port)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
