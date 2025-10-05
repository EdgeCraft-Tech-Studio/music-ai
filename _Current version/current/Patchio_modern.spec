# -*- mode: python ; coding: utf-8 -*-
import plistlib
import os

# Load your custom Info.plist as a dict
with open('builds/build_config/custom_info.plist', 'rb') as f:
    custom_plist = plistlib.load(f)

# Build directories are specified via command-line options:
# --distpath builds/dist --workpath builds/build

a = Analysis(
    ['patchio_main.py'],  # New entry point for modern MVC app
    pathex=[],
    binaries=[],
    datas=[
        ('assets/icons/pistachio.png', '.'),
        ('assets/docs/about.txt', '.'),
        ('assets/docs/PatchIO_Manual.pdf', '.'),
        ('views/patchio_current_ui.ui', 'views/'),
        ('settings/core_settings.py', 'settings/'),
        ('models/', 'models/'),
        ('controllers/', 'controllers/'),
        ('views/', 'views/'),
        ('assets/icons/', 'assets/icons/'),
        ('assets/docs/', 'assets/docs/'),
    ],
    hiddenimports=[
        'PySide6.QtWidgets',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtUiTools',
        'models.settings_model',
        'models.search_model',
        'models.file_model',
        'controllers.main_controller',
        'controllers.search_controller',
        'views.main_window',
        'settings.core_settings',
        'mvc_patchio_loader',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Patchio',
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
    icon=['assets/icons/icon.icns'],  # your app icon file
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Patchio',
)

app = BUNDLE(
    coll,
    name='PatchIO.app',
    icon='assets/icons/icon.icns',
    info_plist=custom_plist,  # add your custom plist here
    bundle_identifier=None,
) 