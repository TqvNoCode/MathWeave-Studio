# Test & Verification Report

## 1. Summary of Executed Verification Gates

All automated test suites, static checks, lockfile checks, diff hygiene checks, and packaging smoke tests passed after the final code edit:

| Check | Command | Outcome | Observed Metrics |
| :--- | :--- | :--- | :--- |
| Full Repository Test Suite | `uv run pytest -q` | **PASSED** | `1467 passed, 2 warnings in 184.80s` (exit `0`) |
| Linter (`ruff`) | `uv run ruff check src/ tests/` | **PASSED** | `All checks passed!` (`0` errors, exit `0`) |
| Lockfile Integrity | `uv lock --check` | **PASSED** | `Resolved 90 packages in 1ms` (exit `0`) |
| Git Whitespace & Patch Hygiene | `git diff --check` | **PASSED** | Clean (exit `0`) |
| Linux PyInstaller Build & Smoke Run | `uv run pyinstaller --noconfirm --clean mathweave-studio.spec` + headless Chromium solve | **PASSED** | `/assets/katex/katex.js` HTTP 200; live solve of `t^2*y'' - t*y' + y = t^2, t > 0` rendered `"Phương trình Euler–Cauchy không thuần nhất"`, `"ĐÁP SỐ CUỐI CÙNG"`, `"v0.3.0"`; clean exit `0` on `SIGINT`, `TRACEBACK=False`. Temporary `build/` and `dist/` removed afterward. |

## 2. Targeted Feature & Regression Coverage

### Backend Solver & Verifier Tests
- [tests/unit/solvers/calculus/test_euler_cauchy_nonhomogeneous_solver.py](file:///home/tqv/Desktop/CODE/Python/math_app/tests/unit/solvers/calculus/test_euler_cauchy_nonhomogeneous_solver.py)
  - Covers Cases A–H: distinct real roots (`t^2*y'' - t*y' - 2*y = 1` and `t^2*y'' - 2*y = 1`), repeated roots, complex conjugate roots, resonance (`g(t) = t` and `g(t) = t^2`), Cauchy IVP at $t_0 \neq 0$, negative domain $t < 0$, multi-branch $\mathbb{R}\setminus\{0\}$, diverse forcing ($\ln t$, $\sin(\ln t)$, rational, exponential), exact `sp.Integral` preservation for $e^{t^2}$, $g(t)=0$ regression guard, singular $t_0 = 0$, pole at $t_0$, cross-zero interval, missing/mismatched IC guards, and pedagogical VoP step structure.
- [tests/unit/solvers/calculus/test_euler_cauchy_solver.py](file:///home/tqv/Desktop/CODE/Python/math_app/tests/unit/solvers/calculus/test_euler_cauchy_solver.py)
  - Existing homogeneous Euler–Cauchy suite preserved; updated nonhomogeneous boundary test `test_nonhomogeneous_euler_cauchy_now_supported`.
- Combined Milestone 1 targeted verification command (`test_euler_cauchy_solver.py`, `test_euler_cauchy_nonhomogeneous_solver.py`, `test_ode_verifier.py`, `test_second_order_ode_pipeline.py`): `118 passed in 29.92s`.

### Presentation & UI Integration Tests
- [tests/unit/presentation/test_euler_cauchy_nonhomogeneous_ui.py](file:///home/tqv/Desktop/CODE/Python/math_app/tests/unit/presentation/test_euler_cauchy_nonhomogeneous_ui.py)
  - Verifies second-order classifier detection of nonhomogeneous Euler–Cauchy (`Phương trình Euler–Cauchy không thuần nhất`), positive/negative intervals, rescaled equations, sign of $g(t)$, and non-misclassification of constant-coefficient and non-Euler ODEs.
  - Verifies 4-stage pedagogical enhancer (`Nghiệm thuần nhất liên kết`, VoP substeps, `y_c + y_p` general solution, Cauchy IVP, `\ln` polishing, and non-elementary `\int` step).
  - Verifies live NiceGUI workspace switching (nonhomogeneous $\leftrightarrow$ homogeneous) and classification card $y_c / y_p$ decomposition.
- Targeted presentation suite (`uv run pytest -q tests/unit/presentation/`): `676 passed, 1 warning in 94.43s`.
