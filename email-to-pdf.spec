# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\admin\\AppData\\Local\\ms-playwright\\chromium-1217', 'playwright-browsers/chromium-1217'), ('C:\\Users\\admin\\AppData\\Local\\ms-playwright\\chromium_headless_shell-1217', 'playwright-browsers/chromium_headless_shell-1217'), ('C:\\Users\\admin\\AppData\\Local\\ms-playwright\\ffmpeg-1011', 'playwright-browsers/ffmpeg-1011')],
    hiddenimports=['win32com', 'win32com.client', 'pythoncom', 'pywintypes', 'win32timezone', 'playwright', 'rich', 'rich.prompt'],
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
    a.binaries,
    a.datas,
    [],
    name='email-to-pdf',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
