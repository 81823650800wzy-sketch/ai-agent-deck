# -*- mode: python ; coding: utf-8 -*-
"""
AI Agent Deck Manager - PyInstaller 打包配置
版本: 2.1.0
"""

import sys
from pathlib import Path

block_cipher = None
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
        'pywin32',
        'win32gui',
        'win32process',
        'psutil',
        'pynput',
        'pynput.keyboard',
        'pynput.mouse',
        'bleak',
        'bleak.backends',
        'bleak.backends.winrt',
        'PyQt5',
        'PyQt5.QtWidgets',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.sip',
        'PIL',
        'PIL.Image',
        'serial',
        'serial.tools',
        'serial.tools.list_ports',
        'esptool',
        'zeroconf',
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
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

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
