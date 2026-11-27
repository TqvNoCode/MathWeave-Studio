# Mathematical Verification Report — Euler–Cauchy Nonhomogeneous ODEs

## 1. Governing Formulation

For constant real coefficients $A \neq 0, B, C$ and forcing function $g(t) \neq 0$ on a connected interval not containing $t = 0$:

$$A t^2 y'' + B t y' + C y = g(t).$$

By linearity, the general solution decomposes into:

$$y(t) = y_c(t) + y_p(t).$$

### Stage A — Associated Homogeneous Solution $y_c(t)$
The associated homogeneous equation $A t^2 y'' + B t y' + C y = 0$ is solved by the existing verified Euler–Cauchy indicial module using

$$A m(m - 1) + B m + C = 0 \iff A m^2 + (B - A) m + C = 0, \qquad \Delta = (B - A)^2 - 4AC.$$

All three real fundamental system cases on positive ($t > 0$) and negative ($t < 0$, coordinate $\tau = -t = |t| > 0$) intervals are preserved:
1. Distinct real roots ($m_1 \neq m_2$): $y_1 = |t|^{m_1},\; y_2 = |t|^{m_2}$.
2. Repeated real root ($m_1 = m_2 = m$): $y_1 = |t|^m,\; y_2 = |t|^m \ln|t|$.
3. Complex conjugate roots ($\alpha \pm i\beta,\; \beta > 0$): $y_1 = |t|^\alpha \cos(\beta \ln|t|),\; y_2 = |t|^\alpha \sin(\beta \ln|t|)$.

### Stage B — Variation of Parameters (General-Purpose Particular Solution)
Normalizing $A t^2 y'' + B t y' + C y = g(t)$ over $A t^2 \neq 0$ yields:

$$y'' + P(t)y' + Q(t)y = R(t), \quad P(t) = \frac{B}{At},\; Q(t) = \frac{C}{At^2},\; R(t) = \frac{g(t)}{At^2}.$$

With Wronskian $W(t) = y_1(t)y_2'(t) - y_1'(t)y_2(t) \neq 0$:

$$u_1'(t) = -\frac{y_2(t) R(t)}{W(t)}, \qquad u_2'(t) = \frac{y_1(t) R(t)}{W(t)},$$

$$y_p(t) = u_1(t) y_1(t) + u_2(t) y_2(t).$$

Integration constants from $u_1, u_2$ are deliberately omitted (absorbed into $C_1, C_2$ of $y_c$), preventing spurious extra arbitrary constants.

## 2. Negative Domains ($\tau = |t| > 0$) and Real-Domain Honesty

To guarantee real-valued antiderivatives without fractional powers of negative $t$ or complex $\ln(t)$ artifacts when solving on $t < 0$:
1. `_integrate_on_real_branch` substitutes $t = -\tau$ ($\tau > 0$) and applies $dt = -d\tau$ cleanly to the integrand before symbolic integration.
2. `_is_elementary_real_closed_form` filters out non-elementary special functions (`hyper`, `meijerg`, `erfi`, `erfc`, `Ei`, `Si`, `Ci`, `li`, `fresnels`, `fresnelc`, `Piecewise`, imaginary unit `i`, and unevaluated `Integral`).
3. For elementary real closed forms, substitution $\tau \mapsto -t$ produces valid real expressions such as `(-t)^m` and `\ln(-t)`.
4. `sp.integrate(..., risch=True)` checks SymPy's `NonElementaryIntegral` decision procedure first (~0.04s), avoiding >9s `heurisch` hangs on non-elementary integrands (e.g., $g(t) = e^{t^2}$) and immediately falling back to standard integration when Risch is not applicable (e.g., fractional powers or nested logarithms).

When an elementary closed-form antiderivative does not exist, the exact symbolic `sp.Integral` representation is preserved honestly, with canonical anchored definite integrals $\int_{t_0}^{t} (\cdot)\,ds$ for Cauchy IVPs so $y_p(t_0) = y_p'(t_0) = 0$ evaluates cleanly.

## 3. Verification Case Matrix & Mathematical Nuance on Case A

| Case | Equation / Scenario | Expected Behavior & Verified Outcome |
| :--- | :--- | :--- |
| **Case A (Distinct real roots — prompt fixture)** | $t^2 y'' - t y' - 2y = 1,\; t > 0$ | **Important mathematical clarification:** The indicial equation of $t^2 y'' - t y' - 2y = 0$ is $m(m-1) - m - 2 = m^2 - 2m - 2 = 0$, whose exact roots are $m_{1,2} = 1 \pm \sqrt{3}$ (NOT $2, -1$; the roots $2, -1$ correspond to $t^2 y'' - 2y = 0$ without the $-t y'$ term). Our solver honestly computes $m_{1,2} = 1 \pm \sqrt{3}$ and $y_p = -1/2$ for $t^2 y'' - t y' - 2y = 1$, AND computes $m = 2, -1$ with $y_c = C_1 t^2 + C_2 t^{-1}$ and $y_p = -1/2$ for $t^2 y'' - 2y = 1$. Both pass `VerificationStatus.VERIFIED`. |
| **Case B (Repeated root)** | $t^2 y'' - t y' + y = t^2,\; t > 0$ | Indicial root $m = 1$ (double), $y_c = t(C_1 + C_2 \ln t)$, $y_p = t^2$, `VERIFIED`. |
| **Case C (Complex conjugate roots)** | $t^2 y'' + t y' + y = t,\; t > 0$ | Indicial roots $\pm i$, $y_c = C_1 \cos(\ln t) + C_2 \sin(\ln t)$, $y_p = t/2$, `VERIFIED`. |
| **Case D (Resonance)** | $t^2 y'' - t y' + y = t,\; t > 0$ and $t^2 y'' - 2y = t^2,\; t > 0$ | Variation of Parameters handles resonant forcing directly without division-by-zero in characteristic polynomials, producing $y_p = \frac{1}{2} t (\ln t)^2$ and $y_p = \frac{1}{3} t^2 \ln t$, `VERIFIED`. |
| **Case E (Cauchy IVP)** | $t^2 y'' - t y' + y = t^2,\; y(1)=0,\; y'(1)=0$ | Solves $2\times 2$ linear system on $W \neq 0$, yielding unique solution $y(t) = t(t - \ln t - 1)$, satisfying equation and both ICs (`VERIFIED`). |
| **Case F (Negative domain)** | $t^2 y'' - t y' + y = t^2,\; t < 0$ | Uses $\tau = -t > 0$, producing real solution $y(t) = C_1(-t) + C_2(-t)\ln(-t) + t^2$ with zero complex artifacts (`VERIFIED`). |
| **Case G (Singular / invalid IVP guards)** | $t_0 = 0$; missing $y'(t_0)$; mismatched $t_0$; $g(t)=0$ guard; $g(t)$ pole at $t_0$; cross-zero interval | Rejected cleanly with honest Vietnamese mathematical validation explanations (`INVALID_INPUT`). |
| **Case H (Non-elementary forcing)** | $t^2 y'' - t y' + y = e^{t^2},\; t > 0$ | Risch detects `NonElementaryIntegral`; preserves exact `sp.Integral` expressions $t\ln t \int \frac{e^{t^2}}{t^2}dt - t\int \frac{e^{t^2}\ln t}{t^2}dt$ and verifies symbolically (`VERIFIED`). |
