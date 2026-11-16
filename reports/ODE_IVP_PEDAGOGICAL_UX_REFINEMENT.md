# MathWeave Studio — Second-Order ODE Pedagogical UX Refinement Report

**Date:** 2026-11-16  
**Branch:** `test`  
**Application:** MathWeave Studio (Clean Architecture, Python 3.14+, NiceGUI, SymPy, MathML, KaTeX)

---

## 1. Executive Summary

This report documents the pedagogical UX refinement of the Second-Order Ordinary Differential Equation (ODE) Cauchy Initial Value Problem (IVP) solution pipeline and the resolution of the visual defect in the final conclusion formula component.

All modifications strictly adhere to Clean Architecture boundaries, preserving mathematical correctness, symbolic precision, and existing test coverage without unnecessary refactoring.

---

## 2. Backup Archive & Workspace Preservation

In accordance with mandatory safety requirements, a complete backup archive was created outside the repository workspace prior to modifications:

- **Backup Archive Path:** `/tmp/mathweave_backup/mathweave_studio_backup_20261116_095323.tar.gz`
- **Archive Size:** 12 MB
- **Verification Command:** `tar -tzf /tmp/mathweave_backup/mathweave_studio_backup_20261116_095323.tar.gz | wc -l`
- **Verification Result:** 1,027 files verified readable and intact.
- **Git Branch Status:** Isolated to branch `test`; no branch switches, commits, merges, pushes, or releases performed. All existing user modifications in the working tree were preserved.

---

## 3. Root Cause Analysis

### 3.1. Issue 1: Step 6 Cauchy Initial Condition System Derivation Gap
- **Root Cause:** In `second_order_constant_coeff_solver.py`, Step 6 jumped directly from the initial conditions to a final algebraic system without displaying the derivation sequence: the general solution was not restated, its derivative was not explicitly evaluated, substitutions were not shown individually, and separate equations for $C_1$ and $C_2$ were omitted before forming the $2 \times 2$ matrix system.
- **Parameter Conflict in Parser:** In `src/math_app/input/ode_parser.py`, auto-detection of the independent variable checked the entire raw input string (including initial conditions). When an initial derivative had a symbolic parameter such as $y'(0) = x$ while the ODE had independent variable $t$, the presence of `x` in the initial condition mistakenly forced the independent variable to become $x$ instead of $t$.

### 3.2. Issue 2: Step 7 Compact Linear System Solution
- **Root Cause:** In Step 7, the solver immediately called `sp.solve(sys_eqs, [c1_sym, c2_sym])` and displayed the resulting constant values and substituted solution. Students could not follow the step-by-step algebraic transformations: isolating $C_1 = 2 - C_2$, substituting into equation (2), expanding $-4 + 2C_2 - 3C_2 = x$, isolating $-C_2 = x + 4 \implies C_2 = -x - 4$, and back-substituting to determine $C_1 = x + 6$. Furthermore, the equivalence between the expanded and factored forms was not demonstrated.

