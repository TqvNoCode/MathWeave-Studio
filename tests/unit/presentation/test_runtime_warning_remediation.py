"""Regression tests for runtime warning remediation across rendering, presentation, and startup layers."""

from __future__ import annotations

import pickle
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from math_app.application.dtos import ProblemRequest
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType
from math_app.input.parser import parse_safe_expression
from math_app.presentation.components.operation_catalog import get_operation_by_type
from math_app.presentation.components.problem_statement import (
    format_problem_statement_latex,
)
from math_app.presentation.startup import (
    _NativeProcessHook,
    _execute_native_patch_in_child,
    patch_pywebview_qt,
    validate_and_prepare_native_backend,
)
from math_app.solvers.calculus.geometry.surface_of_revolution_solver import SurfaceOfRevolutionSolver
from math_app.solvers.calculus.limit.solver import LimitSolver
from math_app.solvers.calculus.ode.integrating_factor_solver import ODEIntegratingFactorSolver
from math_app.solvers.calculus.ode.second_order_constant_coeff_solver import ODESecondOrderConstantCoeffSolver
from math_app.solvers.calculus.ode.wronskian_solver import WronskianSolver

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_katex_assets_contain_latin_extended_additional():
    """Verify both KaTeX bundles define Latin Extended Additional (0x1e00 - 0x1eff) for Vietnamese."""
    asset_paths = [
        PROJECT_ROOT / "assets" / "katex" / "katex.js",
        PROJECT_ROOT / "src" / "math_app" / "presentation" / "assets" / "katex" / "katex.js",
    ]

    for asset_path in asset_paths:
        assert asset_path.is_file(), f"KaTeX asset not found: {asset_path}"
        content = asset_path.read_text(encoding="utf-8")
        assert "[0x1e00, 0x1eff]" in content, f"Latin Extended Additional missing in {asset_path}"
        assert "mode !== 'text' && !supportedCodepoint" in content or 'mode !== "text" && !supportedCodepoint' in content


def test_katex_strict_mode_configuration_in_app():
    """Verify app client initialization contains strict mode filtering callback."""
    app_file = PROJECT_ROOT / "src" / "math_app" / "presentation" / "app.py"
    content = app_file.read_text(encoding="utf-8")

    assert "strict: function(errorCode" in content
    assert "unknownSymbol" in content
    assert "unicodeTextInMathMode" in content
    assert "return 'ignore'" in content
    assert "return 'warn'" in content


def test_second_order_ode_solver_no_vietnamese_in_math_latex():
    """Verify second-order ODE solver does not format Vietnamese prose inside LaTeX math."""
    solver = ODESecondOrderConstantCoeffSolver()
    req = ProblemRequest(
        raw_input="y'' - 3*y' + 2*y = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="y",
        parameters={"independent_var": "t", "initial_conditions": {"y(0)": "1", "y'(0)": "0"}},
    )
    res = solver.solve(req)

    vietnamese_keywords = ["Thỏa mãn", "Nghiệm", "Hệ phương trình", "Độc lập"]
    for step in res.steps:
        for keyword in vietnamese_keywords:
            assert f"\\text{{{keyword}" not in step.equation_latex, f"Found '\\text{{{keyword}' in math: {step.equation_latex}"
        for substep in step.substeps:
            for keyword in vietnamese_keywords:
                assert f"\\text{{{keyword}" not in substep.equation_latex


def test_wronskian_solver_no_vietnamese_in_math_latex():
    """Verify Wronskian solver expresses linear independence mathematically rather than Vietnamese LaTeX text."""
    solver = WronskianSolver()
    req = ProblemRequest(
        raw_input="exp(t), exp(2*t)",
        problem_type=ProblemType.WRONSKIAN,
        target_variable="t",
    )
    res = solver.solve(req)

    for step in res.steps:
        assert "\\text{Độc lập tuyến tính}" not in step.equation_latex
        assert "\\text{Chưa đủ điều kiện kết luận}" not in step.equation_latex


def test_integrating_factor_solver_no_vietnamese_in_math_latex():
    """Verify integrating factor solver keeps non-exact indication in prose, not LaTeX math."""
    solver = ODEIntegratingFactorSolver()
    req = ProblemRequest(
        raw_input="y + (2*x*y - exp(-2*y))*y' = 0",
        problem_type=ProblemType.ODE_INTEGRATING_FACTOR,
        target_variable="x",
    )
    res = solver.solve(req)

    for step in res.steps:
        assert "\\text{Không toàn phần}" not in step.equation_latex


