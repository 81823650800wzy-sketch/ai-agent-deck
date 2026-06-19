#!/usr/bin/env python3
"""
测试崩溃处理器
运行此脚本验证崩溃捕获功能
"""

import sys
import threading
import time

# 添加项目路径
sys.path.insert(0, ".")

from app.utils.crash_handler import setup_crash_handler, manual_crash_report, get_crash_dir


def test_manual_crash_report():
    """测试手动崩溃报告"""
    print("\n[测试1] 手动崩溃报告")
    manual_crash_report("测试手动崩溃报告功能")
    print("  -> 崩溃报告已生成，请检查:", get_crash_dir())


def test_unhandled_exception():
    """测试未处理异常捕获"""
    print("\n[测试2] 未处理异常捕获")
    print("  -> 即将触发 ZeroDivisionError...")
    # 这个会被 sys.excepthook 捕获
    1 / 0


def test_thread_exception():
    """测试线程异常捕获"""
    print("\n[测试3] 线程异常捕获")

    def worker():
        time.sleep(0.5)
        raise ValueError("线程中的测试异常")

    t = threading.Thread(target=worker, name="TestThread")
    t.start()
    print("  -> 等待线程异常...")
    t.join()


def main():
    print("=" * 60)
    print("AI Agent Deck - 崩溃处理器测试")
    print("=" * 60)

    # 安装崩溃处理器
    setup_crash_handler()
    print("\n崩溃处理器已安装")
    print("崩溃报告目录:", get_crash_dir())

    # 测试1: 手动崩溃报告
    test_manual_crash_report()

    # 询问是否继续测试
    print("\n" + "-" * 60)
    choice = input("是否继续测试未处理异常捕获？(y/n): ").strip().lower()
    if choice == 'y':
        # 测试2: 未处理异常
        test_unhandled_exception()
        # 如果上面没有退出，继续测试3
        test_thread_exception()

    print("\n测试完成")


if __name__ == "__main__":
    main()