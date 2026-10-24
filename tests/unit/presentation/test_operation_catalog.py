"""Unit tests for operation catalog configuration and counts."""

from math_app.domain.models import ProblemType
from math_app.presentation.components.operation_catalog import (
    MAIN_OPERATIONS,
    OPERATIONS,
    get_operation_by_type,
)


def test_operation_counts_by_domain():
    # Total available operations
    calculus_all = [o for o in OPERATIONS if "Giải tích (Calculus)" == o.domain]
    assert len(calculus_all) == 11

    # Actual main-menu cards displayed (line, surface, and triple integrals are grouped under definite integral)
    calculus_menu_ops = [o for o in MAIN_OPERATIONS if "Giải tích (Calculus)" == o.domain]
    vector_ops = [o for o in MAIN_OPERATIONS if "Giải tích vectơ" in o.domain]
    linear_algebra_ops = [o for o in MAIN_OPERATIONS if "Đại số tuyến tính" in o.domain]

    # Exactly 8 main-menu calculus cards shown
    assert len(calculus_menu_ops) == 8
    # Exactly 1 definite integration card on the main menu
    integral_cards = [o for o in calculus_menu_ops if "Tích phân" in o.title]
    assert len(integral_cards) == 2  # Nguyên hàm + Tích phân xác định
    assert any(o.problem_type == ProblemType.DEFINITE_INTEGRAL for o in integral_cards)
    assert any(o.problem_type == ProblemType.INDEFINITE_INTEGRAL for o in integral_cards)

    # Subtypes are NOT duplicate cards on main menu
    assert not any(o.problem_type == ProblemType.LINE_INTEGRAL for o in calculus_menu_ops)
    assert not any(o.problem_type == ProblemType.SURFACE_INTEGRAL for o in calculus_menu_ops)
    assert not any(o.problem_type == ProblemType.TRIPLE_INTEGRAL for o in calculus_menu_ops)

    # Vector calculus theorems
    assert len(vector_ops) == 3

    # Linear algebra operations
    assert len(linear_algebra_ops) == 9


def test_single_merged_derivative_card():
    calc_titles = [o.title for o in OPERATIONS if "Giải tích" in o.domain]
    # Must have "Đạo hàm"
    assert "Đạo hàm" in calc_titles
    # Redundant cards must be gone
    assert "Đạo hàm bậc 1" not in calc_titles
    assert "Đạo hàm cấp cao (f^(n))" not in calc_titles

    deriv_op = get_operation_by_type(ProblemType.DERIVATIVE)
    assert deriv_op.title == "Đạo hàm"
    assert "order" in deriv_op.extra_fields


def test_integral_mathematical_notation_icons():
    indef_op = get_operation_by_type(ProblemType.INDEFINITE_INTEGRAL)
    assert indef_op.math_icon is not None
    assert "\\int" in indef_op.math_icon

    def_op = get_operation_by_type(ProblemType.DEFINITE_INTEGRAL)
    assert def_op.math_icon is not None
    assert "\\int_{a}^{b}" in def_op.math_icon or "\\int_a^b" in def_op.math_icon


def test_rref_card_configured():
    rref_op = get_operation_by_type(ProblemType.MATRIX_RREF)
    assert rref_op.title == "Dạng bậc thang rút gọn (RREF)"
    assert "Gauss" in rref_op.description or "bậc thang rút gọn" in rref_op.description


def test_solve_equation_card_configured():
    op = get_operation_by_type(ProblemType.SOLVE_EQUATION)
    assert op.title == "Giải phương trình"
    assert op.problem_type == ProblemType.SOLVE_EQUATION
    assert op.is_calculus is True
