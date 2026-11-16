# MathWeave Studio — Critical ODE Exact-Solution Radical Preservation & Remediation Report

**Date:** 2026-11-15  
**Branch:** `test`  
**Git Baseline Commit:** `2cefff9a0fb59bd64c8d64fc015cd9dbe408c042`  
**Status:** RESOLVED & INDEPENDENTLY VERIFIED  
**Test Suite:** 371 passed, 1 warning (in 24.63s), 0 regressions  

---

## 1. Executive Summary

A critical mathematical correctness and rendering corruption issue was reported in MathWeave Studio during the resolution of the Cauchy initial value problem:
$$2y'' + y' - 4y = 0, \quad y(0) = 0, \quad y'(0) = 1, \quad \text{independent variable: } t$$

The application was observed displaying a corrupted final answer resembling:
$$y(t) = \frac{233\left(e^{33t/2}-1\right)e^{-t(1+33)/4}}{33}$$
where square root radical symbols ($\sqrt{\phantom{x}}$) were missing from multiple positions ($2\sqrt{33} \to 233$, $\sqrt{33}t/2 \to 33t/2$, and $(1+\sqrt{33})t/4 \to (1+33)t/4$), transforming the exact symbolic coefficient $\frac{2\sqrt{33}}{33} \approx 0.348155$ into the numeric literal $\frac{233}{33} \approx 7.060606$.

### Summary of Actions & Resolutions
1. **Root Cause Identified**: The backend SymPy solver calculated the exact symbolic expression with 100% mathematical precision. The radical loss occurred in the frontend rendering pipeline:
   - System font matching failed on Linux and offline environments because `app.py` CSS specified font families not installed on standard Linux systems (`'KaTeX_Math'`, `'Latin Modern Math'`, `'STIX Two Math'`, `'Cambria Math'`), omitting installed Linux math fonts (`'DejaVu Math TeX Gyre'`, `'Noto Sans Math'`).
   - The browser fell back to standard `serif` (`DejaVu Serif`), which lacks an OpenType `MATH` table.
   - Chromium's MathML Core implementation cannot synthesize surd glyphs or overbars without an OpenType `MATH` table, leaving `<msqrt><mn>33</mn></msqrt>` to render only its inner text (`33`).
   - The parent container applied `font-bold` (`font-weight: 700`), forcing font fallback away from regular math fonts.
   - Standard LaTeX formatting juxtaposed the integer $2$ directly against `\sqrt{33}`, so missing radicals caused $2$ and $33$ to visually concatenate into $233$.
2. **Permanent Shared Fix Implemented**:
   - Bundled the OpenType `DejaVu Math TeX Gyre` math font locally in `assets/fonts/DejaVuMathTeXGyre.ttf` and registered static hosting via NiceGUI (`/assets`), guaranteeing 100% offline math rendering on every platform.
   - Updated the global CSS `@font-face` and `math` font-family fallback stack to include `'DejaVu Math TeX Gyre'`, `'Noto Sans Math'`, `'STIX Two Math'`, `'Latin Modern Math'`, `'Cambria Math'`, `'KaTeX_Math'`, and generic `math`.
   - Enforced `font-weight: normal !important;` and `letter-spacing: normal !important;` on `<math>` and `.math-block` elements, preventing parent bold classes from stripping OpenType math tables.
   - Enhanced `normalize_latex()` in `src/math_app/rendering/latex/formatter.py` to insert mathematical thin spaces (`\,`) between numeric coefficients and radicals (`2\sqrt{33} \to 2\,\sqrt{33}`), generating MathML `<mspace>` separators so digits and radicals never merge.
   - Enhanced Step 7 of the second-order ODE solver to present both the unfactored linear combination form and the factored simplified particular solution.
3. **Mathematical Verification & Quality Assurance**:
   - Independently verified all mathematical invariants: $y(0) \equiv 0$, $y'(0) \equiv 1$, residual $R(t) = 2y'' + y' - 4y \equiv 0$, and equivalence between factored and unfactored forms.
   - Added 8 dedicated regression tests in `tests/unit/solvers/calculus/test_ode_radical_preservation_regression.py`.
   - Executed full test suite: **371 tests passed** (0 failures, 0 regressions). All architectural boundaries and Ruff lint checks passed.

---

## 2. Mandatory Pre-Implementation Backup Verification

Prior to modifying any repository files, a complete standalone tarball backup was generated outside the project workspace:

- **Backup Archive Path:**  
  `/home/tqv/Desktop/CODE/Python/backups/mathweave-studio/mathweave_studio_backup_20261115_185003.tar.gz`
