# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-23

### Added
- **Equation Solver**: Implemented algebraic equation solving (`SOLVE_EQUATION`) with standard form transformation, root finding, factor display, and independent root verification.
- **Process Isolation & Hard Timeouts**: Added robust OS worker process isolation (`multiprocessing.Process` via `spawn`) with hard termination on configurable timeout for CPU-bound symbolic calculations.
- **Expression Complexity Hardening**: Added AST node count bounds, constant magnitude limits, logarithmic power magnitude guards, and strict prevention of nested exponent towers (e.g. `x**(9**9**9)`, `9**9**9**9`).
- **HTML Sanitization**: Added explicit HTML escaping in mathematical view fallback rendering to prevent script and event-handler injection.
- **Independent Verifier Tests**: Added dedicated unit test suites for `IntegralVerifier` and `SurfaceAreaVerifier`.
- **Release Readiness**: Added `SECURITY.md`, `CONTRIBUTING.md`, `.github/dependabot.yml`, and configured Ruff linter quality gates in CI.

### Security
- **certifi upgrade**: Verified and remediated `PYSEC-2026-4320` by updating `certifi` from `2026.7.22` to `2026.10.23` in `uv.lock`.
