"""
测试按键监听 - 用于验证 F13-F18 是否能被接收
"""

from pynput import keyboard
import sys

print("=" * 50)
print("  AI Agent Deck - Key Test")
print("=" * 50)
print()
print("Waiting for F13-F18 keys...")
print("Press Ctrl+C to exit")
print()

def on_press(key):
    try:
        if hasattr(key, 'name'):
            name = key.name
        elif hasattr(key, 'char'):
            name = key.char
        else:
            name = str(key)

        print(f"Key pressed: {name} ({key})")

        # Check for F13-F18
        f_keys = ['f13', 'f14', 'f15', 'f16', 'f17', 'f18']
        if name and name.lower() in f_keys:
            print(f"  >>> MATCH: {name.upper()} detected!")

    except Exception as e:
        print(f"Error: {e}")

# Start listening
with keyboard.Listener(on_press=on_press) as listener:
    try:
        listener.join()
    except KeyboardInterrupt:
        print("\nExiting...")
