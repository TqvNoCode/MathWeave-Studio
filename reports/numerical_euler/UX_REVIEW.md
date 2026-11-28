# UI/UX & Responsiveness Review — Explicit Euler Mode

## 1. Workflow & Information Architecture
- **Analytical Default Preserved:** Opening `Phương trình vi phân (ODE)` keeps `Giải tích (Nghiệm chính xác)` selected by default; all numerical inputs ($t_0, y_0, v_0, T, h$, analytical comparison checkbox) stay hidden until the user selects `Phương pháp Euler tiến (Explicit Euler)`.
- **Explicit Concept Separation:**
  - The workspace mode toggle clearly pairs `Giải tích (Nghiệm chính xác)` against `Phương pháp Euler tiến (Explicit Euler)`.
  - Inside numerical mode, quick examples and helper callouts distinguish Explicit Euler (a general numerical IVP approximation scheme) from Euler–Cauchy ODEs ($A t^2 y'' + B t y' + C y = g(t)$) and warn when an interval starts at, ends at, or crosses $t = 0$.
- **Clean 1st-Order vs. 2nd-Order IVP Forms:**
  - Order 1 displays $y' = f(t, y)$, initial $t_0$, initial $y_0 = y(t_0)$, endpoint $T$, and step size $h$.
  - Order 2 adds explicit initial derivative $v_0 = y'(t_0)$ cleanly separated from displacement $y_0 = y(t_0)$ and system equation $y'' = F(t, y, y')$.
- **7-Section Result Hierarchy (`numerical_result_view.py`):**
  1. Approximation & verification banner (honestly labels result as a numerical approximation, never exact).
  2. IVP summary & step metadata ($N$, $h$, final $h_{N-1}$, interval direction, runtime ms).
  3. Solution card with LaTeX initial problem and final approximation $y_N \approx y(T)$ (plus $v_N \approx y'(T)$ for 2nd-order).
  4. Interactive Plotly graph (`numerical_plot_service.py`) showing numerical trajectory, optional exact curve overlay, and collapsible $v_n \approx y'(t_n)$ velocity subplot for 2nd-order systems.
  5. Paginated numerical iteration table (`25` rows/page with First/Prev/Next/Last controls and compact 8-row preview toggle) + analytical error column $|y(t_n) - y_n|$ when available.
  6. Expandable 4-stage KaTeX pedagogical derivation viewer matching existing MathWeave conventions.
  7. Expandable independent verification badge & checklist (9 checks rendered cleanly).

## 2. Usability & Responsive Defect Caught and Fixed During QA
During mobile (`360px` / `390px`) live Chromium inspection, the Plotly chart legend in top-right overlapped the Plotly modebar and crowded the plot header. Updated `src/math_app/presentation/services/numerical_plot_service.py` to move the horizontal legend beneath the x-axis (`y=-0.22`) with expanded bottom margin, then re-verified across all 7 viewports with zero visual collisions.

## 3. Live Headless Chromium Verification (`chromium-1254`)
Tested interactively against `uv run python run.py --browser --no-show --port 8767` across **7 viewports × 2 ODE orders = 14 checks**:

| Viewport Width | Order | `innerWidth` / `scrollWidth` | Horizontal Overflow | KaTeX Nodes | Raw LaTeX Leaks | Main Plot Size (px) |
|---|---|---|---|---|---|---|
| `360px` | 1st-Order | `360` / `360` | `false` | `46` | `0` | `229 × 390` |
| `390px` | 1st-Order | `390` / `390` | `false` | `46` | `0` | `259 × 390` |
| `480px` | 1st-Order | `480` / `480` | `false` | `46` | `0` | `349 × 390` |
| `768px` | 1st-Order | `768` / `753` | `false` | `46` | `0` | `555 × 390` |
| `1024px` | 1st-Order | `1024` / `1009` | `false` | `46` | `0` | `811 × 390` |
| `1280px` | 1st-Order | `1280` / `1265` | `false` | `46` | `0` | `1067 × 390` |
| `1440px` | 1st-Order | `1440` / `1425` | `false` | `46` | `0` | `1114 × 390` |
| `360px` | 2nd-Order | `360` / `360` | `false` | `54` | `0` | `229 × 390` |
| `390px` | 2nd-Order | `390` / `390` | `false` | `54` | `0` | `259 × 390` |
| `480px` | 2nd-Order | `480` / `480` | `false` | `54` | `0` | `349 × 390` |
| `768px` | 2nd-Order | `768` / `753` | `false` | `54` | `0` | `555 × 390` |
| `1024px` | 2nd-Order | `1024` / `1009` | `false` | `54` | `0` | `811 × 390` |
| `1280px` | 2nd-Order | `1280` / `1265` | `false` | `54` | `0` | `1067 × 390` |
| `1440px` | 2nd-Order | `1440` / `1425` | `false` | `54` | `0` | `1114 × 390` |

*Note:* In 2nd-order view, the optional velocity plot $v_n \approx y'(t_n)$ resides inside a collapsed-by-default `ui.expansion` accordion (measuring `0 × 0` until expanded by the user).

**Interactive Checks Verified:**
- Stale result cleared automatically when `h` or input fields change (`stale_cleared_on_h_edit: true`).
- Switching back from numerical Euler to analytical ODE mode restores analytical UI cleanly (`switched_back_to_analytical: true`).
- Long table ($N = 100$) renders paginated controls cleanly (`desktop_1280_long_table_paginated.png`).
- Euler–Cauchy example and $t=0$ crossing singularity error card verified visually (`desktop_1280_euler_cauchy.png`, `desktop_1280_singularity_error.png`).

## 4. Captured Visual Evidence (`reports/numerical_euler/screenshots/`)
- `desktop_1440_first_order.png` — Desktop 1440px 1st-order Euler solve with exact comparison plot, table, and KaTeX steps
- `tablet_768_first_order.png` — Tablet 768px 1st-order responsive layout
- `mobile_390_first_order.png` — Mobile 390px 1st-order responsive layout (legend cleanly below x-axis)
- `mobile_360_first_order.png` — Mobile 360px compact viewport verification
- `desktop_1280_long_table_paginated.png` — Paginated table ($N=100$, 25 rows/page)
- `desktop_1440_second_order.png` — Desktop 1440px 2nd-order harmonic oscillator ($y'' = -y$)
- `mobile_360_second_order.png` — Mobile 360px 2nd-order responsive view
- `desktop_1280_euler_cauchy.png` — Desktop 1280px Euler–Cauchy numerical integration on $[1, 2]$
- `desktop_1280_singularity_error.png` — Desktop 1280px structured singularity error on $t=0$ crossing $[-1, 1]$
