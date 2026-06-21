# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for File Cleaner
# Usage: pyinstaller file_cleaner.spec

import sys
import os
from pathlib import Path

block_cipher = None

a = Analysis(
    ['cleaner_app.py'],
    pathex=[str(Path('.').resolve())],
    binaries=[],
    datas=[],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'pathlib',
        'threading',
        'queue',
        'shutil',
        'json',
        'config.settings',
        'config.manager',
        'core.scanner',
        'core.matcher',
        'core.deleter',
        'core.models',
        'workers.scan_worker',
        'workers.delete_worker',
        'ui.app',
        'ui.widgets',
        'ui.left_panel',
        'ui.right_panel',
        'ui.dialogs',
        'services.import_export',
        'services.path_history',
        'utils.file_utils',
        'utils.formatters',
        'utils.logger',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['numpy', 'pandas', 'matplotlib', 'scipy', 'PIL'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FileCleaner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # No terminal window on Windows
    disable_windowed_traceback=False,
    argv_emulation=False,    # macOS: don't emulate argv
    target_arch=None,        # 'x86_64' / 'arm64' / 'universal2' for macOS
    codesign_identity=None,
    entitlements_file=None,
    # icon='assets/icon.ico',  # Uncomment and add icon file
)

# macOS: wrap in .app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='FileCleaner.app',
        icon=None,           # 'assets/icon.icns' if you have one
        bundle_identifier='com.yourname.filecleaner',
        info_plist={
            'CFBundleName': 'File Cleaner',
            'CFBundleDisplayName': 'File Cleaner',
            'CFBundleVersion': '1.0.0',
            'CFBundleShortVersionString': '1.0.0',
            'NSHighResolutionCapable': True,
            'NSRequiresAquaSystemAppearance': False,
        },
    )
