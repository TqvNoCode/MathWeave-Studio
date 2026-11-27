# EC1-R1 Implementation Report — Domain & Verification Hardening

**Milestone**: ODE-EC1-R1  
**Project**: MathWeave Studio v0.3.0  
**Branch**: `feature/euler-cauchy-solver` (`origin/main` @ `c2f3f1d`)  
**Version (`pyproject.toml`)**: `0.2.0` (unbumped)  
**Git State**: Uncommitted working-tree changes preserved; no staging, commits, pushes, merges, or tags performed.

---

## 1. Summary of EC1-R1 Hardening Fixes

1. **Structured Domain & Interval Validation (`src/math_app/input/ode_parser.py`, `src/math_app/solvers/calculus/ode/euler_cauchy_solver.py`)**:
   - Replaced fragile string-matching interval logic (`">0"`, `"<0"`, `">=0"`, `"<=0"`) with structured parser metadata (`ParsedIntervalConstraint`, `parse_interval_constraint()`, `_split_top_level_clauses()`, `_is_interval_clause()`) attached to `ParsedODE.interval_spec` and `ParsedSecondOrderODE.interval_spec`.
   - Preserves exact requested interval endpoints and openness (`t > 2` -> `(2, oo)`, `t < -1` -> `(-oo, -1)`, `1 < t < 5` -> `(1, 5)`, `t >= 2` -> `[2, oo)`, `t <= -1` -> `(-oo, -1]`, `[1, 4]`, `t in (2, 5)`).
   - Rejects any connected interval containing `t = 0` in the interior or boundary (`-1 < t < 1`, `t >= 0`, `t <= 0`, `0 <= t < 3`, `-3 < t <= 0`, `[0, 2]`, `(-2, 0]`) with `SolutionStatus.CANNOT_SOLVE` (`method="singular_point_interval"`).
   - Rejects unsupported interval syntax (`t != 0`, `(-oo, 0) U (0, oo)`, invalid bounds, mismatched variable) with `SolutionStatus.CANNOT_SOLVE` (`method="unsupported_interval_syntax"`) without silently falling back to $\mathbb{R} \setminus \{0\}$.

2. **Preservation of Original Domain Metadata (`src/math_app/solvers/calculus/ode/euler_cauchy_solver.py`)**:
   - Reuses `_univariate_constraint_real_set`, `_combine_completeness`, `_format_domain_with_completeness`, `_decompose_set_components`, and `evaluate_initial_point_domain`.
   - Preserves and validates `original_domain_restrictions`, `original_denominators`, `leading_coeffs`, and `original_domain_constraints` across algebraic simplifications (such as `((t - 2)/(t - 2))*t^2*y'' + ...`, `sqrt(t)^2`, and `log(t) - log(t)`), splitting natural domains and rejecting interval/IVP violations against the unsimplified source domain.
   - Uses `sp.Complement(requested_interval, norm_domain)` when SymPy's `Interval.is_subset(Union)` returns `None`, ensuring intervals straddling removed singularities are deterministically rejected.

3. **Conservative Coefficient, Discriminant & Cauchy Input Validation (`src/math_app/solvers/calculus/ode/euler_cauchy_solver.py`, `src/math_app/domain/models.py`)**:
   - Requires established realness (`is_real is True`) and finiteness (`is_finite is True`) for `A`, `B`, `C`; rejects unresolved free parameters, complex coefficients, non-finite values, and unverified `is_real is None` coefficients conservatively without treating `None` as proven real.
   - Classifies the discriminant strictly via SymPy assumptions (`delta.is_positive is True`, `delta.is_zero is True`, `delta.is_negative is True`), returning `CANNOT_SOLVE` + `VerificationStatus.UNVERIFIED` (`indicial_discriminant_unresolved`) when undetermined, without numerical approximation.
   - Validates all Cauchy inputs (`t0`, `y0`, `v0`) via `classify_scalar_real_finite` and symbolic sign checks (`is_negative is True` / `is_positive is True`), returning `UNVERIFIED` on unresolved symbols without raising `TypeError`, and `InvalidInputError` on non-real/non-finite inputs.
   - Registered `ProblemType.ODE_EULER_CAUCHY` in `_ODE_PROBLEM_TYPES` in `src/math_app/domain/models.py`.

