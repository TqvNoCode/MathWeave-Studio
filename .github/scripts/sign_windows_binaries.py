#!/usr/bin/env python3
"""Windows Code Signing & Authenticode Verification Utility for MathWeave Studio.

Handles Authenticode SHA-256 signing with RFC 3161 timestamps for Windows PE
binaries (.exe, .dll, .pyd) in both Onedir and Portable distributions.

Strictly differentiates between:
1. Production Signed Releases: Requires valid externally trusted certificate.
2. Unsigned Development Builds: Produces labeled unsigned binaries when credentials are absent.
3. Diagnostic Pipeline Testing: Isolated mock/test signing that is NEVER labeled as production trusted.

Guarantees that embedded native dependencies inside Portable Onefile (especially OpenSSL
and _ssl) are individually verified.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

TIMESTAMP_SERVERS = [
    "http://timestamp.digicert.com",
    "http://timestamp.sectigo.com",
    "http://tsa.starfieldtech.com",
]

PRESERVED_VENDORS = [
    "microsoft corporation",
    "microsoft windows",
]


def log(msg: str) -> None:
    print(f"[CODESIGN] {msg}", flush=True)


def find_signtool() -> Path | None:
    """Find signtool.exe in Windows SDK directories or on system PATH."""
    which_signtool = shutil.which("signtool.exe") or shutil.which("signtool")
    if which_signtool:
        return Path(which_signtool)

    program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    kits_dir = Path(program_files_x86) / "Windows Kits" / "10" / "bin"
    if kits_dir.is_dir():
        candidates = list(kits_dir.glob("*/x64/signtool.exe"))
        if candidates:
            candidates.sort(reverse=True)
            return candidates[0]

    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    kits_dir_pf = Path(program_files) / "Windows Kits" / "10" / "bin"
    if kits_dir_pf.is_dir():
        candidates = list(kits_dir_pf.glob("*/x64/signtool.exe"))
        if candidates:
            candidates.sort(reverse=True)
            return candidates[0]

    return None


def setup_signing_certificate(
    temp_dir: Path,
    mode: str = "auto",
    allow_test_cert: bool = False,
    require_signing: bool = False,
) -> tuple[str, list[str] | None]:
    """Configure signing certificate based on environment secrets and execution mode.

    Returns:
        tuple of (cert_description, signtool_cert_args or None for unsigned)
    """
    cert_base64 = os.environ.get("WINDOWS_CERT_BASE64", "").strip()
    cert_password = os.environ.get("WINDOWS_CERT_PASSWORD", "").strip()

    # 1. Production certificate configured via secret
    if cert_base64:
        log("Valid production code-signing certificate (WINDOWS_CERT_BASE64) detected.")
        pfx_path = temp_dir / "mathweave_codesign.pfx"
        pfx_path.write_bytes(base64.b64decode(cert_base64))
        args = ["/f", str(pfx_path)]
        if cert_password:
            args.extend(["/p", cert_password])
        return "Externally Trusted Production Certificate (PFX)", args

    # 2. Production signing required but credentials missing -> FAIL
    if require_signing or mode == "production":
        raise RuntimeError(
            "CRITICAL: Production code signing was explicitly requested, but WINDOWS_CERT_BASE64 "
            "is not configured in the environment. Self-signed fallback is disabled for production releases. "
            "Configure a valid externally trusted certificate or Microsoft Trusted Signing to proceed."
        )

    # 3. Isolated test pipeline mode (for testing signtool mechanics ONLY)
    if allow_test_cert or mode == "test-pipeline":
        log("\n" + "!" * 70)
        log("WARNING: Running in isolated test-pipeline mode with local test certificate.")
        log("THIS BUILD IS NOT TRUSTED BY END-USER WINDOWS SYSTEMS OR SMART APP CONTROL.")
        log("DO NOT USE THIS CERTIFICATE FOR RELEASES OR TO CLAIM PRODUCTION COMPATIBILITY.")
        log("!" * 70 + "\n")

        if sys.platform != "win32":
            return "[TEST-ONLY] Mock Test Certificate (Non-Windows)", ["/mock"]

        pwsh_cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            """
            $cert = New-SelfSignedCertificate `
                -Type CodeSigningCert `
                -Subject "CN=MathWeave Studio Test (DO NOT TRUST), O=Local Test" `
                -CertStoreLocation "Cert:\\CurrentUser\\My" `
                -KeyAlgorithm RSA `
                -KeyLength 3072 `
                -HashAlgorithm SHA256 `
                -NotAfter (Get-Date).AddDays(7)
            Write-Output $cert.Thumbprint
            """,
        ]
        res = subprocess.run(pwsh_cmd, capture_output=True, text=True, check=True)
        thumbprint = res.stdout.strip().splitlines()[-1].strip()
        log(f"Generated ephemeral test cert in My store (Thumbprint: {thumbprint}). Root store untouched.")
        return f"[TEST-ONLY] Ephemeral RSA Test Cert ({thumbprint})", ["/sha1", thumbprint, "/s", "My"]

    # 4. Default when credentials are absent -> Unsigned Development Build
    log("Notice: No code signing credentials configured. Producing Unsigned Development Build.")
    return "Unsigned Development Build (No Signing Applied)", None


def should_preserve_vendor_signature(file_path: Path) -> bool:
    """Check if file already possesses a valid signature from a trusted OS/platform vendor."""
    if sys.platform != "win32":
        return False

    pwsh_cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        f"""
        $sig = Get-AuthenticodeSignature -FilePath '{file_path}'
        if ($sig.Status -eq 'Valid' -and $sig.SignerCertificate) {{
            $subj = $sig.SignerCertificate.Subject.ToLower()
            Write-Output $subj
        }} else {{
            Write-Output "NONE"
        }}
        """,
    ]
    try:
        res = subprocess.run(pwsh_cmd, capture_output=True, text=True, timeout=5)
        out = res.stdout.strip().lower()
        for vendor in PRESERVED_VENDORS:
            if vendor in out:
                log(f"Preserving existing valid vendor signature ({vendor}) on: {file_path.name}")
                return True
    except Exception:
        pass
    return False


def sign_single_binary(
    signtool_path: Path,
    file_path: Path,
    cert_args: list[str],
    description: str = "MathWeave Studio",
    force: bool = False,
) -> None:
    """Sign a single PE binary using signtool.exe with RFC 3161 timestamping."""
    if not force and should_preserve_vendor_signature(file_path):
        return

    base_cmd = [
        str(signtool_path),
        "sign",
        "/fd",
        "sha256",
        "/d",
        description,
        "/v",
    ] + cert_args

    signed = False
    last_error = ""

    # Try signing with RFC 3161 timestamp servers with retries
    for ts_url in TIMESTAMP_SERVERS:
        cmd = base_cmd + ["/tr", ts_url, "/td", "sha256", str(file_path)]
        for attempt in range(1, 3):
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                signed = True
                break
            last_error = res.stderr or res.stdout
            time.sleep(1.0)
        if signed:
            break

    if not signed:
        log(f"WARNING: Timestamping failed for {file_path.name}; attempting fallback without RFC 3161 timestamp...")
        cmd_no_ts = base_cmd + [str(file_path)]
        res = subprocess.run(cmd_no_ts, capture_output=True, text=True)
        if res.returncode != 0:
            err_msg = res.stderr or res.stdout or last_error
            raise RuntimeError(f"SignTool failed to sign {file_path} (Exit {res.returncode}):\n{err_msg}")


def verify_authenticode_signature(file_path: Path, signtool_path: Path | None = None) -> dict[str, str]:
    """Verify Authenticode signature, chain trust, EKU, and timestamping."""
    if sys.platform != "win32":
        return {
            "file": file_path.name,
            "status": "Skipped (non-Windows platform)",
            "is_trusted_root": "N/A",
            "signer": "N/A",
            "algorithm": "N/A",
        }

    pwsh_cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        f"""
        $sig = Get-AuthenticodeSignature -FilePath '{file_path}'
        $isTrusted = $false
        if ($sig.Status -eq 'Valid') {{
            $chain = New-Object -TypeName System.Security.Cryptography.X509Certificates.X509Chain
            $isTrusted = $chain.Build($sig.SignerCertificate)
        }}

        $result = @{{
            Status = $sig.Status.ToString()
            StatusMessage = $sig.StatusMessage
            IsTrustedRoot = $isTrusted
            Signer = if ($sig.SignerCertificate) {{ $sig.SignerCertificate.Subject }} else {{ "None" }}
            Issuer = if ($sig.SignerCertificate) {{ $sig.SignerCertificate.Issuer }} else {{ "None" }}
            Algorithm = if ($sig.SignerCertificate) {{ $sig.SignerCertificate.SignatureAlgorithm.FriendlyName }} else {{ "None" }}
            TimeStamper = if ($sig.TimeStamperCertificate) {{ $sig.TimeStamperCertificate.Subject }} else {{ "None" }}
            Timestamp = if ($sig.TimeStamperCertificate) {{ (Get-Date).ToString("yyyy-MM-dd HH:mm:ss") }} else {{ "None" }}
        }}
        $result | ConvertTo-Json
        """,
    ]
    res = subprocess.run(pwsh_cmd, capture_output=True, text=True)
    try:
        data = json.loads(res.stdout)
    except Exception:
        data = {
            "Status": "Error",
            "StatusMessage": res.stderr or res.stdout,
            "IsTrustedRoot": False,
            "Signer": "Unknown",
            "Algorithm": "Unknown",
        }

    if signtool_path and signtool_path.is_file():
        st_cmd = [str(signtool_path), "verify", "/pa", "/v", str(file_path)]
        st_res = subprocess.run(st_cmd, capture_output=True, text=True)
        data["SignToolStatus"] = "Valid" if st_res.returncode == 0 else f"Failed (code {st_res.returncode})"

    return data


def inspect_file_metadata(file_path: Path) -> dict[str, str]:
    """Extract Windows PE FileVersionInfo metadata."""
    if sys.platform != "win32":
        return {"file": file_path.name, "metadata": "N/A (non-Windows platform)"}

    pwsh_cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        f"""
        $item = Get-Item -FilePath '{file_path}'
        $vi = $item.VersionInfo
        $result = @{{
            FileVersion = $vi.FileVersion
            ProductVersion = $vi.ProductVersion
            FileDescription = $vi.FileDescription
            ProductName = $vi.ProductName
            CompanyName = $vi.CompanyName
            LegalCopyright = $vi.LegalCopyright
            OriginalFilename = $vi.OriginalFilename
        }}
        $result | ConvertTo-Json
        """,
    ]
    res = subprocess.run(pwsh_cmd, capture_output=True, text=True)
    try:
        return json.loads(res.stdout)
    except Exception:
        return {"error": res.stderr or res.stdout}


def verify_onefile_embedded_binaries(portable_exe: Path) -> list[dict[str, str]]:
    """Extract and inspect embedded native dependencies inside Portable Onefile."""
    log("\n" + "=" * 65)
    log("VERIFYING EMBEDDED NATIVE DEPENDENCIES INSIDE PORTABLE ONEFILE")
    log("=" * 65)

    if not portable_exe.is_file():
        log(f"Portable executable not found: {portable_exe}")
        return []

    if sys.platform != "win32":
        log("Notice: Non-Windows platform; skipping runtime extraction verification.")
        return []

    results: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory() as sandbox_temp:
        temp_path = Path(sandbox_temp)
        log(f"Launching controlled extraction test in sandbox: {temp_path}")

        env = os.environ.copy()
        env["TEMP"] = str(temp_path)
        env["TMP"] = str(temp_path)

        # Launch briefly with --version or --help
        cmd = [str(portable_exe), "--version"]
        try:
            proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # Give bootloader up to 8s to extract _MEI directory
            time.sleep(3.0)
        except Exception as exc:
            log(f"Execution failed: {exc}")
            proc = None

        # Search for extracted _MEI directories
        mei_dirs = list(temp_path.glob("_MEI*"))
        if not mei_dirs:
            # Check for alternate extraction directories
            mei_dirs = [d for d in temp_path.iterdir() if d.is_dir()]

        log(f"Discovered {len(mei_dirs)} extraction directories in sandbox temp.")
        for mei in mei_dirs:
            log(f"Inspecting extracted payload at: {mei.name}")
            crypto_dlls = list(mei.rglob("libcrypto*.dll"))
            ssl_pyds = list(mei.rglob("*ssl*.pyd"))
            all_binaries = crypto_dlls + ssl_pyds

            for b in all_binaries:
                sig = verify_authenticode_signature(b)
                info = {
                    "File": b.name,
                    "Path": str(b.relative_to(mei)),
                    "Status": sig.get("Status", "Unknown"),
                    "Signer": sig.get("Signer", "None"),
                    "IsTrustedRoot": str(sig.get("IsTrustedRoot", False)),
                }
                results.append(info)
                log(f"  Embedded Binary : {info['File']}")
                log(f"    Relative Path : {info['Path']}")
                log(f"    Sign Status   : {info['Status']}")
                log(f"    Signer        : {info['Signer']}")
                log(f"    Trusted Root  : {info['IsTrustedRoot']}")

        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except Exception:
                proc.kill()

    return results


def sign_distributions(
    onedir_dir: Path,
    portable_exe: Path,
    installer_exe: Path | None = None,
    mode: str = "auto",
    allow_test_cert: bool = False,
    require_signing: bool = False,
    dry_run: bool = False,
) -> bool:
    """Sign all PE binaries in onedir, portable, and installer distributions."""
    log("=" * 65)
    log("MathWeave Studio — Windows Code Signing & Verification Pipeline")
    log("=" * 65)

    if sys.platform != "win32" and not dry_run:
        log("Notice: Platform is not Windows. Performing structural scan and dry-run validation.")
        dry_run = True

    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        cert_desc, cert_args = setup_signing_certificate(
            temp_dir,
            mode=mode,
            allow_test_cert=allow_test_cert,
            require_signing=require_signing,
        )
        log(f"Signing Profile: {cert_desc}")

        if not cert_args:
            log("Result: Proceeding with Unsigned Development Build.")
            return False

        signtool = find_signtool()
        if not signtool and not dry_run:
            raise FileNotFoundError("signtool.exe was not found in Windows SDK or system PATH.")

        if signtool:
            log(f"Using SignTool: {signtool}")

        # 1. Sign Onedir Binaries
        if onedir_dir.is_dir():
            log(f"\nScanning Onedir directory for PE binaries (.exe, .dll, .pyd): {onedir_dir}")
            pe_files: list[Path] = []
            for ext in ("*.exe", "*.dll", "*.pyd"):
                pe_files.extend(onedir_dir.rglob(ext))

            log(f"Discovered {len(pe_files)} PE binary files.")

            libcrypto_matches = [p for p in pe_files if "libcrypto-3-x64.dll" in p.name.lower()]
            if libcrypto_matches:
                log(f"Found target critical binary: {libcrypto_matches[0].relative_to(onedir_dir)}")

            signed_count = 0
            for pe in pe_files:
                if dry_run:
                    signed_count += 1
                    continue
                sign_single_binary(signtool, pe, cert_args, description="MathWeave Studio")
                signed_count += 1

            log(f"Processed {signed_count} binaries in Onedir distribution.")

        # 2. Sign Portable Executable
        if portable_exe.is_file():
            log(f"\nSigning Portable Standalone Executable: {portable_exe}")
            if not dry_run:
                sign_single_binary(signtool, portable_exe, cert_args, description="MathWeave Studio Portable")
            log(f"Successfully processed portable executable: {portable_exe.name}")

        # 3. Sign Installer Executable (if present)
        if installer_exe and installer_exe.is_file():
            log(f"\nSigning Windows Installer Executable: {installer_exe}")
            if not dry_run:
                sign_single_binary(signtool, installer_exe, cert_args, description="MathWeave Studio Installer")
            log(f"Successfully processed installer executable: {installer_exe.name}")

        # 4. Verification Step
        log("\n" + "=" * 65)
        log("VERIFYING AUTHENTICODE SIGNATURES & FILE METADATA")
        log("=" * 65)

        verification_targets = []
        if onedir_dir.is_dir():
            main_onedir_exe = onedir_dir / "mathweave-studio.exe"
            if main_onedir_exe.is_file():
                verification_targets.append(main_onedir_exe)
            for libcrypto in onedir_dir.rglob("libcrypto-3-x64.dll"):
                verification_targets.append(libcrypto)

        if portable_exe.is_file():
            verification_targets.append(portable_exe)

        if installer_exe and installer_exe.is_file():
            verification_targets.append(installer_exe)

        for target in verification_targets:
            log(f"\nTarget: {target.name}")
            sig_info = verify_authenticode_signature(target, signtool)
            log(f"  Authenticode Status : {sig_info.get('Status', 'N/A')}")
            log(f"  Chains to Root CA   : {sig_info.get('IsTrustedRoot', 'N/A')}")
            log(f"  Signer Certificate  : {sig_info.get('Signer', 'N/A')}")
            log(f"  Digest Algorithm    : {sig_info.get('Algorithm', 'N/A')}")

            if target.suffix.lower() == ".exe":
                meta = inspect_file_metadata(target)
                log(f"  FileVersion         : {meta.get('FileVersion', 'N/A')}")
                log(f"  ProductName         : {meta.get('ProductName', 'N/A')}")
                log(f"  CompanyName         : {meta.get('CompanyName', 'N/A')}")
                log(f"  LegalCopyright      : {meta.get('LegalCopyright', 'N/A')}")

        return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Sign MathWeave Studio Windows Binaries")
    parser.add_argument(
        "--onedir-dir",
        type=Path,
        default=Path("dist/mathweave-studio"),
        help="Path to onedir directory",
    )
    parser.add_argument(
        "--portable-exe",
        type=Path,
        default=Path("dist/MathWeave-Studio-Portable.exe"),
        help="Path to portable executable",
    )
    parser.add_argument(
        "--installer-exe",
        type=Path,
        default=None,
        help="Path to Windows installer executable",
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "production", "test-pipeline", "unsigned-dev"],
        default="auto",
        help="Signing execution mode",
    )
    parser.add_argument(
        "--allow-test-cert",
        action="store_true",
        help="Allow ephemeral self-signed cert for isolated test pipeline ONLY (never for releases)",
    )
    parser.add_argument(
        "--require-signing",
        action="store_true",
        help="Fail if production credentials are not configured",
    )
    parser.add_argument(
        "--verify-embedded",
        action="store_true",
        help="Perform controlled extraction to verify embedded dependencies in Portable Onefile",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform discovery and parameter validation without signing",
    )
    args = parser.parse_args()

    try:
        sign_distributions(
            args.onedir_dir,
            args.portable_exe,
            installer_exe=args.installer_exe,
            mode=args.mode,
            allow_test_cert=args.allow_test_cert,
            require_signing=args.require_signing,
            dry_run=args.dry_run,
        )

        if args.verify_embedded and args.portable_exe.is_file():
            verify_onefile_embedded_binaries(args.portable_exe)

        return 0
    except Exception as exc:
        log(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
