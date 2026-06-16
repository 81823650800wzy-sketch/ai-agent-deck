# AI Agent Deck Manager - Complete Guide

## Overview

This system consists of two parts:
1. **ESP32 Device** - Sends F13-F18 key signals via BLE HID
2. **PC Manager** - Listens for these keys and executes actions

## Step-by-Step Setup

### Step 1: Flash Device Firmware

The device firmware has already been flashed. It sends F13-F18 keys when buttons are pressed.

### Step 2: Pair Bluetooth

1. Open Windows Settings (Win + I)
2. Go to **Bluetooth & devices**
3. Click **Add device** → **Bluetooth**
4. Find **AI Agent Deck** and click to pair
5. Wait for pairing to complete

### Step 3: Test Key Detection

Before using the manager, test if keys are being received:

```bash
python test_keys.py
```

Then press buttons on the device. You should see:
```
Key pressed: f13 (KeyCode.f13)
  >>> MATCH: F13 detected!
```

**If no keys appear:**
- Check Bluetooth connection
- Restart the device
- Re-pair the device

### Step 4: Run Manager

```bash
python ai_deck_gui.py
```

Or run the exe:
```
dist\AI_Deck_Manager.exe
```

### Step 5: Configure Actions

Edit `config.json` to customize what each key does:

```json
{
    "keys": {
        "F13": {
            "name": "ChatGPT",
            "action": "command",
            "command": "start chrome https://chat.openai.com"
        },
        "F14": {
            "name": "Claude",
            "action": "command",
            "command": "start cmd /k \"echo Starting Claude...\""
        }
    }
}
```

## Action Types

### 1. Command
Execute a system command:
```json
{
    "action": "command",
    "command": "notepad"
}
```

### 2. Script
Run a batch file:
```json
{
    "action": "script",
    "script": "my_script.bat"
}
```

### 3. Open URL
Open a website:
```json
{
    "action": "open_url",
    "url": "https://chat.openai.com"
}
```

### 4. Open App
Launch an application:
```json
{
    "action": "open_app",
    "path": "C:\\Program Files\\Cursor\\cursor.exe"
}
```

## Example: Open Claude via CMD

To open Claude by typing in cmd:

1. Create script `scripts/open_claude.bat`:
```bat
@echo off
start cmd /k "cd /d %USERPROFILE% && claude"
```

2. Configure in `config.json`:
```json
{
    "F14": {
        "name": "Claude",
        "action": "script",
        "script": "open_claude.bat"
    }
}
```

## Troubleshooting

### No keys detected

1. Check if device is paired in Bluetooth settings
2. Run `test_keys.py` to verify key reception
3. Check device serial output for errors

### Keys detected but no action

1. Check `config.json` syntax
2. Verify script files exist in `scripts/` folder
3. Check Windows permissions

### Connection drops

1. Keep device within 10 meters
2. Avoid WiFi interference
3. Check battery level

## File Structure

```
Manager/
├── ai_deck_gui.py      # Main GUI application
├── config.json         # Key mappings config
├── test_keys.py        # Key detection test
├── scripts/            # Action scripts
│   ├── open_claude.bat
│   └── ...
└── dist/               # Compiled exe
    ├── AI_Deck_Manager.exe
    ├── config.json
    └── scripts/
```

## Quick Start Commands

```bash
# Test key detection
python test_keys.py

# Run GUI manager
python ai_deck_gui.py

# Build exe
pyinstaller --onefile --windowed --name "AI_Deck_Manager" --add-data "config.json;." --add-data "scripts;scripts" ai_deck_gui.py
```
