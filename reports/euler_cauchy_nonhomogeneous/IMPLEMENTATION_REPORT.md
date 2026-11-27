# Implementation Report — Euler–Cauchy Nonhomogeneous ODE Support

## 1. Mission & Baseline Preservation

This feature extends MathWeave Studio (`v0.3.0`) to solve **nonhomogeneous second-order Euler–Cauchy ordinary differential equations** of the form

$$A t^2 y'' + B t y' + C y = g(t), \qquad A \neq 0,\; g(t) \neq 0,$$

on connected regular intervals not crossing the regular singular point $t = 0$.

- **Verified v0.3.0 Baseline (`main` & tag `v0.3.0`):** `170ee84f1677ce4745bf53486581ca891fda0916`
- **Dedicated Feature Branch:** `feature/euler-cauchy-nonhomogeneous`
- **Protected Artifacts:** `main`, tag `v0.3.0`, and `pyproject.toml` version (`0.3.0`) were preserved completely unchanged.

## 2. Clean Architecture & Data Flow

All dependency boundaries specified in `AGENTS.md` were preserved (no NiceGUI/Plotly imports in domain, input, solver, or verification layers; UI invokes `SolveProblemUseCase` exclusively):

```text
Equation-First Input
  └─ parse_second_order_ode_input (src/math_app/input/ode_parser.py)
  └─ classify_second_order_ode (src/math_app/presentation/components/workspace/ode/second_order_classifier.py)
       ├─ Detects At^2 y'' + Bty' + Cy = g(t) (g != 0) without misclassifying constant-coeff ODEs
       ├─ Separates associated homogeneous equation & forcing term g(t), domain hint, & method hint
       └─ Routes to ProblemType.ODE_EULER_CAUCHY via SolveProblemUseCase
            ├─ ODEEulerCauchySolver.solve (src/math_app/solvers/calculus/ode/euler_cauchy_solver.py)
            │    ├─ Stage A: Associated homogeneous indicial solver -> {y1, y2}, Wronskian W(t), yc(t)
            │    ├─ Stage B: Variation of Parameters (_compute_euler_cauchy_vop, _integrate_on_real_branch)
            │    ├─ Stage C: Non-elementary Risch detection + exact sp.Integral preservation
            │    └─ Stage D: General superposition y = yc + yp or Cauchy IVP linear system (t0 != 0)
            └─ ODEVerifier.verify_second_order (src/math_app/verification/calculus/ode_verifier.py)
                 └─ Zero-width integral collapsing + independent residual & IC verification
  └─ Solution Presentation & Pedagogical Flow
       ├─ render_ode_classification_card (solution_view.py): yc / yp structural breakdown
       └─ enhance_ode_solution_flow -> _build_euler_cauchy_flow (ode_pedagogical_enhancer.py): 4 stages
```

## 3. Reused vs. Extended Components

### Reused Without Duplication
- `parse_second_order_ode_input` (`src/math_app/input/ode_parser.py`): reused for coefficient extraction, forcing remainder `rem_expr`, interval parsing, domain restrictions, and inline Cauchy initial conditions.
- `VariationOfParametersResult` & `extract_domain_restrictions_from_expr` (`src/math_app/solvers/calculus/ode/variation_of_parameters.py`).
- `validate_initial_point_against_domain` (`src/math_app/solvers/calculus/ode/nonhomogeneous_ivp.py`).
- Existing homogeneous Euler–Cauchy basis/indicial engine inside `ODEEulerCauchySolver`, kept as the single source of truth for $y_c(t)$.
- `render_ode_staged_steps_container` (`src/math_app/presentation/components/ode_staged_step_viewer.py`) and shared `ui_math` / `status_badge` components.

### Extended Files
1. `src/math_app/solvers/calculus/ode/euler_cauchy_solver.py`:
   - Extended `ODEEulerCauchySolver` to dispatch homogeneous ($g=0$) and nonhomogeneous ($g \neq 0$) cases cleanly.
   - Added `_compute_euler_cauchy_vop`, `_integrate_on_real_branch`, `_is_elementary_real_closed_form`, and `_build_vop_pedagogical_steps`.
   - Added positive-domain $\tau = |t| > 0$ substitution and Risch `NonElementaryIntegral` fast decision check (`0.04s` vs `>9.6s` heuristic timeout).
2. `src/math_app/verification/calculus/ode_verifier.py`:
   - Added `_collapse_zero_width_integrals` to collapse anchored definite integrals $\int_{t_0}^{t_0} f(s)\,ds = 0$ during Cauchy IVP evaluation.
   - Updated second-order verification residual string to include `- ({forcing_expr})` when nonhomogeneous.
3. `src/math_app/presentation/components/workspace/ode/second_order_classifier.py`:
   - Extended `SecondOrderClassificationSummary` with `is_nonhomogeneous`, `associated_homogeneous_latex`, `forcing_term_latex`, and `domain_hint`.
   - Added `_format_ec_lhs_latex` and separated homogeneous vs. nonhomogeneous Euler–Cauchy detection (`Phương trình Euler–Cauchy không thuần nhất`) before homogeneous branching.
4. `src/math_app/presentation/components/workspace/ode/ode_workspace.py`:
   - Updated summary card to render the nonhomogeneous badge, associated homogeneous equation, forcing term $g(t)$, and domain constraint, plus targeted `so_method_container` updates when toggling homogeneous $\leftrightarrow$ nonhomogeneous Euler–Cauchy.
5. `src/math_app/presentation/components/workspace/ode/ode_method_selector.py`:
   - Added read-only recommended method panel (`Phương pháp tự động (Khuyến nghị)` + Variation of Parameters overview) for nonhomogeneous Euler–Cauchy without exposing unsupported constant-coefficient undetermined-coefficients radios.
6. `src/math_app/presentation/components/workspace/ode/ode_classification_selector.py`, `ode_state.py`, & `operation_catalog.py`:
   - Updated Euler–Cauchy formula labels (`= g(t)`), descriptions, and added curated nonhomogeneous general, resonant, and Cauchy IVP examples while preserving all existing homogeneous examples.
7. `src/math_app/presentation/components/solution_view.py`:
   - Fixed nonhomogeneous flag handling for `ProblemType.ODE_EULER_CAUCHY` (`Biến thiên hằng số (Euler–Cauchy)`), extracted `y_c` and `y_p` via `polish_euler_cauchy_latex`, and added mobile `overflow-x-auto` containers.
8. `src/math_app/presentation/components/ode_pedagogical_enhancer.py`:
   - Extended `_extract_euler_cauchy_context` and `_build_euler_cauchy_flow` to produce 4 clear pedagogical stages for nonhomogeneous Euler–Cauchy while leaving the homogeneous 4-stage output unchanged.

### New Test Files
- `tests/unit/solvers/calculus/test_euler_cauchy_nonhomogeneous_solver.py`
- `tests/unit/presentation/test_euler_cauchy_nonhomogeneous_ui.py`