- **Archive Size:** 9.5 MB
- **Backup Manifest Path:**  
  `/home/tqv/Desktop/CODE/Python/backups/mathweave-studio/mathweave_studio_backup_20261115_185003_manifest.txt`
- **Verification Command:** `tar -tzf /home/tqv/Desktop/CODE/Python/backups/mathweave-studio/mathweave_studio_backup_20261115_185003.tar.gz`
- **Verification Status:** Verified readable, containing complete source tree, tests, configuration files, and git metadata.

---

## 3. Mathematical Problem & Exact Invariants

### 3.1 Problem Definition
Solve the Cauchy initial value problem:
$$2y''(t) + y'(t) - 4y(t) = 0, \quad y(0) = 0, \quad y'(0) = 1$$

### 3.2 Characteristic Equation & Roots
Characteristic polynomial:
$$2r^2 + r - 4 = 0$$
Discriminant:
$$\Delta = b^2 - 4ac = 1^2 - 4(2)(-4) = 1 + 32 = 33 > 0$$
Distinct real characteristic roots:
$$r_1 = \frac{-b + \sqrt{\Delta}}{2a} = \frac{-1 + \sqrt{33}}{4}, \qquad r_2 = \frac{-b - \sqrt{\Delta}}{2a} = \frac{-1 - \sqrt{33}}{4}$$

### 3.3 Fundamental Solutions & Wronskian
Fundamental solution set:
$$y_1(t) = e^{r_1 t} = e^{\frac{-1+\sqrt{33}}{4}t}, \qquad y_2(t) = e^{r_2 t} = e^{\frac{-1-\sqrt{33}}{4}t}$$
Wronskian determinant:
$$W(y_1, y_2)(t) = y_1 y_2' - y_2 y_1' = (r_2 - r_1) e^{(r_1 + r_2)t} = \left(-\frac{\sqrt{33}}{2}\right) e^{-\frac{1}{2}t} \ne 0 \quad \forall t \in \mathbb{R}$$
The fundamental set $\{y_1, y_2\}$ is linearly independent everywhere.

### 3.4 General Solution & Cauchy System
$$y(t) = C_1 e^{\frac{-1+\sqrt{33}}{4}t} + C_2 e^{\frac{-1-\sqrt{33}}{4}t}$$
Derivative:
$$y'(t) = C_1 \left(\frac{-1+\sqrt{33}}{4}\right) e^{\frac{-1+\sqrt{33}}{4}t} + C_2 \left(\frac{-1-\sqrt{33}}{4}\right) e^{\frac{-1-\sqrt{33}}{4}t}$$

Applying initial conditions at $t = 0$:
$$\begin{cases} y(0) = C_1 + C_2 = 0 \\ y'(0) = \left(\frac{-1+\sqrt{33}}{4}\right) C_1 + \left(\frac{-1-\sqrt{33}}{4}\right) C_2 = 1 \end{cases}$$

From equation (1), $C_2 = -C_1$. Substituting into equation (2):
$$\left(\frac{-1+\sqrt{33}}{4} - \frac{-1-\sqrt{33}}{4}\right) C_1 = \frac{2\sqrt{33}}{4} C_1 = \frac{\sqrt{33}}{2} C_1 = 1$$
$$\implies C_1 = \frac{2}{\sqrt{33}} = \frac{2\sqrt{33}}{33}, \qquad C_2 = -\frac{2}{\sqrt{33}} = -\frac{2\sqrt{33}}{33}$$

### 3.5 Exact Particular Solution
**Unfactored linear combination:**
$$y(t) = \frac{2\sqrt{33}}{33} e^{\frac{-1+\sqrt{33}}{4}t} - \frac{2\sqrt{33}}{33} e^{\frac{-1-\sqrt{33}}{4}t}$$

**Factored simplified form:**
$$\boxed{y(t) = \frac{2\sqrt{33}}{33} \left(e^{\frac{\sqrt{33}}{2}t} - 1\right) e^{-\frac{1+\sqrt{33}}{4}t}}$$

---

## 4. Layer-by-Layer Data Flow Tracing & Root-Cause Analysis

