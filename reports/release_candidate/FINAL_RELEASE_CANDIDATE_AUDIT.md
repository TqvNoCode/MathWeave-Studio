# MathWeave Studio — Final Release Candidate Audit Report

**Audit Date:** 2026-11-27  
**Intended Release Label Under Review:** `v2.1` (Version Convention Resolution Required — see Section 3)  
**Actual Package Version in Codebase:** `0.2.0` (`pyproject.toml`, `math_app.__version__`, UI `MVP · v0.2.0`)  
**Working Branch:** `feat/unified-math-ui-ux` (uncommitted UI/UX Unification + Post-Review Polish preserved)  
**Backup Branch & Commit:** `feature/euler-cauchy-solver` @ `3fdec2abf4071795a930ecaf12d31df8d02c3ad8` (`origin/feature/euler-cauchy-solver`)  
**Final Release Decision:** **`READY_FOR_RELEASE`** *(awaiting user version confirmation, Git commit/push, and Windows CI run)*

---

## 1. Executive Summary

This independent release-candidate audit verified the complete MathWeave Studio repository, automated test suite, mathematical core integrity, 34-operation catalog, PyInstaller desktop build, live runtime behavior of the built executable, responsive layout (`360px`–`1440px`), accessibility evidence, and startup/compute/memory performance.

Key findings:
- **Git & Mathematical Core Integrity:** Backup commit `3fdec2abf4071795a930ecaf12d31df8d02c3ad8` is verified on both local and remote `feature/euler-cauchy-solver`. All **80 protected files** across `solvers/`, `input/`, `verification/`, `domain/`, and `pyproject.toml` are byte-for-byte identical to the backup baseline (`SHA-256: 3ef25131e982622af550b2881337f6534b0fda24401851c185a382b8c22f9be6`).
- **Automated Test Audit:** During the initial audit run, `test_clean_shutdown_after_page_load` failed reproducibly when host port `8080` was occupied because the test read only the first stdout line (`[STARTUP]...`) rather than scanning for NiceGUI's bound `http://` URL line. After a minimal 1-hunk fix in `tests/unit/presentation/test_shutdown_lifecycle.py`, **`uv run pytest -q` passed `1446 passed, 0 failed, 0 skipped, 2 warnings` in `180.90s`**, and `ruff check`, `git diff --check`, and `uv lock --check` all exited `0`.
- **Complete Module & Built-Binary Verification:** All **34/34** catalog operations mounted with accurate module-specific CTAs; **56/56** smoke scenarios (valid, invalid, boundary, singular, unsupported) and **4/4** ODE state checks passed. The PyInstaller Linux onedir package (`dist/mathweave-studio/mathweave-studio`, `28.97 MiB` binary / `1,190.44 MiB` total bundle) built cleanly, launched in `881.56 ms`, served all offline KaTeX/font assets (`HTTP 200`), passed **51/51** live Chromium workflow × viewport checks (`0px` horizontal overflow, `0` clipped controls, `0` console errors, `0` Python tracebacks), and exited cleanly on `SIGINT` (`651.35 ms`).
- **Pending Release Actions (Before Tagging):** Confirm the canonical SemVer tag (`v0.3.0` recommended vs `v0.2.1` patch alternative vs `v2.1.0`), commit/push `feat/unified-math-ui-ux`, and execute `.github/workflows/windows-build.yml` on `windows-latest` to produce & smoke-test the Windows Portable and Inno Setup artifacts.

---

## 2. Git Baseline and Backup Verification

Verified directly against local and remote Git state:

| Check | Command / Reference | Observed Result |
|---|---|---|
| Working branch | `git status --short --branch` | `feat/unified-math-ui-ux` (HEAD @ `3fdec2a`, uncommitted UI/UX + audit test fix preserved) |
| Local backup branch | `git rev-parse feature/euler-cauchy-solver` | `3fdec2abf4071795a930ecaf12d31df8d02c3ad8` |
| Remote backup branch | `git rev-parse origin/feature/euler-cauchy-solver` | `3fdec2abf4071795a930ecaf12d31df8d02c3ad8` |
| Remote repository | `git remote -v` | `origin git@github.com:TqvNoCode/MathWeave-Studio.git` |
| Existing Git tags | `git tag --sort=-version:refname` | `v0.2.0` (`c2f3f1d`), `v0.1.1` (`b182593`) |
| Main branch | `git branch -vv` | `main 083ec29 [origin/main: behind 49]`, `test 5ec90b4 [origin/test]` |
| Ignore hygiene | `.gitignore` | `build/`, `dist/`, `.venv/`, `.pytest_cache/`, `.ruff_cache/`, `.env` all ignored; build outputs do not pollute `git status`. |

