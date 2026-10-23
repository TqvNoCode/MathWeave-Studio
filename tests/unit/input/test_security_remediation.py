"""Security regression tests for mathematical input parsing and matrix processing.

Guarantees that all mathematical input paths strictly reject arbitrary code execution,
attribute access, comprehension constructs, lambdas, excessive nesting, and malformed structures.
"""

from pathlib import Path
import pytest
import sympy as sp

from math_app.application.dtos import ProblemRequest
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType
from math_app.input.parser import (
    parse_mathematical_input,
    parse_matrix_input,
    parse_safe_expression,
)
from math_app.solvers.calculus.geometry.arc_length_solver import ArcLengthSolver
from math_app.solvers.calculus.geometry.surface_area_solver import SurfaceAreaSolver
from math_app.solvers.calculus.geometry.surface_of_revolution_solver import SurfaceOfRevolutionSolver
from math_app.solvers.calculus.integration.solver import IntegralSolver
from math_app.solvers.calculus.limit.solver import LimitSolver
from math_app.solvers.calculus.vector_calculus.divergence_theorem_solver import DivergenceTheoremSolver
from math_app.solvers.calculus.vector_calculus.greens_theorem_solver import GreensTheoremSolver
from math_app.solvers.calculus.vector_calculus.stokes_theorem_solver import StokesTheoremSolver
from math_app.solvers.linear_algebra.solver import MatrixSolver


def test_poc_matrix_import_payload_rejected_without_side_effects(tmp_path: Path):
    """Confirm proof-of-concept payload using __import__ is rejected and cannot execute."""
    canary_file = tmp_path / "canary.txt"
    # Malicious payload that would create canary file if evaluated
    payload = f"[[__import__('pathlib').Path('{canary_file.as_posix()}').write_text('PWNED'), 1], [0, 1]]"

    with pytest.raises(InvalidInputError):
        parse_matrix_input(payload)

    # Canary file must NOT exist
    assert not canary_file.exists()


def test_poc_matrix_getpid_rejected():
    """Verify the exact audit PoC __import__('os').getpid() is strictly rejected."""
    payload = "[[__import__('os').getpid(), 1], [0, 1]]"
    with pytest.raises(InvalidInputError):
        parse_matrix_input(payload)


def test_attribute_access_rejected_in_expressions_and_matrices():
    """Attribute access like x.__class__ or (1).__class__ must be rejected."""
    disallowed = [
        "x.__class__",
        "x.__doc__",
        "x.__bases__",
        "(1).__class__.__mro__",
        "x.__init__",
    ]
    for expr_str in disallowed:
        with pytest.raises(InvalidInputError):
            parse_safe_expression(expr_str)
        with pytest.raises(InvalidInputError):
            parse_mathematical_input(expr_str, "x")
        with pytest.raises(InvalidInputError):
            parse_matrix_input(f"[[{expr_str}, 1], [0, 1]]")


def test_arbitrary_function_calls_rejected():
    """Unapproved functions and builtins must be rejected before symbolic evaluation."""
    unapproved = [
        "eval('2 + 2')",
        "exec('import os')",
        "open('/etc/passwd')",
        "system('echo hacked')",
        "getattr(x, 'name')",
        "breakpoint()",
        "compile('x', '', 'eval')",
    ]
    for expr_str in unapproved:
        with pytest.raises(InvalidInputError):
            parse_safe_expression(expr_str)
        with pytest.raises(InvalidInputError):
            parse_matrix_input(f"[[{expr_str}, 0], [0, 1]]")


def test_lambdas_and_comprehensions_rejected():
    """Python lambda expressions and comprehensions must be rejected."""
    constructs = [
        "lambda x: x + 1",
        "[x for x in range(10)]",
        "{x for x in [1, 2, 3]}",
        "{x: x**2 for x in [1, 2]}",
        "(x for x in (1, 2))",
    ]
    for c in constructs:
        with pytest.raises(InvalidInputError):
            parse_safe_expression(c)
        with pytest.raises(InvalidInputError):
            parse_matrix_input(f"[[{c}, 1], [2, 3]]")


def test_malformed_and_excessive_matrix_nesting_rejected():
    """Matrix structures with 3D nesting, ragged rows, or empty components must be rejected."""
    # 3-level nesting
    with pytest.raises(InvalidInputError, match="lồng|nesting"):
        parse_matrix_input("[[[1, 2]], [3, 4]]")

    # Mixed nested and non-nested
    with pytest.raises(InvalidInputError):
        parse_matrix_input("[[1, 2], 3]")

    # Ragged dimensions
    with pytest.raises(InvalidInputError, match="không đồng nhất|Mismatched"):
        parse_matrix_input("[[1, 2, 3], [4, 5]]")

    # Empty matrix
    with pytest.raises(InvalidInputError, match="không được để trống|cannot be empty"):
        parse_matrix_input("   ")

    # Empty rows
    with pytest.raises(InvalidInputError, match="không được rỗng|cannot be empty"):
        parse_matrix_input("[[]]")


