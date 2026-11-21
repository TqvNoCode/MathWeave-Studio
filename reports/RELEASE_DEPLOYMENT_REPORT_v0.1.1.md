# OFFICIAL RELEASE DEPLOYMENT REPORT — MATHWEAVE STUDIO v0.1.1

**Date:** November 22, 2026  
**Repository:** `https://github.com/TqvNoCode/MathWeave-Studio`  
**Target Release:** `v0.1.1`  
**Execution Status:** FULLY DEPLOYED, VERIFIED & PUBLISHED  

---

## 1. Executive Summary

MathWeave Studio **v0.1.1** has been successfully prepared, integrated, built on GitHub Actions CI, verified, and published to GitHub Releases. The release provides self-contained native Windows distribution packages (Portable Executable and Inno Setup Windows Installer) alongside verified mathematical solvers for calculus, linear algebra, and differential equations.

---

## 2. Release Identification & Links

| Property | Value / URL |
| :--- | :--- |
| **Release Version** | `0.1.1` |
| **Git Tag** | [`v0.1.1`](https://github.com/TqvNoCode/MathWeave-Studio/releases/tag/v0.1.1) |
| **Merged Pull Request** | [PR #11: Release v0.1.1 — Windows Native Distribution](https://github.com/TqvNoCode/MathWeave-Studio/pull/11) |
| **Merged `main` Commit SHA** | `b18259394891db527239ae4152db14fff1008538` |
| **Windows Build Workflow Run** | [Run #44927183072 (Success)](https://github.com/TqvNoCode/MathWeave-Studio/actions/runs/44927183072) |
| **GitHub Release URL** | [https://github.com/TqvNoCode/MathWeave-Studio/releases/tag/v0.1.1](https://github.com/TqvNoCode/MathWeave-Studio/releases/tag/v0.1.1) |

---

## 3. Official Release Assets & Provenance

All release assets were generated exclusively by automated GitHub Actions CI runner (`windows-latest` / Python 3.14.8) on the exact merged `main` commit `b18259394891db527239ae4152db14fff1008538` (Job ID `136915733330`).

| Asset Filename | Size (Bytes) | SHA-256 Checksum | Direct Download URL |
| :--- | :--- | :--- | :--- |
| **`MathWeave-Studio-Portable-Unsigned-Dev.exe`** | 71,307,704 (68.0 MB) | `18e58609a43c468b171217e0d3d5ef0f4fd67fff8bd1d115ce231fb7c2021a20` | [Download Portable EXE](https://github.com/TqvNoCode/MathWeave-Studio/releases/download/v0.1.1/MathWeave-Studio-Portable-Unsigned-Dev.exe) |
| **`MathWeave-Studio-Setup-Unsigned-Dev.exe`** | 57,770,163 (55.1 MB) | `7021b0055b0479458f3706293ce416e14fd7b1051997d54034c376e995395e89` | [Download Installer EXE](https://github.com/TqvNoCode/MathWeave-Studio/releases/download/v0.1.1/MathWeave-Studio-Setup-Unsigned-Dev.exe) |
| **`SHA256SUMS.txt`** | 215 | N/A (Checksum Manifest) | [Download SHA256SUMS.txt](https://github.com/TqvNoCode/MathWeave-Studio/releases/download/v0.1.1/SHA256SUMS.txt) |

### Integrity Manifest (`SHA256SUMS.txt`)
```text
18e58609a43c468b171217e0d3d5ef0f4fd67fff8bd1d115ce231fb7c2021a20  MathWeave-Studio-Portable-Unsigned-Dev.exe
7021b0055b0479458f3706293ce416e14fd7b1051997d54034c376e995395e89  MathWeave-Studio-Setup-Unsigned-Dev.exe
```

---

## 4. Acceptance Testing & Quality Gates

1. **Automated Unit & Regression Suite:**
   - 664 / 664 tests passing (`uv run pytest`) with 100% pass rate.
   - 0 boundary violations across Clean Architecture layers.
2. **Linting & Code Formatting:**
   - Ruff linting clean (`uv run ruff check .` $\rightarrow$ 0 errors).
3. **CI Windows Runner Acceptance (`smoke_test_windows.py`):**
   - **Native Desktop Launch:** Successfully spawned bare executables without crashing or throwing NiceGUI import errors.
   - **Asset Integrity:** Verified bundled fonts (`DejaVuMathTeXGyre.ttf`), KaTeX CSS/JS assets, and window icons.
   - **Inno Setup Installation:** Verified silent installation, Desktop/Start Menu shortcut generation, and clean silent uninstallation.
   - **Process Cleanup & Graceful Shutdown:** Verified zero lingering worker threads or orphaned Python processes upon exit.
4. **Code Signing Status:**
   - Unsigned Open-Source Release (No commercial certificate secret configured).
   - SmartScreen advisory transparently documented in Release Notes and READMEs.

---

## 5. Documentation & Branch Preservation

- **Documentation:** [README.md](file:///home/tqv/Desktop/CODE/Python/math_app/README.md) and [README.vi.md](file:///home/tqv/Desktop/CODE/Python/math_app/README.vi.md) updated with direct release asset download links and generalized test-passing statements.
- **Branch Preservation:** The `test` branch is preserved intact.
- **Legacy Releases:** The pre-existing `beta_version` draft release was preserved and left completely untouched.

---

## 6. Known Limitations

- **SmartScreen Prompt:** On first execution, Windows SmartScreen will display an "Unknown Publisher" notice. Users can safely proceed by selecting **More info** $\rightarrow$ **Run anyway**.
- **Display Server Requirement:** Native desktop mode requires an active graphical window manager / display server. On headless or remote servers, launch with `--browser`.
