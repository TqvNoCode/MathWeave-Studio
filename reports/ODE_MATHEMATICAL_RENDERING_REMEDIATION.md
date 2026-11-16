# MathWeave Studio — Mathematical Output Correction & Global Rendering Remediation Report

**Date:** 2026-11-15  
**Version:** 0.1.1  
**Author:** Antigravity 3.8 Flash High  
**Branch:** `test`  
**Commit Baseline:** `2cefff9a0fb59bd64c8d64fc015cd9dbe408c042`  
**Test Suite Status:** 363 passed, 1 pre-existing warning, 0 failures (in 24.16s)  
**Linter Status:** Ruff 0 errors (clean)  
**Architecture Boundary Status:** 5/5 boundary contracts verified  
**Pre-Implementation Backup:** `../backups/mathweave-studio/mathweave_studio_backup_20261115_173602.tar.gz`

---

## 1. Executive Summary

This remediation report documents the comprehensive resolution of two critical user-facing issues and two theoretical mathematical edge cases in MathWeave Studio:

1. **Issue A (Second-Order ODE Radical Degradation):** The second-order ODE solver previously produced mathematical steps where square-root radicals ($\sqrt{\Delta}$) were absent or rendered as unformatted raw Python strings (`sqrt(33)`). In initial value problems such as $2y'' + y' - 4y = 0$, $y(0)=0$, $y'(0)=1$, characteristic roots, derivative steps, the Cauchy linear system for $C_1, C_2$, and the particular solution exhibited missing radicals or unrendered algebraic fragments.
2. **Issue B (Global Unformatted Inline Math Strings):** Explanatory text descriptions throughout Calculus (derivatives, integrals, limits), Linear Algebra (matrix arithmetic, determinants, inverses, rank, Gaussian elimination), and First-Order ODEs contained raw Python/SymPy strings (e.g. `d/dx(x) = 1`, `det(A) = ad - bc`, `mu(t) = exp(...)`, `1 / (2*sqrt(x))`). These were displayed as plain text without mathematical styling because the frontend rendered step descriptions via `ui.label`.
3. **Issue C (Wronskian Correctness Remediation):** In the previous implementation, evaluating $W(y_1, y_2) \equiv 0$ for arbitrary functions falsely concluded linear dependence with a green `VERIFIED` badge. Mathematically, by Peano's classical theorem (1889), $W \equiv 0$ for arbitrary differentiable functions is **inconclusive**. Linear dependence is only guaranteed when $y_1, y_2$ are solutions to a common linear homogeneous ODE with continuous coefficients on a connected interval (Abel's theorem).
4. **Issue D (Reduction of Order Domain Regression):** Reduction of order for variable-coefficient equations such as the Euler–Cauchy equation $2t^2y'' + 3ty' - y = 0$ with known solution $y_1(t) = 1/t$ was previously unverified on negative intervals ($t < 0$).

All four issues have been comprehensively diagnosed, remediated across the application, verified with automated tests, and documented.

---

## 2. Root-Cause Analysis

### 2.1 Root Cause of Missing Radicals in Second-Order ODE
Tracing the data flow from `SecondOrderConstantCoeffSolver` to `StepViewer`:
- In `second_order_constant_coeff_solver.py`, the solver formatted step descriptions using Python f-strings interpolating raw SymPy objects `{r1}` and `{r2}`:
  ```python
  description=f"Hai nghiệm thực phân biệt: r1 = {r1}, r2 = {r2}"
  ```
  SymPy's default string conversion `str(r1)` outputs `-1/4 + sqrt(33)/4`.
- When passed to `StepViewer`, `step_viewer.py` rendered `step.description` using `ui.label(step.description)`. NiceGUI's `ui.label` outputs plain HTML text (`<div>-1/4 + sqrt(33)/4</div>`), bypassing KaTeX/MathML entirely.
- Furthermore, SymPy's default LaTeX generator `sp.latex` factored out common rational denominators into $-\frac{1}{4} + \frac{\sqrt{33}}{4}$ rather than the canonical single-fraction textbook quadratic formula $\frac{-1 + \sqrt{33}}{4}$.
- In the Cauchy IVP substitution, the first derivative equation was merged into a generic step rather than articulated as a dedicated pedagogical derivative step, causing the radical coefficients in $y'(t)$ to be obscured.

