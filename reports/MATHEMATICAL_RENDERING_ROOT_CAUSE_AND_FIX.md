# MathWeave Studio — Mathematical Rendering Root Cause Investigation & Permanent Fix Report

**Date:** November 15, 2026  
**Target Application:** MathWeave Studio  
**Branch:** `test`  
**Status:** Resolved, Verified, All Checks Passing (375/375 unit/integration/architecture tests)

---

## 1. Executive Summary

A critical mathematical display defect was reported in MathWeave Studio:
When solving the second-order ordinary differential equation (ODE) with Cauchy initial values:
\[
2y'' + y' - 4y = 0, \quad y(0) = 0, \quad y'(0) = 1, \quad \text{variable: } t
\]
the application visually exhibited missing radical symbols throughout its user interface:
- \(2\sqrt{33}\) was displayed as `233` or `2 33`
- \(\sqrt{33}t/2\) was displayed as `33t/2`
- \((1+\sqrt{33})t/4\) was displayed as `(1+33)t/4`
- Explanatory pedagogical text across Calculus, Linear Algebra, and ODE modules displayed raw programmer tokens (e.g. `sqrt(33)`, `R_{1} \leftrightarrow R_{2}`, `C1*y1 + C2*y2`, `(Delta > 0)`).

Through systematic empirical tracing across the entire data-to-rendering pipeline (from symbolic SymPy engine to frontend browser layout engine), we identified **two primary root causes**:

1. **Frontend Chromium/QtWebEngine/WebView2 MathML Layout Engine Failure:**
   Native browser MathML layout for `<msqrt>` requires an OpenType `MATH` table (`MathVariants` table for glyph `U+221A`). In Chromium-based runtimes, when the active font lacks an OpenType `MATH` table (falling back to fonts like `DejaVu Serif`), Chromium computes **0 width** for the radical hook. Consequently, `<mn>2</mn><msqrt><mn>33</mn></msqrt>` placed the radical bar over nothing or skipped the surd hook, rendering `2` and `33` with zero visible radical surd! Furthermore, a global CSS override `math msqrt, msqrt { display: inline; }` stripped `display: block math`, breaking the MathML radical layout even further.
