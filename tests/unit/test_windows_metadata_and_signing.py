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


def test_inno_setup_installer_script_configuration() -> None:
    iss_path = ROOT_DIR / "installer" / "MathWeave-Studio.iss"
    assert iss_path.is_file(), f"Missing Inno Setup script at {iss_path}"

    content = iss_path.read_text(encoding="utf-8")
    assert "AppId={{780F209D-79B0-498A-84EB-77A1ED4765E4}" in content
    assert 'MyAppPublisher "TqvNoCode"' in content
    assert 'MyAppName "MathWeave Studio"' in content
    assert "ArchitecturesAllowed=x64compatible\n" in content
    assert "ArchitecturesAllowed=x64compatible x64" not in content
    assert "ArchitecturesInstallIn64BitMode=x64compatible\n" in content
    assert "ArchitecturesInstallIn64BitMode=x64compatible x64" not in content
    assert "CloseApplications=yes" in content
    assert "CloseApplicationsTimeout" not in content
    assert "Compression=lzma2/max" in content
    assert "SolidCompression=yes" in content
    assert r"SetupIconFile=..\assets\icon.ico" in content
    assert r"DefaultDirName={autopf}\{#MyAppName}" in content

    # Verify redundant shortcut IconFilename is removed
    assert 'IconFilename: "{app}\\assets\\icon.ico"' not in content
    assert 'Name: "{autoprograms}\\{#MyAppName}\\{#MyAppName}"; Filename: "{app}\\{#MyAppExeName}"\n' in content
    assert 'Name: "{autodesktop}\\{#MyAppName}"; Filename: "{app}\\{#MyAppExeName}"; Tasks: desktopicon\n' in content



def test_signing_script_handles_installer_exe() -> None:
    mod = load_sign_module()
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        onedir = tmp_dir / "dist" / "mathweave-studio"
        internal_dir = onedir / "_internal"
        internal_dir.mkdir(parents=True)

        (onedir / "mathweave-studio.exe").write_bytes(b"MZ" + b"\x00" * 100)
        (internal_dir / "libcrypto-3-x64.dll").write_bytes(b"MZ" + b"\x00" * 100)
        portable_exe = tmp_dir / "dist" / "MathWeave-Studio-Portable.exe"
        portable_exe.write_bytes(b"MZ" + b"\x00" * 100)
        installer_exe = tmp_dir / "dist" / "MathWeave-Studio-Setup-Unsigned-Dev.exe"
        installer_exe.write_bytes(b"MZ" + b"\x00" * 100)

        result = mod.sign_distributions(
            onedir,
            portable_exe,
            installer_exe=installer_exe,
            mode="test-pipeline",
            allow_test_cert=True,
            dry_run=True,
        )
        assert result is True


def test_startup_winforms_patch_safe_import() -> None:
    from math_app.presentation.startup import (
        _execute_native_patch_in_child,
        patch_pywebview_winforms,
    )

    # Must execute safely without raising exceptions in Linux/headless environment
    patch_pywebview_winforms()
    hook = _execute_native_patch_in_child()
    assert hook is not None


def test_github_actions_workflow_node24_pinned_actions() -> None:
    workflow_path = ROOT_DIR / ".github" / "workflows" / "windows-build.yml"
    assert workflow_path.is_file()

    content = workflow_path.read_text(encoding="utf-8")
    assert "actions/checkout@v4" not in content
    assert "actions/upload-artifact@v4" not in content
    assert "astral-sh/setup-uv@v5" not in content

    # Node 24 verified full commit SHAs with version comments
    assert "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1 (node24)" in content
    assert "astral-sh/setup-uv@68559e99cc807c1eb7e9238fd43a15bba460eec2 # v10.3.3 (node24)" in content
    assert "actions/upload-artifact@b7c566a772e6b6bfb58ed0dc250532a479d7789f # v6.0.0 (node24)" in content


def test_github_actions_workflow_notices_and_job_summary() -> None:
    workflow_path = ROOT_DIR / ".github" / "workflows" / "windows-build.yml"
    assert workflow_path.is_file()

    content = workflow_path.read_text(encoding="utf-8")

    # Ensure no deprecated ::warning:: annotations remain
    assert "::warning::" not in content

    # Ensure consolidated ::notice:: is present with clear Unsigned-Dev notice
    assert "::notice::Unsigned Development Build:" in content
    assert "NOT claimed to be Smart App Control compatible" in content
    assert "Self-signed certificates are never accepted for production releases" in content

    # Ensure strict require_signing enforcement is preserved
    assert "if ($requireSigning) {" in content
    assert 'Write-Error "CRITICAL: require_signing was set to true' in content

    # Ensure GitHub Step Summary generation is present
    assert "Generate GitHub Actions Job Summary" in content
    assert "$env:GITHUB_STEP_SUMMARY" in content
    assert "**Build Mode**" in content
    assert "**Smart App Control (SAC)**" in content
    assert "**$sacStatus**" in content
    assert "Node 24 (actions/checkout@v7, actions/upload-artifact@v6, astral-sh/setup-uv@v10)" in content


def test_github_actions_workflow_inno_setup_compilation_hardening() -> None:
    workflow_path = ROOT_DIR / ".github" / "workflows" / "windows-build.yml"
    assert workflow_path.is_file()

    content = workflow_path.read_text(encoding="utf-8")

    # Hardening: Resolve script to absolute path & verify existence
    assert "(Resolve-Path $issRelativePath).Path" in content
    assert 'Test-Path $issRelativePath' in content

    # Hardening: Resolve ISCC compiler via Get-Command and log version
    assert 'Get-Command "ISCC.exe"' in content
    assert "(Get-Item $isccPath).VersionInfo.ProductVersion" in content

    # Hardening: Immediately check $LASTEXITCODE and fail on error
    assert "$exitCode = $LASTEXITCODE" in content
    assert "if ($exitCode -ne 0) {" in content
    assert "exit $exitCode" in content

    # Hardening: Verify non-empty compiled binary
    assert "$item.Length -le 0" in content