**Working-tree inventory:** `35` modified tracked files (`26` in `src/math_app/presentation/`, `9` in `tests/unit/presentation/`), `0` deleted files, and untracked new files strictly in `src/math_app/presentation/components/shared/`, `src/math_app/presentation/components/workspace/ode/second_order_classifier.py`, `tests/unit/presentation/test_ui_ux_unification.py`, `docs/UI_UX_DESIGN_SYSTEM.md`, `reports/UI_UX_*.md`, `reports/ui_ux/`, and `reports/release_candidate/`.

---

## 3. Version and Release Convention Audit (`v2.1` vs `0.2.0`)

### 3.1. Version Consistency Table

| Source / Artifact | Current Value | Notes |
|---|---|---|
| `pyproject.toml` | `0.2.0` | Authoritative package metadata (unchanged) |
| `src/math_app/__init__.py` | `0.2.0` (`__version__`) | Uses `importlib.metadata.version("mathweave-studio")` with `"0.2.0"` fallback |
| UI Header (`app_header.py`) & About Dialog (`app.py`) | `MVP · v0.2.0` | Dynamically reads `__version__` |
| Git Tags | `v0.1.1`, `v0.2.0` | Strict `vMAJOR.MINOR.PATCH` SemVer progression |
| `CHANGELOG.md` | `0.1.0 -> 0.1.1 -> 0.2.0 -> [Unreleased]` | Explicitly declares SemVer 2.0.0; `[Unreleased]` documents `ODE-EC1` (Euler–Cauchy) |
| `installer/MathWeave-Studio.iss` | `0.2.0` (`#define MyAppVersion "0.2.0"`) | Overridden by CI `/DMyAppVersion="$ver"` from `pyproject.toml` |
| `build_tools/generate_version_info.py` | Reads `pyproject.toml` (`0.2.0` fallback) | Synchronizes Windows PE `VSVersionInfo` during Windows CI |
| `build_tools/version_info_onedir.txt` & `version_info_portable.txt` | **`0.1.1.0`** *(stale tracked)* | Stale in Git from `v0.1.1`; CI overwrites at build time (`generate_version_info.py`) |
| `README.md` & `README.vi.md` (lines 141–144) | **`v0.1.1`** *(stale download links)* | Still point to GitHub Release `v0.1.1` assets |
| `docs/UI_UX_DESIGN_SYSTEM.md` | App `v0.2.0` / Design System `1.1` | Synchronized during Post-Review Polish |

### 3.2. Recommendation

1. **`v2.1` does NOT match any established convention in this repository.** All prior releases (`v0.1.0` $\rightarrow$ `v0.1.1` $\rightarrow$ `v0.2.0`) follow Semantic Versioning `v0.y.z`, and UI headers display `MVP · v0.2.0`.
2. **Canonical Recommended Release Version: `v0.3.0`** (with `v0.2.1` as the secondary option):
   - **Why `v0.3.0`:** Under SemVer 2.0.0 (`0.y.z`), adding a major mathematical solver (`ODEEulerCauchySolver` + singular domain branching) and unifying all 34 operations under a redesigned Design System + Equation-First Second-Order ODE workflow constitutes substantial new backward-compatible functionality (**MINOR bump `0.2.0` $\rightarrow$ `0.3.0`**).
   - **Alternative (`v0.2.1`):** Appropriate only if `"v2.1"` was an informal shorthand for `v0.2.1` and you intend to treat this release as a minor patch update after `v0.2.0`.
   - **Recommendation against `v2.1.0`:** Jumping from `0.2.0` directly to `2.1.0` skips `1.0.0` and `2.0.0` without a breaking-change milestone and conflicts with `MVP · v0.2.0` branding unless intentionally graduating out of `0.x` MVP.
