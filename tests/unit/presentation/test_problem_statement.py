"""Unit tests for problem statement and result title formatting."""

from math_app.domain.models import ProblemType
from math_app.presentation.components.problem_statement import (
    format_final_answer_latex,
    format_problem_statement_latex,
    get_result_card_title,
)


def test_result_card_titles():
    # Ordinary and higher order must both use generic title 'KẾT QUẢ ĐẠO HÀM'
    assert get_result_card_title(ProblemType.DERIVATIVE) == "KẾT QUẢ ĐẠO HÀM"
    assert get_result_card_title(ProblemType.HIGHER_ORDER_DERIVATIVE) == "KẾT QUẢ ĐẠO HÀM"

    assert get_result_card_title(ProblemType.PARTIAL_DERIVATIVE) == "KẾT QUẢ ĐẠO HÀM RIÊNG"
    assert get_result_card_title(ProblemType.INDEFINITE_INTEGRAL) == "KẾT QUẢ NGUYÊN HÀM"
    assert get_result_card_title(ProblemType.DEFINITE_INTEGRAL) == "KẾT QUẢ TÍCH PHÂN XÁC ĐỊNH"
    assert get_result_card_title(ProblemType.LIMIT) == "KẾT QUẢ GIỚI HẠN"
    assert get_result_card_title(ProblemType.MATRIX_RREF) == "KẾT QUẢ DẠNG BẬC THANG RÚT GỌN (RREF)"


def test_problem_statement_differentiation_no_raw_syntax():
    raw_input = "x^4 - 3*x^3 + 2*x"
    res = format_problem_statement_latex(raw_input, ProblemType.DERIVATIVE, "x", {"order": 1})

    # Must be f(x) = ... not containing **
    assert "f(x) =" in res
    assert "**" not in res
    assert "x^{4}" in res or "x^4" in res


def test_problem_statement_higher_order_derivative():
    raw_input = "x^4 - 3*x^3 + 2*x"
    res = format_problem_statement_latex(raw_input, ProblemType.DERIVATIVE, "x", {"order": 2})

    # Problem statement remains the original function f(x)
    assert res.startswith("f(x) =")
    assert "**" not in res

    ans = format_final_answer_latex("12 x^{2} - 18 x", ProblemType.DERIVATIVE, "x", {"order": 2})
    assert ans.startswith("f''(x) =")


def test_problem_statement_partial_derivative():
    raw_input = "x^2*y + y^3"
    res = format_problem_statement_latex(raw_input, ProblemType.PARTIAL_DERIVATIVE, "x")

    assert "f(" in res
    assert "\\frac{\\partial f}{\\partial x}" in res


def test_problem_statement_indefinite_integral():
    raw_input = "x^2"
    res = format_problem_statement_latex(raw_input, ProblemType.INDEFINITE_INTEGRAL, "x")

    assert "\\int" in res
    assert "dx" in res
    assert "f(x) =" not in res


def test_problem_statement_definite_integral():
    raw_input = "x^2"
    res = format_problem_statement_latex(
        raw_input,
        ProblemType.DEFINITE_INTEGRAL,
        "x",
        {"lower_bound": "0", "upper_bound": "1"},
    )

    assert "\\int_{0}^{1}" in res
    assert "dx" in res


def test_problem_statement_limit():
    raw_input = "sin(x)/x"
    res = format_problem_statement_latex(
        raw_input,
        ProblemType.LIMIT,
        "x",
        {"limit_point": "0", "direction": "+-"},
    )

    assert "\\lim_{x \\to 0}" in res


def test_problem_statement_differential_equations():
    assert get_result_card_title(ProblemType.ODE_FIRST_ORDER_LINEAR) == "KẾT QUẢ PHƯƠNG TRÌNH VI PHÂN TUYẾN TÍNH"
    assert get_result_card_title(ProblemType.ODE_SEPARABLE) == "KẾT QUẢ PHƯƠNG TRÌNH TÁCH BIẾN"
    assert get_result_card_title(ProblemType.ODE_EXACT) == "KẾT QUẢ PHƯƠNG TRÌNH VI PHÂN TOÀN PHẦN"
    assert get_result_card_title(ProblemType.ODE_INTEGRATING_FACTOR) == "KẾT QUẢ PHƯƠNG TRÌNH THỪA SỐ TÍCH PHÂN"
    assert get_result_card_title(ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF) == "KẾT QUẢ PHƯƠNG TRÌNH VI PHÂN CẤP 2"
    assert get_result_card_title(ProblemType.ODE_SECOND_ORDER_IVP) == "KẾT QUẢ BÀI TOÁN CAUCHY CẤP 2"
    assert get_result_card_title(ProblemType.ODE_REDUCTION_OF_ORDER) == "KẾT QUẢ HẠ BẬC PHƯƠNG TRÌNH CẤP 2"
    assert get_result_card_title(ProblemType.WRONSKIAN) == "KẾT QUẢ ĐỊNH THỨC WRONSKIAN"

    raw_input = "y' + (1/2)*y = t + 2, y(0) = 1"
    res = format_problem_statement_latex(raw_input, ProblemType.ODE_FIRST_ORDER_LINEAR, "t")
    assert "\\frac{dy}{dt}" in res
    assert "y(0) = 1" in res

    # Second-order IVP
    raw_so = "y'' + 5*y' + 6*y = 0, y(0) = 2, y'(0) = 3"
    res_so = format_problem_statement_latex(raw_so, ProblemType.ODE_SECOND_ORDER_IVP, "t")
    assert "\\frac{d^2y}{dt^2}" in res_so
    assert "\\frac{dy}{dt}" in res_so
    assert "y(0) = 2" in res_so
    assert "y'(0) = 3" in res_so

    # Reduction of order
    raw_red = "2*t^2*y'' + 3*t*y' - y = 0, y1 = 1/t"
    res_red = format_problem_statement_latex(raw_red, ProblemType.ODE_REDUCTION_OF_ORDER, "t")
    assert "y_1 = 1/t" in res_red

    # Wronskian
    raw_w = "cos(t), sin(t)"
    res_w = format_problem_statement_latex(raw_w, ProblemType.WRONSKIAN, "t")
    assert "W" in res_w
    assert "\\cos" in res_w
    assert "\\sin" in res_w
