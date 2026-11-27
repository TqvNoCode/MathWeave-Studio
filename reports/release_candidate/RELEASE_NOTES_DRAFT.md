# MathWeave Studio — v0.3.0 Release Notes

All items below reflect verified, implemented functionality in MathWeave Studio `v0.3.0` (`pyproject.toml` version `0.3.0`, Git tag `v0.3.0` pending CI & final release gate).

---

## New Capabilities

- **Second-Order Euler–Cauchy ODE Solver (`ODE-EC1`):**
  - Added dedicated `ODEEulerCauchySolver` for homogeneous second-order Euler–Cauchy equations $a t^2 y'' + b t y' + c y = 0$ ($a \neq 0$) across all three indicial root regimes (distinct real, repeated real with $\ln|t|$, and complex conjugate with $\cos(\beta \ln|t|), \sin(\beta \ln|t|)$).
  - Full support for general solutions across positive/negative connected branches ($t > 0$ and $t < 0$ with independent constants $C_1, C_2$ and $C_3, C_4$), Cauchy Initial Value Problems ($t_0 \neq 0$), and safe rejection of singular initial points ($t_0 = 0$) and zero-crossing intervals.
  - Pedagogical 4-stage derivation flow showing trial substitution $y = t^m$, indicial polynomial, fundamental basis, domain restrictions, branch breakdown, and independent verification.
- **Equation-First Second-Order ODE Workspace & Live Classifier (`second_order_classifier.py`):**
  - Users now enter their differential equation immediately (`NHẬP BÀI TOÁN`) while the workspace automatically detects Homogeneous Constant-Coefficient, Nonhomogeneous Constant-Coefficient (with Undetermined Coefficients vs. Variation of Parameters recommendation), Euler–Cauchy, Reduction of Order (when `y1` is supplied), or Order-1 mismatches.
  - Added an expandable manual classification control (`"Đổi phân loại thủ công"`) and `"Ghi đè thủ công"` / `"Bật lại tự động"` override recovery controls.

---

## UX Improvements

- **Unified Design System Across All 34 Mathematical Operations (`docs/UI_UX_DESIGN_SYSTEM.md`):**
  - Standardized typography, Academic Blue palette, card spacing, responsive header identity (`render_workspace_header()`), and shared feedback cards (`render_loading_card()`, `render_feedback_card()`, `render_empty_state_card()`).
  - **Module-Specific Primary Action Labels (`action_labels.py`):** Replaced generic `"GIẢI PHƯƠNG TRÌNH"` / `"GIẢI PHÉP TOÁN MA TRẬN"` labels across all 34 operations with exact Vietnamese CTAs (`TÍNH ĐẠO HÀM`, `TÍNH NGUYÊN HÀM`, `TÍNH ĐỊNH THỨC`, `KIỂM CHỨNG ĐỊNH LÝ GREEN`, `TÍNH ĐỊNH THỨC WRONSKIAN`, etc.).
  - **Semantic Pre-Solve ODE Section Naming:** Replaced misleading numbered `BƯỚC` badges on system-generated ODE analysis panels with semantic headings (`NHẬP BÀI TOÁN`, `PHÂN TÍCH TỰ ĐỘNG`, `CƠ SỞ PHÂN LOẠI`, `YÊU CẦU BÀI TOÁN:`, `PHƯƠNG PHÁP ĐỀ XUẤT`), keeping Solution Viewer derivation steps numbered normally.
  - **Progressive Disclosure & Mathematical Notation Precision:** First-Order ODE classification reasoning (`CƠ SỞ PHÂN LOẠI`) collapses cleanly on demand (`aria-expanded`), non-identically-zero forcing functions use exact $g(t) \not\equiv 0$ notation, and non-applicable `y` is excluded from ODE independent variable selectors.
  - **Mobile & Tablet Responsiveness (`360px`–`1440px`):** Full-width wrapping example chips (`.mw-example-chip`), horizontal math scroll containers (`.math-scroll-box`), stacked mobile workspace headers, and Material-icon plot toolbars.
  - **Accessibility Hardening:** Global `:focus-visible` outlines, explicit `aria-label` attributes, `Enter`/`Space` activation on example chips, `role="status"` / `role="alert"` semantics, and high-contrast WCAG-checked (`>= 5.02:1`) buttons and badges.

---

## Bug Fixes

- **Fixed First-Order ODE Auto-Align Equation Overwrite:** Preserved the user's entered equation (`preserve_equation=True`) when auto-aligning classification on submission.
- **Fixed Stage-4 Pedagogical Verification Honesty:** Non-Euler ODE builders and Wronskian flows now reflect actual `VerificationStatus` (`FAILED`, `UNVERIFIED`, and $W \equiv 0$ linear dependence) without falsely rendering green verified summaries.
- **Fixed Sticky Nav Bar Duplication & Title Sync:** Removed duplicated icon/badge clutter and synchronized sticky navigation titles when switching ODE families in-place.
- **Fixed One-Shot Deep-Link Query Parameters:** Prevented URL `?eq`/`?ic`/`?solve` parameters from leaking across workspaces after returning to the Catalog.
- **Fixed Single-Step Conclusion Duplication & Stale Results:** Deduplicated LHS-prefixed single-step conclusions (e.g., `\det(A) = -2`), cleared stale results immediately when inputs/variables/parameters change, and locked submit buttons during async calculation.
- **Fixed Mobile Overflow & Contrast Regressions:** Eliminated `.katex-mathml` horizontal scroll expansion on `360px`/`390px` viewports, enabled wrapping on long Vietnamese status badges, and resolved Quasar default color overrides on primary buttons, status badges, and verified badges.
- **Fixed Dynamic-Port Lifecycle Test Discovery:** Updated `test_clean_shutdown_after_page_load` to scan stdout lines for NiceGUI's bound `http://` URL instead of reading only the `[STARTUP]` header line.

---

## Technical Improvements

- Maintained strict Clean Architecture boundaries: zero modifications to `solvers/`, `input/`, `verification/`, `domain/`, or `pyproject.toml` throughout the UI/UX Unification and Post-Review Polish initiatives.
- Verified **1,446 automated tests** (`uv run pytest -q`), Ruff linting, `git diff --check`, and `uv lock --check` cleanly.
- Verified Linux desktop PyInstaller packaging (`mathweave-studio.spec`) with offline KaTeX, local `DejaVuMathTeXGyre.ttf` font, and clean `SIGINT` shutdown.

---

## Known Limitations

- **Windows Standalone Artifacts:** Windows Portable and Setup installers (`MathWeave-Studio-Portable*.exe`, `MathWeave-Studio-Setup*.exe`) must be built and smoke-tested on `windows-latest` via GitHub Actions (`.github/workflows/windows-build.yml`).
- **Nonhomogeneous Euler–Cauchy Equations:** Current `ODEEulerCauchySolver` supports homogeneous Euler–Cauchy equations only and rejects nonhomogeneous Euler–Cauchy inputs with an explicit explanation.
- **Linear System Negative-Entry Single-String Input (`Ax = b`):** Entering negative entries in coefficient matrix `A` within a single `A = b` string triggers a pre-existing operator precedence split on `"-"` inside `MatrixSolver._extract_two_matrices`.
- **Accessibility Testing Scope:** Live DOM ARIA/contrast/keyboard checks were verified automatically in headless Chromium; formal screen-reader user testing (NVDA/VoiceOver) remains pending.
