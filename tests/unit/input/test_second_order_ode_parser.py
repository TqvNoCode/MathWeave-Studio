"""Unit tests for second-order ODE input parser and normalization."""

import pytest
import sympy as sp

from math_app.domain.exceptions import InvalidInputError
from math_app.input.ode_parser import (
    normalize_ode_equation_string,
    parse_known_solution,
    parse_second_order_initial_conditions,
    parse_second_order_ode_input,
    parse_wronskian_input,
)


def test_normalize_second_order_notations():
    """Verify various forms of second derivatives normalize to y_double_prime."""
    assert "y_double_prime" in normalize_ode_equation_string("y'' + 5*y' + 6*y = 0")
    assert "y_double_prime" in normalize_ode_equation_string("y''(t) + 9*y(t) = 0")
    assert "y_double_prime" in normalize_ode_equation_string("d2y/dt2 + 4*y = 0")
    assert "y_double_prime" in normalize_ode_equation_string(r"\frac{d^2y}{dt^2} + 4y = 0")
    assert "y_double_prime" in normalize_ode_equation_string('y" + y = 0')


def test_parse_constant_coeff_second_order():
    """Verify standard homogeneous constant-coefficient second-order ODE parsing."""
    parsed = parse_second_order_ode_input("y'' + 5*y' + 6*y = 0", target_variable="t")
    assert parsed.is_constant_coeff is True
    assert parsed.is_homogeneous is True
    assert parsed.a_coeff == sp.Integer(1)
    assert parsed.b_coeff == sp.Integer(5)
    assert parsed.c_coeff == sp.Integer(6)
    assert parsed.p_expr == sp.Integer(5)
    assert parsed.q_expr == sp.Integer(6)
    assert parsed.initial_condition is None
    assert parsed.initial_derivative is None


def test_parse_dual_initial_conditions_in_string():
    """Verify parsing dual initial conditions y(t0) = y0, y'(t0) = v0."""
    raw = "y'' + 5*y' + 6*y = 0, y(0) = 2, y'(0) = 3"
    parsed = parse_second_order_ode_input(raw, target_variable="t")
    assert parsed.initial_condition == (sp.Integer(0), sp.Integer(2))
    assert parsed.initial_derivative == (sp.Integer(0), sp.Integer(3))


def test_parse_dual_initial_conditions_in_parameters():
    """Verify passing initial conditions via parameters."""
    parsed = parse_second_order_ode_input(
        "y'' + 9*y = 0",
        target_variable="t",
        parameters={"t0": 0, "y0": 1, "v0": -3},
    )
    assert parsed.initial_condition == (sp.Integer(0), sp.Integer(1))
    assert parsed.initial_derivative == (sp.Integer(0), sp.Integer(-3))


def test_mismatched_initial_condition_points_rejected():
    """Verify rejection when y(t0) and y'(t1) have different initial points."""
    with pytest.raises(InvalidInputError, match="không cùng điểm khởi đầu|y\\(0\\) và y'\\(1\\)"):
        parse_second_order_initial_conditions("y(0) = 2", "y'(1) = 3", indep_var="t")


def test_parse_variable_coeff_and_known_solution():
    """Verify reduction of order parsing with known solution y1."""
    raw = "2*t^2*y'' + 3*t*y' - y = 0, y1 = 1/t"
    parsed = parse_second_order_ode_input(raw, target_variable="t")
    t = sp.Symbol("t")
    assert parsed.is_constant_coeff is False
    assert parsed.is_homogeneous is True
    assert sp.simplify(parsed.a_coeff - 2 * t**2) == 0
    assert sp.simplify(parsed.b_coeff - 3 * t) == 0
    assert sp.simplify(parsed.c_coeff - (-1)) == 0
    assert sp.simplify(parsed.p_expr - sp.Rational(3, 2) / t) == 0
    assert parsed.known_solution is not None
    assert sp.simplify(parsed.known_solution - 1 / t) == 0


def test_known_solution_zero_rejected():
    """Verify identically zero known solution is rejected."""
    with pytest.raises(InvalidInputError, match="không được là hàm hằng 0"):
        parse_known_solution("0", indep_var="t")


def test_rejection_of_first_order_equation():
    """Verify an equation without y'' is rejected."""
    with pytest.raises(InvalidInputError, match="không chứa đạo hàm cấp 2"):
        parse_second_order_ode_input("y' + 5*y = 0", target_variable="t")


def test_rejection_of_zero_a_coeff():
    """Verify 0*y'' is rejected."""
    with pytest.raises(InvalidInputError, match="không chứa đạo hàm cấp 2|bằng 0; không phải phương trình cấp hai"):
        parse_second_order_ode_input("0*y'' + 5*y' + 6*y = 0", target_variable="t")


def test_rejection_of_nonlinear_ode():
    """Verify nonlinear second-order equations are rejected."""
    with pytest.raises(InvalidInputError, match="phi tuyến"):
        parse_second_order_ode_input("(y'')^2 + 5*y = 0", target_variable="t")

    with pytest.raises(InvalidInputError, match="phi tuyến"):
        parse_second_order_ode_input("y'' + (y')^2 + y = 0", target_variable="t")

    with pytest.raises(InvalidInputError, match="phi tuyến"):
        parse_second_order_ode_input("y'' + y^2 = 0", target_variable="t")


def test_parse_wronskian_input():
    """Verify Wronskian input parser accepts two functions."""
    y1, y2, var = parse_wronskian_input("cos(t), sin(t)", target_variable="t")
    t = sp.Symbol("t")
    assert var == t
    assert y1 == sp.cos(t)
    assert y2 == sp.sin(t)

    # Named format
    y1_b, y2_b, _ = parse_wronskian_input("y1 = exp(t), y2 = t*exp(t)", target_variable="t")
    assert y1_b == sp.exp(t)
    assert y2_b == t * sp.exp(t)