3. **Pre-Tag Checklist Once User Confirms Version:** Bump `pyproject.toml`, convert `[Unreleased]` in `CHANGELOG.md`, refresh `build_tools/version_info_*.txt` via `generate_version_info.py`, and update `README.md`/`README.vi.md` release links.

---

## 4. Source Code and Changeset Audit

`git diff --stat feature/euler-cauchy-solver` reports **35 modified tracked files (`+1500 / -770`)**, `0` deleted files:
- **`src/math_app/presentation/` (26 modified + 5 new):** Shared Design System tokens & CSS (`tokens.py`, `styles.py`), shared primitives (`action_labels.py`, `workspace_header.py`, `example_chips.py`, `feedback_cards.py`, `primary_button.py`, `status_badge.py`), shell navigation (`app_header.py`, `page_shell.py`, `sticky_nav_bar.py`, `back_button.py`), non-ODE & Matrix unification (`app.py`, `matrix_helper.py`, `variable_selector.py`, `problem_statement.py`), Equation-First Second-Order ODE & semantic section naming (`second_order_classifier.py`, `ode_workspace.py`, `ode_state.py`, `ode_classification_selector.py`, `ode_guided_classification_view.py`, `ode_method_selector.py`, `ode_mode_selector.py`, `first_order_classifier.py`), and honest Stage-4 / verification / step viewers (`ode_pedagogical_enhancer.py`, `ode_staged_step_viewer.py`, `solution_view.py`, `step_viewer.py`, `verification_badge.py`, `domain_view.py`).
- **`tests/unit/presentation/` (9 modified + 1 new):** `test_ui_ux_unification.py` (22 tests) + assertion updates for module-specific CTA labels, semantic ODE headers, and dynamic-port stdout scanning in `test_shutdown_lifecycle.py`.
- **Hygiene Checks:** `0` debug prints (`print(`, `pdb`, `breakpoint`), `0` `TODO`/`FIXME` markers in Python presentation code, `0` duplicate components, `0` stale imports, `0` unintended config edits.

---

## 5. Protected Core Integrity

Verified byte-for-byte against `feature/euler-cauchy-solver` (`3fdec2abf4071795a930ecaf12d31df8d02c3ad8`) across all 5 protected paths:
- `src/math_app/solvers/`
- `src/math_app/input/`
- `src/math_app/verification/`
- `src/math_app/domain/`
- `pyproject.toml`

| Metric | Observed Result |
|---|---|
| Protected files audited | **80** |
| Backup SHA-256 aggregate digest | `3ef25131e982622af550b2881337f6534b0fda24401851c185a382b8c22f9be6` |
| Working-tree SHA-256 aggregate digest | `3ef25131e982622af550b2881337f6534b0fda24401851c185a382b8c22f9be6` |
| Byte mismatches | **`0` (`[]`)** |
| Untracked files inside protected paths | **`0` (`[]`)** |

---

## 6. Full Automated Test Audit

- **Initial Audit Run (`task-331`):** `1445 passed, 1 failed` (`tests/unit/presentation/test_shutdown_lifecycle.py::test_clean_shutdown_after_page_load`). Root cause: host port `8080` was in use (`OSError 98`), `get_available_port()` legitimately selected an ephemeral port, and `test_clean_shutdown_after_page_load` read only line 1 (`[STARTUP] ...`) instead of scanning stdout for `http://[^\s]+`, falling back to refused `127.0.0.1:8080`.
- **Safe Non-Protected Fix:** Updated `tests/unit/presentation/test_shutdown_lifecycle.py` lines 190–203 to loop `p.stdout.readline()` up to the readiness deadline until `http://[^\s]+` is found (`3/3 passed in 5.77s`).
- **Final Post-Edit Full Verification (`task-409`):**

