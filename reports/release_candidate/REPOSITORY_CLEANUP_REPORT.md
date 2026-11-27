# MathWeave Studio — Pre-Release Repository Cleanup Report (`v0.3.0`)

**Cleanup Date:** 2026-11-27  
**Branch:** `feat/unified-math-ui-ux`  
**Initial Checkpoint Commit:** `dd688cb4379bc86996a323cd0b9aa526c3757ca2`  
**Cleanup Commit SHA:** `74784083861d3e04db1f572b4aaf02360d583f34` (`chore: clean repository artifacts before v0.3.0 release`)  
**Backup Branch & Commit (Untouched):** `feature/euler-cauchy-solver` @ `3fdec2abf4071795a930ecaf12d31df8d02c3ad8` (local & `origin/feature/euler-cauchy-solver`)  
**Final Decision:** **`CLEANUP_COMPLETE`**

---

## 1. Executive Summary

A scoped, verification-first repository hygiene cleanup was completed on `feat/unified-math-ui-ux` ahead of the `v0.3.0` release:
- Removed **44 redundant tracked artifacts** (`4` old `.patch` diff snapshots totaling `477,933` bytes and `40` superseded pre-polish/pre-unification screenshots totaling `13,096,087` bytes) from both GitHub (`origin/feat/unified-math-ui-ux`) and the local working tree.
- Hardened `.gitignore` with precise Python, test/coverage/trace, temp-log, and `*.patch` rules while ensuring zero exclusion of `reports/`, `docs/`, `tests/`, `assets/`, `*.spec`, `installer/`, or `.github/workflows/`.
- Converted leaked local filesystem links (`file:///home/tqv/...`) in `reports/UI_UX_INDEPENDENT_REVIEW.md` and `reports/UI_UX_UNIFICATION_FINAL_REPORT.md` into clean repository-relative Markdown links (`0` local paths remain across all `.md` files).
- Reclaimed **`126,992,366` bytes (`121.11 MiB`)** of local disk space by removing `build/`, `.pytest_cache/`, `.ruff_cache/`, `47` repository `__pycache__` directories, empty screenshot subdirectories, and the 44 deleted tracked artifacts—while keeping `.venv/` and the validated Linux `dist/mathweave-studio/` deliverable completely intact.

---

## 2. Cleanup Categorization Table (Deleted, Retained, Ignored)

