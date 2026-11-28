# Mathematical Verification Report — Explicit Euler Method

## 1. Implemented Formulas & Numerical Design

### 1.1 First-Order Initial Value Problem
Given:
$$y' = f(t, y), \qquad y(t_0) = y_0, \qquad t \in [t_0, T] \text{ (or } [T, t_0]\text{)}$$

Explicit Euler (Forward Euler) update at step $n = 0, \dots, N-1$:
$$t_{n+1} = t_n + d \cdot h_n, \qquad d = \operatorname{sgn}(T - t_0) \in \{+1, -1\}$$
$$h_n = \min\left(h, |T - t_n|\right)$$
$$y_{n+1} = y_n + (d \cdot h_n) f(t_n, y_n)$$

- Exact time-grid construction uses `decimal.Decimal` arithmetic (`t_0 + n * dir * h`) until the final shortened step $h_n = \min(h, |T - t_n|)$, preventing accumulated binary floating-point drift on long grids and guaranteeing $t_N = T$ with zero overshoot.
- Every slope evaluation $f(t_n, y_n)$ uses only the previous iteration's values $(t_n, y_n)$.

### 1.2 Second-Order Initial Value Problem (Reduced to First-Order System)
Given:
$$y'' = F(t, y, y'), \qquad y(t_0) = y_0, \qquad y'(t_0) = v_0$$

State reduction $z_1 = y, \; z_2 = y'$:
$$\begin{cases} z_1' = z_2 \\ z_2' = F(t, z_1, z_2) \end{cases}$$

Simultaneous Explicit Euler updates from old state $(t_n, y_n, v_n)$:
$$y_{n+1} = y_n + \Delta t_n \cdot v_n$$
$$v_{n+1} = v_n + \Delta t_n \cdot F(t_n, y_n, v_n), \qquad \Delta t_n = d \cdot h_n$$

`ExplicitEulerSolver` evaluates $F(t_n, y_n, v_n)$ **before** updating $y_n \to y_{n+1}$ and computes both updates strictly from $(t_n, y_n, v_n)$, avoiding the semi-implicit Euler bug where $y_{n+1}$ is mistakenly fed into $v_{n+1}$.

### 1.3 Euler–Cauchy Safe Transformation & Distinction
- **Explicit Euler** (this feature): general numerical approximation scheme advancing solution values across discrete steps from initial value(s).
- **Euler–Cauchy ODE** (protected analytical solver + safe numerical reduction): linear variable-coefficient ODE of the form
$$A t^2 y'' + B t y' + C y = g(t)$$
- In numerical mode, `solvers/numerical/expression_adapter.py` detects explicit `t^2 * y''` / Euler–Cauchy structure when entered and transforms it safely into:
$$y'' = \frac{g(t) - B t y' - C y}{A t^2}$$
subject to:
  1. $A \neq 0$,
  2. $t_0 \neq 0$ and $T \neq 0$,
  3. The interval $[t_0, T]$ (or $[T, t_0]$) **must not contain or cross** $t = 0$ ($\operatorname{sgn}(t_0) = \operatorname{sgn}(T)$). Any interval starting at, ending at, or crossing $t = 0$ is rejected immediately as `NumericalODEStatus.SINGULARITY_ERROR` before iteration begins.

## 2. Error Order, Stability & Conservative Bounds
- **Local Truncation Error:** $O(h^2)$ per step.
- **Global Error:** $O(h)$ under suitable smoothness and stability assumptions; documentation and UI explanations explicitly clarify that Explicit Euler is **not unconditionally stable** and smaller $h$ does not guarantee monotonic pointwise error reduction for stiff or unstable regimes.
- **Resource & Overflow Safety:** `DEFAULT_MAX_STEPS = 10_000` (rejecting requests needing $> 10{,}000$ steps with `ITERATION_LIMIT_EXCEEDED`). All intermediate values are validated for `NaN`, `Inf`, overflow (`> 1e150`), division by zero, negative square roots/even fractional powers, non-positive logarithms, domain errors (e.g., $\tan(\pi/2)$), and complex evaluations, reporting the exact `failing_step` and diagnostic cause.
- **AST-Safe Evaluator:** `expression_adapter.py` uses Python's `ast` module with an explicit real-valued math whitelist (`sin`, `cos`, `tan`, `exp`, `ln`/`log`, `sqrt`, `abs`, `asin`, `acos`, `atan`, `sinh`, `cosh`, `tanh`, `pi`, `e`)—never Python `eval()`, `exec()`, or `sympy.lambdify()`.

## 3. Independent Verifier (`ExplicitEulerVerifier`)
Implemented in `src/math_app/verification/numerical/euler_verifier.py`, independently checking **without trusting solver outputs**:
1. Request parameter & order consistency.
2. Iteration count matches exact `Decimal` ceiling step formula and `DEFAULT_MAX_STEPS = 10_000` guard.
3. Initial state matches $(t_0, y_0[, v_0])$.
4. Time grid construction and monotonicity match direction $\operatorname{sgn}(T - t_0)$.
5. Step-size handling matches $h$ for interior steps and $h_n = \min(h, |T - t_n|)$ on the last step.
6. Final endpoint reaches $T$ within floating-point tolerance without overshoot.
7. First-order / second-order recurrence independently re-evaluated via the AST expression evaluator (`y_{n+1}` and `v_{n+1}` simultaneous check from old `y_n, v_n` across sampled & boundary steps).
8. Output invariants: all rows finite, non-NaN, consistent `final_value == rows[-1].y`, `final_derivative == rows[-1].v`.
9. Analytical comparison integrity when available (`|y(t_n) - y_n|`, non-negative finite errors).

Tampering tests in `tests/unit/verification/test_euler_verifier.py` (`test_verifier_detects_tampered_recurrence_and_semi_implicit_bug`) explicitly prove that corrupting a step value or introducing a semi-implicit 2nd-order update causes `ExplicitEulerVerifier` to fail verification (`passed=False`).

## 4. Verified Mathematical Test Matrix (Tests A–J & Invalid Inputs)
All executed in `tests/unit/solvers/numerical/test_explicit_euler_solver.py` (32 collected tests) and `tests/unit/verification/test_euler_verifier.py` (3 tests):

| Case | Equation & IVP | Configuration | Expected & Verified Behavior |
|---|---|---|---|
| **Test A** | $y' = y,\; y(0) = 1$ | $T = 1,\; h = 0.1$ | $y_n = (1.1)^n$; $y_{10} = 2.5937424601$ compared against $e \approx 2.7182818285$ (`abs_error = 0.124539...`); verifier passed. |
| **Test B** | $y' = -2y,\; y(0) = 1$ | $h \in \{0.2, 0.1, 0.05\},\; T = 1$ | Recurrence $(1 - 2h)^n$ verified for 5, 10, 20 steps; compared against $e^{-2t}$. |
| **Test C** | $y' = 3,\; y(0) = 2$ | $h = 0.25,\; T = 2$ | Exact linear solution $y(t) = 2 + 3t$ (`abs_error < 1e-12`). |
| **Test D** | $y' = t + y,\; y(0) = 1$ | $h = 0.2,\; T = 0.6$ | Consecutive steps verified against independent recurrence ($1.0, 1.2, 1.48, 1.856$). |
| **Test E** | $y' = y,\; y(1) = 1$ | Backward $T = 0,\; h = 0.2$ | Negative step direction $t_n$ decreasing from $1 \to 0$; $y_5 = (0.8)^5 = 0.32768$. |
| **Test F** | $y' = y,\; y(0) = 1$ | Non-divisible $T = 0.55,\; h = 0.2$ | Steps $[0.2, 0.2, 0.15]$ ending cleanly at $t_3 = 0.55$ with zero overshoot. |
| **Nonlinear** | $y' = \sin(t) + y^2,\; y(0) = 0.5$ | $T = 0.5,\; h = 0.1$ | Succeeds numerically; omits unavailable analytical comparison cleanly. |
| **Test G** | $y'' = -y,\; y(0)=0, v(0)=1$ | $T = 0.4,\; h = 0.1$ | Simultaneous $(y_n, v_n)$ updates match $(0,1) \to (0.1,1) \to (0.2,0.99) \to (0.299,0.97) \to (0.396,0.9401)$. |
| **Test H** | $y'' = 0,\; y(0)=2, v(0)=3$ | $T = 2,\; h = 0.25$ | Exact linear solution $y(t) = 2 + 3t$, $v(t) = 3$. |
| **Test I** | $y'' = 2y' - y + t,\; y(0)=0, v(0)=1$ | $T = 0.3,\; h = 0.1$ | Verified against independent simultaneous recurrence & analytical comparison. |
| **Test J** | $t^2 y'' - 2t y' + 2y = 0$ | Positive $[1, 2]$, Negative $[-2, -1]$, Crossing $[-1, 1]$ | Succeeds cleanly on $[1, 2]$ and $[-2, -1]$ with transformed $y'' = (2ty' - 2y)/t^2$; rejects $[-1, 1]$ with `SINGULARITY_ERROR` referencing $t=0$. |
| **Invalid / Singular (19 cases)** | $h \le 0$, $T=t_0$, missing $y_0$/$v_0$, NaN/Inf, malformed syntax, order mismatch, $1/t$, $\ln(-1)$, $\sqrt{-1}$, $\tan(\pi/2)$, $>10{,}000$ steps, runtime overflow | Various | All return structured error statuses (`INVALID_INPUT`, `SINGULARITY_ERROR`, `NUMERICAL_ERROR`, `ITERATION_LIMIT_EXCEEDED`, `OVERFLOW_ERROR`) with explicit failing step info and zero crashes. |

## 5. Analytical Solver Non-Regression Confirmation
- `git diff --name-only main` confirmed zero changes in `src/math_app/solvers/calculus/ode/`, `src/math_app/input/ode_parser.py`, `src/math_app/verification/calculus/ode_verifier.py`, and `solve_problem.py`.
- `test_existing_analytical_ode_solvers_remain_unchanged` in `tests/unit/verification/test_euler_verifier.py` plus all existing analytical ODE tests passed inside the `1505`-test full suite.
