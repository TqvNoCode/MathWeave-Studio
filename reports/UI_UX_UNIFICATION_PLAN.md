# MathWeave Studio — UI/UX Unification, Design System & Learning Experience Overhaul Plan

**Project:** MathWeave Studio v0.2.0 (Euler–Cauchy Integration Track; `pyproject.toml` version `0.2.0` preserved)  
**Working Branch:** `feat/unified-math-ui-ux`  
**Verified Backup Branch & Commit:** `feature/euler-cauchy-solver` @ `3fdec2abf4071795a930ecaf12d31df8d02c3ad8` (`origin/feature/euler-cauchy-solver`)  
**Date:** 2026-11-27

---

## 1. Executive Summary

MathWeave Studio has evolved rapidly across 34 mathematical operations (23 primary Screen A catalog cards + 11 secondary subtype/specialist workflows) spanning Differential Calculus, Integral Calculus, Equations & Algebra, Multivariable & Vector Calculus, Ordinary Differential Equations (First-Order, Second-Order Constant-Coefficient, Cauchy IVP, Euler–Cauchy, Reduction of Order, Wronskian), and Linear Algebra / Matrices.

While the mathematical core (`domain`, `input`, `solvers`, `verification`) is rigorous and passes 1,424 tests, the presentation layer accumulated two distinct interface dialects and several concrete usability/accessibility defects:
- Traditional Calculus & Vector Calculus workspaces render generic `"GIẢI PHƯƠNG TRÌNH"` primary buttons on non-equation tasks (`Đạo hàm`, `Tích phân`, `Giới hạn`, `Định lý Green`, etc.), while Matrix workspaces use a generic `"GIẢI PHÉP TOÁN MA TRẬN"` label rather than the specific matrix operation.
- Example chips (`ui.chip` without `color=None`) inherit Quasar's default medium-blue background (`rgb(88, 152, 212)`) paired with dark slate text, failing WCAG AA contrast and overflowing horizontally by 25px on `360px` mobile screens.
- Independent variable labels (`"Biến số / biến vi ..."`, `"Biến số độc..."`) truncate inside fixed `w-36` inputs.
- First-Order ODE pre-solve explanation cards are verbose before the Solve action and use `$g(t) \neq 0$` instead of the mathematically precise non-identically-zero notation `$g(t) \not\equiv 0$`.
- Second-Order ODE requires picking classification (`BƯỚC 1`) before entering an equation and lacks live classification detection + one-click sync banner (unlike First-Order ODE).
- Interactive plot/tool buttons use emoji prefixes without standardized Material icon accessibility, formula scroll containers lack `overflow-y-hidden` (`ode_staged_step_viewer.py:333`), and changing parameters/variables does not consistently clear stale results or disable repeat submissions.

This initiative establishes **"One Design System, Multiple Mathematical Workflows"**: shared design tokens, accessible high-contrast UI primitives, consistent layout and result hierarchy, beginner-friendly progressive disclosure, accurate mathematical notation, and mobile-safe responsiveness across `360px`–`1440px` while leaving the verified mathematical core untouched.

---

## 2. Current Application UX Audit

Baseline inspection of source code (`src/math_app/presentation/**`) and headless live rendering (`PyQt6.QtWebEngineWidgets` screenshots in `reports/ui_ux/screenshots/before/`):