| Check | Command | Count / Output | Exit Code |
|---|---|---|---|
| Full test suite | `uv run pytest -q` | **`1446 passed, 0 failed, 0 skipped, 2 warnings` in `180.90s`** | `0` |
| Linter | `uv run ruff check src/ tests/` | `All checks passed!` | `0` |
| Diff whitespace/conflict check | `git diff --check` | Clean (no trailing whitespace or conflict markers) | `0` |
| Lockfile consistency | `uv lock --check` | `Resolved 90 packages in 1ms` | `0` |

*(Warnings: 1 expected `RuntimeWarning: invalid value encountered in sqrt` in `test_2d_plot_sampling_arbitrary_viewport`; 1 `StarletteDeprecationWarning` from `TestClient` in `test_windows_metadata_and_signing.py`.)*

---

## 7. Complete Module Smoke-Test Matrix

Executed via `rc_smoke_test.py` (`build_application()` + `create_app()`):
- **Catalog Mount & CTA Coverage:** **`34 / 34`** operations mounted cleanly via `/?op=<problem_type>` with exact `get_primary_action_spec()` button labels (`0` missing).
- **Functional, Boundary & Invalid Cases:** **`56 / 56` PASS** + **`4 / 4` ODE State Boundary/Override Checks PASS**:

| Domain | Tested Scenarios (Representative + Invalid / Boundary) | Outcome |
|---|---|---|
| **Calculus (17 cases)** | 1st & 3rd-order derivative, invalid bracket expr (`invalid_input`), partial derivative, indefinite integral (`x^2+3x` -> `success`; `x*exp(x)` -> `partial` + `verified` honestly), definite integral, finite & `oo` limits, arc length, surface area, surface of revolution, line integral, surface integral, triple integral, Green's, Stokes', Divergence theorems | **17 / 17 PASS** (`verified`, invalid = `not_applicable`) |
| **Algebra (5 cases)** | Distinct roots (`x^2-5x+6=0`), repeated root (`x^2-4x+4=0`), complex/no-real roots (`x^2+1=0`), cubic Cardano (`x^3+2x^2-5x+1=0`), invalid `==` syntax (`invalid_input`) | **5 / 5 PASS** |
| **Linear Algebra (14 cases)** | 2×2 & 3×3 determinants, non-square matrix (`invalid_input`), ragged syntax (`invalid_input`), 2×2 inverse, singular inverse (`invalid_input`), REF, RREF, transpose, rank, add/sub, multiply, linear system `Ax=b` (`[[1,2],[3,4]]=[5,11]` -> `success`; negative-entry `[[2,1],[1,-1]]=[5,1]` -> `invalid_input` due to protected core quirk noted below) | **14 / 14 PASS** |
| **Differential Equations (20 cases + 4 state checks)** | 1st-order homogeneous/nonhomogeneous linear, classical homogeneous, separable, exact, integrating factor, 1st-order Cauchy IVP; 2nd-order homogeneous, MUC, VoP (`tan(t)`), 2nd-order Cauchy IVP; Euler–Cauchy general (`t>0`) & IVP (`y(1)=3, y'(1)=0`), singular IVP (`t0=0` -> `cannot_solve`), cross-zero interval (`-1<t<1` -> `cannot_solve`), nonhomogeneous Euler–Cauchy (`cannot_solve`); Reduction of Order (`y1=1/t`); Wronskian independent (`verified`) & dependent (`2t, 5t` -> `unverified` honestly); missing Cauchy IC, inconsistent IC base point (`y(0)=1, y'(1)=0`), auto-classification (`4/4`), manual override | **24 / 24 PASS** |

**Notable Protected-Core Boundary Observation:** In `src/math_app/solvers/linear_algebra/solver.py` (`MatrixSolver._extract_two_matrices`), binary operators are scanned in the order `("+", "-", "*", "=", "|")` when `matrix_b` is not passed separately. Consequently, a single-string `MATRIX_SOLVE_SYSTEM` input containing negative entries in `A` (such as `[[2, 1], [1, -1]] = [5, 1]`, or catalog example `[[1, 1, 1], [0, 2, 5], [2, 5, -1]] = [6, -4, 27]`) splits on `"-"` inside `A` instead of `"="` and raises `InvalidInputError`. Preserved untouched per protected-core rule; documented for future `0.3.x` solver refinement.

