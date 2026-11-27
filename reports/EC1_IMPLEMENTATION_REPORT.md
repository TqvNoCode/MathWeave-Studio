# EC1 Implementation Review Report: Second-Order Euler–Cauchy ODE Solver

**Milestone**: ODE-EC1 (hardened in ODE-EC1-R1)  
**Project**: MathWeave Studio v0.3.0  
**Feature Branch**: `feature/euler-cauchy-solver` (based on `origin/main` @ commit `c2f3f1d`)  
**Date**: 2026-11-26  
**Status**: Feature Complete & Hardened (EC1-R1 Verified)  

---

## 1. Implementation Summary

Milestone **ODE-EC1** introduces a dedicated, mathematically rigorous second-order Euler–Cauchy ordinary differential equation solver to MathWeave Studio. 

The solver handles homogeneous second-order Euler–Cauchy equations of the form:
$$a\,t^2\,y''(t) + b\,t\,y'(t) + c\,y(t) = 0 \qquad (a \neq 0)$$
where $a, b, c$ are finite real constants, and the equation is defined away from the singular point $t = 0$.

Key architectural and mathematical highlights:
1. **Mathematical Core**: Implemented `ODEEulerCauchySolver` in `src/math_app/solvers/calculus/ode/euler_cauchy_solver.py`, deriving the authoritative indicial polynomial $A\,m(m-1) + B\,m + C = 0$ ($A\,m^2 + (B-A)m + C = 0$) using exact SymPy arithmetic. All three characteristic root cases (distinct real, repeated real, and complex conjugate) are classified strictly using SymPy assumptions (`delta.is_positive`, `delta.is_zero`, `delta.is_negative`) with purely real representations.
2. **Strict Domain & Singularity Handling**: Preserves original source-domain metadata (`original_domain_restrictions`, `original_denominators`, `leading_coeffs`, `original_domain_constraints`) and the leading coefficient singularity at $t = 0$. Structured interval parsing (`parse_interval_constraint`) preserves exact requested intervals (e.g., `(2, +oo)`, `(-oo, -1)`, `(1, 5)`, `[1, 4]`), rejects intervals containing $t = 0$, and rejects unsupported interval syntax without silently broadening to $\mathbb{R} \setminus \{0\}$. In natural domain mode, disconnected intervals receive independent integration constants ($C_1, C_2$, $C_3, C_4$, etc.).
3. **Cauchy IVP Support**: Solves complete Cauchy Initial Value Problems ($y(t_0) = y_0$, $y'(t_0) = v_0$) for $t_0 \neq 0$ on the connected component containing $t_0$ via exact $2 \times 2$ Cramer's rule linear system resolution, validating finite realness of `t0`, `y0`, `v0` and source-domain admissibility before solving.
4. **Pedagogical Integration**: Built a 4-stage pedagogical solution pipeline in `_build_euler_cauchy_flow()` in `ode_pedagogical_enhancer.py` whose Stage 4 verification state (`is_completed`, badge color, summary LaTeX, intermediate results) faithfully reflects the actual `VerificationResult` (`VERIFIED`, `UNVERIFIED`, `FAILED`).
5. **Clean Architecture & UI Routing**: Integrated through `ProblemType.ODE_EULER_CAUCHY` across domain (`_ODE_PROBLEM_TYPES`), use cases, operation catalog, state management, and NiceGUI classification selector cards without altering existing constant-coefficient or reduction-of-order solvers.
6. **Zero Regressions & Quality Assurance**: 100% test pass rate across the entire repository (`1392 passed` in `uv run pytest -q`, `571 passed` in `tests/unit/solvers/calculus/`, `76 passed` in `tests/unit/solvers/calculus/test_euler_cauchy_solver.py`). Full Ruff linting (`uv run ruff check src/ tests/`), git diff whitespace (`git diff --check`), and package lockfile validation (`uv lock --check`) passed.

---

## 2. Exact List of Changed and Newly Created Files

### 2.1 Newly Created Files (Source & Tests)
1. `src/math_app/solvers/calculus/ode/euler_cauchy_solver.py` (2,037 lines)
   - Core mathematical solver class `ODEEulerCauchySolver`.
   - Structural equation validation ($A = a(t)/t^2, B = b(t)/t, C = c(t)$) requiring proven realness and finiteness.
   - Source-domain metadata preservation (`_build_domain_metadata`) and structured `ParsedIntervalConstraint` validation.
   - Indicial equation derivation, assumption-based discriminant classification, and real basis construction.
   - Cauchy IVP $2 \times 2$ linear system solver and independent `ODEVerifier` pipeline with fundamental-system Wronskian gate.
   - Honest verification-status propagation in `_build_solution_steps()`.
2. `tests/unit/solvers/calculus/test_euler_cauchy_solver.py` (1,108 lines)
   - 76 unit and regression tests (including parametrized cases) covering all root cases, explicit & shifted intervals, unsupported interval rejection, preserved source-domain restrictions, conservative coefficient/discriminant/Cauchy validation, Wronskian verification gate, and mocked verifier status propagation.

### 2.2 Review Artifacts (Excluded from Source Patch)
1. `reports/ec1_euler_cauchy.patch` (original EC1 patch snapshot)
2. `reports/ec1_euler_cauchy_r1.patch` (4,723 lines; unified diff covering all 19 source/test/changelog files)
3. `reports/EC1_IMPLEMENTATION_REPORT.md` (this implementation report)
4. `reports/EC1_R1_IMPLEMENTATION_REPORT.md` (EC1-R1 hardening report)

### 2.3 Modified Existing Files
1. `CHANGELOG.md` (+15)
2. `src/math_app/domain/models.py` (+2) — Added `ProblemType.ODE_EULER_CAUCHY` and registered it in `_ODE_PROBLEM_TYPES`.
3. `src/math_app/input/ode_parser.py` (+394/-4) — Added `ParsedIntervalConstraint`, `parse_interval_constraint()`, top-level clause splitting, and `interval_spec` on `ParsedODE` / `ParsedSecondOrderODE`.
4. `src/math_app/main.py` (+4) — Registered `ODEEulerCauchySolver` in `build_application()`.
5. `src/math_app/verification/calculus/ode_verifier.py` (+186/-3) — Added `ODEVerifier.verify_fundamental_system()` and integrated `fundamental_solutions` gate into `verify_second_order()`.
6. `src/math_app/solvers/calculus/ode/__init__.py` (+2) — Exported `ODEEulerCauchySolver` in `__all__`.
7. `src/math_app/presentation/components/problem_statement.py` (+3)
8. `src/math_app/presentation/components/operation_catalog.py` (+19)
9. `src/math_app/presentation/components/workspace/ode/ode_state.py` (+38/-2)
10. `src/math_app/presentation/components/workspace/ode/ode_classification_selector.py` (+40/-1)
11. `src/math_app/presentation/components/workspace/ode/ode_method_selector.py` (+14)
12. `src/math_app/presentation/components/ode_pedagogical_enhancer.py` (+242/-18) — Added `_build_euler_cauchy_flow()` with faithful `VERIFIED`/`UNVERIFIED`/`FAILED` Stage 4 propagation.
13. `src/math_app/presentation/components/ode_staged_step_viewer.py` (+23/-4) — Updated progress stepper and Stage 4 verification header badge for `VERIFIED`, `UNVERIFIED`, and `FAILED` states.
14. `tests/unit/presentation/test_ux3_1_ode_workspace.py` (+4/-2)
15. `tests/unit/presentation/test_ode_pedagogical_solution_flow.py` (+79)
16. `tests/unit/presentation/test_design_system_and_catalog.py` (+3/-1)
17. `tests/unit/presentation/test_operation_catalog.py` (+8/-3)

---

## 3. Mathematical Implementation Details

### 3.1 Structural Verification
Given an equation parsed via `parse_second_order_ode_input()`:
$$a(t)\,y'' + b(t)\,y' + c(t)\,y = g(t)$$
The solver verifies:
1. Homogeneity: $g(t) = 0$. If $g(t) \neq 0$, the solver returns `CANNOT_SOLVE` explaining that nonhomogeneous Euler–Cauchy equations are out of scope.
2. Variable Power Ratios:
   $$A = \text{simplify}\left(\frac{a(t)}{t^2}\right), \quad B = \text{simplify}\left(\frac{b(t)}{t}\right), \quad C = \text{simplify}(c(t))$$
   The solver checks that $A, B, C$ are finite, real, and independent of $t$, with $A \neq 0$. If any condition fails, the equation is rejected.

### 3.2 Trial Solution and Indicial Equation Derivation
Assuming $y(t) = t^m$ for $t \neq 0$:
$$y'(t) = m\,t^{m-1}, \qquad y''(t) = m(m-1)\,t^{m-2}$$
Substitution yields:
$$A\,t^2\left[m(m-1)\,t^{m-2}\right] + B\,t\left[m\,t^{m-1}\right] + C\,t^m = 0$$
Factoring out $t^m$:
$$A\,m(m-1) + B\,m + C = 0 \iff A\,m^2 + (B - A)\,m + C = 0$$
Discriminant:
$$\Delta = (B - A)^2 - 4AC$$

Exact quadratic discriminant classification uses SymPy's symbolic sign assumptions (`delta.is_positive`, `delta.is_zero`, `delta.is_negative`):
- `delta.is_positive is True` $\implies$ `DISTINCT` ($m_{1,2} = \frac{-(B-A) \pm \sqrt{\Delta}}{2A}$)
- `delta.is_zero is True` $\implies$ `REPEATED` ($m = -\frac{B-A}{2A}$)
- `delta.is_negative is True` $\implies$ `COMPLEX` ($\alpha = -\frac{B-A}{2A}$, $\beta = \frac{\sqrt{-\Delta}}{2|A|}$)
- Otherwise $\implies$ conservative rejection (`CANNOT_SOLVE`, `VerificationStatus.UNVERIFIED`, `indicial_discriminant_unresolved`) without numerical approximation.

---

## 4. Euler–Cauchy Root Classification Results

The characteristic roots are classified into three exhaustive cases:

### Case A: Two Distinct Real Roots ($\Delta > 0$)
- **Roots**: $m_1 \neq m_2 \in \mathbb{R}$.
- **Fundamental System**:
  - For $t > 0$: $y_1(t) = t^{m_1}$, $y_2(t) = t^{m_2}$.
  - For $t < 0$: $y_1(t) = (-t)^{m_1}$, $y_2(t) = (-t)^{m_2}$.
- **General Solution**:
  - $t > 0$: $y(t) = C_1\,t^{m_1} + C_2\,t^{m_2}$
  - $t < 0$: $y(t) = C_1\,(-t)^{m_1} + C_2\,(-t)^{m_2}$
- **Canonical Example**: $t^2 y'' + 4t y' + 2y = 0 \implies m^2 + 3m + 2 = 0 \implies m_1 = -1, m_2 = -2$.
  $$y(t) = C_1 t^{-1} + C_2 t^{-2} = \frac{C_1}{t} + \frac{C_2}{t^2} \quad (t > 0)$$

### Case B: Repeated Real Root ($\Delta = 0$)
- **Roots**: $m_1 = m_2 = m \in \mathbb{R}$.
- **Fundamental System**:
  - For $t > 0$: $y_1(t) = t^m$, $y_2(t) = t^m \ln t$.
  - For $t < 0$: $y_1(t) = (-t)^m$, $y_2(t) = (-t)^m \ln(-t)$.
- **General Solution**:
  - $t > 0$: $y(t) = t^m\left(C_1 + C_2 \ln t\right)$
  - $t < 0$: $y(t) = (-t)^m\left(C_1 + C_2 \ln(-t)\right)$
- **Canonical Example**: $t^2 y'' - 3t y' + 4y = 0 \implies m^2 - 4m + 4 = 0 \implies m = 2$.
  $$y(t) = t^2\left(C_1 + C_2 \ln t\right) \quad (t > 0)$$

### Case C: Complex-Conjugate Roots ($\Delta < 0$)
- **Roots**: $m_{1,2} = \alpha \pm i\beta$ with $\beta > 0$.
- **Fundamental System**:
  - For $t > 0$: $y_1(t) = t^\alpha \cos(\beta \ln t)$, $y_2(t) = t^\alpha \sin(\beta \ln t)$.
  - For $t < 0$: $y_1(t) = (-t)^\alpha \cos(\beta \ln(-t))$, $y_2(t) = (-t)^\alpha \sin(\beta \ln(-t))$.
- **General Solution**:
  - $t > 0$: $y(t) = t^\alpha\left[C_1 \cos(\beta \ln t) + C_2 \sin(\beta \ln t)\right]$
  - $t < 0$: $y(t) = (-t)^\alpha\left[C_1 \cos(\beta \ln(-t)) + C_2 \sin(\beta \ln(-t))\right]$
- **Canonical Example**: $t^2 y'' + t y' + y = 0 \implies m^2 + 1 = 0 \implies \alpha = 0, \beta = 1$.
  $$y(t) = C_1 \cos(\ln t) + C_2 \sin(\ln t) \quad (t > 0)$$

---

## 5. Positive and Negative Domain Handling

The leading coefficient $a(t) = A\,t^2$ vanishes at $t = 0$, making $t = 0$ a regular singular point.

1. **Natural Domain $\mathbb{R} \setminus \{0\}$**:
   When no interval is specified, the natural domain consists of two disconnected components: $(0, \infty)$ and $(-\infty, 0)$.
   The solver returns both branches using `BranchSolution` with independent constants:
   - Branch 1 ($t \in (0, \infty)$): $y(t) = C_1\,y_1(t) + C_2\,y_2(t)$
   - Branch 2 ($t \in (-\infty, 0)$): $y(t) = C_3\,y_1(-t) + C_4\,y_2(-t)$
   This prevents mathematically invalid global connection across the singularity.
2. **Specified Positive Interval ($a > 0$)**:
   The active variable is $t > 0$. Basis functions use $t^m$ and $\ln t$.
3. **Specified Negative Interval ($b < 0$)**:
   The active variable is strictly negative. To maintain real-valued functions for arbitrary real exponents $m$, the substitution $\tau = -t > 0$ is employed. Basis functions strictly use $(-t)^m$ and $\ln(-t)$, guaranteeing real outputs without imaginary residuals.
4. **Intervals Containing or Crossing Zero ($t = 0$)**:
   Rejected immediately with status `CANNOT_SOLVE` (`method="singular_point_interval"`) and error message:
   `"Khoảng xác định yêu cầu '{interval_raw}' chứa điểm kỳ dị t = 0 của phương trình vi phân Euler–Cauchy. Nghiệm không tồn tại qua điểm kỳ dị này."`
5. **Initial Value Problems**:
   The connected component is determined by the sign of $t_0$:
   - If $t_0 > 0$: solved on $(0, \infty)$.
   - If $t_0 < 0$: solved on $(-\infty, 0)$.
   - If $t_0 = 0$: rejected with `CANNOT_SOLVE` identifying $t_0 = 0$ as a regular singular point without asserting mathematical nonexistence.

---

## 6. Cauchy IVP Verification Results

For Cauchy IVP requests ($y(t_0) = y_0$, $y'(t_0) = v_0$ at $t_0 \neq 0$):
$$\begin{pmatrix} y_1(t_0) & y_2(t_0) \\ y_1'(t_0) & y_2'(t_0) \end{pmatrix} \begin{pmatrix} C_1 \\ C_2 \end{pmatrix} = \begin{pmatrix} y_0 \\ v_0 \end{pmatrix}$$
The coefficient determinant is the Wronskian $W(y_1, y_2)(t_0) \neq 0$.
Integration constants $C_1, C_2$ are evaluated exactly using Cramer's rule.

### Independent SymPy Verification Protocol
Every solution is submitted to `ODEVerifier.verify_second_order(..., fundamental_solutions=(y1, y2))`, which enforces:
1. **Differential Residual**:
   $$\mathcal{R}(t) = \text{simplify}\left(a(t) y''(t) + b(t) y'(t) + c(t) y(t)\right) \stackrel{?}{=} 0$$
2. **Initial Condition Residuals** (when IVP):
   $$y(t_0) - y_0 \stackrel{?}{=} 0, \qquad y'(t_0) - v_0 \stackrel{?}{=} 0$$
3. **Fundamental System Linear Independence (`ODEVerifier.verify_fundamental_system`)**:
   Symbolic Wronskian verification gate confirming $W(y_1, y_2) \neq 0$, real, finite, and pole-free on the selected connected interval.
4. **Domain Invariants**: Absence of complex artifacts or divisions by zero on the designated interval.

All verification display metadata in `_build_solution_steps()` and `_build_euler_cauchy_flow()` strictly reflects the actual `VerificationStatus` (`VERIFIED`, `UNVERIFIED`, or `FAILED`).

---

## 7. Complete Test Execution Logs and Exit Codes (EC1-R1 Final Verification)

### 7.1 Dedicated Euler–Cauchy Unit Test Suite
Command: `uv run pytest -q tests/unit/solvers/calculus/test_euler_cauchy_solver.py`  
Exit Code: `0`  
Result: `76 passed in 4.14s`

### 7.2 Calculus Test Suite
Command: `uv run pytest -q tests/unit/solvers/calculus/`  
Exit Code: `0`  
Result: `571 passed in 79.96s (0:01:19)`

### 7.3 Full Repository Test Suite
Command: `uv run pytest -q`  
Exit Code: `0`  
Result: `1392 passed, 2 warnings in 163.04s (0:02:43)`  
Warnings:
- `tests/unit/presentation/test_analysis_service.py::test_2d_plot_sampling_arbitrary_viewport`: `RuntimeWarning: invalid value encountered in sqrt` (pre-existing viewport plot sampling test).
- `tests/unit/test_windows_metadata_and_signing.py::test_setup_test_shutdown_endpoint_security_and_activation`: `StarletteDeprecationWarning` regarding `httpx` / `starlette.testclient`.

---

## 8. Ruff and Formatting Results

### 8.1 Ruff Linter
Command: `uv run ruff check src/ tests/`  
Exit Code: `0` (`All checks passed!`)

### 8.2 Git Whitespace & Line Ending Check
Command: `git diff --check`  
Exit Code: `0`

### 8.3 Package Lockfile Check
Command: `uv lock --check`  
Exit Code: `0` (`Resolved 90 packages in 1ms`)

---

## 9. Application Routing and UI Integration Results

1. **Operation Catalog**:
   - `ProblemType.ODE_EULER_CAUCHY` registered with 5 canonical examples:
     - `t^2*y'' + 4*t*y' + 2*y = 0`
     - `t^2*y'' + 4*t*y' + 2*y = 0, y(1) = 3, y'(1) = -3`
     - `t^2*y'' - 3*t*y' + 4*y = 0`
     - `t^2*y'' + t*y' + y = 0`
     - `x^2*y'' - 2*x*y' + 2*y = 0`
2. **ODE Workspace Classification**:
   - `ODEClassification.EULER_CAUCHY` added as a primary second-order card in `ode_classification_selector.py`.
   - Grid updated to 3-column layout (`grid-cols-1 md:grid-cols-3`):
     - Card 1: Tuyến tính thuần nhất cấp 2 ($y'' + p y' + q y = 0$)
     - Card 2: Tuyến tính không thuần nhất cấp 2 ($y'' + p y' + q y = g(t)$)
     - Card 3: Phương trình Euler–Cauchy ($a t^2 y'' + b t y' + c y = 0$)
3. **Cauchy Mode Support**:
   - Euler–Cauchy equations allow both "Nghiệm tổng quát" (General Solution) and "Bài toán Cauchy (IVP)" modes.
   - Initial conditions $y(t_0) = y_0$, $y'(t_0) = v_0$ are input through standard Cauchy controls.
4. **Pedagogical Solution Flow**:
   - `enhance_ode_solution_flow` generates 4 distinct stages via `_build_euler_cauchy_flow()`:
     - Stage 1: `Giai đoạn 1: Phương trình chỉ số`
     - Stage 2: `Giai đoạn 2: Biệt thức Delta và Hệ nghiệm cơ bản`
     - Stage 3: `Giai đoạn 3: Xác định nghiệm bài toán`
     - Stage 4: `Giai đoạn 4: Kiểm chứng toán học độc lập` (badge, completion flag, and summary LaTeX driven by `VerificationStatus`).

---

## 10. Known Limitations and Unresolved Issues

1. **Nonhomogeneous Euler–Cauchy Equations**:
   Equations of the form $a t^2 y'' + b t y' + c y = g(t)$ with $g(t) \neq 0$ are explicitly rejected with `CANNOT_SOLVE`. Supporting nonhomogeneous forms via Variation of Parameters or substitution $t = e^z$ is planned for a subsequent release.
2. **Higher-Order Euler–Cauchy ($n \ge 3$)**:
   The current implementation focuses strictly on second-order equations ($n=2$).
3. **Regular Singular Points ($t_0 = 0$)**:
   Cauchy initial value problems specified at $t_0 = 0$ cannot be solved using standard continuous integration constants; Frobenius series expansions near $t = 0$ are not part of milestone ODE-EC1 / EC1-R1.
4. **Symbolic Interval Endpoints & Parametric Coefficients**:
   Interval bounds containing unresolved free symbols (e.g., `t > a`) and unresolved parametric coefficients (`k*t^2*y'' + ...`) are conservatively rejected rather than partitioned symbolically.

---

## 11. Full Git Diff and Reviewable Patch File

The hardened EC1-R1 reviewable source/test patch file has been saved to:
`reports/ec1_euler_cauchy_r1.patch` (4,723 lines, strictly excluding `reports/`).

It can be inspected or applied against `HEAD` using:
```bash
git apply --stat reports/ec1_euler_cauchy_r1.patch
git apply --check reports/ec1_euler_cauchy_r1.patch
```

### Exact Patch Diff Stat (`git apply --stat reports/ec1_euler_cauchy_r1.patch`)
```text
 CHANGELOG.md                                       |   15 
 src/math_app/domain/models.py                      |    2 
 src/math_app/input/ode_parser.py                   |  394 ++++
 src/math_app/main.py                               |    4 
 .../components/ode_pedagogical_enhancer.py         |  242 ++
 .../components/ode_staged_step_viewer.py           |   23 
 .../presentation/components/operation_catalog.py   |   19 
 .../presentation/components/problem_statement.py   |    3 
 .../workspace/ode/ode_classification_selector.py   |   40 
 .../workspace/ode/ode_method_selector.py           |   14 
 .../components/workspace/ode/ode_state.py          |   38 
 src/math_app/solvers/calculus/ode/__init__.py      |    2 
 src/math_app/verification/calculus/ode_verifier.py |  186 ++
 .../presentation/test_design_system_and_catalog.py |    3 
 .../test_ode_pedagogical_solution_flow.py          |   79 +
 tests/unit/presentation/test_operation_catalog.py  |    8 
 .../unit/presentation/test_ux3_1_ode_workspace.py  |    4 
 .../solvers/calculus/ode/euler_cauchy_solver.py    | 2037 ++++++++++++++++++++
 .../solvers/calculus/test_euler_cauchy_solver.py   | 1108 +++++++++++
 19 files changed, 4192 insertions(+), 29 deletions(-)
```

---

## 12. Current Branch and Git Status

### 12.1 Working Tree Status
```text
## feature/euler-cauchy-solver...origin/main
 M CHANGELOG.md
 M src/math_app/domain/models.py
 M src/math_app/input/ode_parser.py
 M src/math_app/main.py
 M src/math_app/presentation/components/ode_pedagogical_enhancer.py
 M src/math_app/presentation/components/ode_staged_step_viewer.py
 M src/math_app/presentation/components/operation_catalog.py
 M src/math_app/presentation/components/problem_statement.py
 M src/math_app/presentation/components/workspace/ode/ode_classification_selector.py
 M src/math_app/presentation/components/workspace/ode/ode_method_selector.py
 M src/math_app/presentation/components/workspace/ode/ode_state.py
 M src/math_app/solvers/calculus/ode/__init__.py
 M src/math_app/verification/calculus/ode_verifier.py
 M tests/unit/presentation/test_design_system_and_catalog.py
 M tests/unit/presentation/test_ode_pedagogical_solution_flow.py
 M tests/unit/presentation/test_operation_catalog.py
 M tests/unit/presentation/test_ux3_1_ode_workspace.py
?? reports/
?? src/math_app/solvers/calculus/ode/euler_cauchy_solver.py
?? tests/unit/solvers/calculus/test_euler_cauchy_solver.py
```

### 12.2 Version Verification
- File: `pyproject.toml`
- Version: `0.2.0` (unbumped, strictly preserved).
- Git operations: No staging (`git add`), no commits (`git commit`), no pushes (`git push`), no merges (`git merge`), and no tags (`git tag`) have been performed.
