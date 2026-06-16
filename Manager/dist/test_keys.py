from pynput import keyboard

print("=" * 50)
print("  Key Test - Press any key")
print("  Press Ctrl+C to exit")
print("=" * 50)

def on_press(key):
    try:
        if hasattr(key, 'char') and key.char:
            print(f"Key: {key.char}")
        elif hasattr(key, 'name'):
            print(f"Key: {key.name}")
    except:
        pass

with keyboard.Listener(on_press=on_press) as listener:
    listener.join()
