# UI/UX Review — Live Headless Chromium QA

## 1. Visual & Functional Integration Summary

The nonhomogeneous Euler–Cauchy workflow extends the MathWeave Studio `v0.3.0` equation-first design system seamlessly:

- **Automatic Classification Card (`PHÂN TÍCH TỰ ĐỘNG`):** Displays badge `Phương trình Euler–Cauchy không thuần nhất`, normalized canonical equation $At^2 y'' + Bty' + Cy = g(t)$, associated homogeneous equation `Thuần nhất liên kết: ... = 0`, forcing term `Vế phải: g(t) = ...`, domain constraint hint avoiding $t = 0$, and preserves manual override (`Đổi phân loại thủ công`) and restore auto-detect (`Bật lại tự động`).
- **Method Recommendation Panel (`PHƯƠNG PHÁP ĐỀ XUẤT — EULER–CAUCHY KHÔNG THUẦN NHẤT`):** Appears dynamically when an Euler–Cauchy input is nonhomogeneous, displaying badge `Phương pháp tự động (Khuyến nghị)` and explaining Variation of Parameters without exposing inapplicable constant-coefficient undetermined-coefficients controls.
- **Result Classification Card & Breakdown:** Shows `Cấp 2 • Euler–Cauchy`, `Không thuần nhất`, `Biến thiên hằng số (Euler–Cauchy)`, and clean side-by-side decomposition under `CẤU TRÚC NGHIỆM: y(t) = y_c(t) + y_p(t)`.
- **4-Stage Pedagogical Step Viewer:** Stage 1 (Indicial setup + associated homogeneous identification), Stage 2 (Delta, $\{y_1, y_2\}$, Wronskian, $y_c$), Stage 3 (Normalization $P, Q, R$, $u_1', u_2'$, $u_1, u_2$, $y_p$, superposition $y = y_c + y_p$, and optional Cauchy IVP linear system), and Stage 4 (Independent symbolic verification).

## 2. Issues Found and Fixed During Live Headless Browser QA

1. **8.0s Compute Timeout on Non-Elementary Integrals ($g(t) = e^{t^2}$):**
   - **Observed:** First live QA run on `t^2*y'' - t*y' + y = exp(t^2), t > 0` hit NiceGUI's 8.0s computation timeout because SymPy's general `sp.integrate` spent ~9.63s in `heurisch`/hypergeometric search.
   - **Fix:** Checked `sp.integrate(transformed, tau, risch=True)` first in `_integrate_on_real_branch`. When SymPy returns `NonElementaryIntegral` (~0.04s), we immediately preserve exact symbolic `sp.Integral` without heuristic spin. Live UI solve time dropped from >8000ms (timeout) to ~2117ms end-to-end.
2. **360px Mobile Horizontal Overflow on Wide Integral Formulas:**
   - **Observed:** `test_h_mobile @ 360px` initially reported `overflowX = 43` due to wide $y_p(t)$ integral KaTeX output inside flex columns with `min-w-[200px]` and branch solution cards lacking scroll containers.
   - **Fix:** Added `min-w-0 sm:min-w-[200px] max-w-full overflow-x-auto` to the $y_c/y_p$ breakdown columns and `overflow-x-auto min-w-0` around branch solution `ui_math` blocks in `solution_view.py`. Re-verified `overflowX = 0` at `360px`.
3. **Math Casing Polish in `CẤU TRÚC NGHIỆM` Header:**
   - **Observed:** CSS `uppercase` on `ui_math_text` uppercased `$y(t) = y_c(t) + y_p(t)$` to `Y(T) = Y_C(T) + Y_P(T)`.
   - **Fix:** Styled the prefix `CẤU TRÚC NGHIỆM:` cleanly without `uppercase` transforming the inline KaTeX variables.

## 3. Live Chromium QA Matrix (`QT_QPA_PLATFORM=offscreen`)

Source script: headless Chromium (`PyQt6.QtWebEngineWidgets`) against live `run.py --browser --no-show` server.

| Case | Viewport | `overflowX` | `clippedCount` | KaTeX Rendered | Outcome & Interactive Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `test_b_general` (`t^2*y'' - t*y' + y = t^2, t > 0`) | `360px` | `0` | `0` | `135/135` | Result + $y_c/y_p$ breakdown rendered (`res=True, ycp=True`) |
| `test_b_general` | `390px` | `0` | `0` | `135/135` | Zero overflow, all badges & math crisp |
| `test_b_general` | `768px` | `0` | `0` | `135/135` | Clean tablet stacking |
| `test_b_general` | `1024px` | `0` | `0` | `135/135` | Full desktop flow |
| `test_b_general` | `1280px` | `0` | `0` | `135/135` | Full desktop flow |
| `test_b_general` | `1440px` | `0` | `0` | `135/135` | Full desktop flow (`251ms` load / `1914ms` ready) |
| `test_c_complex` (`t^2*y'' + t*y' + y = t, t > 0`) | `1440px` | `0` | `0` | `134/134` | Real $\cos/\sin(\ln t)$ basis + $y_p = t/2$ |
| `test_e_cauchy_ivp` (`..., y(1)=0, y'(1)=0`) | `1440px` | `0` | `0` | `158/158` | Unique Cauchy solution verified |
| `test_f_negative_domain` (`t < 0`) | `1440px` | `0` | `0` | `136/136` | Real $\ln(-t)$ domain rendering |
| `test_g_singular_t0` (`y(0)=1, y'(0)=0`) | `1440px` | `0` | `0` | `11/11` | Clean validation alert (`alert=True`, no traceback) |
| `test_h_nonelementary` (`exp(t^2), t > 0`) | `1440px` | `0` | `0` | `133/133` | Exact symbolic $\int$ KaTeX rendered (`int=True`, `~2117ms`) |
| `test_h_mobile` (`exp(t^2), t > 0`) | `360px` | `0` | `0` | `133/133` | Zero horizontal overflow (`ovX=0`) |

- Browser console errors: `0`
- Backend runtime tracebacks: `False`
- Interactive accordion expand/collapse: `true -> false -> true`

## 4. Curated Visual Evidence Screenshots

- [desktop_1440_general.png](file:///home/tqv/Desktop/CODE/Python/math_app/reports/euler_cauchy_nonhomogeneous/screenshots/desktop_1440_general.png)
- [desktop_1440_ivp.png](file:///home/tqv/Desktop/CODE/Python/math_app/reports/euler_cauchy_nonhomogeneous/screenshots/desktop_1440_ivp.png)
- [desktop_1440_nonelementary.png](file:///home/tqv/Desktop/CODE/Python/math_app/reports/euler_cauchy_nonhomogeneous/screenshots/desktop_1440_nonelementary.png)
- [tablet_768_general.png](file:///home/tqv/Desktop/CODE/Python/math_app/reports/euler_cauchy_nonhomogeneous/screenshots/tablet_768_general.png)
- [mobile_360_general.png](file:///home/tqv/Desktop/CODE/Python/math_app/reports/euler_cauchy_nonhomogeneous/screenshots/mobile_360_general.png)