### 2.2 Root Cause of Cross-Application Raw Inline Strings
- Across all solvers (`power_rule.py`, `trig_rule.py`, `rule_engine.py`, `matrix_solver.py`, `linear_solver.py`), step authors wrote descriptive text with embedded ASCII math formulas (`"det(A) = ad - bc"`, `"d/dx(u*v) = u'v + uv'"`).
- Because no shared inline rendering layer existed, `StepViewer` had no choice but to display `step.description` as plain text.
- Previous attempts to use KaTeX delimiters (`$...$`) inside `ui.label` failed because `ui.label` does not process KaTeX or MathML.

---

## 3. Shared Rendering Architecture & Clean Architecture Boundaries

To resolve the root cause permanently without violating Clean Architecture boundaries, a pure rendering module and presentation adapter were established:

```
┌────────────────────────────────────────────────────────┐
│                   Domain Layer                         │
│  (Pure business models, SolutionStep, ExpressionContent)│
└───────────────────────────▲────────────────────────────┘
                            │
┌───────────────────────────┴────────────────────────────┐
│                  Rendering Layer                       │
│  src/math_app/rendering/                               │
│  ├── latex/formatter.py: normalize_latex,              │
│  │   format_quadratic_root_latex                       │
│  └── text_math_renderer.py:                            │
│      ├── convert_latex_to_mathml()                     │
│      ├── delimit_unwrapped_math_in_text()              │
│      └── render_math_in_text_html()                    │
│  (Zero dependencies on NiceGUI, Web, or Plotly)        │
└───────────────────────────▲────────────────────────────┘
                            │
┌───────────────────────────┴────────────────────────────┐
│                 Presentation Layer                     │
│  src/math_app/presentation/components/                 │
│  ├── math_view.py: ui_math_text()                      │
│  └── step_viewer.py: render_step(),                    │
│      render_substep_compact()                          │
│  (Invokes render_math_in_text_html -> ui.html)         │
└────────────────────────────────────────────────────────┘
```

### Architectural Guarantees
1. **Purity of Solvers and Rendering**: `text_math_renderer.py` and `formatter.py` contain zero imports of `nicegui`, `plotly`, or GUI frameworks. Solvers produce pure DTOs containing mathematical LaTeX strings.
2. **HTML Sanitization & Anti-XSS**: All non-mathematical text in `render_math_in_text_html` is escaped via `html.escape()`. Inside mathematics blocks (`$ ... $` or `$$ ... $$`), LaTeX expressions are parsed by `latex2mathml` into strictly validated XML `<math>` elements. Any unescaped `<script>`, `<img onerror=...>`, or raw HTML tags are sanitized.
3. **Automatic Fallback for Unwrapped Math**: `delimit_unwrapped_math_in_text()` uses targeted regex heuristics to detect ASCII math (e.g. `sqrt(...)`, `x**2`, `1/(2*sqrt(x))`, `det(A)`) and automatically wraps them into `$ ... $`, ensuring legacy solver steps without explicit delimiters are rendered as textbook MathML.

---

## 4. Detailed Verification of the Reported Problem

### 4.1 Problem Specification
```text
Equation: 2y'' + y' - 4y = 0
Initial Conditions: y(0) = 0, y'(0) = 1
Independent Variable: t
```

### 4.2 Mathematical Derivation
1. **Characteristic Equation**:
   $$2r^2 + r - 4 = 0$$
   Coefficients: $a = 2$, $b = 1$, $c = -4$.
2. **Discriminant Calculation**:
   $$\Delta = b^2 - 4ac = 1^2 - 4(2)(-4) = 1 + 32 = 33 > 0$$
   The discriminant is strictly positive, yielding two distinct real roots.
3. **Characteristic Roots with Radical Preservation**:
   $$\sqrt{\Delta} = \sqrt{33}$$
   $$r_1 = \frac{-b + \sqrt{\Delta}}{2a} = \frac{-1 + \sqrt{33}}{4}, \qquad r_2 = \frac{-b - \sqrt{\Delta}}{2a} = \frac{-1 - \sqrt{33}}{4}$$