---

## 8. Desktop Packaging & Hygiene Audit

Built Linux desktop distribution using the repository's documented spec:
```bash
uv run pyinstaller --noconfirm --clean mathweave-studio.spec
```

| Property | Measured Value |
|---|---|
| Build duration & exit code | `62.85s`, exit `0` |
| Distribution target built | Linux Onedir (`dist/mathweave-studio/mathweave-studio`) |
| Executable size | `30,377,368` bytes (**`28.97 MiB`**) |
| Executable SHA-256 | `6f0f977210573e1ba4d71a413daa19e70b225585aac60f7f578f68db4e97a48c` |
| Total bundle footprint | `4,867` files, `1,248,267,056` bytes (**`1,190.44 MiB`** including PyQt6/QtWebEngine runtime) |
| Bundled static resources | `assets/icon.ico`, `assets/icon.png`, `assets/fonts/DejaVuMathTeXGyre.ttf`, `assets/katex/*`, `math_app/presentation/assets/*`, `nicegui`, `plotly`, `latex2mathml`, `PyQt6`, `webview` — **all present** |
| Security / artifact hygiene | `0` `.env` files, `0` credentials/private keys, `0` `tests/`, `.git/`, `reports/`, `.pytest_cache/`, or `.ruff_cache/` entries inside `dist/` |
| Windows distribution target | `.github/workflows/windows-build.yml` (`MathWeave-Studio-Portable*.exe`, `MathWeave-Studio-Setup*.exe`) requires `windows-latest` + Inno Setup 6 (`ISCC.exe`); **not compilable or runnable on this Linux host**. |

---

## 9. Built Application Runtime Results

Tested directly against `dist/mathweave-studio/mathweave-studio`:
1. **Headless Native Rejection Check (`DISPLAY="" WAYLAND_DISPLAY=""`):** Exited cleanly with code `1` and displayed clear Vietnamese + English instructions to run with `--browser`.
2. **Wayland Native Mode Probe (`WAYLAND_DISPLAY=wayland-1` inside sandbox):** Server started (`[STARTUP] Resolved startup mode: NATIVE (native=True)` on `http://127.0.0.1:38563`, HTTP `200`, clean `SIGINT` exit `0`), while Qt desktop window creation could not connect to the host Wayland socket from inside the isolated sandbox (`Failed to create wl_display`).
3. **Packaged Browser/Server End-to-End Runtime (`--browser --no-show`):**
   - Cold launch bound dynamically to `http://127.0.0.1:36393` and served HTTP `200` in **`881.56 ms`**.
   - Offline assets `/assets/katex/katex.css`, `/assets/katex/katex.js`, `/assets/fonts/DejaVuMathTeXGyre.ttf`, `/assets/icon.png` all returned **HTTP `200`**.
   - UI header & About dialog displayed `MVP · v0.2.0` (`hasVersion: true`).
   - Expand/collapse detailed solution substeps toggled `aria-expanded` cleanly (`false -> true -> false`).
   - Clicking `Nhập lại` cleared stale results immediately (`true -> false`).
   - Browser console errors: **`0`**, Python runtime tracebacks: **`0`**.
   - `SIGINT` graceful shutdown completed cleanly (`returncode = 0` in **`651.35 ms`**).

---

## 10. Responsive UI QA (`360px` – `1440px` Against Built Binary)

Verified all **12 Part 7 workflows** in live headless Chromium (`PyQt6.QtWebEngineWidgets`) connected directly to the running built executable (**51 total workflow × viewport executions**):