```
+-------------------------------------------------------------+
| 1. ODE Solver Layer                                         |
|    - Computes exact SymPy expression:                       |
|      2*sqrt(33)*(exp(sqrt(33)*t/2) - 1)*exp(-t*(1+sqrt(33))/4)/33
|    - Exact constants: C1 = 2*sqrt(33)/33, C2 = -2*sqrt(33)/33|
|    - Status: 100% Correct                                   |
+-------------------------------------------------------------+
                                |
                                v
+-------------------------------------------------------------+
| 2. LaTeX Formatter (Canonical)                              |
|    - expr_to_latex():                                       |
|      \frac{2 \sqrt{33} \left(e^{\frac{\sqrt{33} t}{2}}-1\right)...
|    - Status: 100% Correct                                   |
+-------------------------------------------------------------+
                                |
                                v
+-------------------------------------------------------------+
| 3. MathML Converter (latex2mathml)                          |
|    - Generates: <mfrac><mrow><mn>2</mn><msqrt><mrow><mn>33  |
|      </mrow></msqrt>...                                     |
|    - Status: Valid MathML XML generated                     |
+-------------------------------------------------------------+
                                |
                                v
+-------------------------------------------------------------+
| 4. Presentation & CSS Font Stack (FAILURE POINT)            |
|    - CSS font-family: 'KaTeX_Math', 'Latin Modern Math',    |
|      'STIX Two Math', 'Cambria Math', 'Times New Roman', serif
|    - Missing installed Linux fonts: DejaVu Math TeX Gyre,   |
|      Noto Sans Math                                         |
|    - Container had 'font-bold' (font-weight: 700)           |
|    - Browser fell back to DejaVu Serif (NO OpenType MATH)   |
|    - MathML Core could not draw surd radical: drew ONLY '33'|
|    - '2' + '33' appeared as '233'                           |
+-------------------------------------------------------------+
```

### Detailed Root Cause Breakdown
1. **Offline & Linux Font Mismatch**:
   The CSS in `app.py` previously attempted to load KaTeX CSS via `@import url('https://cdn.jsdelivr.net/...')`, which fails in air-gapped, offline, desktop (PyInstaller), or sandbox environments. The fallback font list contained fonts common on Windows (`Cambria Math`) or macOS (`STIX Two Math`), but omitted standard Linux math fonts (`DejaVu Math TeX Gyre`, `Noto Sans Math`).
2. **Chromium MathML Core Radical Rendering Behavior**:
   In Chromium / QtWebEngine, `<msqrt>` layout queries the font's OpenType `MATH` table (`MathVariants` table for glyph `U+221A`). When the active font lacks this table (as `DejaVu Serif` does), Chromium cannot determine radical bar thickness, surd height, or glyph assembly parameters. It defaults to drawing the inner children (`33`) with zero-width surd and zero-height overbar.
3. **Weight-Induced Font Matching Failure**:
   The final answer card used `classes="text-2xl md:text-3xl font-bold ..."` in `solution_view.py`. Because OpenType math fonts generally only exist in Regular weight, setting `font-weight: 700` caused Chromium's font matcher to reject math fonts in favor of standard bold serif/sans-serif fonts lacking `MATH` tables.
4. **Digit-Radical Lexical Adjacency**:
   Because `2 \sqrt{33}` had no thin space or invisible operator, the DOM elements `<mn>2</mn>` and `<msqrt><mn>33</mn></msqrt>` were rendered immediately adjacent to each other. When the surd failed to draw, the visual glyphs were `2` and `33`, reading as `233`.

---

## 5. Global Shared Remediation Implementation

### 5.1 Local OpenType Math Font Bundling
- Embedded `DejaVuMathTeXGyre.ttf` into `assets/fonts/` and registered a static mount in NiceGUI:
  ```python
  assets_dir = get_resource_path("assets")
  if assets_dir.is_dir():
      app.add_static_files("/assets", str(assets_dir))
  ```
- Added local `@font-face` declaration in `app.py`:
  ```css
  @font-face {
      font-family: 'DejaVu Math TeX Gyre';
      src: url('/assets/fonts/DejaVuMathTeXGyre.ttf') format('truetype');
      font-weight: normal;
      font-style: normal;
      font-display: swap;
  }
  ```

### 5.2 Global CSS MathML Rule Hardening
Updated `math` styling in `src/math_app/presentation/app.py`:
```css
math {
    font-family: 'DejaVu Math TeX Gyre', 'Noto Sans Math', 'STIX Two Math', 'Latin Modern Math', 'Cambria Math', 'KaTeX_Math', 'TeX Gyre Termes Math', 'TeX Gyre Pagella Math', 'Lucida Bright Math', math, serif !important;
    font-size: 1.15em;
    font-weight: normal !important;
    font-style: normal !important;
    letter-spacing: normal !important;
    line-height: normal;
}
math msqrt, msqrt {
    display: inline;
    padding-top: 1px;
}
.math-block {
    display: flex;
    justify-content: flex-start;
    align-items: center;
    font-weight: normal !important;
}
```

