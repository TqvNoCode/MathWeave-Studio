# Post-Review Responsive QA Matrix (`360px` – `1440px`)

**Application Version:** MathWeave Studio `v0.2.0` (`pyproject.toml` preserved)  
**Branch:** `feat/unified-math-ui-ux`  
**Execution Engine:** Live NiceGUI server (`build_application()` + `create_app()`) rendered in real headless Chromium (`PyQt6.QtWebEngineWidgets`, `QT_QPA_PLATFORM=offscreen`)  
**Total Measured Scenarios × Viewports:** **67** (`66` automated matrix runs + `1` dedicated `1024px` Multivariable Surface Integral capture)  
**Final Pass Rate:** **67 / 67 PASS (`overflowX = 0`, `clippedControls = 0`, `formulaVScroll = 0`, `overlaps = 0`)**

---

## 1. Real Mobile Overflows Discovered & Remediated During Post-Review QA

Testing long fraction-heavy equations, cubic Cardano radical roots, and long Vietnamese classification badges on narrow viewports exposed three real horizontal overflows that were not visible on shorter M5 inputs. All three were fixed and re-verified to `0px`:

| Scenario | Viewport | Initial `overflowX` | Root Cause | Fix Applied | Verified Final `overflowX` |
|---|---|---|---|---|---|
| `derivative_result` (`(x^4+3x^3-5x^2+7x-11)/(x^2+1)`) | `360px`, `390px` | `69px`, `39px` | KaTeX's visually hidden `<span class="katex-mathml"><math>` inherited `.math-tex math { overflow: visible !important }` without `position: relative` containment, expanding `documentElement.scrollWidth`. | Added `.katex { position: relative }` and strict `1px` clipping on `.katex .katex-mathml` & `.katex .katex-mathml math` in [`styles.py`](../../../src/math_app/presentation/design_system/styles.py), plus `overflow-x: auto` on `.prose-text` and `overflow-hidden` on `step_viewer.py` expansions. | **`0px`**, **`0px`** |
| `solve_equation` (`x^3+2x^2-5x+1=0`, cubic Cardano roots) | `360px` | `111px` | Wide inline `Nghiệm xấp xỉ số học:` formula bar lacked `.math-scroll-box` and `.katex-mathml` leaked outside viewport width. | Added `w-full max-w-full min-w-0 math-scroll-box` on `ĐỀ CHO:` and `Nghiệm xấp xỉ số học:` in [`solution_view.py`](../../../src/math_app/presentation/components/solution_view.py) + `.katex-mathml` clipping. | **`0px`** |
| `fo_ode_input` & `fo_ode_result` (`Phương trình vi phân tuyến tính không thuần nhất cấp 1`) | `360px` | `28px`, `28px` | Quasar `.q-badge` enforced `white-space: nowrap` on a 54-character Vietnamese status pill inside `status_badge()`. | Added `whitespace-normal max-w-full leading-snug text-left` and `color=None` to [`status_badge.py`](../../../src/math_app/presentation/components/shared/status_badge.py). | **`0px`**, **`0px`** |
| Mobile Workspace Header (`360px`, Matrix & ODE) | `360px` | Visual crowding | Horizontal flex row squeezed title + description beside domain/order badge on `360px`. | Stacked header badge cleanly below title block on `< sm` (`flex-col sm:flex-row`) in [`workspace_header.py`](../../../src/math_app/presentation/components/shared/workspace_header.py). | **`0px`** (full-width mobile title) |

---

## 2. Complete Measured Responsive Matrix (67 Live Executions)

Every row below is taken directly from the final live Chromium DOM inspection (`qa_post_review_results.json` + `1024px` surface integral capture):