4. **Fundamental Solutions & General Solution**:
   $$y_1(t) = e^{\frac{-1+\sqrt{33}}{4}t}, \qquad y_2(t) = e^{\frac{-1-\sqrt{33}}{4}t}$$
   $$y(t) = C_1 e^{\frac{-1+\sqrt{33}}{4}t} + C_2 e^{\frac{-1-\sqrt{33}}{4}t}$$
5. **Dedicated First Derivative Equation**:
   $$y'(t) = C_1 r_1 e^{r_1 t} + C_2 r_2 e^{r_2 t} = C_1 \left(\frac{-1+\sqrt{33}}{4}\right) e^{\frac{-1+\sqrt{33}}{4}t} + C_2 \left(\frac{-1-\sqrt{33}}{4}\right) e^{\frac{-1-\sqrt{33}}{4}t}$$
6. **Cauchy 2x2 Linear System at $t_0 = 0$**:
   $$\begin{cases} y(0) = C_1 + C_2 = 0 \\ y'(0) = \left(\frac{-1+\sqrt{33}}{4}\right) C_1 + \left(\frac{-1-\sqrt{33}}{4}\right) C_2 = 1 \end{cases}$$
7. **Resolution of Exact Constants**:
   From $C_2 = -C_1$:
   $$\left(\frac{-1+\sqrt{33}}{4} - \frac{-1-\sqrt{33}}{4}\right) C_1 = 1 \implies \frac{2\sqrt{33}}{4} C_1 = 1 \implies \frac{\sqrt{33}}{2} C_1 = 1$$
   $$C_1 = \frac{2}{\sqrt{33}} = \frac{2\sqrt{33}}{33}, \qquad C_2 = -\frac{2}{\sqrt{33}} = -\frac{2\sqrt{33}}{33}$$
8. **Particular Solution**:
   $$y(t) = \frac{2\sqrt{33}}{33} e^{\frac{-1+\sqrt{33}}{4}t} - \frac{2\sqrt{33}}{33} e^{\frac{-1-\sqrt{33}}{4}t} = \frac{2\sqrt{33}}{33} \left(e^{\frac{\sqrt{33}t}{2}} - 1\right) e^{-\frac{(1+\sqrt{33})t}{4}}$$
9. **Independent Invariant Residual Verification**:
   $$R(t) = 2y''(t) + y'(t) - 4y(t) \equiv 0$$
   $$y(0) = 0, \qquad y'(0) = 1$$
   Symbolic residual simplification confirms exact identity zero ($R(t) \equiv 0$).

### 4.3 Rendered MathML Snippet Verification
In automated test `tests/unit/solvers/calculus/test_ode_second_order_constant_coeff_solver.py::test_reported_problem_square_root_preservation_and_ivp`, the rendered HTML of step descriptions was verified:
- `step.description` contains `$\frac{-1 + \sqrt{33}}{4}$`.
- `render_math_in_text_html(step.description)` outputs:
  ```xml
  <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline">
    <mrow>
      <msub><mi>r</mi><mn>1</mn></msub>
      <mo>=</mo>
      <mfrac>
        <mrow><mo>-</mo><mn>1</mn><mo>+</mo><msqrt><mn>33</mn></msqrt></mrow>
        <mn>4</mn>
      </mfrac>
    </mrow>
  </math>
  ```
  The `<msqrt><mn>33</mn></msqrt>` tag is verified to be present in Step 3 (roots), Step 4 (general solution), Step 5 (derivative), Step 6 (Cauchy system), and Step 7 (particular solution).

---

## 5. Cross-Application Mathematical Rendering Remediation

The remediation was extended across all four major functional areas:

