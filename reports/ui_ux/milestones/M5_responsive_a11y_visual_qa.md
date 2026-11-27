# Milestone 5 Report — Application-Wide Responsive (360–1440px), Accessibility, Regression & Visual QA

**Milestone:** M5  
**Status:** Completed  
**Branch:** `feat/unified-math-ui-ux`

## 1. Scope & Objectives
Validate the unified UI/UX across all 34 catalog operations, test representative valid and invalid workflows for every module group, verify keyboard focus & non-color-only ARIA accessibility, audit all 7 required responsive breakpoints (`360px`–`1440px`), capture 14 `after_*` screenshots under `reports/ui_ux/screenshots/after/`, and visually inspect live renders to eliminate defects.

## 2. Live Visual Defects Found & Resolved During M5
1. **Collapsed Equation Input in ODE Workspaces:** Caught via `after_06` and `after_08` initial captures where placing `so_detect_container` / `variable_selector` inside the same `md:flex-nowrap` row collapsed `eq_input` width. Resolved by placing `eq_input` (`w-full` + `clearable`) on its own primary line above `so_detect_container` and the variable row (`ode_workspace.py`, `variable_selector.py`).
2. **360px Residual 18px Overflow:** Caught in initial `after_13` (`scrollW=363 > clientW=345`). Resolved by hiding the redundant sticky-nav `math_icon` on `xs` (`hidden sm:flex`) and allowing clean flex wrapping in `workspace_header.py` and `sticky_nav_bar.py`. After re-capture, **all 19 live scenarios (across 360, 390, 480, 768, 1024, 1280, 1440px) measured `overflowX = 0`**.
3. **Stepper Badge Wrapping:** Added `whitespace-nowrap` on the 4-stage stepper badge in `ode_staged_step_viewer.py` so stage labels (`2. μ(t)`) remain single-line pills.

## 3. Responsive QA Matrix (All 7 Required Breakpoints)

| Viewport | Tested Scenario(s) | `clientW` | `scrollW` | `overflowX` | Math Rendered | Raw LaTeX Leaks | Status |
|---|---|---|---|---|---|---|---|
| `360px` | Second-Order ODE, Matrix Determinant | `345px` | `345px` | `0` | `8/8`, `8/8` | `[]` | PASS |
| `390px` | Second-Order ODE | `375px` | `375px` | `0` | `8/8` | `[]` | PASS |
| `480px` | First-Order ODE | `465px` | `465px` | `0` | `16/16` | `[]` | PASS |
| `768px` | Derivative Result | `753px` | `753px` | `0` | `25/25` | `[]` | PASS |
| `1024px` | Surface Integral (subtype UI) | `1009px` | `1009px` | `0` | `2/2` | `[]` | PASS |
| `1280px` | Catalog, Calculus, Algebra, ODE1, ODE2, Euler–Cauchy, IVP, Matrix, Green's | `1265px` | `1265px` | `0` | 100% (`2/2`–`174/174`) | `[]` | PASS |
| `1440px` | First-Order ODE Result | `1425px` | `1425px` | `0` | `76/76` | `[]` | PASS |

## 4. Test & Lint Additions
- Created `tests/unit/presentation/test_ui_ux_unification.py` covering all 34 operations' CTA labels & Screen B mounting, shared primitives, chip contrast, First-Order `$g(t) \not\equiv 0$` + Step 3 toggle, Second-Order auto-detection & sync banner, stale-result clearing, single-step deduplication (including LHS-prefixed matrix determinants), representative valid/invalid submissions across all major module groups, and independent-review regressions (`preserve_equation=True`, Stage-4 verification honesty, dependent Wronskian, sticky nav title sync, one-shot query params, ODE independent variable pool `["t", "x"]`, and Quasar badge palette mapping — 18 tests passing in 15.40s).
- Re-captured all 14 `after_*.png` screenshots post-review (`task-778`): `14/14` scenarios measured `overflowX = 0`, `badLatex = []`, and `100%` KaTeX rendering.