| Category | Scope | Items / Paths | Count / Size | Disposition |
|---|---|---|---|---|
| **Redundant `.patch` Snapshots** | GitHub + Local | `reports/ec1_euler_cauchy.patch`, `ec1_euler_cauchy_r1.patch`, `ec1_euler_cauchy_ux1.patch`, `ode_final_r1.patch` | `4` files (`477,933` bytes) | **Deleted** (superseded by committed Git history @ `3fdec2a`) |
| **Obsolete Pre-Unification ODE Screenshots** | GitHub + Local | `reports/screenshots/01..11_*.png` and `reports/screenshots/r1/r1_01..r1_08_*.png` | `19` files (`8,572,115` bytes) | **Deleted** (zero broken links; superseded by `rc_01..rc_09` & `post_01..post_10`) |
| **Obsolete Pre-Polish UI/UX Screenshots** | GitHub + Local | `reports/ui_ux/screenshots/before/before_01..07_*.png` and `after/after_01..14_*.png` | `21` files (`4,523,972` bytes) | **Deleted** (zero broken links; superseded by `post_review/` & `release_candidate/`) |
| **PyInstaller Intermediate Build Dir** | Local only | `./build/` | `104,379,194` bytes | **Deleted** (ignored by `.gitignore`, reproducible via `mathweave-studio.spec`) |
| **Local Python/Tool Caches** | Local only | `./.pytest_cache/`, `./.ruff_cache/`, `47` `__pycache__` dirs (`src/`, `tests/`, `build_tools/`, `.github/scripts/`) | `9,039,152` bytes | **Deleted** (ignored by `.gitignore`, automatically regenerated cleanly on test/lint) |
| **Report Relative Link Fixes** | GitHub + Local | `reports/UI_UX_INDEPENDENT_REVIEW.md`, `reports/UI_UX_UNIFICATION_FINAL_REPORT.md` | `2` files | **Retained & Fixed** (replaced `file:///home/tqv/...` with `../...`) |
| **Release Candidate Deliverables** | GitHub + Local | `reports/release_candidate/FINAL_RELEASE_CANDIDATE_AUDIT.md`, `RELEASE_NOTES_DRAFT.md`, `REPOSITORY_CLEANUP_REPORT.md`, `screenshots/rc_01..rc_09_*.png` | `12` files | **Preserved** |
| **UI/UX Design & Post-Review Docs + Evidence** | GitHub + Local | `docs/UI_UX_DESIGN_SYSTEM.md`, `reports/UI_UX_*.md`, `reports/ui_ux/milestones/M1..M5_*.md`, `reports/ui_ux/post_review/*.md`, `reports/ui_ux/screenshots/post_review/post_01..post_10_*.png` | `21` files | **Preserved** |
| **Historical ODE Implementation Reports** | GitHub + Local | `reports/EC1_*.md`, `reports/ODE_FINAL_*.md` | `5` files | **Preserved** |
| **Application Source, Tests, Assets & Packaging** | GitHub + Local | `src/`, `tests/`, `assets/` (`133` tracked asset files), `*.spec`, `installer/`, `build_tools/`, `.github/`, `README*.md`, `CHANGELOG.md`, `pyproject.toml`, `uv.lock` | All | **Preserved 100%** |
| **Validated Linux Build Deliverable** | Local only | `dist/mathweave-studio/` (`4,760` files, `837,233,909` bytes) | `798.45 MiB` | **Retained & Ignored** (`SHA-256` verified below) |
| **Project Virtual Environment** | Local only | `.venv/` (`842M`) | Preserved | **Retained & Ignored** |

**Total Local Disk Space Reclaimed:** **`126,992,366` bytes (`~121.11 MiB` / `127.0 MB`)**.

---

## 3. `.gitignore` Improvements & Verification

Updated `/home/tqv/Desktop/CODE/Python/math_app/.gitignore` (`+17 / -4` lines) to ignore:
- **Python artifacts:** `*$py.class`, `.Python` (alongside `__pycache__/`, `*.py[cod]`).
- **Test, coverage, and browser traces:** `coverage.xml`, `pytest.xml`, `junit.xml`, `.tox/`, `.nox/`, `.hypothesis/`, `test-results/`, `playwright-report/`, `playwright/.cache/`, `*.trace.zip`.
- **Temporary logs, scratch dumps, and patches:** `smoke_*.log`, `*.tmp`, `*.bak`, `*~`, and `*.patch` (replacing `/git_diff.patch`).

Verified with `git check-ignore -v`:
- **Matched cleanly (`exit 0`):** `.pytest_cache/x`, `.ruff_cache/x`, `__pycache__/a.pyc`, `build/x`, `dist/x`, `smoke_a.log`, `reports/x.patch`, `coverage.xml`, `test-results/a.zip`, `.env`.
- **Not ignored (`exit 1`):** `reports/release_candidate/FINAL_RELEASE_CANDIDATE_AUDIT.md`, `reports/release_candidate/screenshots/rc_01_built_catalog_1280.png`, `docs/UI_UX_DESIGN_SYSTEM.md`, `assets/fonts/DejaVuMathTeXGyre.ttf`, `assets/katex/katex.js`, `mathweave-studio.spec`, `mathweave-studio-onefile.spec`, `installer/MathWeave-Studio.iss`, `.github/workflows/windows-build.yml`, `README.md`, `CHANGELOG.md`, `tests/conftest.py`.

---