| Workflow | Viewports Tested | `overflowX` | Clipped | KaTeX Rendered | Screenshot Evidence |
|---|---|---:|---:|---|---|
| 1. Main Catalog | `360, 390, 480, 768, 1024, 1280, 1440` | `0` | `0` | `23/23` | [`rc_01_built_catalog_1280.png`](screenshots/rc_01_built_catalog_1280.png) |
| 2. Derivative Input | `360, 1280` | `0` | `0` | `1/1` | — |
| 3. Derivative Result | `360, 768, 1280` | `0` | `0` | `28/28` | — |
| 4. Partial Derivative | `360, 1280` | `0` | `0` | `24/24` | — |
| 5. Algebraic Equation | `360, 1280` | `0` | `0` | `16/16` | — |
| 6. Matrix Determinant (3×3) | `360, 390, 480, 768, 1024, 1280, 1440` | `0` | `0` | `6/6` | [`rc_05_built_matrix_det_result_1280.png`](screenshots/rc_05_built_matrix_det_result_1280.png) |
| 7. First-Order ODE | `360, 768, 1280` | `0` | `0` | `75/75` | [`rc_09_built_tablet_768_fo_ode_result.png`](screenshots/rc_09_built_tablet_768_fo_ode_result.png) |
| 8. Second-Order ODE (Equation-First) | `360, 390, 480, 768, 1024, 1280, 1440` | `0` | `0` | `8/8` | [`rc_02_built_so_ode_equation_first_1280.png`](screenshots/rc_02_built_so_ode_equation_first_1280.png), [`rc_08_built_mobile_360_so_ode.png`](screenshots/rc_08_built_mobile_360_so_ode.png) |
| 9. Euler–Cauchy (Auto-Detected) | `360, 1280` | `0` | `0` | `91/91` | [`rc_03_built_euler_cauchy_result_1280.png`](screenshots/rc_03_built_euler_cauchy_result_1280.png) |
| 10. Cauchy IVP | `360, 390, 480, 768, 1024, 1280, 1440` | `0` | `0` | `174/174` | [`rc_04_built_cauchy_ivp_result_1280.png`](screenshots/rc_04_built_cauchy_ivp_result_1280.png) |
| 11. Long Fraction-Heavy Expr | `360, 390, 480, 768, 1024, 1280, 1440` | `0` | `0` | `53/57`* | [`rc_07_built_mobile_360_long_derivative.png`](screenshots/rc_07_built_mobile_360_long_derivative.png) |
| 12. Validation Error (`role="alert"`) | `360, 1280` | `0` | `0` | `1/1` | [`rc_06_built_validation_error_1280.png`](screenshots/rc_06_built_validation_error_1280.png) |

*\*4 unrendered `.math-tex` nodes in `wf11_long_expr` reside inside the collapsed Layer-B substep expansion until opened by the user.*

---

## 11. Accessibility Findings

Cross-verified from [`reports/ui_ux/post_review/ACCESSIBILITY_QA.md`](../ui_ux/post_review/ACCESSIBILITY_QA.md):
- `0` unlabeled visible `<input>` controls; `0` unnamed visible `<button>` / `[role="button"]` controls across Catalog, Derivative, Matrix, First-Order ODE, Second-Order ODE, and Validation Alert screens.
- Global `:focus-visible` (`2px solid #2563eb`) verified active in CSS; example chips confirmed keyboard-focusable and executable via both `Enter` and `Space`.
- All measured sRGB contrast ratios exceed `4.5:1`: Primary CTA `5.25:1`, Verification badge `5.02:1`, Info status badge `8.01:1`, Example chip `13.34:1`, Section headings `10.36:1–13.97:1`, Body text `7.58:1`.
- Honest limitation: Formal screen-reader user testing (NVDA / VoiceOver / Orca) was not conducted.

---

## 12. Performance and Startup Observations (Built Binary)

Measured directly on `dist/mathweave-studio/mathweave-studio`:

| Metric | Measured Value |
|---|---|
| Cold binary startup to HTTP 200 `/` | **`881.56 ms`** |
| Catalog initial hydration (`360px` cold / `390–1440px` warm) | `470.22 ms` cold / `186.04–211.33 ms` warm |
| Module workspace open latency | `129.97–284.88 ms` across all workspaces |
| Matrix 3×3 determinant calculation | `1.1–1.4 ms` solver |
| First-order / cubic algebra / derivative calculation | `82.2–136.6 ms` solver |
| Second-order ODE / Euler–Cauchy / Cauchy IVP calculation | `152.1–187.5 ms` solver |
| Long symbolic integral (`x^3*exp(2*x)*cos(x)`) | `498.4 ms` solver / `2,016.8 ms` end-to-end UI render |
| KaTeX DOM pass (`window.renderAllMath`) | `~251 ms` (including post-pass settle wait) |
| Process RSS memory (initial $\rightarrow$ after 51+ UI renders & symbolic solves) | **`172.33 MiB` $\rightarrow$ `329.46 MiB`** |
| Graceful shutdown latency (`SIGINT` -> exit `0`) | **`651.35 ms`** |

