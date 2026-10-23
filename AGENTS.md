
# MathStudio — Agent Guidelines

## Project goals
Build a cross-platform mathematics learning application using
Python 3.14+, NiceGUI, SymPy, NumPy and Plotly.

## Architecture
- Follow Clean Architecture with clear dependency boundaries.
- UI must call application use cases, never solvers directly.
- Keep domain and solver code independent of NiceGUI and Plotly.
- Use typed DTOs at application boundaries.
- Prefer simple composition over unnecessary inheritance.
- Add abstractions only when they solve a concrete problem.

## Mathematical correctness
- Never invent a mathematical rule or solution step.
- Distinguish the final symbolic result from the explanation.
- Preserve domain restrictions and relevant assumptions.
- Use exact arithmetic where possible.
- Verify results independently with SymPy or mathematical invariants.
- If a step cannot be justified, report that limitation honestly.

## Development workflow
- Inspect the existing code before making changes.
- Propose a short plan before multi-file modifications.
- Implement one small, testable task at a time.
- Do not rewrite unrelated files.
- Do not add dependencies without explaining why.
- Never delete user data or run destructive commands without approval.

## Testing
- Add tests for every new solver and transformation rule.
- Include valid inputs, invalid inputs and boundary cases.
- Run relevant tests after every change.
- Run the full test suite before declaring a task complete.
- Report commands executed and any tests that could not run.

## Code quality
- Use type hints and clear naming.
- Keep functions and classes focused.
- Follow existing project conventions.
- Update documentation when behavior or interfaces change.
