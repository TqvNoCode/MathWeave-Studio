"""Unit tests for ODE derivative order detection and input validation."""

from __future__ import annotations

import pytest

from math_app.domain.exceptions import InvalidInputError
from math_app.input.ode_parser import (
    detect_ode_order,
    validate_ode_order,
    parse_ode_input,
    parse_second_order_ode_input,
)


def test_detect_ode_order_first_order_variations():
    """Verify detection of various supported first-order derivative notations."""
    cases = [
        "y' + 2*y = exp(-t)",
        "y'(t) + 2*y(t) = exp(-t)",
        "y'(x) + 2*y(x) = exp(-x)",
        "dy/dt + 2*y = 0",
        "dy/dx + 2*y = 0",
        r"\frac{dy}{dt} + 2y = 0",
        r"\frac{dy}{dx} + 2y = 0",
        "2*x*y*dx + (x^2 + 1)*dy = 0",
        "(3*x*y + y^2)*dx + (x^2 + x*y)*dy = 0",
        "diff(y, t) + 2*y = 0",
        "diff(y, x, 1) + 2*y = 0",
    ]
    for eq in cases:
        order = detect_ode_order(eq)
        assert order == 1, f"Expected order 1 for '{eq}', got {order}"


def test_detect_ode_order_second_order_variations():
    """Verify detection of various supported second-order derivative notations."""
    cases = [
        "y'' + 4*y = 4*t",
        "y''(t) + 4*y(t) = 4*t",
        "y''(x) + 4*y(x) = 4*x",
        "d2y/dt2 + 4*y = 4*t",
        "d^2y/dt^2 + 4*y = 0",
        "d2y/dx2 + 4*y = 0",
        "d^2y/dx^2 + 4*y = 0",
        r"\frac{d^2y}{dt^2} + 4y = 0",
        r"\frac{d^2y}{dx^2} + 4y = 0",
        'y" + 4*y = 0',
        'y"(t) + 4*y = 0',
        "diff(y, t, 2) + 4*y = 0",
        "diff(y, x, 2) + 4*y = 0",
    ]
    for eq in cases:
        order = detect_ode_order(eq)
        assert order == 2, f"Expected order 2 for '{eq}', got {order}"


def test_detect_ode_order_higher_order_variations():
    """Verify detection of unsupported higher-order (>= 3) derivative notations."""
    cases = [
        "y''' + y = 0",
        "y'''' - y = 0",
        'y"" + y = 0',
        "d3y/dt3 + y = 0",
        "d^3y/dt^3 + y = 0",
        "d4y/dx4 + y = 0",
        r"\frac{d^3y}{dt^3} + y = 0",
        r"\frac{d^4y}{dx^4} + y = 0",
        "diff(y, t, 3) + y = 0",
        "y^(3) + y = 0",
        "y^(4) + y = 0",
    ]
    for eq in cases:
        order = detect_ode_order(eq)
        assert order >= 3, f"Expected order >= 3 for '{eq}', got {order}"


def test_detect_ode_order_algebraic_expressions():
    """Verify ordinary algebraic expressions or equations have order 0."""
    cases = [
        "x^2 + 2*x + 1 = 0",
        "y + 4*t = 0",
        "y = 2*t + 1",
        "sin(t) + cos(t) = 0",
        "my_variable + 2*y = 0",
        "happy = 10",
        "exp(t) + y = 0",
    ]
    for eq in cases:
        order = detect_ode_order(eq)
        assert order == 0, f"Expected order 0 for algebraic '{eq}', got {order}"


def test_cauchy_ivp_derivatives_do_not_confuse_equation_order():
    """Verify derivative in initial condition y'(0)=2 does not override equation order."""
    # Second order equation with first order derivative in IC
    eq_so_ivp = "y'' + 4*y = 4*t, y(0)=1, y'(0)=2"
    assert detect_ode_order(eq_so_ivp) == 2

    # First order equation with value IC
    eq_fo_ivp = "y' + 2*y = exp(-t), y(0)=1"
    assert detect_ode_order(eq_fo_ivp) == 1


def test_validate_ode_order_accepts_matching_order():
    """Verify validate_ode_order accepts matching orders without raising."""
    # First order in first order
    validate_ode_order("y' + 2*y = exp(-t)", expected_order=1)
    validate_ode_order("2*x*y*dx + (x^2 + 1)*dy = 0", expected_order=1, indep_var="x")

    # Second order in second order
    validate_ode_order("y'' + 4*y = 4*t", expected_order=2)
    validate_ode_order("y'' + 4*y = 4*t, y(0)=1, y'(0)=2", expected_order=2)


def test_validate_ode_order_rejects_second_order_in_first_order():
    """Verify second-order ODE is rejected in first-order context with clear message."""
    with pytest.raises(InvalidInputError) as exc_info:
        validate_ode_order("y'' + 4*y = 4*t", expected_order=1)

    msg = str(exc_info.value)
    assert "cấp 2" in msg
    assert "cấp 1" in msg
    assert "Phương trình vi phân cấp 2" in msg
    assert "y_double_prime" not in msg


def test_validate_ode_order_rejects_first_order_in_second_order():
    """Verify first-order ODE is rejected in second-order context with clear message."""
    with pytest.raises(InvalidInputError) as exc_info:
        validate_ode_order("y' + 2*y = exp(-t)", expected_order=2)

    msg = str(exc_info.value)
    assert "cấp 1" in msg
    assert "cấp 2" in msg
    assert "y_prime" not in msg


def test_validate_ode_order_rejects_higher_order():
    """Verify higher-order (>= 3) ODE is rejected in both contexts."""
    for higher in ["y''' + 4*y = 0", "d^3y/dt^3 + y = 0"]:
        with pytest.raises(InvalidInputError) as exc_1:
            validate_ode_order(higher, expected_order=1)
        assert "cấp cao" in str(exc_1.value)

        with pytest.raises(InvalidInputError) as exc_2:
            validate_ode_order(higher, expected_order=2)
        assert "cấp cao" in str(exc_2.value)


def test_validate_ode_order_distinguishes_syntax_error():
    """Verify genuine syntax errors (unbalanced parenthesis, invalid tokens) are distinguished."""
    with pytest.raises(InvalidInputError) as exc_info:
        validate_ode_order("y'' + (4*y = 0", expected_order=1)

    msg = str(exc_info.value)
    assert "ngoặc" in msg.lower() or "syntax" in msg.lower()
    assert "không đúng cấp" not in msg


def test_parse_ode_input_clean_error_on_second_order():
    """Verify parse_ode_input raises clean message on second-order input without exposing internal identifiers."""
    with pytest.raises(InvalidInputError) as exc_info:
        parse_ode_input("y'' + 4*y = 4*t", target_variable="t")

    msg = str(exc_info.value)
    assert "cấp 2" in msg
    assert "y_double_prime" not in msg


def test_parse_second_order_ode_input_clean_error_on_first_order():
    """Verify parse_second_order_ode_input raises clean message on first-order input."""
    with pytest.raises(InvalidInputError) as exc_info:
        parse_second_order_ode_input("y' + 2*y = exp(-t)", target_variable="t")

    msg = str(exc_info.value)
    assert "cấp 1" in msg
    assert "cấp 2" in msg
    assert "y_prime" not in msg
