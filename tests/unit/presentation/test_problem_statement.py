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