4. **Faithful Verification Status Propagation (`euler_cauchy_solver.py`, `ode_pedagogical_enhancer.py`, `ode_staged_step_viewer.py`)**:
   - Derived step descriptions, `expression_after`, `latex_after`, substeps, Stage 4 `ODEStageSummary` (`is_completed`, `badge_text`, `badge_color`, `summary_latex`, `subtitle`), and UI stage badges strictly from `VerificationResult.status`.
   - `UNVERIFIED` and `FAILED` outcomes never display `is_completed=True`, `R(t) \equiv 0`, or `VERIFIED`.

5. **Fundamental-System Linear Independence Verification Gate (`src/math_app/verification/calculus/ode_verifier.py`)**:
   - Added `ODEVerifier.verify_fundamental_system()` and integrated it via `fundamental_solutions=(y1, y2)` into `ODEVerifier.verify_second_order()`.
   - Symbolically verifies $W(y_1, y_2) \neq 0$, realness, finiteness, and pole-freedom on the exact connected interval (failing on $W \equiv 0$, non-real/non-finite $W$, or zeros/poles on the interval; returning `UNVERIFIED` when independence cannot be established symbolically).

---

## 2. Exact Changed File List

### 2.1 Source & Test Files (Included in `reports/ec1_euler_cauchy_r1.patch`)

**Modified Tracked Files (17):**
- `CHANGELOG.md`
- `src/math_app/domain/models.py`
- `src/math_app/input/ode_parser.py`
- `src/math_app/main.py`
- `src/math_app/presentation/components/ode_pedagogical_enhancer.py`
- `src/math_app/presentation/components/ode_staged_step_viewer.py`
- `src/math_app/presentation/components/operation_catalog.py`
- `src/math_app/presentation/components/problem_statement.py`
- `src/math_app/presentation/components/workspace/ode/ode_classification_selector.py`
- `src/math_app/presentation/components/workspace/ode/ode_method_selector.py`
- `src/math_app/presentation/components/workspace/ode/ode_state.py`
- `src/math_app/solvers/calculus/ode/__init__.py`
- `src/math_app/verification/calculus/ode_verifier.py`
- `tests/unit/presentation/test_design_system_and_catalog.py`
- `tests/unit/presentation/test_ode_pedagogical_solution_flow.py`
- `tests/unit/presentation/test_operation_catalog.py`
- `tests/unit/presentation/test_ux3_1_ode_workspace.py`

**Newly Created Untracked Source & Test Files (2):**
- `src/math_app/solvers/calculus/ode/euler_cauchy_solver.py` (2,037 lines)
- `tests/unit/solvers/calculus/test_euler_cauchy_solver.py` (1,108 lines)

### 2.2 Review Artifacts (Excluded from `reports/ec1_euler_cauchy_r1.patch`)
- `reports/EC1_IMPLEMENTATION_REPORT.md`
- `reports/EC1_R1_IMPLEMENTATION_REPORT.md`
- `reports/ec1_euler_cauchy.patch` (pre-existing EC1 snapshot)
- `reports/ec1_euler_cauchy_r1.patch` (4,723 lines)

### 2.3 Exact Diff Statistics (`git apply --stat reports/ec1_euler_cauchy_r1.patch`)
```text
 CHANGELOG.md                                       |   15 
 src/math_app/domain/models.py                      |    2 
 src/math_app/input/ode_parser.py                   |  394 ++++
 src/math_app/main.py                               |    4 
 .../components/ode_pedagogical_enhancer.py         |  242 ++
 .../components/ode_staged_step_viewer.py           |   23 
 .../presentation/components/operation_catalog.py   |   19 
 .../presentation/components/problem_statement.py   |    3 
 .../workspace/ode/ode_classification_selector.py   |   40 
 .../workspace/ode/ode_method_selector.py           |   14 
 .../components/workspace/ode/ode_state.py          |   38 
 src/math_app/solvers/calculus/ode/__init__.py      |    2 
 src/math_app/verification/calculus/ode_verifier.py |  186 ++
 .../presentation/test_design_system_and_catalog.py |    3 
 .../test_ode_pedagogical_solution_flow.py          |   79 +
 tests/unit/presentation/test_operation_catalog.py  |    8 
 .../unit/presentation/test_ux3_1_ode_workspace.py  |    4 
 .../solvers/calculus/ode/euler_cauchy_solver.py    | 2037 ++++++++++++++++++++
 .../solvers/calculus/test_euler_cauchy_solver.py   | 1108 +++++++++++
 19 files changed, 4192 insertions(+), 29 deletions(-)
```
Patch apply verification against a clean temporary clone of `HEAD`: `git apply --check` succeeded (`exit code 0`).

