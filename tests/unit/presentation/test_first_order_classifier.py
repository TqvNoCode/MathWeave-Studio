"""Unit tests for First-Order ODE Guided Mathematical Classifier (UX3.6)."""

from __future__ import annotations

from math_app.domain.models import ProblemType
from math_app.presentation.components.workspace.ode.first_order_classifier import (
    classify_first_order_ode,
)


def test_classify_linear_homogeneous():
    """y' + 2*y = 0 is a Linear Homogeneous First-Order ODE."""
    res = classify_first_order_ode("y' + 2*y = 0", target_var="t")
    assert res.is_valid_ode is True
    assert res.detected_order == 1
    assert res.primary_category == "LINEAR_HOMOGENEOUS"
    assert "tuyến tính thuần nhất" in res.primary_title.lower()
    assert res.is_linear is True
    assert res.is_linear_homogeneous is True
    assert res.p_expr_latex == "2"
    assert res.g_expr_latex == "0"
    assert res.target_problem_type == ProblemType.ODE_FIRST_ORDER_LINEAR

    # Must explain that forcing term / RHS is zero
    assert any("triệt tiêu" in p or "bằng 0" in p for p in res.explanation_points)
    # Recommended method is Integrating Factor
    assert "thừa số tích phân" in res.recommended_method_title.lower()


def test_classify_linear_nonhomogeneous():
    """y' + 2*y = exp(-t) is a Linear Nonhomogeneous First-Order ODE."""
    res = classify_first_order_ode("y' + 2*y = exp(-t)", target_var="t")
    assert res.is_valid_ode is True
    assert res.detected_order == 1
    assert res.primary_category == "LINEAR_NONHOMOGENEOUS"
    assert "không thuần nhất" in res.primary_title.lower()
    assert res.is_linear is True
    assert res.is_linear_homogeneous is False
    assert res.p_expr_latex == "2"
    assert "e^{- t}" in res.g_expr_latex or "exp" in res.g_expr_latex
    assert res.reference_homogeneous_latex is not None
    assert "= 0" in res.reference_homogeneous_latex
    assert res.target_problem_type == ProblemType.ODE_FIRST_ORDER_LINEAR

    # Explanation must state that RHS is non-zero
    assert any("khác không" in p or "không triệt tiêu" in p for p in res.explanation_points)


def test_classify_linear_and_separable():
    """y' = t*y is BOTH Linear Homogeneous AND Separable."""
    res = classify_first_order_ode("y' = t*y", target_var="t")
    assert res.is_valid_ode is True
    assert res.detected_order == 1
    assert res.is_linear is True
    assert res.is_linear_homogeneous is True
    assert res.is_separable is True

    # Primary is Linear Homogeneous, additional includes Separable
    assert res.primary_category == "LINEAR_HOMOGENEOUS"
    cat_names = [c["category"] for c in res.additional_categories]
    assert "SEPARABLE" in cat_names

    # Alternative method includes Separation of Variables
    alt_ids = [m["method_id"] for m in res.alternative_methods]
    assert "SEPARATION_OF_VARIABLES" in alt_ids


def test_classify_nonlinear_separable():
    """y' = y*(1 - y) is a Nonlinear Separable ODE."""
    res = classify_first_order_ode("y' = y*(1 - y)", target_var="t")
    assert res.is_valid_ode is True
    assert res.detected_order == 1
    assert res.is_linear is False
    assert res.is_separable is True
    assert res.primary_category == "SEPARABLE"
    assert "tách biến" in res.primary_title.lower()
    assert res.target_problem_type == ProblemType.ODE_SEPARABLE
    assert "phân tách biến số" in res.recommended_method_title.lower()


def test_classify_classical_homogeneous_ratio():
    """y' = (y + x)/x is a Classical Homogeneous (Ratio form y/x) ODE."""
    res = classify_first_order_ode("y' = (y + x)/x", target_var="x")
    assert res.is_valid_ode is True
    assert res.detected_order == 1
    assert res.is_classical_homogeneous is True
    # Explicitly distinguish from linear homogeneous
    assert "dạng tỷ số" in res.primary_title.lower() or any(
        "thuần nhất" in c["title"].lower() for c in res.additional_categories
    )


def test_classify_exact_equation():
    """(2*x*y + 3)*dx + (x^2 + 4*y)*dy = 0 is an Exact Differential Equation."""
    res = classify_first_order_ode("(2*x*y + 3)*dx + (x^2 + 4*y)*dy = 0", target_var="x")
    assert res.is_valid_ode is True
    assert res.detected_order == 1
    assert res.is_exact_form is True
    assert res.is_exact is True
    assert res.primary_category == "EXACT"
    assert "toàn phần" in res.primary_title.lower()
    assert res.target_problem_type == ProblemType.ODE_EXACT
    assert res.dM_dy_latex == res.dN_dt_latex  # ∂M/∂y == ∂N/∂x
    assert "thế vị" in res.recommended_method_title.lower()


def test_classify_non_exact_differential_form():
    """2*y*dx + x*dy = 0 is NOT exact because dM/dy = 2 != dN/dx = 1."""
    res = classify_first_order_ode("2*y*dx + x*dy = 0", target_var="x")
    assert res.is_valid_ode is True
    assert res.is_exact_form is True
    assert res.is_exact is False  # Must NOT be falsely identified as exact
    assert res.dM_dy_latex != res.dN_dt_latex


def test_classify_second_order_detection_and_guidance():
    """y'' + 4*y = 4*t must be detected as order 2 with guidance to switch module."""
    res = classify_first_order_ode("y'' + 4*y = 4*t", target_var="t")
    assert res.is_valid_ode is False
    assert res.detected_order == 2
    assert "phương trình vi phân cấp 2" in res.error_message
    assert "cấp 2" in res.order_mismatch_recommendation


def test_classify_higher_order_detection():
    """y''' + y = 0 must be rejected with higher order message."""
    res = classify_first_order_ode("y''' + y = 0", target_var="t")
    assert res.is_valid_ode is False
    assert res.detected_order >= 3
    assert "cấp cao" in res.error_message or "cấp 3 trở lên" in res.error_message


def test_classify_algebraic_expression():
    """x^2 + 2*x + 1 = 0 has no derivatives (order 0) and suggests algebra."""
    res = classify_first_order_ode("x^2 + 2*x + 1 = 0", target_var="x")
    assert res.is_valid_ode is False
    assert res.detected_order == 0
    assert "Không phát hiện đạo hàm" in res.error_message
    assert "đại số" in res.order_mismatch_recommendation