| Scenario | Stress Input / Coverage | Viewport | `clientW` | `scrollW` | `overflowX` | KaTeX Rendered | Clipped Controls | Formula V-Scroll | Overlaps | Primary CTA Height | Min Chip Height | Status |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Catalog (Screen A) | 23 cards + 5 domain groups | `360px` | 345 | 345 | `0` | 23/23 | 0 | 0 | 0 | — | — | PASS |
| Catalog (Screen A) | 23 cards + 5 domain groups | `390px` | 375 | 375 | `0` | 23/23 | 0 | 0 | 0 | — | — | PASS |
| Catalog (Screen A) | 23 cards + 5 domain groups | `480px` | 465 | 465 | `0` | 23/23 | 0 | 0 | 0 | — | — | PASS |
| Catalog (Screen A) | 23 cards + 5 domain groups | `768px` | 753 | 753 | `0` | 23/23 | 0 | 0 | 0 | — | — | PASS |
| Catalog (Screen A) | 23 cards + 5 domain groups | `1024px` | 1009 | 1009 | `0` | 23/23 | 0 | 0 | 0 | — | — | PASS |
| Catalog (Screen A) | 23 cards + 5 domain groups | `1280px` | 1265 | 1265 | `0` | 23/23 | 0 | 0 | 0 | — | — | PASS |
| Catalog (Screen A) | 23 cards + 5 domain groups | `1440px` | 1425 | 1425 | `0` | 23/23 | 0 | 0 | 0 | — | — | PASS |
| Derivative Input | Default expr + 6 chips | `360px` | 345 | 345 | `0` | 1/1 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Derivative Input | Default expr + 6 chips | `768px` | 753 | 753 | `0` | 1/1 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Derivative Input | Default expr + 6 chips | `1280px` | 1265 | 1265 | `0` | 1/1 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Derivative Result | Fraction-heavy `(x^4+3x^3-5x^2+7x-11)/(x^2+1)` | `360px` | 345 | 345 | `0` | 53/57* | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Derivative Result | Fraction-heavy quotient rule | `390px` | 375 | 375 | `0` | 53/57* | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Derivative Result | Fraction-heavy quotient rule | `480px` | 465 | 465 | `0` | 53/57* | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Derivative Result | Fraction-heavy quotient rule | `768px` | 753 | 753 | `0` | 53/57* | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Derivative Result | Fraction-heavy quotient rule | `1024px` | 1009 | 1009 | `0` | 53/57* | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Derivative Result | Fraction-heavy quotient rule | `1280px` | 1265 | 1265 | `0` | 53/57* | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Derivative Result | Fraction-heavy quotient rule | `1440px` | 1425 | 1425 | `0` | 53/57* | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Partial Derivative Result | `x^3*y^2 + sin(x*y)` | `360px` | 345 | 345 | `0` | 24/24 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Partial Derivative Result | `x^3*y^2 + sin(x*y)` | `768px` | 753 | 753 | `0` | 24/24 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Partial Derivative Result | `x^3*y^2 + sin(x*y)` | `1280px` | 1265 | 1265 | `0` | 24/24 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Algebraic Equation Result | Cubic Cardano `x^3+2x^2-5x+1=0` | `360px` | 345 | 345 | `0` | 9/9 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Algebraic Equation Result | Cubic Cardano `x^3+2x^2-5x+1=0` | `768px` | 753 | 753 | `0` | 9/9 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Algebraic Equation Result | Cubic Cardano `x^3+2x^2-5x+1=0` | `1280px` | 1265 | 1265 | `0` | 9/9 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Matrix Determinant Input | Matrix helper + 5 quick templates | `360px` | 345 | 345 | `0` | 1/1 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Matrix Determinant Input | Matrix helper + 5 quick templates | `768px` | 753 | 753 | `0` | 1/1 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Matrix Determinant Input | Matrix helper + 5 quick templates | `1280px` | 1265 | 1265 | `0` | 1/1 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Matrix Determinant 3×3 Result | `[[2,-1,3],[0,4,-2],[1,5,1]]` | `360px` | 345 | 345 | `0` | 6/6 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Matrix Determinant 3×3 Result | 3×3 expansion | `390px` | 375 | 375 | `0` | 6/6 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Matrix Determinant 3×3 Result | 3×3 expansion | `480px` | 465 | 465 | `0` | 6/6 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Matrix Determinant 3×3 Result | 3×3 expansion | `768px` | 753 | 753 | `0` | 6/6 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Matrix Determinant 3×3 Result | 3×3 expansion | `1024px` | 1009 | 1009 | `0` | 6/6 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Matrix Determinant 3×3 Result | 3×3 expansion | `1280px` | 1265 | 1265 | `0` | 6/6 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Matrix Determinant 3×3 Result | 3×3 expansion | `1440px` | 1425 | 1425 | `0` | 6/6 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| First-Order ODE Input | Long Vietnamese badge + semantic sections | `360px` | 345 | 345 | `0` | 15/15 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| First-Order ODE Input | Semantic sections | `390px` | 375 | 375 | `0` | 15/15 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| First-Order ODE Input | Semantic sections | `480px` | 465 | 465 | `0` | 15/15 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| First-Order ODE Input | Semantic sections | `768px` | 753 | 753 | `0` | 15/15 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| First-Order ODE Input | Semantic sections | `1024px` | 1009 | 1009 | `0` | 15/15 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| First-Order ODE Input | Semantic sections | `1280px` | 1265 | 1265 | `0` | 15/15 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| First-Order ODE Input | Semantic sections | `1440px` | 1425 | 1425 | `0` | 15/15 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| First-Order ODE Result | `y'+(1/2)*y=t+2` (4-stage viewer) | `360px` | 345 | 345 | `0` | 75/75 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| First-Order ODE Result | 4-stage viewer | `768px` | 753 | 753 | `0` | 75/75 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| First-Order ODE Result | 4-stage viewer | `1280px` | 1265 | 1265 | `0` | 75/75 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Second-Order ODE Input | Equation-First + collapsed override | `360px` | 345 | 345 | `0` | 8/8 | 0 | 0 | 0 | `64px` (wrapped) | `28px` | PASS |
| Second-Order ODE Input | Equation-First | `390px` | 375 | 375 | `0` | 8/8 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Second-Order ODE Input | Equation-First | `480px` | 465 | 465 | `0` | 8/8 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Second-Order ODE Input | Equation-First | `768px` | 753 | 753 | `0` | 8/8 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Second-Order ODE Input | Equation-First | `1024px` | 1009 | 1009 | `0` | 8/8 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Second-Order ODE Input | Equation-First | `1280px` | 1265 | 1265 | `0` | 8/8 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Second-Order ODE Input | Equation-First | `1440px` | 1425 | 1425 | `0` | 8/8 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Second-Order ODE Result | Auto-detected Euler–Cauchy `t^2*y''+4*t*y'+2*y=0, t>0` | `360px` | 345 | 345 | `0` | 91/91 | 0 | 0 | 0 | `64px` | `28px` | PASS |
| Second-Order ODE Result | Auto-detected Euler–Cauchy | `768px` | 753 | 753 | `0` | 91/91 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Second-Order ODE Result | Auto-detected Euler–Cauchy | `1280px` | 1265 | 1265 | `0` | 91/91 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Cauchy IVP Result | `y''-3y'-4y=3e^(2t), y(0)=1, y'(0)=0` | `360px` | 345 | 345 | `0` | 174/174 | 0 | 0 | 0 | `64px` | `28px` | PASS |
| Cauchy IVP Result | Second-Order Cauchy IVP | `390px` | 375 | 375 | `0` | 174/174 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Cauchy IVP Result | Second-Order Cauchy IVP | `480px` | 465 | 465 | `0` | 174/174 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Cauchy IVP Result | Second-Order Cauchy IVP | `768px` | 753 | 753 | `0` | 174/174 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Cauchy IVP Result | Second-Order Cauchy IVP | `1024px` | 1009 | 1009 | `0` | 174/174 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Cauchy IVP Result | Second-Order Cauchy IVP | `1280px` | 1265 | 1265 | `0` | 174/174 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Cauchy IVP Result | Second-Order Cauchy IVP | `1440px` | 1425 | 1425 | `0` | 174/174 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Multivariable Surface Integral | Dynamic Graph/Parametric controls | `360px` | 345 | 345 | `0` | 1/1 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Multivariable Surface Integral | Dynamic Graph/Parametric controls | `768px` | 753 | 753 | `0` | 1/1 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Multivariable Surface Integral | Dynamic Graph/Parametric controls | `1024px` | 1009 | 1009 | `0` | 1/1 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Multivariable Surface Integral | Dynamic Graph/Parametric controls | `1280px` | 1265 | 1265 | `0` | 1/1 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Vector Calculus Green's Theorem | `-y, x` dual theorem verification | `360px` | 345 | 345 | `0` | 9/9 | 0 | 0 | 0 | `44px` | `42px` | PASS |
| Vector Calculus Green's Theorem | `-y, x` dual theorem verification | `768px` | 753 | 753 | `0` | 9/9 | 0 | 0 | 0 | `44px` | `28px` | PASS |
| Vector Calculus Green's Theorem | `-y, x` dual theorem verification | `1280px` | 1265 | 1265 | `0` | 9/9 | 0 | 0 | 0 | `44px` | `28px` | PASS |

