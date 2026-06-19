# -*- mode: python ; coding: utf-8 -*-
"""
AI Agent Deck Manager - PyInstaller 打包配置
版本: 2.1.0
"""

from pathlib import Path

base_dir = Path(SPECPATH)

a = Analysis(
    ['run_app.py'],
    pathex=[str(base_dir)],
    binaries=[],
    datas=[
        (str(base_dir / 'profiles'), 'profiles'),
        (str(base_dir / 'firmware'), 'firmware'),
    ],
    hiddenimports=[
        # Windows API
        'pywin32',
        'win32gui',
        'win32process',
        # 进程监控
        'psutil',
        # 键盘监听
        'pynput',
        'pynput.keyboard',
        'pynput.mouse',
        # BLE 通信
        'bleak',
        'bleak.backends',
        'bleak.backends.winrt',
        # PyQt5 GUI
        'PyQt5',
        'PyQt5.QtWidgets',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.sip',
        # 图像处理
        'PIL',
        'PIL.Image',
        # 串口通信
        'serial',
        'serial.tools',
        'serial.tools.list_ports',
        # ESP32 烧录
        'esptool',
        'esptool.cmds',
        # WiFi 发现
        'zeroconf',
        # 应用模块
        'app.core',
        'app.ui',
        'app.utils',
        'app.data',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'cv2',
        'torch',
        'tensorflow',
        'IPython',
        'jupyter',
        'pytest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AI_Deck_Manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可替换为 .ico 文件路径
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AI_Deck_Manager',
)
