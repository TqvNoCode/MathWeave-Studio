"""Architectural boundary and clean architecture compliance tests."""

import ast
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parent.parent.parent / "src" / "math_app"


def get_imported_modules(py_file: Path) -> set[str]:
    """Parse a python file with AST and return set of top-level imported module names."""
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module)
    return imported


def test_domain_boundary_isolation():
    """Domain must not depend on application, solvers, presentation, nicegui, plotly, or sympy."""
    domain_dir = SRC_ROOT / "domain"
    assert domain_dir.exists(), "Domain directory must exist."

    forbidden_prefixes = (
        "math_app.application",
        "math_app.solvers",
        "math_app.presentation",
        "nicegui",
        "plotly",
        "sympy",
    )

    for py_file in domain_dir.rglob("*.py"):
        imports = get_imported_modules(py_file)
        for imp in imports:
            for forbidden in forbidden_prefixes:
                assert not imp.startswith(forbidden), (
                    f"Domain violation in {py_file.name}: "
                    f"Domain is forbidden from importing '{imp}'."
                )


def test_application_boundary_isolation():
    """Application must not depend on solvers, presentation, nicegui, or plotly."""
    app_dir = SRC_ROOT / "application"
    assert app_dir.exists(), "Application directory must exist."

    forbidden_prefixes = (
        "math_app.solvers",
        "math_app.presentation",
        "nicegui",
        "plotly",
    )

    for py_file in app_dir.rglob("*.py"):
        imports = get_imported_modules(py_file)
        for imp in imports:
            for forbidden in forbidden_prefixes:
                assert not imp.startswith(forbidden), (
                    f"Application violation in {py_file.name}: "
                    f"Application is forbidden from importing '{imp}'."
                )


def test_solvers_boundary_isolation():
    """Solvers must not depend on presentation, nicegui, or plotly."""
    solvers_dir = SRC_ROOT / "solvers"
    if not solvers_dir.exists():
        return

    forbidden_prefixes = (
        "math_app.presentation",
        "nicegui",
        "plotly",
    )

    for py_file in solvers_dir.rglob("*.py"):
        imports = get_imported_modules(py_file)
        for imp in imports:
            for forbidden in forbidden_prefixes:
                assert not imp.startswith(forbidden), (
                    f"Solver violation in {py_file.name}: "
                    f"Solvers are forbidden from importing '{imp}'."
                )


def test_verification_boundary_isolation():
    """Verification must not depend on presentation, nicegui, or plotly."""
    verif_dir = SRC_ROOT / "verification"
    if not verif_dir.exists():
        return

    forbidden_prefixes = (
        "math_app.presentation",
        "nicegui",
        "plotly",
    )

    for py_file in verif_dir.rglob("*.py"):
        imports = get_imported_modules(py_file)
        for imp in imports:
            for forbidden in forbidden_prefixes:
                assert not imp.startswith(forbidden), (
                    f"Verification violation in {py_file.name}: "
                    f"Verification is forbidden from importing '{imp}'."
                )


def test_presentation_boundary_isolation():
    """Presentation must not import solvers directly (must go through application use cases)."""
    pres_dir = SRC_ROOT / "presentation"
    if not pres_dir.exists():
        return

    forbidden_prefixes = (
        "math_app.solvers",
        "math_app.verification",
    )

    for py_file in pres_dir.rglob("*.py"):
        imports = get_imported_modules(py_file)
        for imp in imports:
            for forbidden in forbidden_prefixes:
                assert not imp.startswith(forbidden), (
                    f"Presentation violation in {py_file.name}: "
                    f"Presentation is forbidden from directly importing '{imp}'."
                )