## 4. Verification Evidence (Pre-Cleanup-Push Gate + Independent Review)

### 4.1. Mathematical Core Integrity
- `git diff --exit-code 3fdec2abf4071795a930ecaf12d31df8d02c3ad8 74784083861d3e04db1f572b4aaf02360d583f34 -- src/math_app/solvers/ src/math_app/input/ src/math_app/verification/ src/math_app/domain/` exited **`0`** (`0` changes across all **79** tracked files in those four protected directories; SHA-256 `91c554679714c9d44c420ebb489234e2194fe4bc77200813bc7037af4409bcc1`).
- `git diff --name-status dd688cb..7478408 -- tests/` returned **empty** (`0` test files modified or deleted).

### 4.2. Automated Tests, Linting & Links
- `uv run pytest -q`: **`1446 passed, 0 failed, 0 skipped, 2 warnings` in `237.49s`** (matching exact baseline).
- `uv run ruff check src/ tests/`: **`All checks passed!`** (`exit 0`).
- `uv lock --check`: **`Resolved 90 packages in 2ms`** (`exit 0`).
- `git diff --check`: clean (`exit 0`).
- Markdown link check across all 43 Markdown files (`python3 -B`): **`0` broken links** across all project docs and reports (`README.md`, `README.vi.md`, `CHANGELOG.md`, `docs/`, `reports/`), **`0` `/home/tqv` local paths** remaining. *(Vendored third-party `assets/katex/README.md` retains KaTeX upstream's `CONTRIBUTING.md` reference, expected.)*

### 4.3. Linux Packaging & Live Binary Verification (`v0.3.0`)
- Rebuilt via `uv run pyinstaller --noconfirm --clean mathweave-studio.spec`:
  - Executable: `dist/mathweave-studio/mathweave-studio` (**`30,377,368` bytes**)
  - SHA-256: **`50d0260aa7a3d69b82814322ff83e1d7e2dc90793eb257b13bd12259731c11d2`**
  - Retained bundle footprint: **`4,760` files**, **`837,233,909` bytes** (`798.45 MiB`)
- Live headless Chromium QA (`QT_QPA_PLATFORM=offscreen`) against the rebuilt binary:
  - Cold startup HTTP `200` in `1553.75 ms`, UI displays **`MVP · v0.3.0`**, offline KaTeX & `DejaVuMathTeXGyre.ttf` return `HTTP 200`.
  - **51/51** workflow × viewport checks (`360px`–`1440px`) passed with `overflowX = 0`, `clipped = 0`, `0` console errors, `0` Python tracebacks, RSS `173.7 MB -> 326.91 MB`, graceful `SIGINT` exit `0` in `912.76 ms`.

### 4.4. Independent Read-Only Review
- Conducted by fresh-context read-only reviewer subagent (`5fae10e2-1993-46cc-bc1f-98e5209bd174`) across all 9 audit questions:
  - **Verdict:** **`APPROVED`** (`0` Critical, `0` High, `0` Medium findings; 3 minor informational observations noted).

---

## 5. Git Status, Remote Push & Unresolved Items Outside Cleanup Scope

- **Cleanup Commit:** `74784083861d3e04db1f572b4aaf02360d583f34` (`dd688cb..7478408 feat/unified-math-ui-ux -> feat/unified-math-ui-ux`), followed by the commit adding this report.
- **Backup Branch Preserved:** `feature/euler-cauchy-solver` & `origin/feature/euler-cauchy-solver` remain at `3fdec2abf4071795a930ecaf12d31df8d02c3ad8`.
- **GitHub Releases / Tags / `main`:** Untouched (tag `v0.3.0` not created yet; `main` not merged).
- **Unresolved Item Outside Cleanup Scope:** Windows CI (`.github/workflows/windows-build.yml`) trigger via `gh workflow run` remains pending user re-authentication (`gh auth login -h github.com`) from the separate v0.3.0 Release Finalization workflow.