| Module | Before (Raw Plain Text) | After (Textbook MathML) |
|---|---|---|
| **Calculus: Power Rule** | `u'(x) = n * x^(n-1)` | `$u'(x) = n \cdot x^{n-1}$` $\to$ `<msup><mi>x</mi><mrow><mi>n</mi><mo>-</mo><mn>1</mn></mrow></msup>` |
| **Calculus: Trig Rule** | `1 / sqrt(1 - x^2)` | `$\frac{1}{\sqrt{1 - x^2}}$` $\to$ `<mfrac><mn>1</mn><msqrt>...</msqrt></mfrac>` |
| **Calculus: Integration** | `int 1/x dx = ln|x| + C` | `$\int \frac{1}{x}\,dx = \ln|x| + C$` $\to$ `<mo>∫</mo><mfrac><mn>1</mn><mi>x</mi></mfrac>` |
| **Calculus: Limits** | `x -> a` | `$x \to a$` $\to$ `<mi>x</mi><mo>→</mo><mi>a</mi>` |
| **Linear Algebra: Det 2x2** | `det(A) = ad - bc = (a)*(d) - (b)*(c)` | `$\det(A) = ad - bc = (a)\cdot(d) - (b)\cdot(c)$` |
| **Linear Algebra: Inverse** | `A^(-1) = (1/det(A)) * adj(A)` | `$A^{-1} = \frac{1}{\det(A)} \cdot \operatorname{adj}(A)$` |
| **Linear Algebra: Row Ops** | `R_i <- R_i - (c)*R_k` | `$R_i \leftarrow R_i - (c) \cdot R_k$` |
| **ODE 1: Integrating Factor**| `mu(t) = exp(int P dt)` | `$\mu(t) = e^{\int P(t)\,dt}$` |
| **ODE 2: Cauchy IVP** | `C1 + C2 = 0` | `$\begin{cases} C_1 + C_2 = y_0 \\ r_1 C_1 + r_2 C_2 = v_0 \end{cases}$` |

---

## 6. Wronskian Correctness Remediation (Peano vs. Abel)

### 6.1 The Mathematical Problem
In the original implementation, any pair of functions satisfying $W(y_1, y_2) \equiv 0$ was declared linearly dependent with a green `VERIFIED` badge.

This is mathematically false for arbitrary functions:
- **Peano's Counterexample (1889):** Consider $y_1(t) = t^2$ and $y_2(t) = t|t|$ on $\mathbb{R}$.
  - Both functions are continuously differentiable on $\mathbb{R}$ ($y_1'(t) = 2t$, $y_2'(t) = 2|t|$).
  - For $t > 0$: $W = t^2(2t) - (2t)(t^2) = 0$.
  - For $t < 0$: $W = t^2(-2t) - (2t)(-t^2) = 0$.
  - At $t = 0$: $W(0) = 0$.
  - Hence $W(y_1, y_2)(t) \equiv 0$ everywhere on $\mathbb{R}$.
  - However, $y_1$ and $y_2$ are **linearly independent** on $\mathbb{R}$: if $c_1 t^2 + c_2 t|t| = 0$, evaluating at $t = 1 \implies c_1 + c_2 = 0$ and at $t = -1 \implies c_1 - c_2 = 0$, forcing $c_1 = c_2 = 0$.

### 6.2 The Remediated Logic
1. **Arbitrary Function Pairs**: If $W(y_1, y_2) \equiv 0$ without a verified common linear homogeneous ODE, the result is reported as:
   - `VerificationStatus.UNVERIFIED` (inconclusive).
   - `SolutionStatus.UNVERIFIED` (amber badge, never green).
   - An educational explanation citing Peano's counterexample is provided.
2. **Solutions of a Common Linear Homogeneous ODE**: By Abel's theorem, if $y_1, y_2$ are solutions of $y'' + p(t)y' + q(t)y = 0$ with continuous $p(t), q(t)$ on a connected interval $I$, then $W(y_1, y_2)(t) = W(t_0) \exp\left(-\int_{t_0}^t p(s)\,ds\right)$. Here, $W \equiv 0$ if and only if $y_1, y_2$ are linearly dependent. In MathWeave Studio, linear dependence is reported as `VERIFIED` only when this common ODE hypothesis is verified.

---

## 7. Reduction of Order Negative Interval Support

For variable-coefficient equations, such as Euler-Cauchy equations:
$$2t^2 y'' + 3t y' - y = 0, \qquad y_1(t) = \frac{1}{t}$$
Normalized standard form:
$$y'' + \frac{3}{2t}y' - \frac{1}{2t^2}y = 0 \implies p(t) = \frac{3}{2t}$$
First-order reduction for $u = v'$:
$$u(t) = \frac{e^{-\int p(t)\,dt}}{y_1(t)^2} = \frac{e^{-\frac{3}{2}\ln|t|}}{t^{-2}} = |t|^{-3/2} t^2 = |t|^{1/2}$$