| # | Severity | Area | Observed Defect (Verified in Code & Live Render) |
|---|---|---|---|
| 1 | High | Primary Action Labels | `app.py:839` hardcodes `"GIẢI PHƯƠNG TRÌNH"` for all calculus ops (`Đạo hàm`, `Tích phân`, `Giới hạn`, `Độ dài cung`, `Green/Stokes/Divergence`) and `"GIẢI PHÉP TOÁN MA TRẬN"` for all 9 matrix ops; `ode_workspace.py:579` uses `"GIẢI PHƯƠNG TRÌNH"` even for Wronskian & Second-Order ODE. |
| 2 | High | Chip Contrast & Mobile Overflow | Quasar `ui.chip(...)` defaults to `rgb(88, 152, 212)` background with dark slate text (`oklch(0.279 0.041 260.031)` — low contrast < 4:1). At `360px`, long Vietnamese chips push `scrollW=370 > clientW=345` (`overflowX=25px`, `before_06_mobile_360_ode.png`). |
| 3 | Medium | Truncated Input Labels | `w-36` on `var_input` truncates `"Biến số / biến vi phân"` -> `"Biến số / biến vi ..."` (`before_02`) and `"Biến số độc lập"` -> `"Biến số độc..."` (`before_03`, `before_04`). |
| 4 | Medium | Card & Header Hierarchy | Workspace card header puts badge next to long title+description causing badge wrap (`before_04`); `line-clamp-1` clips description in ODE mobile view (`before_06`). Second-Order cards have uneven button vertical alignment. |
| 5 | Medium | First-Order Pre-Solve Clutter | `ode_guided_classification_view.py` renders full expanded `BƯỚC 2` + `BƯỚC 3` + `BƯỚC 4` stacked before the Solve button (~1539px height before solving). |
| 6 | Medium | Mathematical Notation Precision | `first_order_classifier.py:290,316` uses `$g(t) \neq 0$`; `ode_classification_selector.py:125` uses `g(t) ≠ 0`; `ode_state.py:99` uses `g(t) ≠ 0` — implying pointwise non-zero rather than not identically zero ($g(t) \not\equiv 0$). |
| 7 | Medium | Second-Order Equation-First Flow | Second-Order ODE workspace shows classification cards before equation input with no live equation-type detection/sync helper when user types an Euler–Cauchy or Nonhomogeneous equation into another tab. |
| 8 | Low/Med | Mobile Formula & Flex Constraints | Fixed `min-w-[280px]`, `min-w-[240px]`, `w-56`, `w-64`, `w-60` in `app.py`, `ode_workspace.py`, `step_viewer.py`, `ode_staged_step_viewer.py` risk narrow-screen crowding; `ode_staged_step_viewer.py:333` lacks `overflow-y-hidden`. |
| 9 | Low/Med | Interaction & State Consistency | `app.py` does not clear `results_container` when `var_input` or extra parameters change; `solve_button` / `solve_btn` remain clickable during async execution; `problem_statement.py:491-495` has unreachable dead code; `?solve=1` only auto-solves ODEs, not generic workspaces. |
| 10 | Low | Accessibility & Focus Visibility | `styles.py` lacks global `:focus-visible` outlines for Quasar buttons/inputs/chips; tool buttons in `solution_view.py` use emoji strings (`⬅`, `🔍+`, `📊`) instead of uniform Material icons + `aria-label`; feedback/loading cards lack `role="status"` / `role="alert"`. |

---

## 3. Complete Module Inventory (All 34 Catalog Operations)

Audited directly from `src/math_app/presentation/components/operation_catalog.py` (23 `is_menu_card=True`, 11 `is_menu_card=False`):

