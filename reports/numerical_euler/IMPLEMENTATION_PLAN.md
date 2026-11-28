# Implementation Plan — Explicit Euler Numerical ODE Solver

## 1. Initial State & Backup Strategy
- **Baseline Branch:** `main`
- **Baseline Commit SHA:** `cf81d1c0dea691c4d9cb45c139f54612ea1e3483` (Release `v0.3.1`, `pyproject.toml` version `0.3.1` unchanged)
- **Backup Branch:** `backup/pre-numerical-euler-implementation` created at `cf81d1c0dea691c4d9cb45c139f54612ea1e3483` and pushed to `origin` (`git ls-remote origin refs/heads/backup/pre-numerical-euler-implementation` -> `cf81d1c0dea691c4d9cb45c139f54612ea1e3483`).
- **Development Branch:** `feat/numerical-euler-method` branched from `main`.

## 2. Architectural Principles
1. **Clean Architecture & Dependency Isolation (`tests/architecture/test_boundaries.py`):**
   - `domain/numerical_ode.py`: stdlib-only immutable models (`NumericalODEMethod`, `NumericalODEOrder`, `NumericalODEStatus`, `NumericalODERequest`, `NumericalODEResponse`, `NumericalIterationRow`, `AnalyticalComparisonPoint`, `AnalyticalComparisonResult`, `NumericalVerificationCheck`, `NumericalVerificationReport`). Zero dependencies on NiceGUI, Plotly, SymPy, or `math_app.solvers`/`presentation`.
   - `application/ports/numerical_ode.py` & `application/use_cases/solve_numerical_ode.py`: runtime-checkable `Protocol` ports (`NumericalODESolver`, `NumericalODEVerifier`, `AnalyticalComparisonProvider`) and use-case orchestration connecting solver, optional read-only analytical comparison, and independent verification.
   - `solvers/numerical/*`: safe AST real-valued evaluator (`expression_adapter.py`, zero `eval`/`exec`/`lambdify`), Explicit Euler engine (`explicit_euler_solver.py`), and read-only analytical comparison adapter (`analytical_comparison.py`).
   - `verification/numerical/euler_verifier.py`: independent `ExplicitEulerVerifier` performing 9 independent consistency & recurrence checks without trusting solver output.
   - `presentation/*`: NiceGUI workspace integration (`ode_workspace.py`, `numerical_euler_panel.py`, `numerical_result_view.py`, `app.py`) and Plotly chart builder (`numerical_plot_service.py`).
2. **Protected Analytical Core (Zero Modifications):**
   - `src/math_app/solvers/calculus/ode/` — untouched (`0` changed files)
   - `src/math_app/input/ode_parser.py` — untouched (`0` changed files)
   - `src/math_app/verification/calculus/ode_verifier.py` — untouched (`0` changed files)
   - `src/math_app/domain/models.py`, `src/math_app/application/dtos.py`, `src/math_app/application/use_cases/solve_problem.py` — untouched (`0` changed files)
   - `src/math_app/presentation/components/operation_catalog.py`, `src/math_app/presentation/components/shared/action_labels.py` — untouched (`0` changed files, preserving 34 operations / 23 main cards invariant).
3. **Extensibility:** Numerical abstractions (`NumericalODEMethod`, `NumericalODESolver` protocol, `NumericalODEVerifier` protocol) allow future methods (e.g., Heun or RK4) to plug in without altering Explicit Euler or analytical ODE code.

## 3. Executed Milestones

| Milestone | Scope & Deliverables | Verification Gate | Status |
|---|---|---|---|
| **Milestone 0 — Backup & Audit** | Created `backup/pre-numerical-euler-implementation`, created `feat/numerical-euler-method`, audited architecture boundaries, design system (`docs/UI_UX_DESIGN_SYSTEM.md`), and ODE workspace contracts. | Remote backup SHA verified; Clean Architecture rules mapped. | **DONE** |
| **Milestone 1 — Domain, Ports & Safe Evaluator** | Created `domain/numerical_ode.py`, `application/ports/numerical_ode.py`, and `solvers/numerical/expression_adapter.py` (AST whitelist evaluator, `Decimal` scalar parsing, Euler–Cauchy structure & $t=0$ crossing checks). | `tests/architecture/test_boundaries.py` + `tests/unit/test_contracts.py` pass (`13 passed`). | **DONE** |
| **Milestone 2 — Explicit Euler Solver, Analytical Comparison, Verifier & Wiring** | Created `explicit_euler_solver.py` (`DEFAULT_MAX_STEPS = 10_000`, `Decimal` drift-free grid, simultaneous 2nd-order update, shortened last step), `analytical_comparison.py` (3.0s timeout read-only delegation to `SolveProblemUseCase`), `euler_verifier.py`, `solve_numerical_ode.py`, and wired `build_numerical_ode_use_case` in `main.py`. | `test_explicit_euler_solver.py` + `test_euler_verifier.py` pass. | **DONE** |
| **Milestone 3 — UI/UX Integration & Plotly** | Created `numerical_plot_service.py`, `numerical_euler_panel.py`, `numerical_result_view.py`; integrated analytical/numerical mode toggle in `ode_workspace.py` and `?mode=numerical` query handling in `app.py`; kept numerical params hidden by default; placed mobile Plotly legend at `y=-0.22` below x-axis. | `test_numerical_euler_ui.py` + 78 existing presentation regression tests pass. | **DONE** |
| **Milestone 4 — Focused & Full Regression Testing** | Executed focused suite (`43 passed`) and full repository suite (`uv run pytest --cov=src --cov-report=term-missing --cov-fail-under=70`) + `ruff check .` + `uv lock --check` + `git diff --check` + protected-file audit. | `1505 passed, 2 warnings`, `81.51%` coverage, `0` lint/diff/protected-file issues. | **DONE** |
| **Milestone 5 — Live Chromium Responsive QA & Benchmarks** | Tested live NiceGUI runtime across 7 viewports (`360px`–`1440px` × 1st & 2nd order = 14 checks), interactive stale-clearing, pagination, Euler–Cauchy, singularity errors, 9 screenshots, and 6 runtime benchmarks. | `0` horizontal overflows, `0` raw LaTeX leaks, all 6 benchmarks verified `True`. | **DONE** |
| **Milestone 6 — Packaging, Documentation & Handover** | Verified Linux PyInstaller build & HTTP/shutdown smoke test; cleaned `build/`/`dist/`; updated `README.md`, `README.vi.md`, `docs/USER_GUIDE.md`; created `docs/NUMERICAL_EULER.md`; authored 5 handover reports under `reports/numerical_euler/`. | PyInstaller exit code `0`, HTTP 200 on `/`, KaTeX, `/?mode=numerical`, clean `/_test/shutdown`. | **DONE** |

## 4. Known Non-Goals Preserved
- **No Heun or RK4 implemented** in this task (Explicit Euler only, with `NumericalODEMethod` enum and protocol ports ready for future methods).
- **No version bump, release tag, merge to `main`, or git push of `feat/numerical-euler-method`** performed, preserving review readiness.