### Domain Analysis:
- On $t > 0$: $u(t) = \sqrt{t} \implies v(t) = \frac{2}{3}t^{3/2} \implies y_2(t) \propto \sqrt{t}$.
- On $t < 0$: $u(t) = \sqrt{-t} \implies v(t) = -\frac{2}{3}(-t)^{3/2} \implies y_2(t) \propto \sqrt{-t}$.
- At $t = 0$: $a(0) = 0$, creating a singular point that separates the domain into $(-\infty, 0)$ and $(0, +\infty)$.

Automated test `test_euler_cauchy_negative_interval_domain_regression` verifies:
1. $y_2(t) = \sqrt{-t}$ satisfies $2t^2 y_2'' + 3t y_2' - y_2 \equiv 0$ on $t < 0$.
2. Wronskian $W(y_1, y_2)(-1) = 3/2 \ne 0$.
3. $y_2(t) = \sqrt{t}$ satisfies the ODE on $t > 0$ with $W(y_1, y_2)(1) = 3/2 \ne 0$.
4. Domain restriction alerts user to the singularity at $t = 0$.

---

## 8. Security Evaluation

1. **Strict Input Sanitization**:
   - `html.escape()` sanitizes all plain-text segments.
   - Any `<script>`, `<iframe>`, or HTML event handler (`onerror`, `onclick`) is rendered inert as `&lt;script&gt;` or `&lt;img ...&gt;`.
   - Verified by `tests/unit/rendering/test_text_math_renderer.py::test_xss_payload_safety_escaping`.
2. **Safe MathML Generation**:
   - Only mathematical LaTeX inside `$ ... $` is converted by `latex2mathml` into standard `<math>` tags.
   - Disallowed constructs or invalid LaTeX do not crash the app; they safely fall back to escaped text.
3. **AST Bounding**:
   - The ODE parser enforces a maximum input length of 500 characters, maximum AST depth of 15, maximum node count of 120, and bounds exponents to 100.
   - `eval`, `exec`, and unrestricted `sympify` are strictly banned.
4. **Process Isolation**:
   - Long-running symbolic calculations execute inside isolated child processes with an 8.0-second hard timeout.

---

## 9. Verification Results & Test Metrics

### 9.1 Test Execution Summary
- **Baseline Test Count (Prior to Remediation)**: 290 passing tests.
- **Milestone 2 Intermediate Count**: 349 passing tests.
- **Post-Remediation Final Count**: **363 passed, 1 warning in 24.16 seconds**.
- **Failed Tests**: **0**.
- **Skipped Tests**: **0**.