---

## 3. Test Execution Evidence

| Command | Exit Code | Result | Warnings |
| :--- | :---: | :--- | :--- |
| `uv run pytest -q tests/unit/solvers/calculus/test_euler_cauchy_solver.py` | `0` | `76 passed in 4.14s` | None |
| `uv run pytest -q tests/unit/solvers/calculus/` | `0` | `571 passed in 79.96s (0:01:19)` | None |
| `uv run pytest -q` | `0` | `1392 passed, 2 warnings in 163.04s (0:02:43)` | 2 pre-existing unrelated warnings (explained below) |
| `uv run ruff check src/ tests/` | `0` | `All checks passed!` | None |
| `git diff --check` | `0` | Clean (no whitespace errors) | None |
| `uv lock --check` | `0` | `Resolved 90 packages in 1ms` | None |

### Warnings Explanation (Full Suite)
1. `tests/unit/presentation/test_analysis_service.py::test_2d_plot_sampling_arbitrary_viewport` — `RuntimeWarning: invalid value encountered in sqrt` (pre-existing NumPy out-of-domain sampling in 2D plot viewport test).
2. `tests/unit/test_windows_metadata_and_signing.py::test_setup_test_shutdown_endpoint_security_and_activation` — `StarletteDeprecationWarning` on `httpx` / `starlette.testclient` (pre-existing test client setup).

### Newly Added EC1-R1 Tests
In `tests/unit/solvers/calculus/test_euler_cauchy_solver.py` (50 newly added test cases, expanding suite from 26 to 76 tests):
- `test_explicit_valid_intervals_preserved_exactly` (11 parametrized cases: `t > 0`, `t < 0`, `t > 2`, `t < -1`, `1 < t < 5`, `-5 < t < -1`, `t >= 2`, `t <= -1`, `t in (2, 5)`, `[1, 4]`, `(-5, -2]`)
- `test_intervals_containing_or_crossing_zero_rejected` (9 parametrized cases: `-1 < t < 1`, `t >= 0`, `t <= 0`, `0 <= t < 3`, `-3 < t <= 0`, `t > -2`, `t < 1`, `[0, 2]`, `(-2, 0]`)
- `test_unsupported_interval_syntax_never_broadens_to_natural_domain` (7 parametrized cases: `t != 0`, `(-oo, 0) U (0, oo)`, `positive_or_invalid`, `z > 2`, `5 < t < 1`, `[0, oo]`)
- `test_cauchy_ivp_respects_explicit_shifted_interval`
- `test_cancelled_denominator_restriction_preserved_across_modes`
- `test_sqrt_squared_preserves_nonnegative_source_domain`
- `test_canceled_logarithm_preserves_positive_source_domain`
- `test_conservative_rejection_of_unresolved_coefficients_and_complex`
- `test_unverified_is_real_none_coefficient_and_unresolved_discriminant`
- `test_unresolved_symbolic_cauchy_inputs_fail_closed_without_typeerror` (3 parametrized cases: symbolic `t0`, `y0`, `v0`)
- `test_nonreal_cauchy_inputs_raise_invalid_input_error` (3 parametrized cases: non-real `t0`, `y0`, `v0`)
- `test_all_three_root_cases_pass_fundamental_system_wronskian_gate` (6 parametrized cases: all 3 root cases on positive and negative intervals)
- `test_ode_verifier_fundamental_system_gate_direct`
- `test_solver_returns_unverified_when_fundamental_system_gate_unverified`
- `test_mocked_verifier_status_propagates_to_steps_and_pedagogical_flow` (3 parametrized cases: `VERIFIED`, `UNVERIFIED`, `FAILED`)

In `tests/unit/presentation/test_ode_pedagogical_solution_flow.py` (3 newly added test cases):
- `test_euler_cauchy_pedagogical_flow_verification_states` (`VERIFIED`, `UNVERIFIED`, `FAILED` with UI mounting)

