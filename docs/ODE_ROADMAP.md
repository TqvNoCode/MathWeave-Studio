# MathWeave Studio — Ordinary Differential Equations (ODE) Roadmap

## 1. Executive Summary & Architectural Overview

MathWeave Studio provides an educational and research-grade symbolic mathematics environment built on Python 3.14+, SymPy, NumPy, and NiceGUI. This document outlines the architectural boundaries, mathematical foundations, verification methodology, and milestone roadmap for the Ordinary Differential Equations (ODE) subsystem.

The differential equations engine adheres strictly to Clean Architecture:
- **Domain Layer (`src/math_app/domain/`)**: Immutable data models, problem types (`ProblemType`), solution statuses (`SolutionStatus`), and verification outcomes (`VerificationStatus`). Absolutely no dependencies on UI or plotting frameworks.
- **Application Layer (`src/math_app/application/`)**: Use cases (`SolveProblemUseCase`), ports (`Solver`, `Verifier`, `SolverRegistry`), and typed DTOs (`ProblemRequest`, `SolutionResponse`, `SolutionStep`, `VerificationResult`). Enforces hard computation timeouts via isolated worker processes.
- **Input & Security Layer (`src/math_app/input/`)**: Strict AST-based expression validation, operator whitelisting, denial-of-service bounds (maximum expression length, AST depth, exponent magnitude), and parameter normalization (`ode_parser.py`). Rejects arbitrary Python execution, `eval`, `exec`, and unsafe `sympify`.
- **Solvers Layer (`src/math_app/solvers/calculus/ode/`)**: Pure symbolic mathematical solvers implementing discrete pedagogical steps. Solvers produce explicit or implicit symbolic solutions, preserving singular and equilibrium solutions.
- **Verification Layer (`src/math_app/verification/calculus/ode_verifier.py`)**: Independent verifiers calculating analytic and numerical residuals, gradient compatibility, and initial value satisfaction.
- **Rendering Layer (`src/math_app/rendering/`)**: LaTeX formatters and bilingual pedagogical step generators.
- **Presentation Layer (`src/math_app/presentation/`)**: Responsive NiceGUI components, operation catalogs, and dynamic problem configuration forms.

---

## 2. Repository Audit Findings & Baseline Status

Prior to expanding the ODE subsystem, an audit of the repository established the following baseline:
- **Baseline Test Suite**: 290 passing tests (with 1 non-fatal runtime warning in NumPy 2D plot sampling).
- **Linter**: Ruff passes with 0 errors across the entire codebase.
- **Existing ODE Solvers**:
  - `ODELinearSolver`: Handled constant coefficients $y' = ay + b$ and variable coefficients $y' + p(t)y = g(t)$.
  - `ODESeparableSolver`: Handled separable equations $y' = f(t)g(y)$, equilibrium solutions $g(y) = 0$, and IVP.
  - `ODEExactSolver`: Handled exact equations $M(x,y)dx + N(x,y)dy = 0$ when $\partial M/\partial y = \partial N/\partial x$.