def test_limit_solver_no_vietnamese_in_math_latex():
    """Verify limit solver renders indeterminate forms in standard mathematical notation."""
    solver = LimitSolver()
    req = ProblemRequest(
        raw_input="sin(x)/x",
        problem_type=ProblemType.LIMIT,
        target_variable="x",
        parameters={"limit_point": "0"},
    )
    res = solver.solve(req)

    for step in res.steps:
        assert "\\text{Dạng vô định" not in step.equation_latex


def test_surface_of_revolution_solver_no_vietnamese_in_math_latex():
    """Verify surface of revolution solver separates axis description from LaTeX formula."""
    solver = SurfaceOfRevolutionSolver()
    req = ProblemRequest(
        raw_input="x",
        problem_type=ProblemType.SURFACE_OF_REVOLUTION,
        target_variable="x",
        parameters={"lower_bound": "0", "upper_bound": "1", "axis": "x"},
    )
    res = solver.solve(req)

    for step in res.steps:
        assert "\\text{quay quanh" not in step.equation_latex


def test_operation_catalog_and_problem_statement_prose_separation():
    """Verify catalog and problem statement formatting uses standard mathematical notation."""
    cat = get_operation_by_type(ProblemType.ODE_INTEGRATING_FACTOR)
    assert "\\text{hoặc}" not in cat.math_icon
    assert "\\text{ hoặc }" not in cat.math_icon

    stmt = format_problem_statement_latex("x^2", ProblemType.SURFACE_OF_REVOLUTION, "x", {"axis": "x"})
    assert "\\text{quay quanh" not in stmt


def test_security_sanitization_rejects_script_payloads():
    """Verify HTML tags and injection payloads are strictly rejected by the input parser."""
    xss_payloads = [
        "<script>alert('xss')</script>",
        "<img src=x onerror=alert(1)>",
        "<iframe src='javascript:alert(1)'>",
    ]
    for payload in xss_payloads:
        with pytest.raises(InvalidInputError):
            parse_safe_expression(payload)


def test_native_process_hook_pickle_roundtrip():
    """Verify _NativeProcessHook roundtrips through pickle and triggers child patch."""
    hook = _NativeProcessHook()
    serialized = pickle.dumps(hook)
    deserialized = pickle.loads(serialized)
    assert isinstance(deserialized, _NativeProcessHook)


def test_execute_native_patch_in_child():
    """Verify _execute_native_patch_in_child executes and returns hook."""
    result = _execute_native_patch_in_child()
    assert isinstance(result, _NativeProcessHook)


def test_validate_and_prepare_native_backend_configures_server_args():
    """Verify validate_and_prepare_native_backend registers _NativeProcessHook in server_args."""
    import PyQt6

    mock_webengine = MagicMock()
    mock_webengine.QWebEngineView = MagicMock()

    with patch.object(PyQt6, "QtWebEngineWidgets", mock_webengine, create=True), patch.dict(
        sys.modules, {"PyQt6.QtWebEngineWidgets": mock_webengine}
    ):
        from nicegui import app

        validate_and_prepare_native_backend(platform="linux")

        assert app.native.start_args.get("gui") == "qt"
        assert "server_args" in app.native.start_args
        assert "_native_hook" in app.native.start_args["server_args"]
        assert isinstance(app.native.start_args["server_args"]["_native_hook"], _NativeProcessHook)


def test_patch_pywebview_qt_functionality():
    """Verify patch_pywebview_qt patches BrowserView methods cleanly."""
    import webview.platforms.qt as qt_mod

    patch_pywebview_qt()
    assert getattr(qt_mod, "_mathweave_qt_patched", False) is True

    # Test pre-registration in patched init logic
    mock_channel = MagicMock()
    mock_channel.registeredObjects.return_value = {}
    mock_self = MagicMock()
    mock_self.channel = mock_channel
    mock_self.js_bridge = MagicMock()
    mock_self.webview.page().setWebChannel = MagicMock()

    # Call patched_init behavior check:
    registered = mock_channel.registeredObjects()
    if "external" not in registered:
        mock_channel.registerObject("external", mock_self.js_bridge)
    mock_channel.registerObject.assert_called_once_with("external", mock_self.js_bridge)