### 3.3. Issue 3: Step 8 Independent Mathematical Verification Purpose
- **Root Cause:** Step 8 showed a verification badge and residual formula without explaining its educational purpose to students ("Ta không tìm nghiệm mới mà kiểm tra lại nghiệm..."). It lacked distinct subsections for (A) verifying the differential equation residual ($R(t) \equiv 0$) and (B) independently verifying the initial conditions ($y(t_0) = y_0$ and $y'(t_0) = v_0$).

### 3.4. Issue 4: Visual Defect — Unwanted Inner Border Around Final Conclusion Formula
- **Root Cause:** In `src/math_app/presentation/components/step_viewer.py`, line 142 artificially wrapped the final answer LaTeX string in `\boxed{...}` (`boxed_latex = f"\\boxed{{{final_answer_latex}}}"`).
  - In KaTeX, `\boxed` expands to `\fbox{...}` rendered as `<span class="mord fbox">` with CSS `border: 0.04em solid;`.
  - In MathML (via `latex2mathml`), `\boxed` is converted to `<menclose notation="box">`, which browsers style with a solid black rectangular frame.
  This produced an unwanted dark inner rectangular frame tightly surrounding the formula inside the light-blue conclusion card.

---

## 4. Files Created and Modified

| File | Status | Description |
|---|---|---|
| `src/math_app/input/ode_parser.py` | Modified | Restricts independent variable auto-detection to the ODE equation string (`eq_str`), preventing initial condition parameters (e.g. `y'(0) = x`) from overriding independent variable `t`. |
| `src/math_app/solvers/calculus/ode/second_order_constant_coeff_solver.py` | Modified | Implements detailed 6-item sequence for Step 6, step-by-step substitution method with intermediate transformations for Step 7, and dual pedagogical verification (Sections A & B) for Step 8. |
| `src/math_app/presentation/components/step_viewer.py` | Modified | Removes artificial `\boxed{...}` wrapping on final conclusion formula; unescapes/strips any outer box wrappers; assigns `.conclusion-formula` class. |
| `src/math_app/presentation/app.py` | Modified | Adds scoped CSS rule suppressing any inner box borders inside `.conclusion-formula` while leaving the outer light-blue card and global focus outlines untouched. |
| `tests/unit/solvers/calculus/test_ode_ivp_pedagogical_refinement.py` | Created | 9 comprehensive regression tests for reference example with parameter $x$, Step 6 derivation, Step 7 algebraic transformations, Step 8 verification, FAILED/UNVERIFIED states, MathML rendering, and border fix. |
| `reports/ODE_IVP_PEDAGOGICAL_UX_REFINEMENT.md` | Created | Comprehensive final report detailing all requirements and verification results. |

---

## 5. Before / After Descriptions

### Step 6: Derive the Cauchy Initial Condition System

#### Before
- Description: `"Thay điều kiện ban đầu Cauchy y(t0) = y0 và y'(t0) = v0 vào nghiệm tổng quát và đạo hàm."`
- Equation: A simple system of two equations without derivation, or a raw matrix without explaining row origins.
- Substeps: None.

#### After
- Title: `"Thiết lập hệ phương trình xác định hằng số C1, C2"`
- Description:
  1. Displays general solution:
     $$y(t) = C_1 y_1(t) + C_2 y_2(t) = C_1 e^{-2t} + C_2 e^{-3t}$$
  2. Displays first derivative explicitly:
     $$y'(t) = C_1 y_1'(t) + C_2 y_2'(t) = -2C_1 e^{-2t} - 3C_2 e^{-3t}$$
  3. Substitutes $y(t_0) = y_0$:
     $$y(0) = C_1(1) + C_2(1) = C_1 + C_2 = 2$$
  4. Substitutes $y'(t_0) = v_0$:
     $$y'(0) = -2C_1(1) - 3C_2(1) = -2C_1 - 3C_2 = x$$
  5. Separates into individual equations:
     - Phương trình (1): $C_1 + C_2 = 2$
     - Phương trình (2): $-2C_1 - 3C_2 = x$
  6. Combines into $2 \times 2$ linear matrix system:
     $$\begin{pmatrix} 1 & 1 \\ -2 & -3 \end{pmatrix} \begin{pmatrix} C_1 \\ C_2 \end{pmatrix} = \begin{pmatrix} 2 \\ x \end{pmatrix}$$
- Equation:
  $$\begin{cases} C_1 + C_2 = 2 \\ -2C_1 - 3C_2 = x \end{cases} \iff \begin{pmatrix} 1 & 1 \\ -2 & -3 \end{pmatrix} \begin{pmatrix} C_1 \\ C_2 \end{pmatrix} = \begin{pmatrix} 2 \\ x \end{pmatrix}$$
- Substeps (Layer B):
  - Substep 6.1: Thay điều kiện hàm số ban đầu $y(t_0) = y_0$ vào nghiệm tổng quát.
  - Substep 6.2: Thay điều kiện đạo hàm ban đầu $y'(t_0) = v_0$ vào đạo hàm nghiệm tổng quát.
  - Substep 6.3: Xây dựng hệ ma trận $2 \times 2$.

---

### Step 7: Solve the Linear System Step by Step

#### Before
- Description: `"Giải hệ phương trình tuyến tính ta nhận được: C_1 = ... và C_2 = ... Thay vào nghiệm tổng quát..."`
- Equation: Directly showed the particular solution without intermediate transformations.
- Substeps: None.

#### After
- Title: `"Xác định nghiệm riêng thỏa mãn bài toán Cauchy (IVP)"`
- Description:
  1. Restates system from Step 6:
     $$\begin{cases} (1) \quad C_1 + C_2 = 2 \\ (2) \quad -2C_1 - 3C_2 = x \end{cases}$$
  2. Identifies method: Phương pháp thế (Method of Substitution).
  3. Shows ordered algebraic transformations:
     - Từ phương trình (1): $C_1 = 2 - C_2$
     - Thay vào phương trình (2): $-2(2 - C_2) - 3C_2 = x$
     - Khai triển: $-4 + 2C_2 - 3C_2 = x \implies -C_2 - 4 = x$
     - Cô lập: $-C_2 = x + 4 \implies C_2 = -x - 4$
     - Thay ngược: $C_1 = 2 - (-x - 4) = x + 6$
  4. Concludes constants: $C_1 = x + 6, \quad C_2 = -x - 4$.
  5. Substitutes into general solution:
     $$y(t) = (x + 6)e^{-2t} + (-x - 4)e^{-3t}$$
  6. Presents particular solution:
     $$y(t) = (-x + (x + 6)e^t - 4)e^{-3t}$$
  7. Displays factored equivalent form:
     $$y(t) = ((x + 6)e^t - x - 4)e^{-3t}$$
- Substeps (Layer B):
  - Substep 7.1: Biểu diễn $C_1$ theo $C_2$ từ phương trình thứ nhất.
  - Substep 7.2: Thay $C_1$ vào phương trình thứ hai.
  - Substep 7.3: Xác định giá trị hằng số $C_2$.
  - Substep 7.4: Thay ngược $C_2$ để xác định hằng số $C_1$.

---

### Step 8: Explain Independent Mathematical Verification

#### Before
- Title: `"Kiểm chứng toán học độc lập"`
- Description: Single line noting residual formula $R(t)$ with brief status string.
- Substeps: None.

#### After
- Title: `"Kiểm chứng nghiệm"` (renders as `"Bước 8: Kiểm chứng nghiệm"`)
- Pedagogical Explanation:
  > *"Bước này không tìm nghiệm mới. Ta thay nghiệm vừa tìm được trở lại phương trình vi phân ban đầu và kiểm tra các điều kiện ban đầu để xác nhận rằng nghiệm thực sự đúng."*
- Section A (Differential Equation):
  $$R(t) = 1\,y''(t) + 5\,y'(t) + 6\,y(t)$$
  Substitution of $y(t), y'(t), y''(t)$ with algebraic cancellation establishing:
  $$R(t) \equiv 0 \quad \text{(Thỏa mãn đồng nhất)}$$
- Section B (Initial Conditions):
  1. $y(0) = (x + 6) - (x + 4) = 2 = y_0 \quad \text{(Thỏa mãn)}$
  2. $y'(0) = -2(x + 6) - 3(-x - 4) = -2x - 12 + 3x + 12 = x = v_0 \quad \text{(Thỏa mãn)}$
- Substeps (Layer B):
  - Substep 8.1: Kiểm chứng vế trái phương trình vi phân ($R(t) \equiv 0$).
  - Substep 8.2: Kiểm chứng hệ điều kiện ban đầu Cauchy ($y(0) = 2, y'(0) = x$).
- Status Badge:
  - Green `✓ Đã kiểm chứng toán học` only when all checks are mathematically proven.
  - `✗ Phát hiện sai lệch toán học` (FAILED) if any condition is violated.
  - `⚠ Chưa kiểm chứng độc lập` (UNVERIFIED) if symbolic simplification is inconclusive.

---

## 6. Mathematical Derivation for the Reference Example

**Problem:**
$$y'' + 5y' + 6y = 0, \quad y(0) = 2, \quad y'(0) = x, \quad \text{biến độc lập } t$$

1. **Phương trình đặc trưng:**
   $$r^2 + 5r + 6 = 0$$

2. **Biệt thức Delta:**
   $$\Delta = 5^2 - 4(1)(6) = 25 - 24 = 1 > 0$$

3. **Nghiệm phương trình đặc trưng:**
   $$r_1 = \frac{-5 + 1}{2} = -2, \quad r_2 = \frac{-5 - 1}{2} = -3$$

4. **Nghiệm tổng quát:**
   $$y(t) = C_1 e^{-2t} + C_2 e^{-3t}$$

5. **Đạo hàm cấp một:**
   $$y'(t) = -2C_1 e^{-2t} - 3C_2 e^{-3t}$$

6. **Thiết lập hệ phương trình Cauchy:**
   - Thay $t = 0$ vào $y(t)$:
     $$C_1 e^0 + C_2 e^0 = 2 \implies C_1 + C_2 = 2 \quad (1)$$
   - Thay $t = 0$ vào $y'(t)$:
     $$-2C_1 e^0 - 3C_2 e^0 = x \implies -2C_1 - 3C_2 = x \quad (2)$$
   - Hệ phương trình dạng ma trận:
     $$\begin{pmatrix} 1 & 1 \\ -2 & -3 \end{pmatrix} \begin{pmatrix} C_1 \\ C_2 \end{pmatrix} = \begin{pmatrix} 2 \\ x \end{pmatrix}$$

7. **Giải hệ phương trình:**
   - Từ (1): $C_1 = 2 - C_2$
   - Thay vào (2):
     $$-2(2 - C_2) - 3C_2 = x \implies -4 + 2C_2 - 3C_2 = x \implies -C_2 = x + 4 \implies C_2 = -x - 4$$
   - Thay ngược:
     $$C_1 = 2 - (-x - 4) = x + 6$$
   - Nghiệm riêng dạng khai triển:
     $$y(t) = (x + 6)e^{-2t} + (-x - 4)e^{-3t}$$
   - Dạng đặt nhân tử chung tương đương:
     $$y(t) = \left((x + 6)e^t - x - 4\right) e^{-3t}$$
   - Chứng minh tương đương hình thức:
     $$(x + 6)e^{-2t} + (-x - 4)e^{-3t} - ((x + 6)e^t - x - 4)e^{-3t} = (x + 6)e^{-2t} - (x + 6)e^{-2t} - (x + 4)e^{-3t} + (x + 4)e^{-3t} \equiv 0$$

8. **Kiểm chứng độc lập:**
   - **Phần A (Phương trình):**
     $$y'(t) = -2(x + 6)e^{-2t} - 3(-x - 4)e^{-3t} = -(2x + 12)e^{-2t} + (3x + 12)e^{-3t}$$
     $$y''(t) = 4(x + 6)e^{-2t} + 9(-x - 4)e^{-3t} = (4x + 24)e^{-2t} - (9x + 36)e^{-3t}$$
     $$R(t) = y'' + 5y' + 6y = [4x + 24 - 10x - 60 + 6x + 36]e^{-2t} + [-9x - 36 + 15x + 60 - 6x - 24]e^{-3t} = 0 \equiv 0$$
   - **Phần B (Điều kiện ban đầu):**
     $$y(0) = (x + 6) + (-x - 4) = 2 \quad (\text{Khớp với } y_0 = 2)$$
     $$y'(0) = -2(x + 6) - 3(-x - 4) = -2x - 12 + 3x + 12 = x \quad (\text{Khớp với } v_0 = x)$$

---

## 7. Resolution of the Final Conclusion Inner Border Visual Defect

### 7.1. Mechanism of the Defect
In `step_viewer.py`:
```python
# Before
boxed_latex = f"\\boxed{{{final_answer_latex}}}"
ui_math(boxed_latex, block=True, classes="text-xl md:text-2xl font-bold text-blue-900 py-1")
```
- `\boxed{...}` prompted KaTeX to output `.fbox { border: 0.04em solid; }` and `latex2mathml` to output `<menclose notation="box">`.
- This resulted in an extra dark black rectangular border framing the mathematical symbols inside the light-blue conclusion card.

### 7.2. Implementation of the Fix
```python
# After
clean_conclusion = final_answer_latex.strip()
if clean_conclusion.startswith(r"\boxed{") and clean_conclusion.endswith("}"):
    clean_conclusion = clean_conclusion[7:-1].strip()
elif clean_conclusion.startswith(r"\fbox{") and clean_conclusion.endswith("}"):
    clean_conclusion = clean_conclusion[6:-1].strip()

with ui.card().classes("w-full p-4.5 my-2 border-2 border-blue-200 bg-gradient-to-r from-blue-50/80 to-indigo-50/60 rounded-xl gap-2 shadow-xs"):
    with ui.row().classes("items-center gap-2"):
        ui.icon("task_alt", color="primary", size="1.3rem")
        ui.label("Kết luận:").classes("text-base font-bold text-blue-950")
    ui_math(clean_conclusion, block=True, classes="conclusion-formula text-xl md:text-2xl font-bold text-blue-900 py-1")
```
Scoped CSS defense-in-depth added to `src/math_app/presentation/app.py`:
```css
/* Clean conclusion card formula: eliminate inner boxed borders while preserving outer card */
.conclusion-formula menclose[notation="box"],
.conclusion-formula .fbox {
    border: none !important;
}
```

### 7.3. Preservation Constraints
- **Outer Card Preserved:** The outer conclusion card styling (`border-2 border-blue-200 bg-gradient-to-r from-blue-50/80 to-indigo-50/60 rounded-xl`) remains unchanged.
- **MathML & Typography Preserved:** Native MathML font rendering (`DejaVu Math TeX Gyre`), KaTeX fallback, and responsive formula scaling remain intact.
- **Accessibility Protected:** Global focus outlines and interactive control borders were not disabled or modified.

---

## 8. Verification and Test Results

### 8.1. Unit Test Suite
- **Command:** `uv run pytest`
- **Total Tests:** 384 passed, 0 failed, 1 harmless warning (`RuntimeWarning: invalid value encountered in sqrt` in 2D plot sampling boundary check).
- **Execution Time:** ~26.3 seconds.

### 8.2. Dedicated Pedagogical Test Suite
- **Command:** `uv run pytest tests/unit/solvers/calculus/test_ode_ivp_pedagogical_refinement.py`
- **Results:** 9 passed in 1.00s.
  - `test_reference_example_parser_preserves_x_as_parameter`: PASSED
  - `test_reference_example_step6_cauchy_derivation_sequence`: PASSED
  - `test_reference_example_step7_algebraic_solution_and_equivalence`: PASSED
  - `test_reference_example_step8_independent_verification`: PASSED
  - `test_verification_status_failed_on_invalid_conditions`: PASSED
  - `test_verification_status_failed_on_wrong_ode_solution`: PASSED
  - `test_mathml_rendering_of_all_new_derivation_steps`: PASSED
  - `test_final_conclusion_card_has_no_inner_box_border`: PASSED
  - `test_use_case_end_to_end_regression`: PASSED

### 8.3. Static Code Analysis (Ruff)
- **Command:** `uv run ruff check .`
- **Result:** `All checks passed!` (0 lint errors across the entire codebase).

### 8.4. Architecture Boundaries
- **Command:** `uv run pytest tests/architecture/test_boundaries.py`
- **Result:** 5 passed in 0.12s.
  - Domain isolation: Verified.
  - Application port boundaries: Verified.
  - Solver independence from presentation/Plotly: Verified.

### 8.5. UI Rendering Evidence
- Rendered HTML confirmed free of `<menclose notation="box">` and `.fbox`.
- KaTeX data attributes (`data-tex`, `data-display="block"`) verified present for cross-browser fallback.
- No unescaped user input or HTML injection vulnerabilities detected.

---

## 9. Remaining Limitations and Unverified Assumptions

1. **Nonlinear & Nonhomogeneous Second-Order ODEs:**
   The current solver explicitly addresses homogeneous linear constant-coefficient second-order ODEs and known-solution variable-coefficient ODEs (Reduction of Order). General nonhomogeneous ODEs ($a y'' + b y' + c y = f(t)$) report `CANNOT_SOLVE` as designed until Milestone Phase 2.
2. **Symbolic Discriminant Sign Ambiguity:**
   If the characteristic equation discriminant $\Delta$ contains undetermined symbolic parameters where the sign cannot be proven real or nonzero, the solver safely reports `CANNOT_SOLVE` with guidance to provide parameter assumptions.
3. **Cross-Platform Visual Inspection:**
   All unit, pipeline, and MathML DOM tests passed on Linux (x86_64). Desktop Webview and browser presentation on Windows/macOS require platform-specific CI runs to capture native window screenshots.
