# Post-Review Practical Accessibility Audit

**Application Version:** MathWeave Studio `v0.2.0` (`pyproject.toml` preserved)  
**Branch:** `feat/unified-math-ui-ux`  
**Audit Scope:** Practical automated + live-DOM accessibility inspection in real headless Chromium (`PyQt6.QtWebEngineWidgets`) across 6 representative screens: Catalog (`/`), Derivative Result, Matrix Result, First-Order ODE Input, Second-Order ODE Input, and Invalid Input Alert state.

> [!NOTE]
> **Honest Scope Statement:** This document records practical, measured accessibility verification results (DOM semantics, keyboard activation, focus-visible styling, accessible names, non-color-only indicators, and computed sRGB contrast ratios). It does **not** claim formal third-party WCAG 2.1 AA/AAA certification or screen-reader user testing (NVDA/JAWS/VoiceOver).

---

## 1. Real Accessibility Defects Found & Remediated During Audit

Live Chromium contrast computation exposed three real Quasar CSS specificity defects that degraded contrast below 4.5:1 despite high-contrast tokens in `tokens.py`:

| Control | Initial Measured Contrast | Root Cause | Remediation | Verified Final Contrast |
|---|---:|---|---|---:|
| `status_badge()` (`Giải tích (Calculus)`, `Cấp 1 (First-Order)`, `Thuần nhất: g(t) = 0`) | **`2.85:1`** (FAIL) | `ui.badge(text)` defaulted to Quasar `color="primary"` (`rgb(88,152,212)` `!important`), overriding the inline `#eff6ff` light background behind `#1e40af` text. | Passed `color=None` in [`status_badge.py`](../../../src/math_app/presentation/components/shared/status_badge.py). | **`8.01:1`** (PASS) |
| `primary_button()` (`TÍNH ĐẠO HÀM`, `TÍNH ĐỊNH THỨC`, `GIẢI PHƯƠNG TRÌNH VI PHÂN CẤP 2`) | **`3.06:1`** (FAIL) | `ui.button(...)` defaulted to Quasar `color="primary"` (`rgb(88,152,212)`), overriding Tailwind `bg-blue-600`. | Passed `color=None` + `bg-blue-600 !bg-blue-600 hover:!bg-blue-700 text-white !text-white` in [`primary_button.py`](../../../src/math_app/presentation/components/shared/primary_button.py) (and matched active mode buttons in `ode_mode_selector.py`). | **`5.25:1`** (PASS) |
| `render_verification_badge()` (`✓ Đã kiểm chứng toán học`, `✓ Kiểm chứng nối trơn C¹`) | **`2.57:1`** (FAIL) | Quasar `color="positive"` uses bright green `rgb(33,186,69)` with white text. | Preserved `color="positive"` prop contract while applying high-contrast dark emerald `#15803d` / `#ffffff` in [`verification_badge.py`](../../../src/math_app/presentation/components/verification_badge.py). | **`5.02:1`** (PASS) |

---

## 2. Practical Audit Checklist & Live DOM Evidence

