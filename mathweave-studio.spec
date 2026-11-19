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

for pkg in ["nicegui", "plotly", "latex2mathml"]:
    datas += collect_data_files(pkg)
    hiddenimports += collect_submodules(pkg)

hiddenimports += collect_submodules("math_app")
datas += [(assets_dir, "assets")]

datas += collect_data_files("webview")
binaries += collect_dynamic_libs("webview")
hiddenimports += collect_submodules("webview")

for pkg in ["pythonnet", "clr_loader"]:
    try:
        pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
        datas += pkg_datas
        binaries += pkg_binaries
        hiddenimports += pkg_hidden
    except Exception:
        pass

if sys.platform.startswith("linux"):
    for pkg in ["PyQt6"]:
        try:
            pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
            datas += pkg_datas
            binaries += pkg_binaries
            hiddenimports += pkg_hidden
        except Exception:
            pass

hiddenimports += [
    "uvicorn",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    "wsproto",
    "clr",
    "pythonnet",
    "clr_loader",
    "clr_loader.ffi",
    "webview.platforms.winforms",
    "webview.platforms.edgechromium",
    "webview.platforms.win32",
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
    [],
    exclude_binaries=True,
    name="mathweave-studio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=icon_path,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="mathweave-studio",
)