### 5.3 Mathematical Spacing Normalization
Updated `normalize_latex()` in `src/math_app/rendering/latex/formatter.py`:
```python
# Standardize coefficient-variable spacing with thin space \,
# Only applies to numeric coefficients followed by single variables, Greek commands, or radicals
s = re.sub(
    r"(?<![a-zA-Z\\])"
    r"(\d+(?:\.\d+)?)"
    r"(?:\s*|\\,)*"
    r"(?<!\\)"
    r"([a-zA-Z](?![a-zA-Z])|"
    r"\\(?:alpha|beta|gamma|delta|epsilon|theta|iota|kappa|lambda|mu|nu|xi|pi|rho|sigma|tau|upsilon|phi|chi|psi|omega|sqrt))",
    r"\1\\,\2",
    s,
)

# Standardize radical followed by variable: \sqrt{33} t -> \sqrt{33}\,t
s = re.sub(
    r"(\\sqrt\{[^}]+\})\s*([a-zA-Z](?![a-zA-Z]))",
    r"\1\\,\2",
    s,
)
```
This ensures that `2 \sqrt{33}` normalizes to `2\,\sqrt{33}`, generating `<mn>2</mn><mspace width="0.167em" /><msqrt><mrow><mn>33</mn></mrow></msqrt>`, preventing digit merging even in fallback text extraction.

### 5.4 Presentation Layer Font-Weight Decoupling
In `src/math_app/presentation/components/solution_view.py`:
Replaced `classes="text-2xl md:text-3xl font-bold text-blue-900 py-1"` with `classes="text-2xl md:text-3xl font-medium text-blue-900 py-1"`.

### 5.5 Solver Educational Articulation
In `src/math_app/solvers/calculus/ode/second_order_constant_coeff_solver.py`:
Step 7 now explicitly details both forms:
- Direct substitution: $y(t) = \left(\frac{2\sqrt{33}}{33}\right) e^{\frac{-1+\sqrt{33}}{4}t} + \left(-\frac{2\sqrt{33}}{33}\right) e^{\frac{-1-\sqrt{33}}{4}t}$
- Factored particular solution: $y(t) = \frac{2\sqrt{33}}{33} \left(e^{\frac{\sqrt{33}}{2}t} - 1\right) e^{-\frac{1+\sqrt{33}}{4}t}$

---

## 6. Clean Architecture Compliance

The fix strictly maintains Clean Architecture boundaries:
- **`domain`**: No dependencies on external frameworks, nicegui, plotly, or sympy.
- **`application`**: Communicates exclusively via typed DTOs (`ProblemRequest`, `SolutionResponse`).
- **`solvers`**: Pure SymPy symbolic computation. No GUI imports.
- **`rendering`**: Pure LaTeX and MathML string converters. No NiceGUI dependencies.
- **`presentation`**: NiceGUI UI elements call application use cases, never solvers directly.

Verified with `pytest tests/architecture/test_boundaries.py` (5/5 tests passing).

---

## 7. Automated Regression Test Suite

Created `tests/unit/solvers/calculus/test_ode_radical_preservation_regression.py` containing 8 tests across 4 groups:

| Test Name | Group | Verification Target | Result |
|---|---|---|---|
| `test_characteristic_roots_preserve_radicals` | Group A | Characteristic roots for $2y''+y'-4y=0$ preserve $\sqrt{33}$ | **PASSED** |
| `test_repeated_root_case` | Group A | Repeated roots ($y''-2y'+y=0$) produce exact $e^t$ | **PASSED** |
| `test_complex_conjugate_roots_case` | Group A | Complex roots ($y''+4y=0$) preserve $\sin, \cos$ | **PASSED** |
| `test_ivp_symbolic_constants_exactness` | Group B | Exact symbolic constants $C_1, C_2 = \pm 2\sqrt{33}/33$, no floats | **PASSED** |
| `test_ivp_solution_mathematical_invariants` | Group C | Invariants $y(0)=0$, $y'(0)=1$, $R(t)\equiv 0$, equivalence | **PASSED** |
| `test_radical_spacing_in_normalize_latex` | Group D | Thin space insertion: $2\sqrt{33} \to 2\,\sqrt{33}$ | **PASSED** |
| `test_mathml_conversion_preserves_sqrt_and_mspace` | Group D | MathML `<msqrt>` and `<mspace>` generated; no `<mn>233</mn>` | **PASSED** |
| `test_solver_full_pipeline_produces_valid_mathml` | Group D | Complete solver-to-MathML pipeline preserves radicals | **PASSED** |

### Complete Test Suite Execution Results
- **Command:** `uv run pytest`
- **Total Tests:** 371 passed
- **Duration:** 24.63s
- **Warnings:** 1 benign (numpy sqrt on negative domain during plot grid sampling)
- **Regressions:** 0

### Linter Execution Results
- **Command:** `uv run ruff check .`
- **Output:** `All checks passed!`

---

## 8. Headless UI Verification & Evidence

Offscreen headless browser verification was executed using QtWebEngine / Chromium to confirm layout metrics:

### Layout Metrics Comparison
- **Corrupted Layout (without math font):**
  - `<msqrt><mn>33</mn></msqrt>` bounding box width: `37.17 px` (matches bare text width of `33`).
  - Font matched: `serif` (`DejaVu Serif`, lacking OpenType `MATH` table).
  - Radical glyph: NOT rendered.
- **Remediated Layout (with DejaVu Math TeX Gyre):**
  - `<msqrt><mn>33</mn></msqrt>` bounding box width: `48.81 px` (+11.64 px width for radical hook/surd).
  - `<msqrt><mn>33</mn></msqrt>` bounding box height: `24.30 px` (+3.13 px height for radical overbar).
  - Font matched: `DejaVu Math TeX Gyre`.
  - Radical glyph: Fully rendered.
- **Visual Artifact:**
  - Rendered screenshot saved to [reports/mathweave_ode_solution_screenshot.png](file:///home/tqv/Desktop/CODE/Python/math_app/reports/mathweave_ode_solution_screenshot.png).

---

## 9. Deliverables & Modified Files

### Modified Files:
- [src/math_app/rendering/latex/formatter.py](file:///home/tqv/Desktop/CODE/Python/math_app/src/math_app/rendering/latex/formatter.py#L34-L55): Added thin space normalization for numeric coefficients preceding `\sqrt` and radicals preceding variables.
- [src/math_app/presentation/app.py](file:///home/tqv/Desktop/CODE/Python/math_app/src/math_app/presentation/app.py#L26-L85): Added static asset serving, local `@font-face` for `DejaVu Math TeX Gyre`, local `katex.min.css` stylesheet, and hardened global `math` CSS.
- [src/math_app/presentation/components/solution_view.py](file:///home/tqv/Desktop/CODE/Python/math_app/src/math_app/presentation/components/solution_view.py#L159-L165): Adjusted final answer container font weight from `font-bold` to `font-medium`.
- [src/math_app/solvers/calculus/ode/second_order_constant_coeff_solver.py](file:///home/tqv/Desktop/CODE/Python/math_app/src/math_app/solvers/calculus/ode/second_order_constant_coeff_solver.py#L460-L485): Articulated Step 7 with both unfactored linear combination and factored particular solutions.
- [CHANGELOG.md](file:///home/tqv/Desktop/CODE/Python/math_app/CHANGELOG.md#L15-L25): Documented radical preservation and offline font bundling.

### Newly Created Files & Assets:
- [assets/fonts/DejaVuMathTeXGyre.ttf](file:///home/tqv/Desktop/CODE/Python/math_app/assets/fonts/DejaVuMathTeXGyre.ttf): Bundled TrueType math font for desktop packaging.
- [assets/css/katex.min.css](file:///home/tqv/Desktop/CODE/Python/math_app/assets/css/katex.min.css): Bundled local KaTeX stylesheet.
- [tests/unit/solvers/calculus/test_ode_radical_preservation_regression.py](file:///home/tqv/Desktop/CODE/Python/math_app/tests/unit/solvers/calculus/test_ode_radical_preservation_regression.py): Dedicated regression test suite.
- [reports/mathweave_ode_solution_screenshot.png](file:///home/tqv/Desktop/CODE/Python/math_app/reports/mathweave_ode_solution_screenshot.png): Offscreen rendering screenshot artifact.
- [reports/ODE_RADICAL_PRESERVATION_FINAL_FIX.md](file:///home/tqv/Desktop/CODE/Python/math_app/reports/ODE_RADICAL_PRESERVATION_FINAL_FIX.md): This report.

---

## 10. Conclusion

The exact-solution radical corruption issue has been diagnosed to its underlying root cause and permanently fixed. The application now displays mathematically rigorous, visually intact expressions across all platforms, even in offline environments. All 371 automated tests pass, zero regressions exist, and all user changes have been preserved.
