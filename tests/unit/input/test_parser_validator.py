"""Unit tests for input parsing, normalization, and syntax validation."""

import pytest
import sympy as sp

from math_app.domain.exceptions import InvalidInputError
from math_app.input.parser import normalize_expression_string, parse_mathematical_input
from math_app.input.validator import validate_expression_syntax


def test_normalization_converts_power_symbol():
    raw = "x^3 + 2*x^2 - 1"
    normalized = normalize_expression_string(raw)
    assert "^" not in normalized
    assert "**" in normalized
    assert normalized == "x**3 + 2*x**2 - 1"


def test_normalization_expands_implicit_multiplication():
    assert normalize_expression_string("2x") == "2*x"
    assert normalize_expression_string("3(x + 1)") == "3*(x + 1)"
    assert normalize_expression_string("(x - 1)(x + 1)") == "(x - 1)*(x + 1)"
    assert normalize_expression_string("x sin(x)") == "x*sin(x)"
    assert normalize_expression_string("ln(x)") == "log(x)"


def test_parse_mathematical_input_valid():
    expr, var = parse_mathematical_input("x^2 * sin(x)", target_variable="x")
    assert isinstance(expr, sp.Expr)
    assert var.name == "x"
    # Should equal x**2 * sin(x)
    assert expr == var ** 2 * sp.sin(var)


def test_validation_rejects_empty_input():
    with pytest.raises(InvalidInputError, match="cannot be empty"):
        validate_expression_syntax("   ")


def test_validation_rejects_mismatched_brackets():
    with pytest.raises(InvalidInputError, match="brackets"):
        validate_expression_syntax("(x + 1")

    with pytest.raises(InvalidInputError, match="brackets"):
        validate_expression_syntax("x + 1)")


def test_validation_rejects_disallowed_identifier():
    with pytest.raises(InvalidInputError, match="Unknown identifier"):
        validate_expression_syntax("foo(x) + 1")


def test_validation_rejects_attribute_access():
    with pytest.raises(InvalidInputError, match="Disallowed language construct"):
        validate_expression_syntax("x.__class__")


def test_validation_rejects_excessive_length():
    long_expr = "x + " * 70 + "x"
    with pytest.raises(InvalidInputError, match="maximum allowable length"):
        validate_expression_syntax(long_expr)


def test_validation_rejects_excessive_exponent():
    with pytest.raises(InvalidInputError, match="exceeds maximum allowed value"):
        validate_expression_syntax("x**999")


def test_normalize_variable_name_and_greek():
    from math_app.input.parser import normalize_variable_name
    assert normalize_variable_name("dx") == "x"
    assert normalize_variable_name("dy") == "y"
    assert normalize_variable_name("dtheta") == "theta"
    assert normalize_variable_name("dθ") == "theta"
    assert normalize_variable_name("θ") == "theta"
    assert normalize_variable_name("φ") == "phi"
    assert normalize_variable_name("t") == "t"


def test_parse_mathematical_input_greek_and_trig():
    expr, var = parse_mathematical_input("sin(θ) + cos(θ)", target_variable="θ")
    assert var.name == "theta"
    assert sp.simplify(expr - (sp.sin(var) + sp.cos(var))) == 0


def test_parse_matrix_input_formats():
    from math_app.input.parser import parse_matrix_input
    # Nested brackets
    m1 = parse_matrix_input("[[1, 2], [3, 4]]")
    assert m1.shape == (2, 2)
    assert m1[0, 0] == 1 and m1[1, 1] == 4

    # Semicolon format
    m2 = parse_matrix_input("1, 2; 3, 4")
    assert m2.shape == (2, 2)

    # Ragged matrix fails
    with pytest.raises(InvalidInputError):
        parse_matrix_input("[[1, 2], [3]]")

    # Empty matrix fails
    with pytest.raises(InvalidInputError):
        parse_matrix_input("   ")