- **Identified Gaps Addressed in Milestone 1**:
  1. *Integrating Factor for Non-Exact Equations*: Was completely unsupported; non-exact equations were rejected with `CANNOT_SOLVE`.
  2. *Implicit vs. Explicit Separation in Separable ODEs*: For cubic or higher relations in $y$ (e.g. $y' = x^2/(1 - y^2)$), `sp.solve` previously returned unwieldy Cardano formulas with complex numbers (`I`) rather than preserving the natural implicit relationship $y - y^3/3 = x^3/3 + C$.
  3. *Implicit Residual Verification*: Implicit solutions in `ODESeparableSolver` bypassed true residual calculation. Independent implicit verification $\frac{dy}{dx} = -\frac{\Phi_x}{\Phi_y}$ is required.
  4. *Variable Invariance*: In textbooks, independent variables fluctuate between $x$ and $t$. The parser must seamlessly handle either variable while maintaining strict AST security.
  5. *UI Registry*: Integrating factor problems must be accessible and selectable in the UI.

---

## 3. Milestone 1 — First-Order ODEs (Current Milestone)

Milestone 1 implements four comprehensive first-order ODE solvers based on Course Parts 2.02 and 2.03:

### 3.1 Linear First-Order ODEs
- **General Form**:
  $$y'(x) + p(x)y(x) = g(x)$$
- **Methodology**: Integrating factor method:
  $$\mu(x) = \exp\left(\int p(x)\,dx\right)$$
  Multiplying through yields $\frac{d}{dx}[\mu(x)y(x)] = \mu(x)g(x)$, leading to:
  $$y(x) = \frac{1}{\mu(x)}\left(\int \mu(x)g(x)\,dx + C\right)$$
- **Features**:
  - Constant coefficient specialization ($y' = ay + b$) with equilibrium solution $y_{eq} = -b/a$.
  - Variable coefficients with symbolic integration.
  - Explicit error handling when $\int p(x)\,dx$ or $\int \mu(x)g(x)\,dx$ is non-elementary.
  - Initial Value Problems (IVP) $y(x_0) = y_0$ with exact determination of $C$.

### 3.2 Separable Differential Equations
- **General Form**:
  $$\frac{dy}{dx} = f(x)g(y)$$
- **Methodology**:
  $$\frac{1}{g(y)}\,dy = f(x)\,dx \implies \int \frac{1}{g(y)}\,dy = \int f(x)\,dx + C$$
- **Features**:
  - **Equilibrium Preservation**: Roots of $g(y) = 0$ are identified before division to avoid losing constant equilibrium solutions $y(x) = y_{eq}$.
  - **Denominator Tracking**: Singularities where $g(y)$ or $f(x)$ is undefined are preserved as domain restrictions.
  - **Implicit vs. Explicit Distinction**: Solves explicitly only when $y$ can be isolated cleanly without introducing extraneous complex branches (e.g. linear in $y$ or single invertible function). Retains natural implicit relations (e.g. $y - y^3/3 = x^3/3 + C$) when degree in $y \ge 2$.
  - Initial Value Problems with direct support for equilibrium trajectories.

### 3.3 Exact Differential Equations
- **General Form**:
  $$M(x,y)\,dx + N(x,y)\,dy = 0 \quad\text{or}\quad M(x,y) + N(x,y)\,y' = 0$$
- **Exactness Criterion**:
  $$\frac{\partial M}{\partial y} = \frac{\partial N}{\partial x}$$
- **Methodology**:
  Construct potential function $\Psi(x, y)$ such that $\frac{\partial \Psi}{\partial x} = M$ and $\frac{\partial \Psi}{\partial y} = N$:
  $$\Psi(x, y) = \int M(x, y)\,dx + h(y), \quad h'(y) = N(x, y) - \frac{\partial}{\partial y}\int M(x, y)\,dx$$
  General solution is $\Psi(x, y) = C$.
- **Features**:
  - Strict exactness check before solving; non-exact equations are never mislabeled as exact.
  - Two-way partial derivative consistency verification.
  - Initial Value Problems $y(x_0) = y_0 \implies C = \Psi(x_0, y_0)$.

### 3.4 Integrating Factors for Non-Exact Equations
- **General Form**:
  $$M(x,y)\,dx + N(x,y)\,dy = 0 \quad\text{where}\quad \frac{\partial M}{\partial y} \ne \frac{\partial N}{\partial x}$$
- **Special Cases Supported**:
  1. **Integrating factor depending only on $x$**:
     $$\frac{M_y - N_x}{N} = f(x) \implies \mu(x) = \exp\left(\int f(x)\,dx\right)$$
  2. **Integrating factor depending only on $y$**:
     $$\frac{N_x - M_y}{M} = g(y) \implies \mu(y) = \exp\left(\int g(y)\,dy\right)$$
- **Derivation Pipeline**:
  1. Evaluate exactness defect $\Delta = M_y - N_x \ne 0$.
  2. Test if $\Delta / N$ is free of $y$. If so, compute $\mu(x)$.
  3. Test if $-\Delta / M$ is free of $x$. If so, compute $\mu(y)$.
  4. Form transformed coefficients $M_{new} = \mu M$ and $N_{new} = \mu N$.
  5. Formally verify exactness condition $\frac{\partial M_{new}}{\partial y} = \frac{\partial N_{new}}{\partial x}$.
  6. Construct potential function $\Psi(x, y) = \int M_{new}\,dx + h(y) = C$.
  7. Handle zero denominators ($M=0$ or $N=0$) and clearly report unsupported cases when neither condition applies.

---

## 4. Milestone 2 — Second-Order ODEs (Current Milestone)

Milestone 2 implements a complete, mathematically verified Second-Order Differential Equations module based on Course Part 2.04:

### 4.1 Constant-Coefficient Homogeneous Second-Order ODEs
- **General Form**:
  $$a y'' + b y' + c y = 0, \quad a, b, c \in \mathbb{R}, \; a \ne 0$$
- **Characteristic Polynomial**:
  $$a r^2 + b r + c = 0, \quad \Delta = b^2 - 4ac$$
- **Case Classification**:
  1. **Distinct Real Roots ($\Delta > 0$)**:
     $$r_1 = \frac{-b + \sqrt{\Delta}}{2a}, \quad r_2 = \frac{-b - \sqrt{\Delta}}{2a}$$
     General solution:
     $$y(t) = C_1 e^{r_1 t} + C_2 e^{r_2 t}$$
  2. **Complex Conjugate Roots ($\Delta < 0$)**:
     $$r_{1,2} = \alpha \pm i\beta, \quad \alpha = -\frac{b}{2a}, \quad \beta = \frac{\sqrt{-\Delta}}{2|a|} > 0$$
     Real-valued general solution via Euler's identity:
     $$y(t) = e^{\alpha t}(C_1 \cos(\beta t) + C_2 \sin(\beta t))$$
     (Specializes to $y(t) = C_1 \cos(\beta t) + C_2 \sin(\beta t)$ when $b = 0 \implies \alpha = 0$).
  3. **Repeated Real Root ($\Delta = 0$)**:
     $$r = -\frac{b}{2a}$$
     General solution (incorporating linearly independent factor $t$ derived via reduction of order):
     $$y(t) = (C_1 + C_2 t) e^{r t}$$
     (Specializes to $y(t) = C_1 + C_2 t$ when $b = c = 0 \implies r = 0$).

### 4.2 Second-Order Initial Value Problems (Cauchy IVP)
- **Initial Conditions**:
  $$\begin{cases} y(t_0) = y_0 \\ y'(t_0) = v_0 \end{cases}$$
- **Linear Algebraic System**:
  $$\begin{pmatrix} y_1(t_0) & y_2(t_0) \\ y_1'(t_0) & y_2'(t_0) \end{pmatrix} \begin{pmatrix} C_1 \\ C_2 \end{pmatrix} = \begin{pmatrix} y_0 \\ v_0 \end{pmatrix}$$
  The system matrix determinant is the non-zero Wronskian $W(y_1, y_2)(t_0) \ne 0$.
- **Exact Particular Solution**:
  $$y(t) = C_1 y_1(t) + C_2 y_2(t)$$
  Independently verified against both conditions $y(t_0) = y_0$ and $y'(t_0) = v_0$, and the original ODE residual $R(t) \equiv 0$.

### 4.3 Reduction of Order
- **General Form**:
  $$y'' + p(t)y' + q(t)y = 0 \quad (\text{or } a(t)y'' + b(t)y' + c(t)y = 0)$$
- **Prerequisite Validation**:
  Candidate solution $y_1(t)$ is parsed, differentiated, and verified against $R_1(t) = y_1'' + p(t)y_1' + q(t)y_1 = 0$. Identically zero functions $y_1 \equiv 0$ and invalid candidates are rejected with clear error explanations.
- **Derivation Pipeline**:
  1. Substitution: $y_2(t) = v(t)y_1(t)$.
  2. Derivative calculation: $y_2' = v' y_1 + v y_1'$, $y_2'' = v'' y_1 + 2v' y_1' + v y_1''$.
  3. Substitution into ODE: $y_1 v'' + (2y_1' + p y_1)v' = 0$.
  4. Reduction to first-order in $u = v'$: $u' + (p(t) + 2y_1'/y_1)u = 0$.
  5. Exact integration:
     $$u(t) = \frac{e^{-\int p(t)\,dt}}{y_1(t)^2}, \quad v(t) = \int u(t)\,dt$$
  6. Second fundamental solution: $y_2(t) = v(t)y_1(t)$.
  7. Linear independence verification via Wronskian: $W(y_1, y_2) \ne 0$.
  8. General solution: $y(t) = C_1 y_1(t) + C_2 y_2(t)$.
- **Domain & Singularity Preservation**:
  Identifies zeros of $y_1(t)$ and singular points of $p(t), q(t)$, reporting explicit domain intervals. Specifically for Euler–Cauchy equations (e.g. $2t^2y'' + 3ty' - y = 0, y_1 = 1/t$), reduction of order is supported on both positive ($t > 0$, $y_2 \propto \sqrt{t}$) and negative ($t < 0$, $y_2 \propto \sqrt{-t}$) intervals, noting the singularity at $t = 0$.

### 4.4 Wronskian Determinant & Linear Independence
- **Formula**:
  $$W(y_1, y_2)(t) = \begin{vmatrix} y_1(t) & y_2(t) \\ y_1'(t) & y_2'(t) \end{vmatrix} = y_1(t)y_2'(t) - y_1'(t)y_2(t)$$
- **Corrected Mathematical Criteria (Peano's Theorem & Abel's Theorem)**:
  - **$W(y_1, y_2) \not\equiv 0$ on a connected interval**: Guarantees linear independence for any pair of differentiable functions.
  - **$W(y_1, y_2) \equiv 0$ for arbitrary functions**: **Mathematically inconclusive**. Peano (1889) provided the classical counterexample $y_1(t) = t^2, y_2(t) = t|t|$ on $\mathbb{R}$, which has $W(y_1, y_2) \equiv 0$ everywhere on $\mathbb{R}$ yet $y_1$ and $y_2$ are strictly linearly independent on $\mathbb{R}$. In MathWeave Studio, arbitrary functions with $W \equiv 0$ are reported as `UNVERIFIED` / `INCONCLUSIVE` (amber badge, never green) with educational Peano warnings.
  - **$W(y_1, y_2) \equiv 0$ for solutions of a common ODE**: By Abel's theorem, if $y_1, y_2$ solve a common homogeneous linear ODE $y'' + p(t)y' + q(t)y = 0$ with continuous coefficients on an interval $I$, then $W \equiv 0$ if and only if $y_1, y_2$ are linearly dependent on $I$. Linear dependence is reported as `VERIFIED` only when this common ODE hypothesis is mathematically confirmed.

### 4.5 Scope Boundaries & Limitations
- **Supported**: Homogeneous constant-coefficient ODEs ($a y'' + b y' + c y = 0$), two-point Cauchy IVPs, Reduction of Order with verified $y_1$, and Wronskian analysis.
- **Unsupported in this Milestone**: Nonhomogeneous second-order equations ($a y'' + b y' + c y = g(t)$) and general unconstrained variable-coefficient second-order equations without a known fundamental solution.

### 4.6 Mathematical Formatting & Native MathML Remediation
- **Radical Preservation in Second-Order ODEs**: Characteristic roots $r_{1,2} = \frac{-b \pm \sqrt{\Delta}}{2a}$, general solutions, derivative equations, Cauchy 2x2 linear systems, and particular solutions preserve square-root radical forms ($\sqrt{33}$) rather than degrading to raw decimals or missing radical symbols.
- **Cross-Application Native MathML Rendering**: Explanatory text descriptions in solution steps across Calculus, Linear Algebra, and ODEs wrap mathematical symbols in `$ ... $`, converted via `text_math_renderer.py` into native, secure MathML. Plain HTML tags are strictly escaped to prevent injection.

---

## 5. Verification & Validation Strategy

The system enforces independent verification at application boundaries:
1. **First-Order Explicit Solutions**:
   $$R(x) = y'(x) + p(x)y(x) - g(x)$$
2. **Second-Order Explicit Solutions**:
   $$R(t) = a y''(t) + b y'(t) + c y(t) \equiv 0$$
   Dual initial conditions independently verified: $y(t_0) = y_0$ and $y'(t_0) = v_0$.
3. **Exact Solutions & Integrating Factors**:
   $$\nabla \Psi = \left(\frac{\partial \Psi}{\partial x}, \frac{\partial \Psi}{\partial y}\right) \equiv (M, N) \quad\text{or}\quad (\mu M, \mu N)$$
4. **Wronskian Independence**:
   $$W(y_1, y_2)(t) \ne 0 \text{ on the domain interval}$$
5. **Integrity Rule**: A solution is **never** reported as `VERIFIED` unless the residual, initial conditions, or Wronskian identity are mathematically confirmed. Inconclusive checks report `UNVERIFIED`; discrepancies report `FAILED`.

---

## 6. Security & Resource Bounding

- **AST Validation**: Equations are parsed via Python `ast.parse` into restricted nodes (`ast.Expression`, `ast.BinOp`, `ast.UnaryOp`, `ast.Call`, `ast.Name`, `ast.Constant`).
- **Whitelisting**: Only whitelisted mathematical functions and approved symbols ($x, t, y, y', y'', C, C_1, C_2, a, b, c, k, m, n, p, q, g, v_0, t_0, y_0$) are permitted.
- **Denial of Service Prevention**:
  - Maximum raw input length: 500 characters.
  - Maximum AST node count: 120 nodes.
  - Maximum AST tree depth: 15 levels.
  - Maximum exponent value: 100.
  - Maximum integer literal: $10^9$.
- **Process Isolation**: CPU-intensive symbolic operations execute inside child worker processes using `multiprocessing.get_context("spawn")` with a default 8.0-second hard cancellation deadline.

---

## 7. Future Milestones

### Milestone 3 — Nonhomogeneous Second-Order ODEs & Advanced Topics
- Method of Undetermined Coefficients.
- Variation of Parameters (Lagrange method).
- Resonance phenomena in driven oscillators.

### Milestone 4 — Autonomous Equations & Numerical Methods (Parts 2.02 & 2.03)
- Autonomous equations $\frac{dy}{dt} = f(y)$, phase lines, equilibria, and stability.
- Euler's numerical method with configurable step size $h$.
- Direction fields / slope fields.

### Milestone 5 — Theoretical Analysis
- Cauchy–Lipschitz (Picard–Lindelöf) theorem, existence and uniqueness bounds.
