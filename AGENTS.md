
# MathWeave Studio — Agent Guidelines

## Project goals
Build a cross-platform mathematics learning and research application using
Python 3.14+, NiceGUI, SymPy, NumPy, and Plotly.

## Architecture
- Follow Clean Architecture with clear dependency boundaries:
  - `domain`: Pure business rules, enums, exceptions, and immutability models (no framework dependencies).
  - `application`: Use cases (`SolveProblemUseCase`), ports (`Solver`, `SolverRegistry`, `Verifier`), and typed DTOs.
  - `input`: AST-based validation, parser, and whitelist security bounds.
  - `solvers`: Pure mathematical solvers (calculus, algebra, linear algebra).
  - `verification`: Independent symbolic and numerical verifiers.
  - `rendering`: LaTeX and MathML converters.
  - `presentation`: NiceGUI UI components, services, and layout.
- UI must call application use cases, never solvers directly.
- Keep domain, input, and solver code strictly independent of NiceGUI and Plotly.
- Use typed DTOs (`ProblemRequest`, `SolutionResponse`, `VerificationResult`, `SolutionStep`) at application boundaries.
- Prefer simple composition over unnecessary inheritance.
- Add abstractions only when they solve a concrete problem.

## Mathematical correctness
- Never invent a mathematical rule or solution step.
- Distinguish the final symbolic result from the explanation.
- Preserve domain restrictions and relevant assumptions.
- Use exact arithmetic where possible.
- Verify results independently with SymPy or mathematical invariants.
- If a step cannot be justified, report that limitation honestly.
- Verification failures must never be reported as successful verification.

## Development workflow
- Inspect the existing code before making changes.
- Propose a short plan before multi-file modifications.
- Implement one small, testable task at a time.
- Do not rewrite unrelated files.
- Do not add dependencies without explaining why.
- Never delete user data or run destructive commands without approval.

## Common commands
- Sync environment: `uv sync`
- Launch app: `uv run python run.py`
- Run test suite: `uv run pytest`
- Run coverage: `uv run pytest --cov=src --cov-report=term-missing`
- Lint code: `uv run ruff check .`
- Build package: `pyinstaller mathweave-studio.spec`

## Testing
- Add tests for every new solver, verifier, and transformation rule.
- Include valid inputs, invalid inputs, boundary cases, and adversarial denial-of-service cases.
- Run relevant tests after every change.
- Run the full test suite before declaring a task complete.
- Report commands executed and any tests that could not run.

## Code quality
- Use type hints and clear naming.
- Keep functions and classes focused.
- Follow existing project conventions.
- Update documentation when behavior or interfaces change.