| # | Module Name | ProblemType | Input Structure | Configuration | Classification | Result Layout | Solution Viewer | Special Components | Current UX Issues | Proposed UX Direction | Regression Risks |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Đạo hàm | `DERIVATIVE` | `f(x)` expr | Order `n` (1–10), variable | Automatic (non-ODE) | Standard card: `ĐỀ CHO` -> `ĐÁP SỐ` -> Domain -> Tools | `step_viewer` | Adaptive var chips, 2D plot, BBT | Button `GIẢI PHƯƠNG TRÌNH`; truncated var label; blue/dark chips | Action `TÍNH ĐẠO HÀM`, clean chips, clear var change | `order`, `target_var` binding |
| 2 | Đạo hàm riêng | `PARTIAL_DERIVATIVE` | Multivar `f(x,y,...)` | Partial var (`x,y,z`) | Automatic | Standard card + 3D plot tool | `step_viewer` | Adaptive multivar chips | Generic button label, chip contrast | Action `TÍNH ĐẠO HÀM RIÊNG`, preserve multivar chips | Multivariable var extraction |
| 3 | Tích phân bất định (Nguyên hàm) | `INDEFINITE_INTEGRAL` | `f(x)` expr | Integration var | Automatic | Standard card (`+ C`), 2D/BBT tools | `step_viewer` | Adaptive var chips | Generic `GIẢI PHƯƠNG TRÌNH` label | Action `TÍNH NGUYÊN HÀM` | Constant `+ C` rendering |
| 4 | Tích phân xác định | `DEFINITE_INTEGRAL` | `f(x)` expr | Bounds `[a, b]`, var | Manual subtype tabs (`Một biến/Đường/Mặt/Khối`) | Standard card | `step_viewer` | Subtype banner + bounds box | Generic button label; subtype banner styling | Action `TÍNH TÍCH PHÂN`, responsive bounds & banner | Subtype switching routes |
| 5 | Tích phân đường *(sec.)* | `LINE_INTEGRAL` | `f` or `P,Q,R` | Scalar/Vector, orient, `t`, `r(t)` | Subtype tab | Standard card | `step_viewer` | Parametric curve config | Fixed widths (`w-52`,`w-44`), generic button | Action `TÍNH TÍCH PHÂN ĐƯỜNG`, responsive grid | Param extraction & mode switch |
| 6 | Tích phân mặt *(sec.)* | `SURFACE_INTEGRAL` | `f` or `P,Q,R` | Scalar/Flux, orient, Graph/Parametric | Subtype tab | Standard card + 3D plot | `step_viewer` | Dynamic Graph vs Parametric form | Fixed `w-64/60/56`, stale results on mode switch | Action `TÍNH TÍCH PHÂN MẶT`, clear stale results on rebuild | `test_ux2_4` isolation & reset |
| 7 | Tích phân khối *(sec.)* | `TRIPLE_INTEGRAL` | `f(x,y,z)` | Descartes / Cylindrical / Spherical bounds | Subtype tab | Standard card | `step_viewer` | Dynamic coordinate bounds panel | Fixed `w-64`, stale bounds clearance | Action `TÍNH TÍCH PHÂN KHỐI`, responsive bounds | `test_ux2_4` coord isolation |
| 8 | Giới hạn hàm số | `LIMIT` | `f(x)` expr | Var, point `a`, direction `+-/+/-` | Automatic | Standard card | `step_viewer` | Quick preset chips (`0,+∞,-∞,1`) | Generic button, low-contrast preset chips | Action `TÍNH GIỚI HẠN`, unified chips | `oo`/`-oo` parsing |
| 9 | Giải phương trình | `SOLVE_EQUATION` | Equation / expr | Unknown var | Automatic | Standard card + numeric approx roots | `step_viewer` | Root approximation pill bar | Chip contrast, var truncation | Preserve `GIẢI PHƯƠNG TRÌNH` & root approx bar | Root approximation & complex roots |
| 10 | Độ dài cung | `ARC_LENGTH` | `f(x)` or `(x(t),y(t))` | Bounds `[a, b]`, var | Automatic | Standard card | `step_viewer` | Bounds panel | Generic button, chip contrast | Action `TÍNH ĐỘ DÀI CUNG`, clear stale results | Parametric comma input handling |
| 11 | Diện tích mặt cong | `SURFACE_AREA` | `z = f(x,y)` or `r(u,v)` | Domain `[x_min,x_max]×[y_min,y_max]` | Automatic | Standard card + 3D surface plot | `step_viewer` | Rect domain panel | Generic button, chip contrast | Action `TÍNH DIỆN TÍCH MẶT CONG`, 3D preservation | `u_min..v_max` keys |
| 12 | Mặt & Khối tròn xoay | `SURFACE_OF_REVOLUTION` | `y = f(x)` | Axis (`Ox/Oy`), `[a, b]`, var | Automatic | Standard card + 2D plot | `step_viewer` | Axis & interval box | Generic button, chip contrast | Action `TÍNH MẶT & KHỐI TRÒN XOAY` | `axis` `'x'`/`'y'` mapping |
| 13 | Định lý Green | `GREENS_THEOREM` | `P, Q` vector field | Circulation/Flux, rect `[x,y]` | Theorem mode | Dual verification summary | `step_viewer` | Vector theorem panel | Generic button, fixed `w-56` | Action `KIỂM CHỨNG ĐỊNH LÝ GREEN` | `circulation`/`flux` form param |
| 14 | Định lý Stokes | `STOKES_THEOREM` | `P, Q, R` field | Surface `z=g(x,y)`, domain `D` | Theorem mode | Dual verification summary | `step_viewer` | Surface & domain bounds | Generic button, chip contrast | Action `KIỂM CHỨNG ĐỊNH LÝ STOKES` | `surface_expr` param |
| 15 | Định lý Divergence | `DIVERGENCE_THEOREM` | `P, Q, R` field | Box `V` bounds | Theorem mode | Triple/flux summary | `step_viewer` | 3D box bounds | Generic button, chip contrast | Action `KIỂM CHỨNG ĐỊNH LÝ DIVERGENCE` | `z_max` bounds extraction |
| 16–20 | PTVP Cấp 1 (`LINEAR`, `HOMOGENEOUS`, `SEPARABLE`, `EXACT`, `INTEGRATING_FACTOR`) | 5 `ODE_*` types (1 main + 4 sec.) | Equation, var, opt IVP `y(t0)=y0` | General vs Cauchy IVP | Automatic (`classify_first_order_ode`) + sync banner | `ĐỀ CHO` -> `ĐÁP SỐ` -> Domain -> Branches | 4-stage `ode_staged_step_viewer` | Guided classification cards, IVP clear button | Verbose pre-solve Step 3, `$g(t)\neq 0$`, mobile chip overflow | Action `GIẢI PHƯƠNG TRÌNH VI PHÂN`, collapsible Step 3, `$g(t)\not\equiv 0$` | `test_ux3_7_1` (no `ui.expansion` inside guided view!), `test_ux3_6`, `border-rose-300` |
| 21–24 | PTVP Cấp 2 (`CONSTANT_COEFF`, `IVP`, `EULER_CAUCHY`, `REDUCTION_OF_ORDER`) | 4 `ODE_*` types (1 main + 3 sec.) | Equation (optional `, y0, y'0, interval`), var, opt `y1` | Classification, General vs IVP, Method (`AUTO/UC/VOP`) | Manual `BƯỚC 1` cards | `ĐỀ CHO` -> Classif & Method panel -> `ĐÁP SỐ` -> Domain -> Branches | 4-stage `ode_staged_step_viewer` | Classification cards, Cauchy IVP box, Reduction `y1` field | No live equation-type detect/sync banner, `g(t)≠0`, mobile overflow, Stage summary v-scroll | Action `GIẢI PHƯƠNG TRÌNH VI PHÂN CẤP 2`, live sync banner + manual override, `g(t)≢0` | `test_ec1_ux1`, `test_ode_final_r1`, `test_ode_screen_b`, `test_ux3_3..3_5` |
| 25 | Định thức Wronskian *(sec.)* | `WRONSKIAN` | `y1, y2`, var | Advanced SO tool card | Manual card | Wronskian value + linear independence | 4-stage or step viewer | Advanced tool toggle | Uses `GIẢI PHƯƠNG TRÌNH` instead of Wronskian label | Action `TÍNH ĐỊNH THỨC WRONSKIAN` | `test_ux3_3` `WRONSKIAN` test |
| 26–34 | Ma trận (`DET`, `INV`, `REF`, `RREF`, `TRANS`, `RANK`, `ADD_SUB`, `MUL`, `SOLVE_SYS`) | 9 `MATRIX_*` types (all main cards) | `[[...]]` / `A + B` / `A = b` | None | N/A | Standard card (`ĐỀ CHO` -> `ĐÁP SỐ`) + RREF/Gauss steps | `step_viewer` | `matrix_helper` syntax & quick templates | All 9 share identical `GIẢI PHÉP TOÁN MA TRẬN`; `determine_contextual_tools` stays False | Operation-specific action labels (`TÍNH ĐỊNH THỨC`, etc.), keep `matrix_helper` | `test_ux2_3_matrix_workspace_and_button_label`, no plot/table tools |

