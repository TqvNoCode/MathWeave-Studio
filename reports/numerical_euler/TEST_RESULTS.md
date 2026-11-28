# Test, Regression, Benchmark & Build Results

## 1. Execution Summary (All Run After Final Source Edit)

| Check / Suite | Command | Outcome | Notes |
|---|---|---|---|
| **Protected Core Audit** | `git diff --name-only main -- src/math_app/solvers/calculus/ode/ src/math_app/input/ode_parser.py src/math_app/verification/calculus/ode_verifier.py src/math_app/domain/models.py src/math_app/application/dtos.py src/math_app/application/use_cases/solve_problem.py src/math_app/presentation/components/operation_catalog.py src/math_app/presentation/components/shared/action_labels.py` | **PASSED** (0 files modified) | Protected analytical core and catalog invariants 100% intact. |
| **Linter** | `uv run ruff check .` | **PASSED** (`All checks passed!`) | Zero lint errors or new suppressions. |
| **Lockfile Consistency** | `uv lock --check` | **PASSED** (`Resolved 90 packages in 2ms`) | Zero unapproved dependencies added. |
| **Whitespace & Diff Hygiene** | `git diff --check` | **PASSED** (exit 0) | No conflict markers or trailing whitespace. |
| **Focused Numerical & Boundary Suite** | `uv run pytest -q tests/architecture/test_boundaries.py tests/unit/solvers/numerical/test_explicit_euler_solver.py tests/unit/verification/test_euler_verifier.py tests/unit/presentation/test_numerical_euler_ui.py` | **43 passed** in `53.92s` | 5 architecture + 32 solver + 3 verifier + 3 UI tests. |
| **Full Repository Test Suite & Coverage** | `uv run pytest --cov=src --cov-report=term-missing --cov-fail-under=70` | **1505 passed, 2 warnings** in `461.39s (0:07:41)` | Total coverage: **81.51%** (exceeds 70% gate). Zero failures, zero skips. |
| **Live Chromium Responsive & Interactive QA** | Headless Chromium (`chromium-1254`) against `uv run python run.py --browser --no-show --port 8767` | **14 / 14 viewport checks PASS** | 7 widths (`360..1440`) × 1st & 2nd order: 0 horizontal overflows, 0 raw LaTeX leaks; 9 PNGs saved. |
| **Linux PyInstaller Packaging** | `uv run pyinstaller --noconfirm --clean mathweave-studio.spec` | **PASSED** (exit 0) | Binary bundle built cleanly on Linux (`Build complete!`). |
| **Packaged App Runtime Smoke Test** | `./dist/mathweave-studio/mathweave-studio --browser --no-show --port 55827` | **PASSED** (exit 0, no traceback) | `/` HTTP 200, `/assets/katex/katex.js` HTTP 200 (`618845` B), `/?mode=numerical` HTTP 200, `POST /_test/shutdown` HTTP 200. Build artifacts removed afterward. |

## 2. Coverage Breakdown for Numerical & Integration Modules
Observed from `uv run pytest --cov=src --cov-report=term-missing --cov-fail-under=70`:

| Module | Statements | Missed | Coverage |
|---|---|---|---|
| `src/math_app/domain/numerical_ode.py` | 104 | 2 | **98%** |
| `src/math_app/application/ports/numerical_ode.py` | 16 | 3 | **81%** |
| `src/math_app/application/use_cases/solve_numerical_ode.py` | 30 | 3 | **90%** |
| `src/math_app/solvers/numerical/__init__.py` | 2 | 0 | **100%** |
| `src/math_app/solvers/numerical/explicit_euler_solver.py` | 132 | 22 | **83%** |
| `src/math_app/solvers/numerical/analytical_comparison.py` | 106 | 19 | **82%** |
| `src/math_app/solvers/numerical/expression_adapter.py` | 505 | 185 | **63%** |
| `src/math_app/verification/numerical/__init__.py` | 2 | 0 | **100%** |
| `src/math_app/verification/numerical/euler_verifier.py` | 144 | 21 | **85%** |
| `src/math_app/presentation/services/numerical_plot_service.py` | 36 | 4 | **89%** |
| `src/math_app/presentation/components/workspace/ode/numerical_euler_panel.py` | 158 | 44 | **72%** |
| `src/math_app/presentation/components/workspace/ode/numerical_result_view.py` | 313 | 24 | **92%** |
| `src/math_app/presentation/components/workspace/ode/ode_workspace.py` | 521 | 65 | **88%** |
| `src/math_app/presentation/app.py` | 739 | 112 | **85%** |
| `src/math_app/main.py` | 310 | 136 | **56%** |
| **TOTAL Repository Coverage** | **20052** | **3707** | **81.51%** |

## 3. Performance Benchmarks
Measured via `SolveNumericalODEUseCase` on small ($N=10$), medium ($N=500$), and maximum ($N=10{,}000$) iteration grids (`qa_summary.json`):

| Benchmark | Steps ($N$) | Analytical Comparison | Status | Verified | Wall Time (ms) | Reported Engine Time (ms) |
|---|---|---|---|---|---|---|
| `1st_order_N10_with_ana` | 10 | Enabled | `success` | `True` | `2259.12` | `2259.09` |
| `1st_order_N10_no_ana` | 10 | Omitted (nonlinear) | `success` | `True` | `12.17` | `12.14` |
| `1st_order_N500_no_ana` | 500 | Disabled (`max_rows=50000` / comparison off) | `success` | `True` | `83.22` | `83.20` |
| `1st_order_N10000_no_ana` | 10000 | Disabled | `success` | `True` | `61.55` | `61.47` |
| `2nd_order_N10_with_ana` | 10 | Enabled | `success` | `True` | `1939.45` | `1938.10` |
| `2nd_order_N10000_no_ana` | 10000 | Disabled | `success` | `True` | `59.64` | `59.61` |

*Observations:* Pure numerical integration at the maximum $10{,}000$-step limit executes in ~60 ms for both 1st-order and 2nd-order ODEs (no per-step symbolic SymPy calls). When SymPy analytical comparison is requested and solvable, the optional SymPy solve adds ~1.9–2.25 s off the UI thread (`asyncio.to_thread`), bounded by a 3.0 s comparison timeout and stale-token cancellation.

## 4. Local Linux vs. Remote Windows CI Distinction
- **Local Linux Verification (Executed & Passed):** Full pytest suite (`1505 passed`), ruff lint, PyInstaller Linux binary build (`mathweave-studio.spec`), and runtime HTTP/KaTeX/graceful-shutdown smoke tests all ran and passed locally on Linux (`Python 3.14.8`).
- **Remote Windows CI (`.github/workflows/windows-build.yml`):** **NOT RUN** during this implementation task, per instructions not to push unfinished feature branches or trigger a release build prematurely. The Windows CI workflow file remains intact and unmodified.