2. **Pedagogical Prose Parsing & Component Failure:**
   `delimit_unwrapped_math_in_text()` previously wrapped `sqrt(...)` into `$sqrt(...)` (without a backslash `\`), causing `latex2mathml` and KaTeX to interpret `sqrt(33)` as four multiplied variables \(s \cdot q \cdot r \cdot t(33)\). In addition, for expressions like `2*sqrt(33)/33`, regex only captured `sqrt(33)`, creating fragmented text `2*$sqrt(33)$/33`. Step titles and notes were also passed directly to plain text `ui.label()` and `ui.badge()` components which never parsed mathematical delimiters.

**Implemented Permanent Remediation:**
- **Local KaTeX Offline Integration (Option B):** Staged local, self-contained KaTeX offline assets (`assets/katex/katex.js`, `assets/katex/katex.css`, and full WOFF2/WOFF/TTF fonts) into MathWeave Studio. Mounted under `/assets/katex/` with zero external CDN dependency.
- **Client-Side KaTeX Upgrade with MathML Fallback:** Server generates `<span class="math-inline math-tex" data-tex="..." data-display="inline">{mathml}</span>`. The native MathML is immediately available for SSR/accessibility/non-JS contexts, while client-side KaTeX generates vector SVG radical paths with non-zero surd geometry and exact math typography, completely immune to missing OS OpenType tables.
- **Resilient Dynamic Vue/NiceGUI DOM Observer:** Injected a `MutationObserver` and periodic listener in `app.py` ensuring that dynamically generated math elements (upon clicking Solve) are immediately upgraded without page refresh.
- **Comprehensive Natural Language Math Processor:** Overhauled `delimit_unwrapped_math_in_text()` in `text_math_renderer.py` to handle linear algebra row operations (`R_{1} \leftrightarrow R_{2}`), quadratic discriminant \(\Delta\) expressions (`(\Delta > 0)`), coefficients with radicals (`C1 = 2*sqrt(33)/33`), exponential terms (`exp(sqrt(33)*t/2)`), and Cauchy conditions (`y(0) = 0, y'(0) = 1`).
- **Pedagogical Step Viewer Upgrade:** Updated `step_viewer.py` to render step titles, rule names, and notes using `ui_math_text`.

---

## 2. Pre-Implementation Backup Manifest

Before modifying any project files, a complete external backup archive and git patch were created and verified outside the workspace:

- **Archive Location:** `/home/tqv/Desktop/CODE/Python/backups/mathweave-studio/mathweave_studio_backup_20261115_214432.tar.gz`
- **Archive Size:** 4,499,313 bytes (4.5 MB, 292 files)
- **Patch Location:** `/home/tqv/Desktop/CODE/Python/backups/mathweave-studio/mathweave_studio_diff_20261115_214432.patch` (107 KB)
- **Manifest File:** `/home/tqv/Desktop/CODE/Python/backups/mathweave-studio/mathweave_studio_manifest_20261115_214432.txt`
- **Verification:** Verified with `tar -tzf` with exit code 0.

---

## 3. Data Flow & Checkpoint Diagnostic Analysis

To pinpoint the exact stage where mathematical expressions lost radical symbols, we tested each checkpoint of the pipeline:

### Checkpoint A: Symbolic Computation (SymPy Engine)
- **Input:** \(2y'' + y' - 4y = 0, y(0) = 0, y'(0) = 1\)
- **Solver:** `ODESecondOrderConstantCoeffSolver.solve()`
- **Result:**
  - `delta = 33`
  - `r1 = -1/4 + sqrt(33)/4`, `r2 = -1/4 - sqrt(33)/4`
  - `c1 = 2*sqrt(33)/33`, `c2 = -2*sqrt(33)/33`
  - `final_sol = 2*sqrt(33)*(exp(sqrt(33)*t/2) - 1)*exp(-t*(1 + sqrt(33))/4)/33`
- **Evaluation:** **PASSED**. Symbolic computation in SymPy was 100% exact. No radical loss occurred here.

### Checkpoint B: LaTeX Generation (`expr_to_latex`)
- **Execution:** `expr_to_latex(final_sol)`
- **Output:**
  ```latex
  y(t) = \frac{2 \sqrt{33} \left(e^{\frac{\sqrt{33} t}{2}} - 1\right) e^{- \frac{t \left(1 + \sqrt{33}\right)}{4}}}{33}
  ```
- **Evaluation:** **PASSED**. LaTeX string contained all `\sqrt{33}` commands and correct parentheses.

### Checkpoint C: LaTeX Normalization (`normalize_latex`)
- **Execution:** `normalize_latex(cleaned)`
- **Output:** Preserved `\sqrt{33}` intact, applied thin space `2\,\sqrt{33}` and `\sqrt{33}\,t`.
- **Evaluation:** **PASSED**.

### Checkpoint D: MathML Serialization (`latex2mathml`)
- **Execution:** `latex2mathml.converter.convert(latex_str)`
- **Output:**
  ```xml
  <mfrac>
    <mrow>
      <mn>2</mn><mspace width="0.167em" /><msqrt><mrow><mn>33</mn></mrow></msqrt>
      <mo stretchy="false">(</mo>
      <msup>
        <mi>e</mi>
        <mrow><mfrac><mrow><msqrt><mrow><mn>33</mn></mrow></msqrt><mspace width="0.167em" /><mi>t</mi></mrow><mrow><mn>2</mn></mrow></mfrac></mrow>
      </msup>
      ...
    </mrow>
    <mrow><mn>33</mn></mrow>
  </mfrac>
  ```
- **Evaluation:** **PASSED**. Valid MathML with `<msqrt>` elements was produced.

### Checkpoint E: Browser Rendering & Layout Engine (THE FIRST ROOT CAUSE)
- **Empirical Measurement in Chromium / QtWebEngine:**
  We measured DOM geometry via JavaScript `getBoundingClientRect()` on native MathML `<msqrt>`:
  - `<mn>33</mn>` width: `17.890625 px`
  - `<msqrt><mn>33</mn></msqrt>` width: `17.890625 px`!
- **Root Cause Discovery:**
  The radical hook width was exactly `0 px`! Chromium's MathML layout engine requires an OpenType font with an explicit `MATH` table (`MathVariants` table for glyph `U+221A`). When the system falls back to a font without this table (e.g., standard `DejaVu Serif`), Chromium computes zero width for the radical hook and fails to draw the surd glyph. In addition, the stylesheet rule `math msqrt, msqrt { display: inline; }` forced an inline layout on a block math element, destroying the radical layout entirely.
- **Evaluation:** **PROVEN FIRST FAILURE POINT**.

### Checkpoint F: Explanatory Prose Parser (THE SECOND ROOT CAUSE)
- **Issue 1:** `delimit_unwrapped_math_in_text()` regex produced `$sqrt(33)$` (no backslash), which rendered as \(s \cdot q \cdot r \cdot t(33)\).
- **Issue 2:** `2*sqrt(33)/33` only matched `sqrt(33)`, fragmenting into `2*$sqrt(33)$/33`.
- **Issue 3:** Linear algebra row operations `R_{1} \leftrightarrow R_{2}` and titles with `(Delta > 0)` were rendered by `ui.label()` as plain text.
- **Evaluation:** **PROVEN SECOND FAILURE POINT**.

---

## 4. Architecture and Implementation Details

### 4.1. Local KaTeX Offline Assets
We copied the complete offline KaTeX distribution (v0.16.x) into `assets/katex/`:
```
assets/katex/
├── katex.css
├── katex.js
├── LICENSE
├── README.md
└── fonts/
    ├── KaTeX_AMS-Regular.woff2 / .woff / .ttf
    ├── KaTeX_Main-Regular.woff2 / .woff / .ttf
    ├── KaTeX_Math-Italic.woff2 / .woff / .ttf
    ├── KaTeX_Size1-Regular.woff2 ...
    └── [20+ OpenType/TrueType/WOFF font variants]
```
Mounted in `app.py`:
```python
if base_assets.is_dir():
    app.add_static_files("/assets", str(base_assets))
```

### 4.2. Dual MathML Fallback + KaTeX Client-Side Renderer
In `src/math_app/rendering/text_math_renderer.py`:
```python
def convert_latex_to_mathml(latex_str: str, block: bool = False, is_icon: bool = False) -> str:
    cleaned = latex_str.strip()
    if not cleaned:
        return ""

    normalized = normalize_latex(cleaned)
    escaped_tex = html.escape(normalized)
    display_mode = "block" if block else "inline"

    if is_icon:
        cls = "math-icon math-container math-tex select-none pointer-events-none"
    else:
        cls = "math-block math-tex my-1" if block else "math-inline math-tex"

    tag = "div" if block else "span"

    try:
        mathml = latex2mathml.converter.convert(normalized, display="block" if block else "inline")
        if re.search(r"<(?:script|iframe|object|embed|style)", mathml, re.IGNORECASE) or re.search(r"\bon\w+\s*=", mathml, re.IGNORECASE):
            raise ValueError("Unsafe HTML tags or event handlers detected in MathML output.")
        return f'<{tag} class="{cls}" data-tex="{escaped_tex}" data-display="{display_mode}">{mathml}</{tag}>'
    except Exception:
        safe_fallback = html.escape(normalized)
        fallback_cls = (
            f"{cls} math-fallback font-serif text-blue-900 tracking-wide select-none"
            if is_icon
            else f"{cls} math-fallback font-serif text-blue-900 tracking-wide"
        )
        return f'<{tag} class="{fallback_cls}" data-tex="{escaped_tex}" data-display="{display_mode}">{safe_fallback}</{tag}>'
```

### 4.3. Client-Side MutationObserver
In `src/math_app/presentation/app.py`:
```javascript
(function() {
    function renderMathElement(el) {
        if (!window.katex || el.getAttribute('data-rendered') === 'true') return;
        const tex = el.getAttribute('data-tex');
        if (!tex) return;
        const isBlock = el.getAttribute('data-display') === 'block';
        try {
            window.katex.render(tex, el, {
                displayMode: isBlock,
                throwOnError: false,
                output: 'htmlAndMathml'
            });
            el.setAttribute('data-rendered', 'true');
        } catch (e) {
            console.warn('KaTeX render error:', e);
        }
    }

    function renderAllMath(root) {
        if (!window.katex) return;
        const target = root || document.body;
        if (!target) return;
        if (target.matches && target.matches('.math-tex:not([data-rendered="true"])')) {
            renderMathElement(target);
        }
        const elements = target.querySelectorAll('.math-tex:not([data-rendered="true"])');
        elements.forEach(renderMathElement);
    }

    window.renderAllMath = renderAllMath;

    const observer = new MutationObserver(function(mutations) {
        if (!window.katex) return;
        for (let i = 0; i < mutations.length; i++) {
            const m = mutations[i];
            for (let j = 0; j < m.addedNodes.length; j++) {
                const node = m.addedNodes[j];
                if (node.nodeType === 1) {
                    renderAllMath(node);
                }
            }
        }
    });

    document.addEventListener('DOMContentLoaded', function() {
        renderAllMath();
        if (document.body) {
            observer.observe(document.body, { childList: true, subtree: true });
        }
    });

    window.addEventListener('load', function() {
        renderAllMath();
    });

    setInterval(renderAllMath, 500);
})();
```

### 4.4. Natural Language Math Pipeline in `delimit_unwrapped_math_in_text`
The parser performs staged parsing across non-mathematical text chunks:
1. **Row operations in linear algebra:** `R_{1} \leftrightarrow R_{2}` wrapped into `$R_{1} \leftrightarrow R_{2}$`.
2. **Delta expressions:** `(Delta > 0)` \(\to\) `$(\Delta > 0)$`, `Delta = 33` \(\to\) `$\Delta = 33$`.
3. **Exp with radicals:** `exp(sqrt(33)*t/2)` \(\to\) `$e^{\frac{\sqrt{33} t}{2}}$`.
4. **Equation with radical fractions:** `r1 = (-1 + sqrt(33))/4` \(\to\) `$r_1 = \frac{-1 + \sqrt{33}}{4}$`.
5. **Equation with radicals:** `C1 = 2*sqrt(33)/33` \(\to\) `$C_1 = \frac{2\sqrt{33}}{33}$`.
6. **Standalone radical expressions:** `2*sqrt(33)/33` \(\to\) `$\frac{2\sqrt{33}}{33}$`, `-2*sqrt(33)/33` \(\to\) `$-\frac{2\sqrt{33}}{33}$`.
7. **Linear combinations & Wronskian:** `C1*y1 + C2*y2` \(\to\) `$C_1 y_1 + C_2 y_2$`, `W(y1, y2)` \(\to\) `$W(y_1, y_2)$`.
8. **Cauchy conditions:** `y(0) = 0` \(\to\) `$y(0) = 0$`, `y'(0) = 1` \(\to\) `$y'(0) = 1$`.
9. **Programmer exponents:** `x**2` \(\to\) `$x^2$`.

---

## 5. Verification & Test Evidence

### 5.1. Automated Test Suite Results
Executed `uv run pytest`:
```
======================= 375 passed, 1 warning in 25.08s ========================
```
- **Total Test Cases:** 375
- **Passed:** 375
- **Failed:** 0
- **Errors:** 0

### 5.2. Clean Architecture Boundary Enforcement
Executed `uv run pytest tests/architecture/test_boundaries.py`:
```
tests/architecture/test_boundaries.py .....                              [100%]
============================== 5 passed in 0.13s ===============================
```
All boundary isolation rules between `domain`, `application`, `solvers`, `verification`, `rendering`, and `presentation` are strictly preserved.

### 5.3. Code Style & Linting
Executed `uv run ruff check .`:
```
All checks passed!
```

### 5.4. Empirical Browser Rendering & DOM Inspection
Executed in QtWebEngine (Chromium) on active Wayland display (`wayland-1`):
- **Total rendered math elements:** 30
- **Final box TeX:**
  \[
  y(t) = \frac{2\,\sqrt{33} \left(e^{\frac{\sqrt{33}\,t}{2}} - 1\right) e^{- \frac{t \left(1 + \sqrt{33}\right)}{4}}}{33}
  \]
- **Final box SVG vector paths count:** 3
  - **SVG 0 path (numerator radical):** `M95,702 c-2.7,0,-7.17,-2.7,-13...` (geometry verified)
  - **SVG 1 path (first exponent radical):** `M95,702 c-2.7,0,-7.17,-2.7,-13...` (geometry verified)
  - **SVG 2 path (second exponent radical):** `M95,702 c-2.7,0,-7.17,-2.7,-13...` (geometry verified)
- **High-Resolution Screenshot Saved:**
  `mathweave_ode_solution_screenshot.png` (296 KB, 1550x1486 px) at file:///home/tqv/.gemini/antigravity-cli/brain/6def57aa-024e-45fa-a426-87f9cede2067/mathweave_ode_solution_screenshot.png

---

## 6. Summary of Changed Files

1. `src/math_app/rendering/text_math_renderer.py`:
   - Updated `convert_latex_to_mathml` to output `.math-tex` containers with `data-tex` attributes.
   - Re-engineered `delimit_unwrapped_math_in_text` to cleanly transform unwrapped radicals, row operations, Delta, and Cauchy conditions into canonical LaTeX delimiters.
2. `src/math_app/presentation/app.py`:
   - Integrated offline KaTeX CSS and JS from local `/assets/katex/`.
   - Added client-side KaTeX rendering engine with dynamic `MutationObserver`.
   - Removed destructive `math msqrt { display: inline; }` rule and removed external CDN dependency.
3. `src/math_app/presentation/components/step_viewer.py`:
   - Enhanced step titles, rule badges, and notes to render mathematical content via `ui_math_text`.
4. `tests/unit/rendering/test_text_math_renderer.py`:
   - Added unit test cases for row operations, Delta expressions, radical fractions, and Cauchy conditions.