---

## 4. Design Principles

1. **One Design System, Multiple Mathematical Workflows:** Shared tokens (`tokens.py`), typography, borders (`border-slate-200`), Academic Blue accent (`#2563eb`), surfaces (`#ffffff` on `#f8fafc`), and button/card primitives govern every screen, while each mathematical domain keeps the exact specialized inputs and viewers it requires.
2. **Beginner-Friendly by Default:** A new learner sees what to enter, required parameters/modes, examples, and a crystal-clear module-specific action button first — without scrolling past walls of pre-solve theory.
3. **Progressive Disclosure (Three Levels):**
   - *Level 1 — Essential:* Main expression/equation/matrix input, variable & required parameters/bounds/ICs, mode toggle, high-contrast example chips, primary action.
   - *Level 2 — Learning:* Automatic classification summary & canonical form, `p(t)/g(t)` cards, expandable classification reasoning, step-by-step / 4-stage derivations.
   - *Level 3 — Advanced:* Domain & singular-point panels, branch interval breakdown, Wronskian & Reduction of Order tools, interactive 2D/3D Plotly graphs & variation tables, residual verification diagnostics.
4. **Honest & Accurate Mathematical Presentation:** Distinguish `$g(t) \not\equiv 0$` from `$g(t) \neq 0$`; keep original/normalized domain restrictions and `VerificationStatus` honesty untouched.

