"""
AI Agent Deck Manager - 入口
Context-Aware Workflow Controller 桌面端

用法:
    python main.py                  # 默认 BLE 连接 + GUI
    python main.py --cli            # 命令行模式
    python main.py --scan           # 扫描 BLE 设备
    python main.py --no-ble         # 离线模式 (仅窗口检测 + Profile)
"""

import sys
import signal
import argparse
import logging
from pathlib import Path

# 确保模块路径
sys.path.insert(0, str(Path(__file__).parent))

from workflow_manager import WorkflowManager


def main():
    parser = argparse.ArgumentParser(description="AI Agent Deck Manager")
    parser.add_argument("--scan", action="store_true", help="扫描 BLE 设备")
    parser.add_argument("--ble", action="store_true", help="使用 BLE 通信")
    parser.add_argument("--port", type=str, help="指定串口号 (如 COM3)")
    parser.add_argument("--no-ble", dest="no_ble", action="store_true", help="离线模式")
    parser.add_argument("--cli", action="store_true", help="命令行模式 (无 GUI)")
    parser.add_argument("--debug", action="store_true", help="调试日志")
    args = parser.parse_args()

    # 日志
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="[%(asctime)s] %(message)s",
        datefmt="%H:%M:%S"
    )

    if args.scan:
        _scan_devices()
        return

    # 创建工作流管理器 (默认使用串口)
    use_ble = args.ble
    manager = WorkflowManager(use_ble=use_ble, com_port=args.port)

    # 信号处理
    def signal_handler(sig, frame):
        manager.stop()
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)

    if args.no_ble:
        print("[Main] 离线模式: 仅窗口检测 + Profile 切换")
        manager.detector.on_change(lambda new, old: _print_profile(manager, new))
        manager.detector.start()
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            manager.detector.stop()
    elif args.cli:
        # 命令行模式
        manager.run_forever()
    else:
        # GUI 模式
        _run_gui(manager)


def _print_profile(manager, app):
    """离线模式下打印 Profile"""
    profile = manager.profiles.get_profile_by_process(app.process_name)
    if profile:
        print(f"\n{'='*40}")
        print(f"  {profile.name}")
        print(f"{'='*40}")
        for k in profile.keys:
            print(f"  {k.id}: {k.display}")
        print(f"{'='*40}")


def _run_gui(manager=None):
    """运行 GUI 模式"""
    try:
        from gui.app import AI_Deck_App

        print("[Main] 启动 GUI 应用程序...")

        # 创建应用程序
        app = AI_Deck_App()

        # 运行应用程序
        app.run()

    except ImportError as e:
        print(f"[Main] GUI 依赖缺失: {e}")
        print("[Main] 回退到命令行模式...")
        if manager:
            manager.run_forever()
    except Exception as e:
        print(f"[Main] GUI 启动失败: {e}")
        if manager:
            manager.stop()


def _scan_devices():
    """扫描 BLE 设备"""
    import asyncio
    from bleak import BleakScanner

    async def scan():
        print("[Scan] 正在扫描 BLE 设备...\n")
        devices = await BleakScanner.discover(timeout=10.0)
        if not devices:
            print("[Scan] 未找到设备")
            return

        for d in devices:
            name = d.name or "(未知)"
            print(f"  {name:<30} [{d.address}]")

        print(f"\n[Scan] 共找到 {len(devices)} 个设备")

    asyncio.run(scan())


if __name__ == "__main__":
    main()
