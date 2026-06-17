"""
AI Agent Deck - 端到端链路测试
验证: 窗口检测 → Profile 匹配 → (模拟) 发送
"""

import sys
import time
sys.stdout.reconfigure(encoding='utf-8')

from window_detector import WindowDetector
from profile_manager import ProfileManager


def test_full_chain():
    print("=" * 50)
    print("  AI Agent Deck - 链路测试")
    print("=" * 50)

    # 初始化
    detector = WindowDetector(poll_interval=0.5)
    profiles = ProfileManager()

    # 1. 检测当前窗口
    print("\n[1] 窗口检测...")
    app = detector.get_current_application()
    if not app:
        print("  ❌ 无法检测当前窗口")
        return False

    print(f"  ✅ 进程: {app.process_name}")
    print(f"  ✅ 标题: {app.window_title[:50]}")

    # 2. 匹配 Profile
    print("\n[2] Profile 匹配...")
    profile = profiles.get_profile_by_process(app.process_name)
    if not profile:
        print(f"  ⚠️ 无匹配 Profile: {app.process_name}")
        return False

    print(f"  ✅ 匹配: {profile.name}")
    print(f"  ✅ 按键映射:")
    for k in profile.keys:
        print(f"     {k.id}: {k.display} → {k.action}")

    # 3. 模拟发送到 ESP32
    print("\n[3] 模拟 BLE 发送...")
    import json
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
    print(f"  ✅ JSON 大小: {len(json_str)} 字节")
    print(f"  ✅ 内容预览: {json_str[:80]}...")

    # 4. 模拟 ESP32 收到后的显示
    print("\n[4] ESP32 显示预览:")
    print("  ┌──────────────────────┐")
    print(f"  │ {profile.name:<20} │")
    print("  ├──────────────────────┤")
    for k in profile.keys:
        print(f"  │ {k.id} {k.display:<18} │")
    print("  └──────────────────────┘")

    # 5. 模拟按键切换
    print("\n[5] 模拟应用切换...")
    test_apps = ["blender.exe", "kicad.exe", "chrome.exe", "Code.exe", "unknown.exe"]
    for test_app in test_apps:
        p = profiles.get_profile_by_process(test_app)
        name = p.name if p else "None"
        print(f"  {test_app:<20} → {name}")

    print("\n" + "=" * 50)
    print("  ✅ 链路测试通过!")
    print("=" * 50)
    return True


def test_window_monitor(duration: int = 10):
    """实时监控窗口切换"""
    print(f"\n实时监控 ({duration}秒)...")
    print("切换窗口观察 Profile 变化:\n")

    detector = WindowDetector(poll_interval=0.3)
    profiles = ProfileManager()
    last_profile = None

    def on_change(new_app, old_app):
        nonlocal last_profile
        profile = profiles.get_profile_by_process(new_app.process_name)
        if profile and profile != last_profile:
            last_profile = profile
            keys_str = " | ".join(f"{k.id}:{k.display}" for k in profile.keys[:3])
            print(f"  [{new_app.process_name}] → {profile.name}: {keys_str}...")

    detector.on_change(on_change)
    detector.start()
    time.sleep(duration)
    detector.stop()


if __name__ == "__main__":
    if "--monitor" in sys.argv:
        test_window_monitor(15)
    else:
        test_full_chain()
