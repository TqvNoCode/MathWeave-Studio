# -*- mode: python ; coding: utf-8 -*-

import os
import sys
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
version_file = os.path.join(project_dir, "build_tools", "version_info_portable.txt")

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
datas += collect_data_files("math_app")

# Pywebview and webview backend
try:
    pkg_datas, pkg_binaries, pkg_hidden = collect_all("webview")
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden
except Exception:
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

for pkg in ["PyQt6"]:
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
    "engineio.async_drivers.asgi",
    "socketio.async_drivers.asgi",
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

# Prioritize using signed native binaries from existing onedir distribution
# to ensure embedded dependencies inside Portable Onefile are individually signed
onedir_base = os.path.join(project_dir, "dist", "mathweave-studio")
onedir_internal = os.path.join(onedir_base, "_internal")
if os.path.isdir(onedir_internal) or os.path.isdir(onedir_base):
    staged_binaries = []
    for item in a.binaries:
        dest_name, src_path, btype = item[0], item[1], item[2]
        base_name = os.path.basename(dest_name)
        cand_internal = os.path.join(onedir_internal, base_name)
        cand_root = os.path.join(onedir_base, base_name)
        if os.path.isfile(cand_internal):
            staged_binaries.append((dest_name, cand_internal, btype))
        elif os.path.isfile(cand_root):
            staged_binaries.append((dest_name, cand_root, btype))
        else:
            staged_binaries.append(item)
    a.binaries = staged_binaries

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="MathWeave-Studio-Portable",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
    version=version_file if os.path.exists(version_file) else None,
)