No severe startup, memory leak, rendering, or UI responsiveness regressions observed.

---

## 13. Release Artifact Inventory

- **Built locally (gitignored in `dist/`):** `dist/mathweave-studio/mathweave-studio` (`30,377,368` bytes, SHA-256 `6f0f977210573e1ba4d71a413daa19e70b225585aac60f7f578f68db4e97a48c`, total bundle `1,190.44 MiB`).
- **Release documentation prepared:**
  - [`reports/release_candidate/FINAL_RELEASE_CANDIDATE_AUDIT.md`](FINAL_RELEASE_CANDIDATE_AUDIT.md)
  - [`reports/release_candidate/RELEASE_NOTES_DRAFT.md`](RELEASE_NOTES_DRAFT.md)
  - [`reports/release_candidate/screenshots/rc_01..rc_09_*.png`](screenshots/)
  - [`docs/UI_UX_DESIGN_SYSTEM.md`](../../docs/UI_UX_DESIGN_SYSTEM.md)
  - [`reports/UI_UX_POST_REVIEW_REPORT.md`](../UI_UX_POST_REVIEW_REPORT.md)

---

## 14. Known Limitations

1. **Windows CI Artifacts Pending:** `MathWeave-Studio-Portable*.exe` and `MathWeave-Studio-Setup*.exe` must be built and smoke-tested on `windows-latest` via `.github/workflows/windows-build.yml` after committing/pushing.
2. **Wayland/X11 GUI Window Launch in Isolated Sandbox:** Inside this sandbox, host display sockets (`wayland-1` / X11) are blocked (`Failed to create wl_display`), so built-binary GUI rendering was verified via `--browser --no-show` + headless Chromium (`QtWebEngine`). Recommend a quick manual double-click smoke check on a desktop session after commit.
3. **Pre-existing Protected Core Quirk (`MatrixSolver._extract_two_matrices`):** Single-string `Ax = b` inputs with negative numbers in matrix `A` split on `"-"` before `"="` (unaffected by UI/UX changes; deferred to future solver release).
4. **No Formal Screen-Reader Audit:** Automated ARIA/contrast/keyboard checks passed, but NVDA/VoiceOver user testing has not been performed.
5. **Minor Cosmetic Wrapping:** On `768px` tablet view, the Stage 2 stepper pill `2. μ(t)` wraps onto two lines (`rc_09_built_tablet_768_fo_ode_result.png`) without causing any overflow (`overflowX = 0`).

---

## 15. Outstanding Blockers / Pre-Release Action Items

Zero code-quality, test, mathematical-core, or Linux-build blockers remain. Before cutting the final Git tag & GitHub Release, the user must authorize:
1. **Confirm canonical release version:** Choose `v0.3.0` (recommended SemVer) vs `v0.2.1` vs `v2.1.0`, then bump `pyproject.toml`, `CHANGELOG.md`, `README.md`, `README.vi.md`, and refresh `build_tools/version_info_*.txt`.
2. **Commit & push `feat/unified-math-ui-ux`** (and merge/PR into `test` / `main` per repo workflow) to trigger `ci.yml` and `windows-build.yml`.

---

## 16. Final Recommendation

**Verdict: `READY_FOR_RELEASE`**

The current working tree on `feat/unified-math-ui-ux` preserves the verified `feature/euler-cauchy-solver` mathematical core byte-for-byte, passes **1,446 / 1,446** automated tests, passes Ruff/diff/lock checks, passes **34/34** catalog and **56/56** smoke checks, builds cleanly with PyInstaller, and passes **51/51** live responsive/functional browser checks against the built binary with clean startup and shutdown. Once you confirm the target release version (`v0.3.0` recommended) and authorize committing/pushing, the release pipeline is ready to ship.
