# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Second-Order Euler–Cauchy ODE Solver (ODE-EC1)**:
  - Implemented dedicated `ODEEulerCauchySolver` for homogeneous second-order Euler–Cauchy equations $a t^2 y''(t) + b t y'(t) + c y(t) = 0$ ($a \neq 0$).
  - Integrated into application core with dedicated problem type `ProblemType.ODE_EULER_CAUCHY`.
  - Supported all three indicial characteristic root cases:
    - Case A: Distinct real roots ($m_1 \neq m_2$), yielding $y(t) = C_1 t^{m_1} + C_2 t^{m_2}$ for $t > 0$ and $C_1 (-t)^{m_1} + C_2 (-t)^{m_2}$ for $t < 0$.
    - Case B: Repeated real root ($m_1 = m_2 = m$), yielding $y(t) = t^m (C_1 + C_2 \ln t)$ for $t > 0$ and $(-t)^m (C_1 + C_2 \ln(-t))$ for $t < 0$.
    - Case C: Complex-conjugate roots ($m_{1,2} = \alpha \pm i\beta$), producing purely real-valued trigonometric solutions $y(t) = t^\alpha [C_1 \cos(\beta \ln t) + C_2 \sin(\beta \ln t)]$ for $t > 0$ and $(-t)^\alpha [C_1 \cos(\beta \ln(-t)) + C_2 \sin(\beta \ln(-t))]$ for $t < 0$.
  - Supported complete Cauchy Initial Value Problems ($y(t_0) = y_0, y'(t_0) = v_0$) for $t_0 \neq 0$, resolving exact integration constants via $2 \times 2$ linear systems and validating on the connected component containing $t_0$.
  - Handled singular point $t = 0$ safely: preserved original leading coefficient singular constraints, returned two-branch solutions with independent constants ($C_1, C_2$ on $t > 0$ and $C_3, C_4$ on $t < 0$) in general mode across the natural domain $\mathbb{R} \setminus \{0\}$, rejected intervals crossing zero, and flagged Cauchy IVPs at $t_0 = 0$ as unsupported singular points without claiming mathematical nonexistence.
  - Added rich pedagogical step-by-step derivations (form classification, trial solution $y = t^m$, indicial polynomial derivation, discriminant calculation and root classification, fundamental solution construction, general solution assembly, and Cauchy IVP linear system resolution).
  - Integrated into second-order ODE workspace UI with a dedicated Euler–Cauchy classification card, problem request builder, and pedagogical solution flow enhancer.
  - Rejected nonhomogeneous Euler–Cauchy equations with clear explanations to maintain mathematical boundaries.
  - Added comprehensive test coverage across all root cases, domains, Cauchy IVPs, singular point edge cases, and UI workflows.

## [0.2.0] - 2026-11-25

### Added
- **Second-Order Nonhomogeneous ODE Solvers & Solvers Pipeline**:
  - Implemented Method of Undetermined Coefficients (MUC) with automatic polynomial, exponential, trigonometric resonance boosting factor $t^s$.
  - Implemented Variation of Parameters (VoP) using Wronskian integration for nonhomogeneous second-order equations where MUC is inapplicable.
  - Integrated full Cauchy Initial Value Problem (IVP) solving for second-order equations ($y(t_0) = y_0, y'(t_0) = v_0$) with $2 \times 2$ linear system resolution.
  - Added reduction of order solver deriving fundamental pairs from a known solution $y_1(t)$.
  - Added Wronskian solver with Abel's identity verification and Peano theorem warnings on linear independence.
- **Fail-Closed Domain Validation & Tri-State Verification**:
  - Implemented tri-state (`valid` / `invalid` / `unknown`) domain validation across all ODE solvers and Cauchy IVP handlers, preventing unresolved symbolic conditions from silently passing.
  - Added domain restriction extraction preserving source-level denominators and constraints through algebraic simplification.
  - Added singular Cauchy point analysis, connected domain branching, and $C^1$ smooth continuation validation.
- **Minimalist Pedagogical Workspaces & Design System**:
  - Introduced dedicated mathematical workspaces (First-Order ODEs, Second-Order ODEs, Linear Algebra, Multivariable Calculus) with responsive NiceGUI layout and design system tokens.
  - Added comprehensive Operation Catalog, guided first-order ODE classifier, interactive problem statement builder, and staged step viewer with step-by-step pedagogical breakdowns.
  - Added sticky navigation bar and scroll manager for intuitive exploration.
- **Portable Cross-Platform Computation Timeout**:
  - Implemented `process_guard.py` (`run_with_process_timeout`) providing robust, process-based execution timeouts compatible with Windows multiprocessing `spawn` and Linux.
  - Eliminated Unix-only `signal.setitimer` and `SIGALRM` across solvers and verifiers, ensuring reliable timeout behavior in multithreaded environments and on Windows.
  - Added explicit two-phase process handshake separating interpreter initialization latency from pure mathematical computation budgets.
  - Added `SolutionStatus.INCONCLUSIVE` to domain models for mathematical outcomes where convergence or divergence cannot be proven.

### Fixed
- **Arc Length Numerical Benchmark & Verification Hardening**:
  - Verified and documented true numerical arc length benchmark for $f(x) = \cos(x) - \tan(x)$ on $[0, 1]$ ($L \approx 2.280484110764684$).
  - Hardened unit tests with explicit tolerance assertions (`math.isclose`), covering regular lines, nonlinear curves, convergent endpoint singularities, divergent singularities, and parametric curves.
  - Updated `SolveProblemUseCase` to use `daemon=False` and clean up OS process handles (`p.close()`), preventing handle leaks on Windows.
- **Branding & Footer Consistency**:
  - Synchronized application version metadata across desktop shell, about dialog, and automated test assertions.

## [0.1.1] - 2026-11-15

### Added
- **Global Mathematical Output Correction & Safe MathML Rendering Engine**:
  - Implemented `text_math_renderer.py` providing `convert_latex_to_mathml()`, `delimit_unwrapped_math_in_text()`, and `render_math_in_text_html()`.
  - Added `ui_math_text()` in `math_view.py` and integrated into `step_viewer.py` to seamlessly convert `$ ... $` and `$$ ... $$` math blocks into native textbook MathML while strictly escaping HTML text with `html.escape` and stripping script/event injection vectors.
  - Upgraded step descriptions and notes across Calculus (differentiation, integration, limits), Linear Algebra (matrix operations, determinants, inverses, rank, Gaussian elimination), and ODEs to native LaTeX notation wrapped in `$...$`.
- **Second-Order ODE Radical Preservation & Full Cauchy IVP Pipeline**:
  - Corrected radical formatting in `second_order_constant_coeff_solver.py`: characteristic roots now preserve square root radicals ($r_{1,2} = \frac{-b \pm \sqrt{\Delta}}{2a} = \frac{-1 \pm \sqrt{33}}{4}$).
  - Fully articulated educational steps: Step 3 clearly distinguishes $\Delta$ from $\sqrt{\Delta}$; Step 4 preserves radicals in fundamental/general solutions; Step 5 breaks out explicit first derivative $y'(t)$; Step 6 formats Cauchy 2x2 linear system $\begin{cases} C_1 + C_2 = 0 \\ r_1 C_1 + r_2 C_2 = 1 \end{cases}$; Step 7 solves exact constants $C_1 = \frac{2\sqrt{33}}{33}, C_2 = -\frac{2\sqrt{33}}{33}$ and formats particular solution with both unfactored linear combination and factored forms.
  - Resolved exact-solution radical omission corruption where integer coefficient juxtaposed with radical rendered as single integer ($2\sqrt{33} \to 233$): standardized thin spacing in `normalize_latex()` for numeric coefficients preceding `\sqrt` ($2\,\sqrt{33}$ generating `<mspace>` separator), updated global MathML font fallback list to include `DejaVu Math TeX Gyre`, `Noto Sans Math`, `math`, and bundled offline OpenType math fonts in `assets/fonts/` with `font-weight: normal !important;` to ensure radical surd and overbar rendering across all environments.
- **Wronskian Correctness Remediation & Peano Warning**:
  - Distinguish arbitrary function pairs from solutions to a common linear homogeneous ODE on a connected interval.
  - When $W \equiv 0$ without a verified common linear homogeneous ODE, Wronskian verifier and solver now report `VerificationStatus.UNVERIFIED` / `SolutionStatus.UNVERIFIED` (inconclusive, amber badge, never false green).
  - Provided pedagogical warnings citing Peano's theorem and the classical counterexample ($y_1 = t^2, y_2 = t|t|$) where $W \equiv 0$ on $\mathbb{R}$ despite linear independence.
  - Linear dependence is only concluded when verified as solutions of a common ODE via Abel's theorem.
- **Reduction of Order Negative Interval Domain Support**:
  - Corrected variable-coefficient reduction of order for Euler-Cauchy equations (e.g. $2t^2y'' + 3ty' - y = 0, y_1 = 1/t$) across both positive ($t > 0$, $y_2 \propto \sqrt{t}$) and negative ($t < 0$, $y_2 \propto \sqrt{-t}$) intervals, noting the singularity at $t = 0$.

## [0.1.0] - 2026-10-23

### Added
- **Equation Solver**: Implemented algebraic equation solving (`SOLVE_EQUATION`) with standard form transformation, root finding, factor display, and independent root verification.
- **Process Isolation & Hard Timeouts**: Added robust OS worker process isolation (`multiprocessing.Process` via `spawn`) with hard termination on configurable timeout for CPU-bound symbolic calculations.
- **Expression Complexity Hardening**: Added AST node count bounds, constant magnitude limits, logarithmic power magnitude guards, and strict prevention of nested exponent towers (e.g. `x**(9**9**9)`, `9**9**9**9`).
- **HTML Sanitization**: Added explicit HTML escaping in mathematical view fallback rendering to prevent script and event-handler injection.
- **Independent Verifier Tests**: Added dedicated unit test suites for `IntegralVerifier` and `SurfaceAreaVerifier`.
- **Release Readiness**: Added `SECURITY.md`, `CONTRIBUTING.md`, `.github/dependabot.yml`, and configured Ruff linter quality gates in CI.

### Security
- **certifi upgrade**: Verified and remediated `PYSEC-2026-4320` by updating `certifi` from `2026.7.22` to `2026.10.23` in `uv.lock`.
