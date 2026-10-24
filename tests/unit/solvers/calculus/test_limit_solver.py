"""Unit tests for calculus limit solver and verifier."""


from math_app.application.dtos import ProblemRequest
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.solvers.calculus.limit.solver import LimitSolver


def test_limit_direct_substitution():
    solver = LimitSolver()
    req = ProblemRequest("x^2 + 2*x + 1", ProblemType.LIMIT, target_variable="x", parameters={"limit_point": "2"})
    resp = solver.solve(req)

    assert resp.status == SolutionStatus.SUCCESS
    assert resp.final_result == "9"
    assert resp.verification.status == VerificationStatus.VERIFIED


def test_limit_sinc():
    """lim_{x->0} sin(x)/x = 1."""
    solver = LimitSolver()
    req = ProblemRequest("sin(x)/x", ProblemType.LIMIT, target_variable="x", parameters={"limit_point": "0"})
    resp = solver.solve(req)

    assert resp.status == SolutionStatus.SUCCESS
    assert resp.final_result == "1"
    assert resp.verification.status == VerificationStatus.VERIFIED
    assert any("Indeterminate" in s.rule_name or "vô định" in s.rule_name for s in resp.steps)


def test_limit_at_infinity():
    """lim_{x->oo} 1/x = 0."""
    solver = LimitSolver()
    req = ProblemRequest("1/x", ProblemType.LIMIT, target_variable="x", parameters={"limit_point": "oo"})
    resp = solver.solve(req)

    assert resp.status == SolutionStatus.SUCCESS
    assert resp.final_result == "0"