def test_resource_bounds_length_depth_and_exponent():
    """Validate expression length, AST nesting depth, and exponent bounds."""
    # Excessive length
    long_expr = "x + " * 75 + "1"
    with pytest.raises(InvalidInputError, match="độ dài|length"):
        parse_safe_expression(long_expr)

    # Excessive nesting depth
    deep_expr = "sin(" * 15 + "x" + ")" * 15
    with pytest.raises(InvalidInputError, match="phức tạp|depth"):
        parse_safe_expression(deep_expr)

    # Excessive exponent
    huge_exp = "x**999"
    with pytest.raises(InvalidInputError, match="Số mũ|Exponent"):
        parse_safe_expression(huge_exp)


def test_solvers_reject_unsafe_parameter_inputs():
    """Verify solvers reject malicious payloads passed via request parameters or bounds."""
    # Limit solver point
    l_solver = LimitSolver()
    with pytest.raises(InvalidInputError):
        l_solver.solve(ProblemRequest("x^2", ProblemType.LIMIT, parameters={"limit_point": "__import__('os').getpid()"}))

    # Integral solver bounds
    i_solver = IntegralSolver()
    with pytest.raises(InvalidInputError):
        i_solver.solve(ProblemRequest("x", ProblemType.DEFINITE_INTEGRAL, parameters={"lower_bound": "0", "upper_bound": "__import__('os').getpid()"}))

    # Arc length bounds
    arc_solver = ArcLengthSolver()
    with pytest.raises(InvalidInputError):
        arc_solver.solve(ProblemRequest("x^2", ProblemType.ARC_LENGTH, parameters={"lower_bound": "0", "upper_bound": "__import__('os').getpid()"}))

    # Surface area surface_expr
    surf_solver = SurfaceAreaSolver()
    with pytest.raises(InvalidInputError):
        surf_solver.solve(ProblemRequest("1", ProblemType.SURFACE_AREA, parameters={"surface_expr": "__import__('os').getpid()"}))

    # Green's theorem components
    g_solver = GreensTheoremSolver()
    with pytest.raises(InvalidInputError):
        g_solver.solve(ProblemRequest("__import__('os').getpid(), x", ProblemType.GREENS_THEOREM))

    # Divergence theorem components
    div_solver = DivergenceTheoremSolver()
    with pytest.raises(InvalidInputError):
        div_solver.solve(ProblemRequest("x, y, __import__('os').getpid()", ProblemType.DIVERGENCE_THEOREM))

    # Stokes theorem components
    stokes_solver = StokesTheoremSolver()
    with pytest.raises(InvalidInputError):
        stokes_solver.solve(ProblemRequest("x, y, __import__('os').getpid()", ProblemType.STOKES_THEOREM))

    # Matrix solver
    m_solver = MatrixSolver()
    with pytest.raises(InvalidInputError):
        m_solver.solve(ProblemRequest("[[__import__('os').getpid(), 1], [0, 1]]", ProblemType.MATRIX_TRANSPOSE))


def test_legitimate_mathematical_expressions_and_matrices_work():
    """Confirm valid expressions, trigonometric functions, and matrices continue to work smoothly."""
    # Polynomial and trigonometric
    expr1, var1 = parse_mathematical_input("3*x^3 + 2*x^2 - 5*x + 1", "x")
    assert isinstance(expr1, sp.Expr)
    assert var1.name == "x"

    expr2, var2 = parse_mathematical_input("sin(x)*cos(x) + exp(x)", "x")
    assert isinstance(expr2, sp.Expr)

    # Symbolic matrix
    mat_sym = parse_matrix_input("[[x, 1], [0, x]]", allowed_variables={"x"})
    assert mat_sym.shape == (2, 2)
    assert mat_sym[0, 0] == sp.Symbol("x")
    assert mat_sym.det() == sp.Symbol("x") ** 2

    # Semicolon matrix
    mat_semi = parse_matrix_input("1, 2; 3, 4")
    assert mat_semi.shape == (2, 2)
    assert mat_semi.det() == -2

    # Vector line bracket
    vec = parse_matrix_input("[5, 11]")
    assert vec.shape == (1, 2)