*\*Note on `53/57` in `derivative_result`: The 4 unrendered `.math-tex` nodes sit inside the collapsed `ui.expansion("Xem giải thích chi tiết các phép biến đổi")` (display:none) until expanded; `badLatexCount = 0` across all visible text.*

---

## 3. Captured Post-Review Screenshots (`reports/ui_ux/screenshots/post_review/`)

| File | Viewport | Purpose / Pairing |
|---|---|---|
| [`post_01_so_ode_equation_first_1280.png`](../screenshots/post_review/post_01_so_ode_equation_first_1280.png) | `1280px` | After: Second-Order ODE Equation-First layout (pairs with `before_04_second_order_ode.png` & `after_08`) |
| [`post_02_so_ode_manual_override_expanded_1280.png`](../screenshots/post_review/post_02_so_ode_manual_override_expanded_1280.png) | `1280px` | After: Second-Order ODE expandable manual classification override panel opened |
| [`post_03_fo_ode_semantic_sections_1280.png`](../screenshots/post_review/post_03_fo_ode_semantic_sections_1280.png) | `1280px` | After: First-Order ODE semantic sections (`NHẬP BÀI TOÁN`, `PHÂN TÍCH TỰ ĐỘNG`, `CƠ SỞ PHÂN LOẠI`, `PHƯƠNG PHÁP ĐỀ XUẤT`) |
| [`post_04_mobile_360_derivative_input.png`](../screenshots/post_review/post_04_mobile_360_derivative_input.png) | `360px` | After: Missing mobile Derivative input evidence (pairs directly with `before_07_mobile_360_derivative.png`) |
| [`post_05_mobile_360_derivative_result.png`](../screenshots/post_review/post_05_mobile_360_derivative_result.png) | `360px` | After: Mobile fraction-heavy Derivative result (`overflowX = 0`) |
| [`post_06_mobile_360_matrix_input.png`](../screenshots/post_review/post_06_mobile_360_matrix_input.png) | `360px` | After: Missing mobile Matrix Determinant input evidence (`overflowX = 0`, full-width header) |
| [`post_07_mobile_360_matrix_result.png`](../screenshots/post_review/post_07_mobile_360_matrix_result.png) | `360px` | After: Mobile 3×3 Matrix Determinant result (`overflowX = 0`, single-step deduplicated) |
| [`post_08_mobile_360_so_ode_equation_first.png`](../screenshots/post_review/post_08_mobile_360_so_ode_equation_first.png) | `360px` | After: Mobile Second-Order ODE Equation-First layout (`overflowX = 0`, pairs with `before_06_mobile_360_ode.png`) |
| [`post_09_tablet_768_cauchy_ivp_result.png`](../screenshots/post_review/post_09_tablet_768_cauchy_ivp_result.png) | `768px` | After: Tablet Second-Order Cauchy IVP input + 4-stage solution result (`overflowX = 0`) |
| [`post_10_desktop_1024_surface_integral_dynamic.png`](../screenshots/post_review/post_10_desktop_1024_surface_integral_dynamic.png) | `1024px` | After: Multivariable Surface Integral dynamic parameter controls (`overflowX = 0`) |
