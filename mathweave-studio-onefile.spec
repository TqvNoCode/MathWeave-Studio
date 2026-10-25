# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import (
    collect_all,
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)

block_cipher = None

# Base directory of the project, resolved from spec file location
project_dir = SPECPATH
assets_dir = os.path.join(project_dir, "assets")
icon_path = os.path.join(assets_dir, "icon.ico")

datas = []
binaries = []
hiddenimports = []

# Core UI and rendering packages
for pkg in ["nicegui", "plotly", "latex2mathml"]:
    datas += collect_data_files(pkg)
    hiddenimports += collect_submodules(pkg)

# Application modules and assets
hiddenimports += collect_submodules("math_app")
datas += [(assets_dir, "assets")]

# Pywebview and webview backend
datas += collect_data_files("webview")
binaries += collect_dynamic_libs("webview")
hiddenimports += collect_submodules("webview")

# Windows-specific native dependencies (pythonnet, clr_loader)
for pkg in ["pythonnet", "clr_loader"]:
    try:
        pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
        datas += pkg_datas
        binaries += pkg_binaries
        hiddenimports += pkg_hidden
    except Exception:
        pass

hiddenimports += [
    # ASGI and WebSocket server
    "uvicorn",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    "wsproto",
    # Windows pywebview native backend (.NET / WinForms / WebView2)
    "clr",
    "pythonnet",
    "clr_loader",
    "clr_loader.ffi",
    "webview.platforms.winforms",
    "webview.platforms.edgechromium",
    "webview.platforms.win32",
    # Platform fallback
    "qtpy",
]

a = Analysis(
    [os.path.join(project_dir, "run.py")],
    pathex=[os.path.join(project_dir, "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib.tests", "scipy", "pytest", "pytest_cov"],
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
    name="MathWeaveStudio-Beta",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Kept True for beta debugging diagnostics
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)
