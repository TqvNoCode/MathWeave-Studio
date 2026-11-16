# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
