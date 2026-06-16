"""
AI Agent Deck - GUI Manager
"""

import json
import os
import sys
import subprocess
import threading
from pathlib import Path
from datetime import datetime

try:
    import tkinter as tk
    from tkinter import ttk
except ImportError:
    print("tkinter not available")
    sys.exit(1)

try:
    from pynput import keyboard
except ImportError:
    print("Please install pynput: pip install pynput")
    sys.exit(1)

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
    CONFIG_FILE = Path(os.path.dirname(sys.executable)) / "config.json"
else:
    BASE_DIR = Path(__file__).parent
    CONFIG_FILE = BASE_DIR / "config.json"

SCRIPTS_DIR = Path(os.path.dirname(CONFIG_FILE)) / "scripts"


class AIDeckGUI:
    def __init__(self):
        self.config = self.load_config()
        self.listener = None
        self.listening = False
        self.status_labels = {}

        SCRIPTS_DIR.mkdir(exist_ok=True)

        self.root = tk.Tk()
        self.root.title("AI Agent Deck Manager")
        self.root.geometry("700x500")
        self.root.configure(bg='#1a1a2e')

        self.colors = {
            'bg': '#1a1a2e',
            'card': '#252540',
            'accent': '#f0833a',
            'green': '#48c78e',
            'red': '#ef4444',
            'yellow': '#f59e0b',
            'purple': '#8b5cf6',
            'blue': '#3b82f6',
            'text': '#e0e0f0',
            'dim': '#6b7280'
        }

        self.create_widgets()

    def load_config(self):
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"keys": {}}

    def create_widgets(self):
        main = tk.Frame(self.root, bg=self.colors['bg'])
        main.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Title
        title_frame = tk.Frame(main, bg=self.colors['bg'])
        title_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(title_frame, text="AI Agent Deck Manager",
                font=('Segoe UI', 16, 'bold'),
                bg=self.colors['bg'], fg=self.colors['accent']).pack(side=tk.LEFT)

        self.status_label = tk.Label(title_frame, text="Disconnected",
                                    font=('Segoe UI', 10),
                                    bg=self.colors['bg'], fg=self.colors['dim'])
        self.status_label.pack(side=tk.RIGHT)

        # Info
        info = tk.Frame(main, bg=self.colors['card'])
        info.pack(fill=tk.X, pady=(0, 15))
        tk.Label(info, text="Device: AI Agent Deck  |  BLE HID Keyboard  |  Keys: a-f",
                font=('Segoe UI', 9), bg=self.colors['card'], fg=self.colors['dim']).pack(padx=10, pady=8)

        # Key mappings
        tk.Label(main, text="Key Mappings",
                font=('Segoe UI', 11, 'bold'),
                bg=self.colors['bg'], fg=self.colors['text']).pack(anchor=tk.W, pady=(0, 8))

        keys_frame = tk.Frame(main, bg=self.colors['bg'])
        keys_frame.pack(fill=tk.X, pady=(0, 15))

        key_colors = [self.colors['green'], self.colors['purple'], self.colors['blue'],
                     self.colors['yellow'], self.colors['red'], self.colors['dim']]

        for i, (key, config) in enumerate(self.config.get('keys', {}).items()):
            row = i // 3
            col = i % 3

            card = tk.Frame(keys_frame, bg=self.colors['card'])
            card.grid(row=row, column=col, padx=5, pady=5, sticky='nsew')
            keys_frame.grid_columnconfigure(col, weight=1)

            color_bar = tk.Frame(card, bg=key_colors[i % len(key_colors)], height=3)
            color_bar.pack(fill=tk.X)

            content = tk.Frame(card, bg=self.colors['card'])
            content.pack(fill=tk.BOTH, padx=8, pady=8)

            tk.Label(content, text=f"Key: {key}",
                    font=('Segoe UI', 8), bg=self.colors['card'], fg=self.colors['dim']).pack(anchor=tk.W)

            tk.Label(content, text=config.get('name', key),
                    font=('Segoe UI', 12, 'bold'),
                    bg=self.colors['card'], fg=key_colors[i % len(key_colors)]).pack(anchor=tk.W)

            status = tk.Label(content, text="Ready",
                            font=('Segoe UI', 8), bg=self.colors['card'], fg=self.colors['dim'])
            status.pack(anchor=tk.W)
            self.status_labels[key] = status

        # Controls
        ctrl = tk.Frame(main, bg=self.colors['bg'])
        ctrl.pack(fill=tk.X, pady=(0, 15))

        self.start_btn = tk.Button(ctrl, text="Start Listening",
                                  command=self.start_listening,
                                  bg=self.colors['green'], fg='white',
                                  font=('Segoe UI', 10, 'bold'),
                                  relief=tk.FLAT, padx=15, pady=5)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.stop_btn = tk.Button(ctrl, text="Stop",
                                 command=self.stop_listening,
                                 bg=self.colors['red'], fg='white',
                                 font=('Segoe UI', 10, 'bold'),
                                 relief=tk.FLAT, padx=15, pady=5,
                                 state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(ctrl, text="Edit Config",
                 command=lambda: os.startfile(str(CONFIG_FILE)),
                 bg=self.colors['card'], fg=self.colors['text'],
                 font=('Segoe UI', 10), relief=tk.FLAT, padx=10, pady=5).pack(side=tk.LEFT)

        # Log
        tk.Label(main, text="Log",
                font=('Segoe UI', 11, 'bold'),
                bg=self.colors['bg'], fg=self.colors['text']).pack(anchor=tk.W, pady=(0, 5))

        log_frame = tk.Frame(main, bg=self.colors['card'])
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_frame, bg=self.colors['card'], fg=self.colors['text'],
                               font=('Consolas', 9), wrap=tk.WORD, height=6)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.log("Manager started")
        self.log(f"Config: {CONFIG_FILE}")

    def log(self, msg):
        time_str = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{time_str}] {msg}\n")
        self.log_text.see(tk.END)

    def start_listening(self):
        if not self.listening:
            self.listening = True
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.status_label.config(text="Listening...", fg=self.colors['green'])

            self.listener = keyboard.Listener(on_press=self.on_key_press)
            self.listener.start()

            self.log("Listening for keys...")

    def stop_listening(self):
        if self.listening:
            self.listening = False
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.status_label.config(text="Disconnected", fg=self.colors['dim'])

            if self.listener:
                self.listener.stop()
                self.listener = None

            self.log("Stopped")

    def on_key_press(self, key):
        try:
            if hasattr(key, 'char') and key.char:
                key_name = key.char
            elif hasattr(key, 'name'):
                key_name = key.name
            else:
                return

            self.root.after(0, self.handle_key, key_name)
        except:
            pass

    def handle_key(self, key_name):
        self.log(f"Key: {key_name}")

        key_config = self.config.get('keys', {}).get(key_name)
        if key_config:
            name = key_config.get('name', key_name)
            self.log(f"  -> {name}")

            if key_name in self.status_labels:
                self.status_labels[key_name].config(text="Active", fg=self.colors['green'])
                self.root.after(1000, lambda: self.status_labels[key_name].config(text="Ready", fg=self.colors['dim']))

            threading.Thread(target=self.execute, args=(key_config,), daemon=True).start()

    def execute(self, config):
        action = config.get('action')
        try:
            if action == 'command':
                cmd = config.get('command')
                if cmd:
                    subprocess.Popen(cmd, shell=True)
            elif action == 'script':
                script = config.get('script')
                if script:
                    path = SCRIPTS_DIR / script
                    if path.exists():
                        subprocess.Popen(str(path), shell=True)
            elif action == 'open_url':
                url = config.get('url')
                if url:
                    os.startfile(url)
        except Exception as e:
            self.root.after(0, self.log, f"Error: {e}")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = AIDeckGUI()
    app.run()