---

## 4. Updated Verification Matrix

| Capability / Gate | Mechanism | Outcome on Success | Outcome on Failure / Inconclusive |
| :--- | :--- | :--- | :--- |
| Equation structural form & coefficients | `A = a/t^2, B = b/t, C = c` with `is_real is True` & `is_finite is True`, `A.is_zero is False` | Proceeds to domain & indicial analysis | `CANNOT_SOLVE` (`NOT_APPLICABLE` or `UNVERIFIED`) |
| Source-domain metadata | `_build_domain_metadata()` + `evaluate_initial_point_domain()` | Exact original & normalized domains preserved | `INVALID_INPUT` / `CANNOT_SOLVE` / `UNVERIFIED` |
| Interval validation | `parse_interval_constraint()` + zero exclusion + `Complement` subset check | Exact `sp.Interval` preserved on branch | `CANNOT_SOLVE` (`singular_point_interval`, `unsupported_interval_syntax`, `source_domain_interval_violation`) |
| Discriminant root classification | `delta.is_positive` / `is_zero` / `is_negative` | `DISTINCT`, `REPEATED`, or `COMPLEX` real basis | `CANNOT_SOLVE` + `UNVERIFIED` (`indicial_discriminant_unresolved`) |
| Cauchy IVP inputs | `classify_scalar_real_finite()` + symbolic sign + `det_M` check | Exact Cramer solution on containing interval | `InvalidInputError` / `UNVERIFIED` / `CANNOT_SOLVE` |
| ODE residual + IVP check | `ODEVerifier.verify_second_order()` | `VERIFIED` | `FAILED` (`DISCREPANCY_DETECTED`) or `UNVERIFIED` |
| Fundamental system independence | `ODEVerifier.verify_fundamental_system()` ($W \neq 0$, real, finite, pole-free on interval) | Appends Wronskian confirmation & returns `VERIFIED` | `FAILED` or `UNVERIFIED` (propagated to `SolutionResponse` & UI) |
| Steps & Stage 4 UI propagation | `_build_solution_steps()` + `_build_euler_cauchy_flow()` + `ode_staged_step_viewer.py` | Emerald `VERIFIED`, `is_completed=True` | Amber `UNVERIFIED` or Rose `FAILED`, `is_completed=False`, no `R(t) \equiv 0` |

---

## 5. Remaining Limitations

1. Nonhomogeneous Euler–Cauchy equations ($g(t) \neq 0$) remain intentionally out of scope (`CANNOT_SOLVE`).
2. Higher-order Euler–Cauchy equations ($n \ge 3$) are out of scope.
3. Cauchy initial value problems at the singular point $t_0 = 0$ are rejected (`CANNOT_SOLVE`, `singular_point_initial_condition`); Frobenius series expansions are not implemented.
4. Symbolic interval endpoints and parametric equation coefficients remain conservatively rejected rather than symbolically case-split.

---

## 6. Current Git Status

```text
## feature/euler-cauchy-solver...origin/main
 M CHANGELOG.md
 M src/math_app/domain/models.py
 M src/math_app/input/ode_parser.py
 M src/math_app/main.py
 M src/math_app/presentation/components/ode_pedagogical_enhancer.py
 M src/math_app/presentation/components/ode_staged_step_viewer.py
 M src/math_app/presentation/components/operation_catalog.py
 M src/math_app/presentation/components/problem_statement.py
 M src/math_app/presentation/components/workspace/ode/ode_classification_selector.py
 M src/math_app/presentation/components/workspace/ode/ode_method_selector.py
 M src/math_app/presentation/components/workspace/ode/ode_state.py
 M src/math_app/solvers/calculus/ode/__init__.py
 M src/math_app/verification/calculus/ode_verifier.py
 M tests/unit/presentation/test_design_system_and_catalog.py
 M tests/unit/presentation/test_ode_pedagogical_solution_flow.py
 M tests/unit/presentation/test_operation_catalog.py
 M tests/unit/presentation/test_ux3_1_ode_workspace.py
?? reports/
?? src/math_app/solvers/calculus/ode/euler_cauchy_solver.py
?? tests/unit/solvers/calculus/test_euler_cauchy_solver.py
```
