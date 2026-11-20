"""Unit and integration tests for Windows Metadata and Code Signing pipelines.

Validates that:
1. Version info resources generated for Onedir and Portable builds match pyproject.toml author.
2. PyInstaller spec files properly link version resource files.
3. mathweave-studio-onefile.spec prioritizes existing signed onedir native binaries.
4. Code signing script strictly fails on production mode when credentials are missing.
5. Code signing script produces unsigned development build by default without credentials.
6. Target critical binaries (libcrypto-3-x64.dll and Portable EXE) are tracked.
"""

from __future__ import annotations

import importlib.util
import re
import sys
import tempfile
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from build_tools.generate_version_info import (  # noqa: E402
    generate_version_text,
    get_project_author,
    get_project_version,
    parse_version_tuple,
)


def load_sign_module():
    script_path = ROOT_DIR / ".github" / "scripts" / "sign_windows_binaries.py"
    spec = importlib.util.spec_from_file_location("sign_windows_binaries", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_project_version_and_author_extraction() -> None:
    version = get_project_version()
    assert re.match(r"^\d+\.\d+\.\d+", version)
    author = get_project_author()
    assert author == "TqvNoCode"


def test_parse_version_tuple() -> None:
    assert parse_version_tuple("0.1.1") == (0, 1, 1, 0)
    assert parse_version_tuple("1.2.3.4") == (1, 2, 3, 4)
    assert parse_version_tuple("2.0") == (2, 0, 0, 0)


def test_generate_version_text_contents() -> None:
    ver_tuple = (0, 1, 1, 0)
    text = generate_version_text(
        file_version_tuple=ver_tuple,
        product_version_tuple=ver_tuple,
        file_description="MathWeave Studio - Test",
        internal_name="mathweave-test",
        original_filename="mathweave-test.exe",
    )

    assert "VSVersionInfo(" in text
    assert "ffi=FixedFileInfo(" in text
    assert "filevers=(0, 1, 1, 0)" in text
    assert "StringStruct('CompanyName', 'TqvNoCode')" in text
    assert "StringStruct('FileDescription', 'MathWeave Studio - Test')" in text
    assert "StringStruct('FileVersion', '0.1.1.0')" in text
    assert "StringStruct('LegalCopyright', 'Copyright (C) 2026 TqvNoCode. All rights reserved.')" in text
    assert "StringStruct('OriginalFilename', 'mathweave-test.exe')" in text
    assert "VarFileInfo([VarStruct('Translation', [1033, 1200])])" in text


def test_spec_files_contain_version_attribute_and_binary_staging() -> None:
    onedir_spec = ROOT_DIR / "mathweave-studio.spec"
    portable_spec = ROOT_DIR / "mathweave-studio-onefile.spec"

    assert onedir_spec.is_file()
    assert portable_spec.is_file()

    onedir_content = onedir_spec.read_text(encoding="utf-8")
    assert "version=" in onedir_content
    assert "version_info_onedir.txt" in onedir_content
    assert "upx=False" in onedir_content
    assert "upx=True" not in onedir_content

    portable_content = portable_spec.read_text(encoding="utf-8")
    assert "version=" in portable_content
    assert "version_info_portable.txt" in portable_content
    assert "upx=False" in portable_content
    assert "upx=True" not in portable_content
    assert "onedir_internal = os.path.join(onedir_base, \"_internal\")" in portable_content


def test_production_signing_fails_without_credentials() -> None:
    mod = load_sign_module()
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        onedir = tmp_dir / "dist" / "mathweave-studio"
        onedir.mkdir(parents=True)
        portable_exe = tmp_dir / "dist" / "MathWeave-Studio-Portable.exe"
        portable_exe.write_bytes(b"MZ" + b"\x00" * 100)

        with pytest.raises(RuntimeError) as exc_info:
            mod.sign_distributions(onedir, portable_exe, mode="production", require_signing=True)

        assert "Production code signing was explicitly requested" in str(exc_info.value)
        assert "Self-signed fallback is disabled" in str(exc_info.value)


def test_auto_signing_produces_unsigned_dev_without_credentials() -> None:
    mod = load_sign_module()
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        onedir = tmp_dir / "dist" / "mathweave-studio"
        onedir.mkdir(parents=True)
        portable_exe = tmp_dir / "dist" / "MathWeave-Studio-Portable.exe"
        portable_exe.write_bytes(b"MZ" + b"\x00" * 100)

        result = mod.sign_distributions(onedir, portable_exe, mode="auto", require_signing=False, dry_run=True)
        assert result is False  # False indicates unsigned dev build


def test_signing_script_handles_test_pipeline_mode() -> None:
    mod = load_sign_module()
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        onedir = tmp_dir / "dist" / "mathweave-studio"
        internal_dir = onedir / "_internal"
        internal_dir.mkdir(parents=True)

        # Create dummy PE targets
        (onedir / "mathweave-studio.exe").write_bytes(b"MZ" + b"\x00" * 100)
        (internal_dir / "libcrypto-3-x64.dll").write_bytes(b"MZ" + b"\x00" * 100)
        portable_exe = tmp_dir / "dist" / "MathWeave-Studio-Portable.exe"
        portable_exe.write_bytes(b"MZ" + b"\x00" * 100)

        result = mod.sign_distributions(onedir, portable_exe, mode="test-pipeline", allow_test_cert=True, dry_run=True)
        assert result is True
