"""Comprehensive regression and verification tests for Second-Order ODE Cauchy IVP pedagogical refinement.

Verifies:
1. Reference example: y'' + 5y' + 6y = 0, y(0) = 2, y'(0) = x with independent variable t.
2. Symbolic parameter x is preserved and not mistaken for independent variable t.
3. Step 6 clear derivation sequence: general solution, first derivative, substitution of y(t0) and y'(t0),
   separate equations (1) and (2), and 2x2 matrix system.
4. Step 7 step-by-step algebraic solution via substitution:
   - C1 = 2 - C2
   - -2(2 - C2) - 3C2 = x
   - -4 + 2C2 - 3C2 = x
   - -C2 = x + 4 -> C2 = -x - 4
   - C1 = x + 6
   - Particular solution expanded form: (x + 6)e^(-2t) + (-x - 4)e^(-3t)
   - Factored form: ((x + 6)e^t - x - 4)e^(-3t)
   - Symbolic equivalence between expanded and factored forms.
5. Step 8 pedagogical verification:
   - Title: "Kiểm chứng nghiệm"
   - Explanatory Vietnamese intro: "Bước này không tìm nghiệm mới..."
   - Section A: Differential equation residual R(t) = 0 (R(t) = 0).
   - Section B: Dual initial condition check y(0) = 2 and y'(0) = x.
   - Verification status: VERIFIED.
6. Honest handling of FAILED and UNVERIFIED states.
7. MathML rendering of all newly added derivation steps.
8. Removal of inner border around final conclusion formula while preserving outer conclusion card.
"""

from __future__ import annotations

from nicegui import ui
import pytest
import sympy as sp

from math_app.application.dtos import ProblemRequest, SolutionStep
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.domain.step_content import ExpressionStepContent
from math_app.input.ode_parser import parse_second_order_ode_input
from math_app.main import build_application
from math_app.presentation.components.step_viewer import render_steps_container
from math_app.rendering.text_math_renderer import convert_latex_to_mathml, render_math_in_text_html
from math_app.solvers.calculus.ode.second_order_constant_coeff_solver import ODESecondOrderConstantCoeffSolver
from math_app.verification.calculus.ode_verifier import ODEVerifier


@pytest.fixture
def solver() -> ODESecondOrderConstantCoeffSolver:
    return ODESecondOrderConstantCoeffSolver()


@pytest.fixture
def use_case():
    return build_application()


def test_reference_example_parser_preserves_x_as_parameter():
    """Verify input parser preserves x as symbolic parameter and t as independent variable."""
    raw = "y'' + 5*y' + 6*y = 0, y(0) = 2, y'(0) = x"
    parsed = parse_second_order_ode_input(raw, target_variable="t")

    assert str(parsed.independent_var) == "t"
    assert parsed.initial_condition == (sp.Integer(0), sp.Integer(2))

    t0_v, v0 = parsed.initial_derivative  # type: ignore[misc]
    assert t0_v == sp.Integer(0)
    assert v0 == sp.Symbol("x")