| Criterion | Verified Screens | Measured Evidence | Result |
|---|---|---|---|
| **Keyboard-only navigation & logical tab order** | Catalog (`24` focusables), Derivative (`22`), Matrix (`13`), ODE 1 (`16`), ODE 2 (`18`), Invalid Alert (`18`) | All catalog cards (`role="button" tabindex="0"`), Back button, inputs, adaptive variable chips, expandable toggles, example chips, Reset, and primary CTA sit in natural top-to-bottom DOM order with no `tabindex > 0` traps. | **PASS** |
| **Focus visibility (`:focus-visible`)** | All 6 screens (`hasFocusVisibleRule: true`) | Global `:focus-visible` rule (`outline: 2px solid #2563eb !important; outline-offset: 2px !important`) verified active in document stylesheets for `button`, `a`, `input`, `[role="button"]`, `.q-btn`, `.q-chip`. | **PASS** |
| **Input labels** | All 6 screens (`unlabeledInputs = []`) | 100% of visible `<input>` controls (`3/3` Derivative, `1/1` Matrix, `2/2` ODE 1, `2/2` ODE 2) carry explicit visible `.q-field__label` text. | **PASS** |
| **Button & icon-button accessible names** | All 6 screens (`unnamedButtons = []`) | `0` unnamed visible buttons across `24` (Catalog), `19` (Derivative), `12` (Matrix), `14` (ODE 1), `16` (ODE 2), `15` (Invalid Alert) interactive buttons. Header About button, Back button, Reset, and Plot toolbar icons all have explicit `aria-label`. | **PASS** |
| **Example chips keyboard `Enter` & `Space`** | `fo_ode_input` live event test + all screens `chipA11y` | Every rendered `.mw-example-chip` has `tabindex="0"`, `role="button"`, and escaped `aria-label`. Live Chromium keyboard dispatch confirmed: `focus()` succeeded (`focused=true`); `Enter` updated input from `y' + (1/2)*y = t + 2` to `y' + 2*t*y = 0`; `Space` updated input to `y' = 2*y + 3`. | **PASS** |
| **Expandable disclosure state (`aria-expanded`)** | `fo_ode_input`, `so_ode_input`, `derivative_result` | `"Xem lý lẽ chi tiết"` (`aria-expanded="false"` -> `"true"`), `"Đổi phân loại thủ công"` (`aria-expanded="false"` -> `"true"`), and step substep expansions accurately expose expanded state. | **PASS** |
| **Validation & loading announcements** | `invalid_alert` (`(((bad_expr`), unit tests for `render_loading_card` | Live invalid submission rendered `role="alert"` (`alertRoles = 1`) with icon + Vietnamese error text; `render_loading_card` emits `role="status" aria-live="polite"`. | **PASS** |
| **Verification status non-color-only** | `derivative_result`, `matrix_result` | `✓ Đã kiểm chứng toán học` carries `role="status"`, explicit text prefix (`✓` / `⚠` / `✗`), descriptive Vietnamese label, and hover tooltip explaining verification method. | **PASS** |

---

## 3. Computed Foreground / Background Contrast Measurements (Live Chromium)

Colors were decoded via Canvas 2D sRGB normalization in live Chromium (accurately resolving Tailwind v4 `oklch(...)` and Quasar styles):

| Element Type | Sample Text | Foreground | Background | Computed Ratio | Reference (`>= 4.5:1`) |
|---|---|---|---|---:|---|
| Primary CTA Button | `TÍNH ĐẠO HÀM` / `TÍNH ĐỊNH THỨC` / `GIẢI PTVP` | `rgb(255, 255, 255)` | `rgb(21, 93, 252)` | **`5.25:1`** | PASS |
| Verification Badge | `✓ Đã kiểm chứng toán học` | `rgb(255, 255, 255)` | `rgb(21, 128, 61)` | **`5.02:1`** | PASS |
| Info Status Badge | `Giải tích (Calculus)` / `Cấp 1 (First-Order)` | `rgb(30, 64, 175)` | `rgb(239, 246, 255)` | **`8.01:1`** | PASS |
| Catalog Count Pill | `8 dạng toán` | `rgb(49, 65, 88)` | `rgb(226, 232, 240)` | **`8.40:1`** | PASS |
| Example Chip | `Đa thức 2x^3 + 6x - 8` / `Ma trận vuông 2x2` | `rgb(29, 41, 61)` | `rgb(241, 245, 249)` | **`13.34:1`** | PASS |
| Section Heading | `NHẬP BÀI TOÁN` / `BIẾN LẤY ĐẠO HÀM:` | `rgb(49, 65, 88)` | `rgb(255, 255, 255)` | **`10.36:1`** | PASS |
| Catalog Group Heading | `GIẢI TÍCH (CALCULUS)` | `rgb(29, 41, 61)` | `rgb(248, 250, 252)` | **`13.97:1`** | PASS |
| Body / Description Text | `Tính đạo hàm bậc 1 hoặc bậc cao...` | `rgb(69, 85, 108)` | `rgb(255, 255, 255)` | **`7.58:1`** | PASS |

---

## 4. Known Accessibility Limitations

1. **No formal screen-reader testing yet:** KaTeX emits hidden `.katex-mathml` MathML trees for screen readers, but live end-to-end reading with NVDA / VoiceOver / Orca has not been performed in this automated headless environment.
2. **Quasar internal `role="status"` on `.q-badge`:** Quasar assigns `role="status"` to all `.q-badge` primitives by default (including decorative metadata badges such as `2 bước` or `8 dạng toán`). They do not use `aria-live="assertive"`, so they do not interrupt speech, though a future refinement could move non-live counts to plain styled `<span>` pills.
3. **Interactive Plotly 2D/3D canvas controls:** Plotly charts rely on WebGL/SVG canvas interactions that remain inherently less keyboard-operable than tabular data; the Variation Table (`Bảng biến thiên`) serves as a structured companion where supported.
