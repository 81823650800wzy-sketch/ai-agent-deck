"""
BLE 连接测试脚本
测试 DeviceManager 的 BLE 功能
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from device_manager import DeviceManager


def on_connect():
    print("[回调] 设备已连接!")


def on_disconnect():
    print("[回调] 设备已断开!")


async def test_ble():
    """测试 BLE 连接"""
    print("=" * 50)
    print("  AI Agent Deck - BLE 测试")
    print("=" * 50)

    # 创建设备管理器
    device = DeviceManager()
    device.on_connect(on_connect)
    device.on_disconnect(on_disconnect)

    # 启动
    device.start()

    # 等待连接
    print("\n等待连接...")
    for i in range(30):
        if device.is_connected:
            print(f"✅ 已连接!")
            break
        await asyncio.sleep(1)
        print(f"  等待中... ({i+1}秒)")

    if not device.is_connected:
        print("❌ 连接超时")
        device.stop()
        return

    # 保持连接，观察心跳
    print("\n保持连接 30 秒，观察心跳...")
    for i in range(30):
        if not device.is_connected:
            print("❌ 连接断开")
            break
        await asyncio.sleep(1)
        if i % 5 == 0:
            print(f"  连接中... ({i}秒)")

    # 停止
    device.stop()
    print("\n测试完成")


def main():
    """主函数"""
    try:
        asyncio.run(test_ble())
    except KeyboardInterrupt:
        print("\n用户中断")


if __name__ == "__main__":
    main()