```text
============================= test session starts ==============================
platform linux -- Python 3.14.8, pytest-9.1.1, pluggy-1.7.0
rootdir: /home/tqv/Desktop/CODE/Python/math_app
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.15.1, cov-7.1.0
collected 363 items

tests/architecture/test_boundaries.py .....                              [  1%]
tests/golden/test_derivative_golden.py ....                              [  2%]
tests/golden/test_unified_pedagogical_derivation.py .......              [  4%]
tests/unit/application/test_solve_problem.py ........                    [  6%]
tests/unit/domain/test_dtos.py ...                                       [  7%]
tests/unit/input/test_parser_validator.py ............                   [ 10%]
tests/unit/input/test_second_order_ode_parser.py ...........             [ 13%]
tests/unit/input/test_security_remediation.py ..........                 [ 16%]
tests/unit/presentation/test_analysis_service.py ........                [ 18%]
tests/unit/presentation/test_branding_and_footer.py .....                [ 20%]
tests/unit/presentation/test_comprehensive_fixes_regression.py ......... [ 22%]
tests/unit/presentation/test_full_multivariable_pipeline.py ............ [ 26%]
tests/unit/presentation/test_integration_and_3d_axes_regression.py ..... [ 29%]
tests/unit/presentation/test_operation_catalog.py ......                 [ 31%]
tests/unit/presentation/test_problem_statement.py ........               [ 33%]
tests/unit/presentation/test_server_config.py ...                        [ 34%]
tests/unit/presentation/test_shutdown_lifecycle.py ...                   [ 35%]
tests/unit/presentation/test_solution_view_rendering.py ........         [ 37%]
tests/unit/presentation/test_startup_mode.py ..............              [ 41%]
tests/unit/presentation/test_submission_pipeline_regression.py ......... [ 43%]
tests/unit/presentation/test_ui_rendering_regression.py ........         [ 46%]
tests/unit/rendering/test_latex_formatter.py ...                         [ 46%]
tests/unit/rendering/test_text_math_renderer.py ........                 [ 49%]
tests/unit/solvers/algebra/test_equation_solver.py .......               [ 50%]
tests/unit/solvers/calculus/test_derivation_regression.py .....          [ 52%]
tests/unit/solvers/calculus/test_derivative_extended.py .......          [ 54%]
tests/unit/solvers/calculus/test_derivative_solver.py .....              [ 55%]
tests/unit/solvers/calculus/test_geometry_solvers.py .....               [ 57%]
tests/unit/solvers/calculus/test_integral_solver.py ....                 [ 58%]
tests/unit/solvers/calculus/test_limit_solver.py ...                     [ 58%]
tests/unit/solvers/calculus/test_line_integral_solver.py ...             [ 59%]
tests/unit/solvers/calculus/test_ode_comprehensive_matrix.py ........... [ 64%]
tests/unit/solvers/calculus/test_ode_integrating_factor_solver.py ...... [ 65%]
tests/unit/solvers/calculus/test_ode_linear_solver.py ................   [ 70%]
tests/unit/solvers/calculus/test_ode_reduction_of_order_solver.py ...... [ 72%]
tests/unit/solvers/calculus/test_ode_second_order_constant_coeff_solver.py ............. [ 76%]
tests/unit/solvers/calculus/test_ode_separable_and_exact_solvers.py .... [ 79%]
tests/unit/solvers/calculus/test_rules.py .......                        [ 81%]
tests/unit/solvers/calculus/test_second_order_ode_pipeline.py .....      [ 82%]
tests/unit/solvers/calculus/test_surface_integral_solver.py ...          [ 83%]
tests/unit/solvers/calculus/test_triple_integral_solver.py ...           [ 84%]
tests/unit/solvers/calculus/test_vector_calculus_solvers.py ....         [ 85%]
tests/unit/solvers/calculus/test_wronskian_solver.py ......              [ 87%]
tests/unit/solvers/linear_algebra/test_matrix_solver.py ............     [ 90%]
tests/unit/test_contracts.py ........                                    [ 92%]
tests/unit/verification/test_derivative_verifier.py ...                  [ 93%]
tests/unit/verification/test_integral_verifier.py ......                 [ 95%]
tests/unit/verification/test_ode_verifier.py ...............             [ 99%]
tests/unit/verification/test_surface_area_verifier.py ...                [100%]

======================= 363 passed, 1 warning in 24.16s ========================
```

### 9.2 Linter Verification
Command: `uv run ruff check .`  
Result: **All checks passed! (0 errors)**

### 9.3 Clean Architecture Boundary Verification
Command: `uv run pytest tests/architecture/test_boundaries.py`  
Result: **5/5 passed (Domain, Application, Rendering, and Solvers completely decoupled from NiceGUI/Plotly)**

---

## 10. Version Bump & Documentation Updates

1. **Version Bump**:
   - `pyproject.toml`: Updated `version = "0.1.1"` and updated description to: `"MathWeave Studio — Phần mềm Hỗ trợ Học tập & Nghiên cứu Toán học Chuyên sâu, giải phương trình vi phân"`.
   - `src/math_app/__init__.py`: Updated fallback version to `"0.1.1"`.
   - `tests/unit/presentation/test_branding_and_footer.py`: Synchronized version tests with `0.1.1`.
2. **Changelog**:
   - `CHANGELOG.md`: Added release notes for `## [0.1.1] - 2026-11-15` documenting global MathML rendering, ODE 2 radical preservation, Wronskian logic correction, and reduction of order negative domain support.
3. **User Documentation**:
   - `README.md` & `README.vi.md`: Bumped status badges to `v0.1.1`, documented native MathML rendering engine.
   - `docs/USER_GUIDE.md`: Added detailed worked examples of ODE 2 radical preservation, Peano Wronskian warning, and reduction of order negative interval domain support.
   - `docs/ODE_ROADMAP.md`: Updated Section 4.4 with Peano and Abel criteria, added Section 4.6 on global MathML remediation, and added negative interval domain specifications.
4. **Git & Release Constraints**:
   - No branches were switched; work remains on `test`.
   - No merges, commits, pushes, or public releases were performed.