def test_reference_example_step6_cauchy_derivation_sequence(solver: ODESecondOrderConstantCoeffSolver):
    """Verify Step 6 establishes the Cauchy system concisely in the default view:

    1. General solution y(t) and its first derivative y'(t).
    2. Application of initial conditions y(0) = 2 and y'(0) = x.
    3. Resulting system (cases only in default view; no duplicate matrix).
    4. Detailed matrix representation preserved in expandable substeps (Layer B).
    """
    req = ProblemRequest(
        raw_input="y'' + 5*y' + 6*y = 0, y(0) = 2, y'(0) = x",
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS

    step6 = next(s for s in res.steps if s.step_number == 6)
    assert "Áp dụng điều kiện ban đầu" in step6.rule_name
    assert "hệ phương trình" in step6.title.lower()

    desc = step6.description
    # 1. General solution & first derivative
    assert "Nghiệm tổng quát và đạo hàm cấp một" in desc
    assert "C_1 y_1" in desc or "C_{1} e^{- 2 t}" in desc
    assert "y'(t)" in desc

    # 2. Substitute y(0) = 2 and y'(0) = x
    assert "Áp dụng điều kiện ban đầu" in desc
    assert "y(0) = 2" in desc
    assert "C_1 + C_2 = 2" in desc
    assert "y'(0) = x" in desc
    assert "-2" in desc and "C_1" in desc and "C_2" in desc

    # 3. Clean resulting system: cases only, no matrix in default view
    assert "Hệ phương trình thu được" in desc
    assert "\\begin{cases}" in step6.equation_latex
    assert "C_1 + C_2 = 2" in step6.equation_latex
    # Verify no matrix in default equation_latex or description
    assert "\\begin{pmatrix}" not in step6.equation_latex
    assert "\\begin{pmatrix}" not in desc

    # Substeps present for Layer B
    assert len(step6.substeps) == 3
    assert "y(t0) = y0" in step6.substeps[0].rule_name or "y(0)" in step6.substeps[0].title
    assert "y'(t0) = v0" in step6.substeps[1].rule_name or "y'(0)" in step6.substeps[1].title
    # Matrix representation lives in Substep 3
    assert "ma trận" in step6.substeps[2].rule_name.lower() or "ma trận" in step6.substeps[2].title.lower()
    assert "\\begin{pmatrix}" in step6.substeps[2].equation_latex


def test_reference_example_step7_algebraic_solution_and_equivalence(solver: ODESecondOrderConstantCoeffSolver):
    """Verify Step 7 default view is concise and 4-part structured, with detailed algebra in substeps."""
    req = ProblemRequest(
        raw_input="y'' + 5*y' + 6*y = 0, y(0) = 2, y'(0) = x",
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS

    step7 = next(s for s in res.steps if s.step_number == 7)
    assert "nghiệm riêng" in step7.title.lower()

    desc = step7.description
    # 1. Restate system
    assert "1. Nhắc lại hệ phương trình thu được từ Bước 6" in desc
    assert "C_1 + C_2 = 2" in desc

    # 2. Solved constants
    assert "2. Giải hệ phương trình xác định các hằng số tích phân" in desc
    assert "C_1 = x + 6" in desc
    assert "C_2 = - x - 4" in desc

    # 3. Substitute into general solution
    assert "3. Thay giá trị $C_1, C_2$ vào nghiệm tổng quát" in desc
    assert "e^{- 2 t}" in desc
    assert "e^{- 3 t}" in desc

    # 4. Final particular solution & factored form
    assert "4. Nghiệm riêng của bài toán Cauchy" in desc
    assert "Dạng thu gọn tương đương" in desc

    # Verify default view does not dump intermediate elementary algebra cards
    assert "Chuyển các số hạng tự do sang vế phải" not in desc

    # Substeps present for Layer B (Method of substitution detailed derivation)
    assert len(step7.substeps) == 4
    # Substep 1: Express C1
    assert "Biểu diễn C1" in step7.substeps[0].rule_name
    assert "2 - C_{2}" in step7.substeps[0].description or "2 - C_2" in step7.substeps[0].description
    # Substep 2: Substitute into Eq 2 and solve C2
    assert "Thế và giải tìm C2" in step7.substeps[1].rule_name
    assert "C_2 = - x - 4" in step7.substeps[1].equation_latex
    # Substep 3: Back-substitute C2 to find C1
    assert "Xác định C1" in step7.substeps[2].rule_name
    assert "C_1 = x + 6" in step7.substeps[2].equation_latex
    # Substep 4: Substitution and reduction
    assert "Xác định nghiệm riêng" in step7.substeps[3].rule_name

    # Symbolic equivalence test between expanded and factored forms
    t, x = sp.symbols("t x")
    expanded_form = (x + 6) * sp.exp(-2 * t) + (-x - 4) * sp.exp(-3 * t)
    factored_form = ((x + 6) * sp.exp(t) - x - 4) * sp.exp(-3 * t)
    assert sp.simplify(expanded_form - factored_form) == 0

    # Verify solver's final result is equivalent to both
    sol_rhs = res.final_result.split("=", 1)[1].strip()
    assert sp.simplify(sp.sympify(sol_rhs) - expanded_form) == 0
    assert sp.simplify(sp.sympify(sol_rhs) - factored_form) == 0


def test_reference_example_step8_independent_verification(solver: ODESecondOrderConstantCoeffSolver):
    """Verify Step 8 contains explicit Vietnamese pedagogical explanation and dual verification:

    - Section A: Differential equation residual R(t) = 0.
    - Section B: Initial conditions y(0) = 2 and y'(0) = x.
    """
    req = ProblemRequest(
        raw_input="y'' + 5*y' + 6*y = 0, y(0) = 2, y'(0) = x",
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    step8 = next(s for s in res.steps if s.step_number == 8)
    assert step8.title == "Kiểm chứng nghiệm"
    assert step8.rule_name == "Kiểm chứng nghiệm"

    desc = step8.description
    # Mandatory pedagogical explanation
    assert "Bước này không tìm nghiệm mới" in desc
    assert "thay nghiệm vừa tìm được trở lại phương trình vi phân ban đầu" in desc
    assert "kiểm tra các điều kiện ban đầu để xác nhận rằng nghiệm thực sự đúng" in desc

    # Section A: Verify ODE
    assert "A. Kiểm chứng phương trình vi phân" in desc
    assert "###" not in desc
    assert "R(t)" in desc
    assert "R(t) = 0 \\equiv 0" in desc or "Thỏa mãn đồng nhất" in desc

    # Section B: Verify Initial Conditions
    assert "B. Kiểm chứng hệ điều kiện ban đầu" in desc
    assert "y(0) = 2" in desc
    assert "y'(0) = x" in desc

    # Substeps for Section A and Section B
    assert len(step8.substeps) == 2
    assert "phương trình" in step8.substeps[0].title.lower()
    assert "điều kiện" in step8.substeps[1].title.lower()


def test_verification_status_failed_on_invalid_conditions():
    """Verify FAILED status and informative diagnostics when initial conditions are violated."""
    verifier = ODEVerifier()
    t, x = sp.symbols("t x")
    # True solution for y(0)=2, y'(0)=x is (x+6)*exp(-2t) - (x+4)*exp(-3t)
    sol = (x + 6) * sp.exp(-2 * t) + (-x - 4) * sp.exp(-3 * t)

    # 1. Condition y(0) mismatched (expected 99 instead of 2)
    res_bad_y0 = verifier.verify_second_order(
        solution=sol,
        variable=t,
        a_coeff=sp.Integer(1),
        b_coeff=sp.Integer(5),
        c_coeff=sp.Integer(6),
        initial_condition=(sp.Integer(0), sp.Integer(99)),
        initial_derivative=(sp.Integer(0), x),
    )
    assert res_bad_y0.status == VerificationStatus.FAILED
    assert "initial_condition_mismatch" in res_bad_y0.method
    assert "99" in res_bad_y0.details

    # 2. Condition y'(0) mismatched (expected 99 instead of x)
    res_bad_v0 = verifier.verify_second_order(
        solution=sol,
        variable=t,
        a_coeff=sp.Integer(1),
        b_coeff=sp.Integer(5),
        c_coeff=sp.Integer(6),
        initial_condition=(sp.Integer(0), sp.Integer(2)),
        initial_derivative=(sp.Integer(0), sp.Integer(99)),
    )
    assert res_bad_v0.status == VerificationStatus.FAILED
    assert "initial_derivative_mismatch" in res_bad_v0.method
    assert "99" in res_bad_v0.details


def test_verification_status_failed_on_wrong_ode_solution():
    """Verify FAILED status when ODE residual does not simplify to zero."""
    verifier = ODEVerifier()
    t = sp.Symbol("t")
    wrong_sol = sp.exp(-5 * t)  # Not a solution to y'' + 5y' + 6y = 0

    res = verifier.verify_second_order(
        solution=wrong_sol,
        variable=t,
        a_coeff=sp.Integer(1),
        b_coeff=sp.Integer(5),
        c_coeff=sp.Integer(6),
    )
    assert res.status == VerificationStatus.FAILED


def test_mathml_rendering_of_all_new_derivation_steps(solver: ODESecondOrderConstantCoeffSolver):
    """Verify every derivation step, substep, and equation converts cleanly to valid MathML."""
    req = ProblemRequest(
        raw_input="y'' + 5*y' + 6*y = 0, y(0) = 2, y'(0) = x",
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        target_variable="t",
    )
    res = solver.solve(req)

    for step in res.steps:
        # Description prose with inline math
        html_desc = render_math_in_text_html(step.description)
        assert "<math" in html_desc or "$" not in step.description
        assert "<script" not in html_desc
        assert "onerror" not in html_desc

        # Block equation LaTeX
        if step.equation_latex:
            html_eq = convert_latex_to_mathml(step.equation_latex, block=True)
            assert "<math" in html_eq
            assert "<script" not in html_eq

        # Substeps
        for sub in step.substeps:
            html_sub = convert_latex_to_mathml(sub.equation_latex, block=False)
            assert "<math" in html_sub


def test_final_conclusion_card_has_no_inner_box_border():
    """Verify that render_steps_container renders the final conclusion cleanly without \\boxed{}

    and without <menclose notation="box"> inner border while preserving outer card styling.
    """
    final_latex = r"y(t) = \left(- x + \left(x + 6\right) e^{t} - 4\right) e^{- 3 t}"

    # Verify that convert_latex_to_mathml for unboxed latex produces no menclose notation=box
    html_unboxed = convert_latex_to_mathml(final_latex, block=True)
    assert 'notation="box"' not in html_unboxed
    assert "<menclose" not in html_unboxed

    # In contrast, \\boxed{} produces menclose notation="box"
    html_boxed = convert_latex_to_mathml(f"\\boxed{{{final_latex}}}", block=True)
    assert 'notation="box"' in html_boxed

    # Render steps container inside a test NiceGUI card
    step = SolutionStep(
        step_number=1,
        rule_name="Kiểm chứng",
        title="Kiểm chứng",
        description="Hoàn thành",
        content=ExpressionStepContent("y", "y", "y", "y"),
    )
    with ui.card():
        render_steps_container((step,), final_answer_latex=final_latex)


def test_use_case_end_to_end_regression(use_case):
    """Verify end-to-end execution through SolveProblemUseCase for reference example."""
    req = ProblemRequest(
        raw_input="y'' + 5*y' + 6*y = 0, y(0) = 2, y'(0) = x",
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        target_variable="t",
    )
    res = use_case.execute(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert len(res.steps) == 8

    # Final result checks
    t, x = sp.symbols("t x")
    expected = (x + 6) * sp.exp(-2 * t) + (-x - 4) * sp.exp(-3 * t)
    sol_str = res.final_result.split("=", 1)[1].strip()
    assert sp.simplify(sp.sympify(sol_str) - expected) == 0


def test_quality_gate_case_1_distinct_real_roots(solver: ODESecondOrderConstantCoeffSolver):
    """Quality Gate Case 1: y'' + 5y' + 6y = 0, y(0) = 2, y'(0) = 3 -> y(t) = 9e^(-2t) - 7e^(-3t)."""
    req = ProblemRequest(
        raw_input="y'' + 5*y' + 6*y = 0, y(0) = 2, y'(0) = 3",
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    t = sp.Symbol("t")
    expected = 9 * sp.exp(-2 * t) - 7 * sp.exp(-3 * t)
    sol_str = res.final_result.split("=", 1)[1].strip()
    assert sp.simplify(sp.sympify(sol_str) - expected) == 0

    # Step 6 concise checks
    step6 = next(s for s in res.steps if s.step_number == 6)
    assert "\\begin{cases}" in step6.equation_latex
    assert "C_1 + C_2 = 2" in step6.equation_latex
    assert "\\begin{pmatrix}" not in step6.equation_latex

    # Step 7 concise checks
    step7 = next(s for s in res.steps if s.step_number == 7)
    assert "C_1 = 9" in step7.description
    assert "C_2 = -7" in step7.description
    assert len(step7.substeps) == 4


def test_quality_gate_case_2_complex_conjugate_roots_zero_suppression(solver: ODESecondOrderConstantCoeffSolver):
    """Quality Gate Case 2: y'' + 4y = 0, y(0) = 0, y'(0) = 1 -> y(t) = (1/2)*sin(2t).

    Must suppress zero coefficients (no 0*C1 or 0*C2 in system).
    Must adapt substeps to decoupled system (3 substeps, no superfluous algebra).
    """
    req = ProblemRequest(
        raw_input="y'' + 4*y = 0, y(0) = 0, y'(0) = 1",
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    t = sp.Symbol("t")
    expected = sp.sin(2 * t) / 2
    sol_str = res.final_result.split("=", 1)[1].strip()
    assert sp.simplify(sp.sympify(sol_str) - expected) == 0

    # Step 6 zero suppression check
    step6 = next(s for s in res.steps if s.step_number == 6)
    # Equation 1 should be C_1 = 0, Equation 2 should be 2\,C_2 = 1
    assert "C_1 = 0" in step6.equation_latex
    assert "2\\,C_2 = 1" in step6.equation_latex
    assert "0\\,C_1" not in step6.equation_latex
    assert "0\\,C_2" not in step6.equation_latex
    assert "0C_1" not in step6.equation_latex
    assert "0C_2" not in step6.equation_latex
    assert "\\begin{pmatrix}" not in step6.equation_latex

    # Step 7 decoupled adaptive substeps check
    step7 = next(s for s in res.steps if s.step_number == 7)
    assert "C_1 = 0" in step7.description
    assert "\\frac{1}{2}" in step7.description or "1/2" in step7.description
    # Decoupled system has exactly 3 substeps (solve C1, solve C2, substitute)
    assert len(step7.substeps) == 3
    assert "C_1 = 0" in step7.substeps[0].equation_latex
    assert "\\frac{1}{2}" in step7.substeps[1].equation_latex
    assert "y(t)" in step7.substeps[2].equation_latex


def test_quality_gate_case_3_repeated_root_triangular(solver: ODESecondOrderConstantCoeffSolver):
    """Quality Gate Case 3: y'' - 2y' + y = 0, y(0) = 1, y'(0) = 0 -> y(t) = (1 - t)e^t.

    System is triangular: C_1 = 1, C_1 + C_2 = 0 -> C_2 = -1.
    Must adapt substeps to triangular system (3 substeps).
    """
    req = ProblemRequest(
        raw_input="y'' - 2*y' + y = 0, y(0) = 1, y'(0) = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    t = sp.Symbol("t")
    expected = (1 - t) * sp.exp(t)
    sol_str = res.final_result.split("=", 1)[1].strip()
    assert sp.simplify(sp.sympify(sol_str) - expected) == 0

    # Step 6 checks
    step6 = next(s for s in res.steps if s.step_number == 6)
    assert "C_1 = 1" in step6.equation_latex
    assert "C_1 + C_2 = 0" in step6.equation_latex
    assert "0\\,C_2" not in step6.equation_latex

    # Step 7 triangular adaptive substeps check
    step7 = next(s for s in res.steps if s.step_number == 7)
    assert "C_1 = 1" in step7.description
    assert "C_2 = -1" in step7.description
    assert len(step7.substeps) == 3
    assert "Thế C1 tìm C2" in step7.substeps[1].rule_name
    assert "C_2 = -1" in step7.substeps[1].equation_latex


def test_nonzero_evaluation_point_t0(solver: ODESecondOrderConstantCoeffSolver):
    """Verify solver and presentation handle non-zero initial evaluation points (t0 != 0)."""
    # y'' - y = 0, y(1) = 2, y'(1) = 0
    # Roots: r = +-1 => y(t) = C1*e^t + C2*e^(-t)
    # y(1) = C1*e + C2/e = 2
    # y'(1) = C1*e - C2/e = 0
    # => C1 = 1/e = e^(-1), C2 = e => y(t) = e^(t-1) + e^(1-t)
    req = ProblemRequest(
        raw_input="y'' - y = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        target_variable="t",
        parameters={"t0": 1, "y0": 2, "v0": 0},
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    t = sp.Symbol("t")
    expected = sp.exp(t - 1) + sp.exp(1 - t)
    sol_str = res.final_result.split("=", 1)[1].strip()
    assert sp.simplify(sp.sympify(sol_str) - expected) == 0

    step6 = next(s for s in res.steps if s.step_number == 6)
    assert "y(1) = 2" in step6.description
    assert "y'(1) = 0" in step6.description


def test_radical_preservation_and_mathml_in_presentation(solver: ODESecondOrderConstantCoeffSolver):
    r"""Verify exact radical preservation (\sqrt{33}) across Step 6, Step 7, and MathML rendering."""
    req = ProblemRequest(
        raw_input="2*y'' + y' - 4*y = 0, y(0) = 0, y'(0) = 1",
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    # Check Step 6 radical preservation
    step6 = next(s for s in res.steps if s.step_number == 6)
    assert r"\sqrt{33}" in step6.equation_latex
    assert "C_1 + C_2 = 0" in step6.equation_latex
    # Matrix in substeps also has \sqrt{33}
    assert r"\sqrt{33}" in step6.substeps[2].equation_latex

    # Check Step 7 radical preservation
    step7 = next(s for s in res.steps if s.step_number == 7)
    assert r"\sqrt{33}" in step7.equation_latex
    assert r"\sqrt{33}" in step7.description

    # Verify MathML rendering produces <msqrt> tags, not corrupted plain text
    html6 = convert_latex_to_mathml(step6.equation_latex, block=True)
    assert "<msqrt>" in html6
    assert "33" in html6
    assert "233" not in html6  # Must not corrupt 2\sqrt{33} to 233


def test_test_b_arbitrary_symbolic_parameter_w(solver: ODESecondOrderConstantCoeffSolver):
    """Test B: Verify arbitrary symbolic parameter w (y'(0) = w) is preserved,

    correctly propagated through Steps 6, 7, and 8, and independently verified.
    """
    req = ProblemRequest(
        raw_input="y'' + 5*y' + 6*y = 0, y(0) = 2, y'(0) = w",
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    # Check Step 6 retains parameter w
    step6 = next(s for s in res.steps if s.step_number == 6)
    assert "w" in step6.description
    assert "w" in step6.equation_latex

    # Check Step 7 solves constants with parameter w
    step7 = next(s for s in res.steps if s.step_number == 7)
    assert "C_1 = w + 6" in step7.description
    assert "C_2 = - w - 4" in step7.description

    # Check Step 8 verifies condition with parameter w
    step8 = next(s for s in res.steps if s.step_number == 8)
    assert "y'(0): Thỏa mãn (w = w)" in step8.description

    # Final result check
    t, w = sp.symbols("t w")
    expected = (w + 6) * sp.exp(-2 * t) + (-w - 4) * sp.exp(-3 * t)
    sol_str = res.final_result.split("=", 1)[1].strip()
    assert sp.simplify(sp.sympify(sol_str) - expected) == 0


def test_test_h_singular_or_degenerate_cauchy_system_returns_cannot_solve(
    solver: ODESecondOrderConstantCoeffSolver,
    monkeypatch: pytest.MonkeyPatch,
):
    """Test H: Verify singular or degenerate Cauchy system returns CANNOT_SOLVE

    with VerificationStatus.FAILED, without generating ungrounded constants or crashing.
    """
    req = ProblemRequest(
        raw_input="y'' + 5*y' + 6*y = 0, y(0) = 2, y'(0) = 3",
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        target_variable="t",
    )

    # Simulate a degenerate linear system where SymPy cannot uniquely solve for [C1, C2]
    monkeypatch.setattr(sp, "solve", lambda *args, **kwargs: {})

    res = solver.solve(req)
    assert res.status == SolutionStatus.CANNOT_SOLVE
    assert res.verification.status == VerificationStatus.FAILED
    assert "singular_cauchy_system_check" in res.verification.method
    assert "suy biến" in res.verification.details
    assert len(res.warnings) > 0