---

## 5. Proposed Shared Architecture

Presentation stays strictly in `src/math_app/presentation/`, consuming only `ProblemType`, `ProblemRequest`, `SolutionResponse`, `OperationDef`, and `SolveProblemUseCase`:
- `design_system/tokens.py` + `design_system/styles.py`: Single source of color, spacing, radius, elevation, typography, keyboard focus, and mobile CSS rules.
- `components/shared/`: Small, single-responsibility composable factories:
  - `section_card.py`, `primary_button.py`, `status_badge.py` (existing, enhanced)
  - `action_labels.py` (new — single authoritative mapping from `ProblemType` to primary button label, icon, and accessible `aria-label`)
  - `workspace_header.py` (new — unified workspace identity row)
  - `example_chips.py` (new — accessible high-contrast wrapping example/preset chips)
  - `feedback_cards.py` (new — semantic loading/alert/empty state cards with ARIA live regions)
- Feature workspaces (`app.py`, `workspace/matrix_helper.py`, `workspace/variable_selector.py`, `workspace/ode/*`) compose shared primitives cleanly without merging incompatible forms into a single mega-component.

---

## 6. Component Inventory (Reused vs. New)

- **Reused & Hardened:** `create_page_shell`, `render_app_header`, `render_sticky_nav_bar`, `render_back_button`, `render_footer`, `render_operation_catalog`, `render_operation_card`, `render_verification_badge`, `render_domain_restrictions`, `render_adaptive_variable_selector`, `render_matrix_helper_panel`, `render_ode_workspace`, `render_ode_mode_selector`, `render_ode_method_selector`, `render_ode_classification_selector`, `render_ode_guided_classification_view`, `render_solution_view`, `render_steps_container`, `render_ode_staged_steps_container`.
- **New Shared Primitives:** `action_labels.py`, `workspace_header.py`, `example_chips.py`, `feedback_cards.py`.

---

## 7. Module-Specific Exceptions

- **Matrix Operations (9):** Retain list/vector matrix input format, `render_matrix_helper_panel`, and suppress 2D/3D/variation-table tools (`determine_contextual_tools` -> `(False, False, False)`).
- **Multivariable & Vector Calculus (7):** Retain coordinate system selectors, Graph vs Parametric toggles, vector component prompts, and circulation/flux/axis selectors.
- **First-Order ODE (5):** Retain 4-stage pedagogical viewer and automatic classification (`classify_first_order_ode`), plus live cross-category sync banner (`test_ux3_7_1` constraint: zero `ui.expansion` elements inside guided classification view).
- **Second-Order ODE & Euler–Cauchy (4 + Wronskian):** Retain manual classification cards (`BƯỚC 1`) for direct exploration + add non-intrusive live detection & one-click sync banner + Cauchy IVP conflict checking + independent branch/singular-point verification displays.

---

## 8. Autonomous Milestone Breakdown

