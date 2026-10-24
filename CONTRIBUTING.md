# Contributing to MathWeave Studio

Thank you for your interest in contributing to MathWeave Studio! This guide describes how to set up the development environment, follow repository conventions, and submit contributions.

## Code of Conduct & Architectural Principles

MathWeave Studio adheres to Clean Architecture and strict mathematical correctness:

1. **Clean Architecture Boundaries**:
   - `domain`: Pure business models, immutability, enums, and exceptions.
   - `application`: Use cases, solver/verifier interfaces, and typed DTOs.
   - `input`: AST-based validation and parsing with strict whitelists and complexity bounds.
   - `solvers`: Pure mathematical solvers (calculus, algebra, linear algebra).
   - `verification`: Independent symbolic and numerical verifiers.
   - `rendering`: LaTeX and MathML rendering.
   - `presentation`: NiceGUI components and user interface.
   - Domain and solver code must **never** import or depend on NiceGUI or Plotly.

2. **Mathematical Correctness**:
   - Never invent a mathematical rule or step.
   - Distinguish the final result from the derivation steps.
   - Preserve domain restrictions and relevant assumptions.
   - Use exact arithmetic where feasible.
   - Verify results independently using invariants or alternative mathematical methods.

## Development Setup

The project uses `uv` for fast, reproducible dependency management and Python 3.14+.

```bash
# 1. Clone repository
git clone https://github.com/TqvNoCode/math_app.git
cd math_app

# 2. Sync virtual environment and dependencies
uv sync

# 3. Launch application in development mode
uv run python run.py
```

## Running Tests and Linting

Before submitting a Pull Request, ensure that all automated checks pass:

```bash
# Run full automated test suite
uv run pytest

# Run tests with coverage report
uv run pytest --cov=src --cov-report=term-missing

# Run code linter
uv run ruff check .
```

## Pull Request Guidelines

1. Keep PRs focused on a single feature, bug fix, or mathematical rule.
2. Include unit tests covering valid inputs, invalid inputs, and boundary cases.
3. Verify that regression suites and Clean Architecture boundaries remain intact.