| Milestone | Scope | Key Outputs |
|---|---|---|
| **M1: Design System Foundation & Shared Primitives** | Tokens, focus-visible & mobile CSS, `action_labels.py`, `workspace_header.py`, `example_chips.py`, `feedback_cards.py`, shell/header/badge polish | Foundation primitives + M1 report |
| **M2: Calculus, Algebra, Matrix & Multivariable Workspaces** | Unify `app.py` workspace header, chips, module-specific action buttons across all 24 non-ODE ops, mobile-safe parameter grids, stale-result clearing & loading disable | Updated `app.py`, helpers, targeted tests + M2 report |
| **M3: ODE Workspaces & Mathematical Precision** | First-Order collapsible `BƯỚC 3` reasoning, `$g(t) \not\equiv 0$` precision, Second-Order live equation-type detection + sync banner, mobile ODE inputs, Wronskian action label | Updated ODE components + M3 report |
| **M4: Result Summary & Solution Viewers** | Unified result summary cards, accessible Material-icon plot toolbar, fix Stage 2 vertical scrollbar & narrow-screen flex widths in step viewers | Updated `solution_view.py`, `step_viewer.py`, `ode_staged_step_viewer.py` + M4 report |
| **M5: Responsive (360–1440px), A11y, Regression & Visual QA** | Dedicated unification regression suite, live QtWebEngine audit across all 7 widths, capture 14 `after_*` screenshots & fix any defects | `test_ui_ux_unification.py`, 14 `after_*` screenshots + M5 report |

---

## 9. Dependencies & Constraints

- **Sequential dependencies:** M1 must land before M2/M3/M4 so all workspaces consume identical primitives (`action_labels`, `example_chips`, `workspace_header`, `feedback_cards`). M5 runs after M2–M4 stabilize.
- **Protected core:** `src/math_app/solvers/`, `src/math_app/input/`, `src/math_app/verification/`, `src/math_app/domain/` are strictly read-only.
- **Preserved contracts:** `tests/unit/presentation/test_ux3_7_1_*.py` (no `ui.expansion` in First-Order guided view), `test_ux3_4_1_defect_remediation.py:253` (`border-rose-300`), `test_operation_catalog.py` (`34 / 23 / 11`).

---

## 10. Acceptance Criteria

1. 100% of 34 catalog operations render cleanly with accurate module-specific primary action labels (zero unrelated `"GIẢI PHƯƠNG TRÌNH"` buttons).
2. High-contrast example chips (`>= 4.5:1`), visible `:focus-visible` rings, non-color-only verification/alert indicators, and accessible button `aria-label`s.
3. Zero unintended horizontal page overflow (`scrollWidth <= clientWidth`) at `360, 390, 480, 768, 1024, 1280, 1440` px across catalog, Calculus, ODE, and Matrix workflows.
4. Accurate mathematical notation (`$g(t) \not\equiv 0$`), beginner-friendly First-Order progressive disclosure, and Second-Order live detection + manual override preserved.
5. `uv run pytest -q`, `uv run ruff check src/ tests/`, `git diff --check`, and `uv lock --check` all exit `0` with zero weakened assertions and zero changes to `pyproject.toml` (`0.2.0`) or protected core.

---

## 11. Regression Strategy

- Run targeted `tests/unit/presentation/` suites after every milestone (M1–M4).
- Add `tests/unit/presentation/test_ui_ux_unification.py` covering all 34 operations' labels/mounting, state isolation, stale-result clearance, notation accuracy, and representative valid/invalid module submissions.
- Run complete `uv run pytest -q` (baseline `1424 passed`) and `ruff` before declaring completion.

---

## 12. Visual Testing Strategy

- Headless `PyQt6.QtWebEngineWidgets` (`QT_QPA_PLATFORM=offscreen`) drives the real NiceGUI server (`build_application()` + `create_app()`).
- Verify all 7 breakpoints (`360, 390, 480, 768, 1024, 1280, 1440` px) programmatically for `scrollW <= clientW`, rendered KaTeX nodes, zero raw LaTeX leaks, and no clipped controls.
- Save 14 `after_*` comparison screenshots under `reports/ui_ux/screenshots/after/` paired against `reports/ui_ux/screenshots/before/` and inspect rendered PNGs directly.

---

## 13. Expected Deliverables

1. Verified GitHub backup on `feature/euler-cauchy-solver` (`3fdec2abf4071795a930ecaf12d31df8d02c3ad8`)
2. Uncommitted UI/UX implementation on `feat/unified-math-ui-ux`
3. `reports/UI_UX_UNIFICATION_PLAN.md`
4. `reports/ui_ux/milestones/M1..M5_*.md`
5. `reports/ui_ux/screenshots/before/` & `reports/ui_ux/screenshots/after/`
6. `docs/UI_UX_DESIGN_SYSTEM.md`
7. `reports/UI_UX_UNIFICATION_FINAL_REPORT.md`
