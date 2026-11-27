# ODE-FINAL — Final Integration Review & Pre-Merge Audit

**Project:** MathWeave Studio v0.3.0 (track) / `pyproject.toml` version `0.2.0`  
**Branch:** `feature/euler-cauchy-solver` (tracking `origin/main` at `c2f3f1d`)  
**Audit Date:** 2026-11-27  
**Milestones Audited:** `ODE-EC1`, `ODE-EC1-R1`, `ODE-UX1`  
**Final Decision:** **`NOT_READY`**

---

## 1. Executive Summary

A full, independent source-level, mathematical, cross-module, live NiceGUI UI, and Git-hygiene audit was performed across the uncommitted `ODE-EC1`, `ODE-EC1-R1`, and `ODE-UX1` working-tree changes on `feature/euler-cauchy-solver`.

The mathematical core (`ODEEulerCauchySolver`, structured interval parsing in `ode_parser.py`, and independent Wronskian/residual verification in `ode_verifier.py`) is **sound, conservative, and passes all 76 dedicated solver unit tests and all 1,403 repository tests**. However, the presentation and workspace integration layer introduces **four material integration and cross-module regression defects (Blockers 1–4)** that break non-Euler–Cauchy ODE domain displays, strip interval constraints during workspace interactions, break `/?op=ode_euler_cauchy` deep linking, and misclassify incomplete/mismatched Cauchy IVP validation errors as order-mismatch errors.

### Audit Classification Summary

| Area | Classification | Summary |
|---|---|---|
| **ODE-EC1 (Mathematical Solver)** | **PASS** | All 3 indicial root cases, positive/negative connected intervals, independent natural-domain constants, Cauchy IVPs, nonhomogeneous rejection, and `t = 0` singularity handling verified. |
| **ODE-EC1-R1 (Domain & Verification Hardening)** | **PASS** | Structured interval parsing, source-domain preservation, conservative realness/discriminant checks, Cauchy scalar validation, independent Wronskian gate, and honest status propagation verified in core. *(Note: UI callers bypass interval preservation — see Blocker 2).* |
| **ODE-UX1 (Presentation & Learning Experience)** | **FAIL** | Euler–Cauchy mode labels, `\ln` formatting, 4-stage flow, and expand/collapse controls work, **but** 4 integration/cross-module blockers affect `domain_view.py`, `ode_state.py`, `ode_workspace.py`, `app.py`, and `solution_view.py`. |
| **Cauchy IVP Red Badge Investigation** | **NEEDS INVESTIGATION -> RESOLVED (MIXED)** | The red element in `07_cauchy_ivp_mode.png` is the enabled `"Xóa điều kiện"` button (`ode_mode_selector.py:113-125`), not an error badge. However, testing Cases A–D uncovered genuine UI defects: amber `y(1)=3, y'(1)=0` branch badge (Case A) and misclassified `"Phương trình không đúng cấp"` cards for Cases B and C (**Blocker 4**). |
| **Mathematical Regression Matrix (16 Cases)** | **PASS** | All 16 core mathematical and verifier scenarios verified via inspected test assertions and direct execution. |
| **Cross-Module Regression** | **FAIL** | Constant-coefficient, nonhomogeneous, and Reduction-of-Order solvers pass; **presentation domain rendering fails** for Reduction of Order, First-Order Linear, and Classical Homogeneous ODEs (**Blocker 1**). |
| **Final Quality Gates (`pytest`, `ruff`, `git diff --check`, `uv lock --check`)** | **PASS** | `1403 passed` (2 pre-existing warnings), Ruff clean, whitespace clean, lockfile valid. |
| **Documentation & Release Readiness** | **PASS** | `pyproject.toml` remains `0.2.0`; no unsupported features advertised; zero secrets/paths in tracked files. |

### Readiness Distinction

- **Code Readiness:** **NOT_READY** — Mathematical core is ready, but 4 concrete UI/integration blockers (`ODE-FINAL-R1`) must be fixed first.
- **Commit Readiness:** **NOT_READY** — Working tree must not be committed until Blockers 1–4 are resolved and re-verified.
- **Merge Readiness:** **NOT_READY** — Implementation is currently uncommitted (`0 ahead / 0 behind` `origin/main`), has not undergone PR review after fixes, and has unresolved blockers.

---

## 2. EC1 Mathematical Audit — **PASS**

**Inspected Files:**
- `src/math_app/solvers/calculus/ode/euler_cauchy_solver.py` (2,037 lines)
- `src/math_app/domain/models.py` (193 lines)
- `src/math_app/main.py` (475 lines)
- `src/math_app/solvers/calculus/ode/__init__.py` (23 lines)

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 1 | Homogeneous 2nd-order Euler–Cauchy handled | **PASS** | `ODEEulerCauchySolver.solve()` (`euler_cauchy_solver.py:255-282`) checks $A = a(t)/t^2$, $B = b(t)/t$, $C = c(t)$ are independent of $t$ and $A \ne 0$; derives indicial polynomial $A m^2 + (B-A)m + C = 0$ (`lines 931-938`). |
| 2 | All 3 characteristic-root cases implemented | **PASS** | `DISTINCT` ($\Delta > 0$, `lines 947-950`), `REPEATED` ($\Delta = 0$, `lines 951-954`), `COMPLEX` ($\Delta < 0$, $\alpha = -(B-A)/(2A), \beta = \sqrt{-\Delta}/(2|A|)$, `lines 955-960`), with real trigonometric basis (`lines 993-998`). |
| 3 | Positive and negative connected intervals | **PASS** | `get_fundamentals(is_neg)` (`lines 984-1003`) uses `base_expr = -var` when `is_neg=True`, producing real $(-t)^m$, $\ln(-t)$, $\sqrt{-t}$ without complex artifacts. |
| 4 | Natural domain uses independent constants | **PASS** | Natural domain (`lines 1221-1354`) creates separate `BranchSolution` entries per connected component with independent `C1, C2` on $(0, \infty)$ and `C3, C4` on $(-\infty, 0)$ (generalized via `C{2*idx+1}`, `C{2*idx+2}`). |
| 5 | Cauchy IVPs at nonzero initial points | **PASS** | `lines 1011-1148` solves the $2 \times 2$ linear system at $t_0 \ne 0$ via Cramer's rule after checking `det_M.is_nonzero is True` (`lines 1035-1081`) on the containing connected component; both $t_0 > 0$ and $t_0 < 0$ verified. |
| 6 | Nonhomogeneous equations explicitly rejected | **PASS** | `lines 232-253` rejects `not parsed.is_homogeneous or sp.simplify(parsed.rem_expr) != 0` with `SolutionStatus.CANNOT_SOLVE` and `VerificationStatus.NOT_APPLICABLE` (`method="euler_cauchy_nonhomogeneous"`). |
| 7 | Singular point `t = 0` handled conservatively | **PASS** | `lines 524-548` returns `CANNOT_SOLVE` (`singular_point_initial_condition`) for $t_0 = 0$ explaining it is a singular point where $a(t)$ vanishes without asserting mathematical nonexistence; `lines 647-671` rejects intervals containing $0$. |
| 8 | Integrated into existing application routing | **PASS** | `ProblemType.ODE_EULER_CAUCHY` in `domain/models.py:30,97`; registered in `main.py:148-149`; exported in `solvers/calculus/ode/__init__.py:4,20`. |
| 9 | No unnecessary second ODE workspace introduced | **PASS** | Integrated directly into unified `ode_workspace.py` via `ODEClassification.EULER_CAUCHY`. |

**Minor Observation (Non-blocking):** `ODEEulerCauchySolver.can_solve()` (`euler_cauchy_solver.py:201-205`) returns `True` for both `ProblemType.ODE_EULER_CAUCHY` and `ProblemType.SOLVE_EQUATION`. In `main.py:125-149`, `EquationSolver` is registered for `SOLVE_EQUATION` and `ODEEulerCauchySolver` strictly for `ODE_EULER_CAUCHY`, so runtime routing is unaffected, though `can_solve()` is broader than intended.

---

## 3. EC1-R1 Domain & Verification Hardening Audit — **PASS** (Core)

**Inspected Files:**
- `src/math_app/input/ode_parser.py` (1,572 lines)
- `src/math_app/verification/calculus/ode_verifier.py` (4,065 lines)
- `src/math_app/solvers/calculus/ode/euler_cauchy_solver.py` (2,037 lines)

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 1 | Structured interval parsing is actually used | **PASS** | `parse_second_order_ode_input()` populates `interval_spec` via `parse_interval_constraint()` (`ode_parser.py:1351`), and `ODEEulerCauchySolver` consumes `parsed.interval_spec` (`euler_cauchy_solver.py:610-646`). |
| 2 | Explicit interval endpoints & openness preserved | **PASS** | `parse_interval_constraint()` (`ode_parser.py:253-469`) preserves open/closed bounds into `sp.Interval(left, right, left_open=..., right_open=...)`, stored on `BranchSolution.domain_interval`, `left_open`, `right_open`, `domain_set`. |
| 3 | Intervals crossing or touching `t = 0` rejected | **PASS** | `requested_interval.contains(sp.Integer(0))` (`euler_cauchy_solver.py:647-671`) returns `CANNOT_SOLVE` (`singular_point_interval`) for `-1 < t < 1`, `t >= 0`, `t <= 0`, `[0, 2]`, `(-2, 0]`, etc. |
| 4 | Unsupported interval syntax never falls back | **PASS** | `if not interval_spec.is_supported or interval_spec.interval is None` (`euler_cauchy_solver.py:621-644`) returns `CANNOT_SOLVE` (`unsupported_interval_syntax`) for `t != 0`, `(-oo, 0) U (0, oo)`, `z > 2`, `5 < t < 1`, `[0, oo]`, etc. |
| 5 | Original source-domain restrictions preserved | **PASS** | `extract_source_domain_constraints()` runs before `sp.simplify()` (`ode_parser.py:1422-1429`); `_build_domain_metadata()` (`euler_cauchy_solver.py:92-186`) builds `orig_domain` and `norm_domain`; `sp.Complement(requested_interval, norm_domain)` (`lines 722-729`) catches intervals straddling removed points (e.g., `(t-2)/(t-2)`). |
| 6 | Coefficient realness/finiteness conservative | **PASS** | `euler_cauchy_solver.py:307-396` rejects free symbols, `oo/zoo/nan`, `sp.I`/`is_real is False`, and requires `c_val.is_real is True and c_val.is_finite is True` and `A_cand.is_zero is False`. |
| 7 | Unresolved discriminant uses no numeric guessing | **PASS** | `euler_cauchy_solver.py:947-981` branches strictly on `delta.is_positive is True`, `delta.is_zero is True`, `delta.is_negative is True`; otherwise returns `CANNOT_SOLVE` + `VerificationStatus.UNVERIFIED` (`indicial_discriminant_unresolved`). |
| 8 | Cauchy inputs validated | **PASS** | `euler_cauchy_solver.py:486-602` checks `classify_scalar_real_finite`, symbolic sign (`t0_val.is_negative` / `is_positive`), and `evaluate_initial_point_domain()` against `original_denominators`, `leading_coeffs`, and `original_domain_constraints`. |
| 9 | Wronskian verification independently enforced | **PASS** | `ODEVerifier.verify_fundamental_system()` (`ode_verifier.py:3521-3682`) computes $W(y_1, y_2)$ with domain sign assumptions, checks `_prove_symbolic_zero`, finiteness, realness, denominator poles (`solveset(..., domain=iv_set)`), and zeros on `iv_set`; enforced inside `verify_second_order(..., fundamental_solutions=(y1, y2))` (`lines 3841-3853`). |
| 10 | `VERIFIED`, `UNVERIFIED`, `FAILED` propagated honestly | **PASS** | `euler_cauchy_solver.py:1435-1440, 1662-1691, 1859-2035` and `ode_pedagogical_enhancer.py:2433, 2857-2897` derive status, completion flags, badges, and equations strictly from `v_res.status`. |

**Parser/UI Boundary Coupling Note:** `extract_second_order_ics_from_string()` (`ode_parser.py:1231-1232`) intentionally discards interval clauses (`elif _is_interval_clause(part): continue`). In `parse_second_order_ode_input()` (`lines 1332-1336`), `extract_interval_from_string()` runs *before* `extract_second_order_ics_from_string()`, preserving `interval_str`. However, UI state/workspace helpers (`ode_state.py`, `ode_workspace.py`) call `extract_second_order_ics_from_string()` directly without `extract_interval_from_string()`, causing **Blocker 2**.

---

## 4. UX1 Presentation & Learning Experience Audit — **FAIL**

**Inspected Files:**
- `src/math_app/presentation/components/ode_pedagogical_enhancer.py` (3,186 lines)
- `src/math_app/presentation/components/ode_staged_step_viewer.py` (358 lines)
- `src/math_app/presentation/components/problem_statement.py` (667 lines)
- `src/math_app/presentation/components/solution_view.py` (888 lines)
- `src/math_app/presentation/components/domain_view.py` (239 lines)
- `src/math_app/presentation/components/workspace/ode/ode_classification_selector.py` (194 lines)
- `src/math_app/presentation/components/workspace/ode/ode_workspace.py` (645 lines)
- `src/math_app/presentation/components/workspace/ode/ode_state.py` (786 lines)
- `src/math_app/presentation/app.py` (1,168 lines)

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 1 | General Solution & Cauchy IVP labels derived from actual mode | **PASS** | `_build_euler_cauchy_flow()` (`ode_pedagogical_enhancer.py:2421-2431`) and `render_ode_classification_card()` (`solution_view.py:158-172`) check `prob_mode == "GENERAL"` / `"CAUCHY_IVP"` first. |
| 2 | No substring collision between `Euler–Cauchy` and `Cauchy IVP` | **PASS** | Uses exact rule names `("Điều kiện ban đầu Cauchy", "Thiết lập hệ Cauchy", "Giải hệ đại số tuyến tính")` and `"hệ điều kiện cauchy"` rather than bare `"cauchy"`. |
| 3 | Natural logarithms display consistently as `ln` | **PASS** | `polish_euler_cauchy_latex()` (`ode_pedagogical_enhancer.py:2254-2284`) converts `\log` to `\ln` across final answer, branch solutions, and all 4 stages. |
| 4 | Negative-domain expressions remain real-valued | **PASS** | Uses `(-t)^m` and `\ln(-t)` in solver steps, Stage 1–3 derivations, final answer, and branch cards. |
| 5 | Repeated pedagogical explanations removed | **PASS** | Stage 1 Step 2 shows trial derivatives once; Stage 2 Step 5 shows Wronskian once; `_is_meaningful_intermediate_result()` (`ode_staged_step_viewer.py:48-79`) suppresses redundant `KẾT QUẢ:` boxes when equal to `equation_latex`. |
| 6 | Mathematical symbols and coefficients consistent | **PASS** (minor caveat) | Stage 2 Step 4 uses `A, B, C, m, \Delta` consistently. Minor caveats: (a) `_extract_euler_cauchy_context` regex (`ode_pedagogical_enhancer.py:2343`) fails to extract `A, B, C` when coefficients are LaTeX fractions (e.g., `\frac{1}{2}`), falling back gracefully to raw Step 1 equation; (b) Stage 3 Step 7 Cauchy prose (`lines 2796, 2834-2835`) hardcodes `y'(t)`, `t_0` when `target_var == "x"`. |
| 7 | Domain explanations mathematically precise | **FAIL** | **Blocker 1:** `domain_view.py:19-27` intercepts *every* restriction containing `"điểm kỳ dị"` globally, mislabeling Reduction of Order (`t = 2`), First-Order Linear (`t = 2`), and Classical Homogeneous (`x != 0`) as Euler–Cauchy `a(t) = At²` at `t = 0`, and produces invalid LaTeX `x = 0)` / `(- \infty, 0)) \cup (0), + \infty)` for `ClassicalHomogeneous`. |
| 8 | Four pedagogical stages remain functional | **PASS** | All 4 stages (`Phương trình chỉ số`, `Biệt thức Delta và Hệ nghiệm cơ bản`, `Xác định nghiệm bài toán`, `Kiểm chứng toán học độc lập`) render cleanly. |
| 9 | Verification status consistent between result card and Stage 4 | **PASS** | Result header (`verification_badge.py`) and Stage 4 (`ode_pedagogical_enhancer.py:2857-2897`, `ode_staged_step_viewer.py:284-297`) match across `VERIFIED`, `UNVERIFIED`, and `FAILED`. |
| 10 | Expand-all and collapse-all controls work | **PASS** | Verified live in `QWebEngineView`: initial open = `1` (Stage 1), after `Mở rộng tất cả` = `4`, after `Thu gọn tất cả` = `0`. |
| 11 | No redundant verification badges or duplicated result displays | **FAIL** | Single-branch `VERIFIED` badge suppression works (`solution_view.py:335`), **but** in Cauchy IVP mode, `solution_view.py:330-334` colors the `y(1) = 3, y'(1) = 0` branch badge **amber (`bg-amber-8`)** because `euler_cauchy_solver.py:1106` sets `integration_constant_val=None`. |

### Additional UX1 Integration Blockers Found

- **Blocker 2 — Interval Stripping in Workspace & Mode Switching (`ode_workspace.py`, `ode_state.py`)**:
  - Clicking `"Miền âm: t^2*y'' + 4*t*y' + 2*y = 0, t < 0"` or `"Nghiệm thực phân biệt: ..., t > 0"` in General Solution mode calls `extract_second_order_ics_from_string(example_val)` (`ode_workspace.py:338, 346-352`) because `EULER_CAUCHY` was added to `has_split_support`, which **strips `, t < 0` and `, t > 0`** and populates `t^2*y'' + 4*t*y' + 2*y = 0` (proven live: `before= "t^2*y'' + 4*t*y' + 2*y = 0, t > 0" after= "t^2*y'' + 4*t*y' + 2*y = 0"`).
  - `ODEState.with_mode()` (`ode_state.py:421, 443`) and `ODEState.build_problem_request()` in `CAUCHY_IVP` mode (`ode_state.py:691, 755`) similarly call `extract_second_order_ics_from_string()` without preserving the interval, silently dropping shifted intervals like `, t > 2` in Cauchy IVP requests built from the UI.
- **Blocker 3 — Broken Deep-Link Routing (`src/math_app/presentation/app.py:344-354`)**:
  - `is_ode_op` in `app.py` lists 9 ODE `ProblemType` values explicitly and omits `ProblemType.ODE_EULER_CAUCHY`. Navigating to `/?op=ode_euler_cauchy` falls through to the generic `f(x)` calculus form (`"Biểu thức toán học f(x)"`) instead of `render_ode_workspace()`, confirmed live in `QWebEngineView`.

---

## 5. Cauchy IVP Validation Badge Investigation

### Meaning of the Red Element in `07_cauchy_ivp_mode.png`

Inspection of `reports/screenshots/07_cauchy_ivp_mode.png` and `src/math_app/presentation/components/workspace/ode/ode_mode_selector.py:78-152` confirms:

- The red-outlined pill (`border border-rose-300 !text-rose-700 bg-white`) at the top-right of the `"ĐIỀU KIỆN BAN ĐẦU CAUCHY"` panel is **NOT** a validation error badge, stale UI state, or frontend/backend mismatch.
- It is the **"Xóa điều kiện" (Clear conditions) action button** (`ode_mode_selector.py:118-125`), which is disabled/slate when `initial_condition` is empty and enabled with rose/red border styling whenever `initial_condition` is non-empty (`has_init_ic = True`). The `ic_input` field itself (`lines 137-141`) has no validation rules or error badges attached.
- **UX Critique:** Placing a bright rose/red outlined pill button directly opposite the `"ĐIỀU KIỆN BAN ĐẦU CAUCHY"` header visually mimics a validation error badge (especially alongside the red pushpin icon `📌` on the hint line below).

### Live Verification of Required Cases A–D

All 4 cases were tested both via `ODEState.build_problem_request()` -> `SolveProblemUseCase.execute()` and live in the running NiceGUI + `QWebEngineView` UI (with audit screenshots saved as `09`–`11`):

| Case | Input | Backend (`ODEState` + `ODEEulerCauchySolver`) | Live NiceGUI UI Observation | Classification |
|---|---|---|---|---|
| **Case A — Valid complete IVP** | `t^2*y'' + 4*t*y' + 2*y = 0`, `y(1) = 3, y'(1) = 0` | `SolutionStatus.SUCCESS`, `VerificationStatus.VERIFIED` (`second_order_ode_residual_and_dual_ic_zero_check`), exact $y(t) = \frac{6}{t} - \frac{3}{t^2}$. | Renders exact $\frac{6}{t} - \frac{3}{t^2}$, green `✓ Đã kiểm chứng toán học` badge, zero validation error cards (`09_audit_cauchy_case_a_valid.png`). **Minor defect:** Branch card badge `y(1) = 3, y'(1) = 0` is colored **amber (`bg-amber-8`)** due to `solution_view.py:331` checking `b.integration_constant_val is not None` (`None` in Euler–Cauchy IVP). | **PASS** (backend) / **FAIL** (amber branch badge) |
| **Case B — Missing initial condition** | `t^2*y'' + 4*t*y' + 2*y = 0`, `y(1) = 3` | `ODEState.build_problem_request()` raises `InvalidInputError("Bài toán Cauchy (IVP) cấp hai yêu cầu cung cấp đầy đủ hai điều kiện ban đầu...")`; direct solver returns `INVALID_INPUT`, `NOT_APPLICABLE`. No fabricated solution. | **Blocker 4:** `render_ode_validation_card()` (`ode_workspace.py:67-70`) matches `"cấp hai"` in the error string and renders an amber order-mismatch card titled **"Phương trình không đúng cấp"** with badge **"Cần chuyển không gian làm việc"** (`10_audit_cauchy_case_b_missing.png`). | **PASS** (backend) / **FAIL** (UI card misclassification) |
| **Case C — Mismatched initial points** | `t^2*y'' + 4*t*y' + 2*y = 0`, `y(1) = 3, y'(2) = 0` | `ODEState.build_problem_request()` raises `InvalidInputError("...y(1) và y'(2) không cùng điểm khởi đầu.")`; direct solver returns `INVALID_INPUT`, `NOT_APPLICABLE`. No Cauchy solution. | **Blocker 4:** Same `"cấp hai"` substring bug in `ode_workspace.py:68` misclassifies the error as **"Phương trình không đúng cấp"** / **"Cần chuyển không gian làm việc"**. | **PASS** (backend) / **FAIL** (UI card misclassification) |
| **Case D — Singular initial point** | `t^2*y'' + 4*t*y' + 2*y = 0`, `y(0) = 3, y'(0) = 0` | `SolutionStatus.CANNOT_SOLVE`, `VerificationStatus.NOT_APPLICABLE` (`singular_point_initial_condition`), explains $t_0 = 0$ is a singular point without claiming mathematical nonexistence. | Renders red `CANNOT_SOLVE` card with singular-point explanation (`11_audit_cauchy_case_d_singular.png`). *(Minor note: `a(t) = t^{2}` renders as raw LaTeX text inside `ui.label()`).* | **PASS** |

---

## 6. Mathematical Regression Matrix

All 16 scenarios were verified by inspecting exact assertions in `tests/unit/solvers/calculus/test_euler_cauchy_solver.py` and `tests/unit/presentation/test_ec1_ux1_euler_cauchy_presentation.py` (confirming assertions check symbolic equivalence via `sp.simplify`, interval endpoints/openness, branch count, realness, and verification status—not merely non-empty output) plus supplemental runtime checks.

| # | Scenario | Inspected Test & Key Assertions | Status |
|---|---|---|---|
| 1 | Distinct real roots | `test_section_8_a_sample_distinct_real_roots`: asserts `SUCCESS`, `VERIFIED`, `C1/t` & `C2/t**2`, 7 steps, `domain_interval == (0, oo)`. | **PASS** |
| 2 | Repeated real roots | `test_section_8_b_repeated_real_root`: asserts `SUCCESS`, `VERIFIED`, `t**2` & `log(t)` in `final_result`, and `\ln t` (no `\log`) in `test_ln_notation_positive_and_negative_domains`. | **PASS** |
| 3 | Complex-conjugate roots | `test_section_8_c_complex_conjugate_roots`, `test_complex_roots_with_nonzero_real_part`: asserts `cos(log(t))`, `sin(log(t))`, `"I" not in res.final_result`. | **PASS** |
| 4 | Negative interval | `test_section_8_d_negative_interval_sample_equation`, `test_negative_interval_repeated_root`, `test_negative_interval_fractional_power_no_complex`: asserts `log(-t)`, `sqrt(-t)` / `(-t)**(1/2)`, `"I" not in res.final_result`, `(-oo, 0)`. | **PASS** |
| 5 | Natural domain | `test_natural_domain_two_branches_independent_constants`: asserts 2 branches `(0, oo)` and `(-oo, 0)`, both `VERIFIED`, independent `C1, C2` and `C3, C4`. | **PASS** |
| 6 | Positive shifted interval | `test_explicit_valid_intervals_preserved_exactly` (`t > 2`, `1 < t < 5`, `t >= 2`, `t in (2, 5)`, `[1, 4]`): asserts exact `domain_interval`, `left_open`, `right_open`. | **PASS** |
| 7 | Negative shifted interval | `test_explicit_valid_intervals_preserved_exactly` (`t < -1`, `-5 < t < -1`, `t <= -1`, `(-5, -2]`): asserts exact `domain_interval`, `left_open`, `right_open`. | **PASS** |
| 8 | Interval crossing zero | `test_intervals_containing_or_crossing_zero_rejected` (`-1 < t < 1`, `t > -2`, `t < 1`): asserts `CANNOT_SOLVE`, `NOT_APPLICABLE`, `singular_point_interval`, empty `branch_solutions`. | **PASS** |
| 9 | Interval touching zero | `test_intervals_containing_or_crossing_zero_rejected` (`t >= 0`, `t <= 0`, `0 <= t < 3`, `-3 < t <= 0`, `[0, 2]`, `(-2, 0]`): asserts `CANNOT_SOLVE`, `singular_point_interval`. | **PASS** |
| 10 | Nonhomogeneous equation | `test_failure_nonhomogeneous_euler_cauchy`: asserts `CANNOT_SOLVE`, `NOT_APPLICABLE`, `nonhomogeneous` method, Vietnamese homogeneous-only warning. | **PASS** |
| 11 | Unresolved coefficients | `test_conservative_rejection_of_unresolved_coefficients_and_complex`, `test_unverified_is_real_none_coefficient_and_unresolved_discriminant`: asserts `CANNOT_SOLVE`, `euler_cauchy_unresolved_parameter`, `euler_cauchy_unverified_coefficient` (`UNVERIFIED`), `indicial_discriminant_unresolved` (`UNVERIFIED`). | **PASS** |
| 12 | Invalid Cauchy data | `test_failure_missing_one_cauchy_initial_condition`, `test_failure_mismatched_initial_points`, `test_nonreal_cauchy_inputs_raise_invalid_input_error`, `test_unresolved_symbolic_cauchy_inputs_fail_closed_without_typeerror`, `test_failure_initial_point_outside_requested_interval`. | **PASS** |
| 13 | Valid Cauchy IVP | `test_section_8_e_positive_domain_cauchy_ivp`, `test_negative_domain_cauchy_ivp`, `test_cauchy_ivp_repeated_root`, `test_cauchy_ivp_complex_roots`, `test_cauchy_ivp_respects_explicit_shifted_interval`: asserts exact `sp.simplify` equality and IC satisfaction. | **PASS** |
| 14 | Wronskian failure | `test_ode_verifier_fundamental_system_gate_direct` (`t, 2*t` -> `FAILED`; `t, t**2` on `(-1, 2)` -> `FAILED`), `test_solver_returns_unverified_when_fundamental_system_gate_unverified` -> `UNVERIFIED`. | **PASS** |
| 15 | Verifier `UNVERIFIED` | `test_mocked_verifier_status_propagates_to_steps_and_pedagogical_flow` (`UNVERIFIED`): asserts `SolutionStatus.UNVERIFIED`, no `VERIFIED` or `\equiv 0`, Stage 4 `is_completed is False`, `amber-7`. | **PASS** |
| 16 | Verifier `FAILED` | `test_mocked_verifier_status_propagates_to_steps_and_pedagogical_flow` (`FAILED`): asserts `SolutionStatus.DISCREPANCY_DETECTED`, no `\equiv 0`, Stage 4 `is_completed is False`, `rose-7`, `\not\equiv 0`. | **PASS** |

---

## 7. Cross-Module Regression Results

| # | Module / Area | Classification | Findings |
|---|---|---|---|
| 1 | Constant-coefficient 2nd-order ODE solver | **PASS** | `y'' - 3*y' - 4*y = 0` and `y'' + 5*y' + 6*y = 0` return `SUCCESS` / `VERIFIED`; `t^2*y'' + 4*t*y' + 2*y = 0` cleanly rejected (`CANNOT_SOLVE`). |
| 2 | Nonhomogeneous 2nd-order ODE solver | **PASS** | Both MUC (`y'' - 3*y' - 4*y = 3*exp(2*t)`) and VoP (`y'' + y = tan(t)`) and IVP (`y'' + 4*y = 4*t, y(0)=1, y'(0)=2`) return `SUCCESS` / `VERIFIED`. |
| 3 | Reduction-of-Order solver | **PASS** (solver) / **FAIL** (domain UI) | Solver `2*t^2*y'' + 3*t*y' - y = 0, y1 = 1/t` returns `SUCCESS` / `VERIFIED`. Domain UI triggers Blocker 1. |
| 4 | Existing ODE classification selector | **PASS** | 3-column grid (`grid-cols-1 md:grid-cols-3`) renders Homogeneous, Nonhomogeneous, and Euler–Cauchy cleanly alongside Reduction of Order and Wronskian buttons. |
| 5 | Operation Catalog | **PASS** | `OPERATIONS == 34`, `MAIN_OPERATIONS == 23`, secondary `== 11`; `ProblemType.ODE_EULER_CAUCHY` registered with `is_menu_card=False`. |
| 6 | Problem statement formatting | **PASS** | `format_problem_statement_latex()` formats `ĐỀ CHO:` with exact Leibniz derivatives and intervals; minor pre-existing dead code in `problem_statement.py:491-495` (unreachable after `return` at `487-489`). |
| 7 | Solution result rendering | **FAIL** | `solution_view.py:331` renders Cauchy IVP branch badge in `amber-8`; `solution_view.py:338` applies `polish_euler_cauchy_latex()` to *all* ODE branch cards (safe on `11\,t^2`, `21\,y`, `\log(x+1)`, though globally rewrites `\log` -> `\ln` on all ODE branch solutions). |
| 8 | Domain restriction rendering | **FAIL** | **Blocker 1 (`domain_view.py:19-27`):** `if "điểm kỳ dị" in res_lower` intercepts *all* ODE types, overwriting `(t - 2)*y'' + y' = 0` (`t = 2`) and `(t - 2)*y' + y = 0` (`t = 2`) with hardcoded `t = 0` and `a(t) = At²`, and breaks `ClassicalHomogeneous` (`x = 0)`) into unbalanced LaTeX `a(x) = 0 \iff x = 0) \implies \mathcal{D}_{\text{chính quy}} = (- \infty, 0)) \cup (0), + \infty)`. |
| 9 | General Solution / Cauchy mode switching | **FAIL** | **Blocker 2 (`ode_state.py`, `ode_workspace.py`):** `extract_second_order_ics_from_string()` skips interval clauses, causing example-chip clicks (`Miền âm`, `Nghiệm thực phân biệt`), mode switching, and Cauchy IVP requests to strip interval constraints like `, t < 0` and `, t > 2`. |
| 10 | Pedagogical flow for non-Euler–Cauchy ODEs | **PASS** | Verified via git diff inspection (`ode_pedagogical_enhancer.py` only added `ODE_EULER_CAUCHY` branch and `is_ode_problem_type` entry) and runtime checks on Const-Coeff Homog/Nonhomog/VoP/IVP & Reduction of Order (all 4 stages intact). |

---

## 8. Architecture and Clean Code Review

- **Clean Architecture & Dependency Direction:** **PASS.** `domain`, `input`, `solvers`, and `verification` have zero imports of `nicegui` or `plotly`. Presentation components invoke `SolveProblemUseCase.execute()` rather than solvers directly (except `problem_statement.py` calling `ode_parser` for display formatting, matching existing pattern).
- **Meaningful Architectural Risks (reported without refactoring):**
  1. **Monolithic Solver Size (`euler_cauchy_solver.py`, 2,037 lines):** `solve()` spans ~1,250 lines (`lines 207-1460`) and `_build_solution_steps()` spans ~575 lines (`lines 1461-2037`), mixing coefficient validation, domain metadata construction, Cramer solving, and Vietnamese prose generation.
  2. **Prose-Regex Presentation Coupling (`ode_pedagogical_enhancer.py`, 3,186 lines):** `_extract_euler_cauchy_context()` (`lines 2307-2412`) reverse-parses formatted Vietnamese step descriptions via regexes. Verified edge case: fractional coefficients like `\frac{1}{2}` fail the `[^,\\]+?` regex (`line 2343`), falling back to raw step equations. Structured solver metadata on `SolutionStep` or `SolutionResponse` would avoid prose parsing.
  3. **Duplicated ODE Routing Set (`app.py:344-354`):** Manually enumerating ODE `ProblemType`s instead of using `current_op.problem_type.is_ode` caused **Blocker 3** (`ODE_EULER_CAUCHY` omitted).
  4. **Fragile Substring Heuristics (`domain_view.py:19-27`, `ode_workspace.py:67-70`):** Matching `"điểm kỳ dị"` globally and `"cấp hai"` on validation messages caused **Blockers 1 and 4**.
  5. **Minor Code Hygiene (`ode_workspace.py:540-546`):** Duplicate `keydown.enter` event bindings on `eq_input` and `var_input`.

---

## 9. UI/UX Inspection Results

Inspected existing screenshots `01`–`08`, ran live headless NiceGUI (`QWebEngineView` + `QT_QPA_PLATFORM=offscreen`) across interactive workflows, and captured focused audit screenshots `09`–`11`.

| State / Check | Result | Notes |
|---|---|---|
| 1. Workspace before solving (`01`) | **PASS** | Clean 3-column card layout; minor truncated label `"Biến số độc..."` at `w-36`. |
| 2. Distinct real roots (`02`) | **PASS** | Crisp KaTeX/MathML rendering, exact $C_1/t + C_2/t^2$, Stage 1 expanded, Stages 2–4 collapsed. |
| 3. Repeated real roots (`03`) | **PASS** | Displays $C_1 t^2 + C_2 t^2 \ln t$ consistently with `\ln t` (no `\log`). |
| 4. Complex-conjugate roots (`04`) | **PASS** | Displays $C_1 \cos(\ln t) + C_2 \sin(\ln t)$ with zero imaginary unit `i`. |
| 5. Negative-domain solution (`05`) | **PASS** (static) / **FAIL** (chip click) | Solution renders cleanly on $t < 0$ using $(-t)^m$; clicking `"Miền âm"` chip live strips `, t < 0` (**Blocker 2**). |
| 6. General Solution mode (`06`) | **PASS** | Displays `"Nghiệm tổng quát"` badge and Stage 3 subtitle with zero Cauchy leakage. |
| 7. Cauchy IVP mode (`07`, `09`) | **FAIL** (badge color) | Renders `y(t) = 6/t - 3/t^2` and green `✓ Đã kiểm chứng toán học`, but branch badge `y(1) = 3, y'(1) = 0` is **amber (`bg-amber-8`)**, and rose-outlined `Xóa điều kiện` button visually resembles a validation badge. |
| 8. All 4 stages expanded (`08`, live) | **PASS** | Live test confirmed `init=1`, `Mở rộng tất cả` -> `4`, `Thu gọn tất cả` -> `0`; slight vertical scrollbar on Stage 2 summary box for fractions. |
| 9. Missing Cauchy condition (`10`) | **FAIL** | No fabricated solution, **but** misclassified as `"Phương trình không đúng cấp"` / `"Cần chuyển không gian làm việc"` (**Blocker 4**). |
| 10. Valid Cauchy IVP (`09`) & Singular `t0=0` (`11`) | **PASS** (Case D backend/card) | Case D explains `t0 = 0` singularity cleanly; minor raw `t^{2}` inside `ui.label()`. |
| Viewports & Overflow | **PASS** (desktop/tablet) | 1280px (`scrollW=1265 == clientW=1265`) and 768px (`scrollW=753 == clientW=753`) have zero horizontal overflow; 480px narrow mobile shows 36px overflow (`501 > 465`). |

---

## 10. Complete Testing Evidence

All test suites and quality gates were executed directly against the current working tree (no code modifications performed):

| Command | Exit Code | Result | Duration | Warnings |
|---|---|---|---|---|
| `uv run pytest -q tests/unit/solvers/calculus/test_euler_cauchy_solver.py` | `0` | `76 passed` | `4.24s` | None |
| `uv run pytest -q tests/unit/presentation/test_ec1_ux1_euler_cauchy_presentation.py` | `0` | `11 passed` | `2.07s` | None |
| `uv run pytest -q tests/unit/solvers/calculus/` | `0` | `571 passed` | `81.44s` | None |
| `uv run pytest -q tests/unit/presentation/` | `0` | `629 passed` | `56.07s` | 1 pre-existing warning |
| `uv run pytest -q` | `0` | `1403 passed` | `162.95s` | 2 pre-existing warnings |
| `uv run ruff check src/ tests/` | `0` | `All checks passed!` | — | None |
| `git diff --check` | `0` | Clean | — | None |
| `uv lock --check` | `0` | `Resolved 90 packages in 1ms` | — | None |

---

## 11. Warnings, Documentation Readiness, and Unresolved Issues

### Warnings Attribution (Pre-Existing Only)
Zero warnings were introduced by Euler–Cauchy (`EC1`, `EC1-R1`, `UX1`). Both full-suite warnings are pre-existing:
1. `tests/unit/presentation/test_analysis_service.py::test_2d_plot_sampling_arbitrary_viewport` — `RuntimeWarning: invalid value encountered in sqrt` (NumPy out-of-domain 2D plot sampling test).
2. `tests/unit/test_windows_metadata_and_signing.py::test_setup_test_shutdown_endpoint_security_and_activation` — `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.`

### Documentation & Hygiene Audit
- **`pyproject.toml`:** Version remains `0.2.0` (`PASS`).
- **`CHANGELOG.md`:** `[Unreleased]` accurately documents homogeneous second-order Euler–Cauchy (`ODEEulerCauchySolver`), all 3 root cases, positive/negative domains, Cauchy IVPs for $t_0 \ne 0$, natural-domain branching, and nonhomogeneous rejection (`PASS`). *(Note: EC1-R1 interval/Wronskian hardening and UX1 polish are not explicitly broken out under `[Unreleased]` yet).*
- **`README.md`, `README.vi.md`, `docs/USER_GUIDE.md`:** Do not advertise unsupported nonhomogeneous or higher-order Euler–Cauchy features (`PASS`; Euler–Cauchy can be documented in User Guide / README in a future docs pass).
- **Secrets / Absolute Paths / Temp Artifacts:** `grep` across all modified/new source files confirmed zero API keys, secrets, or local absolute paths (`PASS`).
- **Minor Report Drift:** `reports/EC1_IMPLEMENTATION_REPORT.md` Section 9 lists example `t^2*y'' + 4*t*y' + 2*y = 0, y(1) = 3, y'(1) = -3` and `x^2*y'' - 2*x*y' + 2*y = 0`, whereas `operation_catalog.py:422-428` contains `y(1)=3, y'(1)=0` and `t < 0` negative-domain example.

---

## 12. Complete Changed and Untracked File Inventory

### Modified Tracked Files (20)
1. `CHANGELOG.md` (+15)
2. `src/math_app/domain/models.py` (+2)
3. `src/math_app/input/ode_parser.py` (+394/-4)
4. `src/math_app/main.py` (+4)
5. `src/math_app/presentation/components/domain_view.py` (+41/-2)
6. `src/math_app/presentation/components/ode_pedagogical_enhancer.py` (+745/-19)
7. `src/math_app/presentation/components/ode_staged_step_viewer.py` (+54/-23)
8. `src/math_app/presentation/components/operation_catalog.py` (+19)
9. `src/math_app/presentation/components/problem_statement.py` (+12/-1)
10. `src/math_app/presentation/components/solution_view.py` (+55/-12)
11. `src/math_app/presentation/components/workspace/ode/ode_classification_selector.py` (+41/-2)
12. `src/math_app/presentation/components/workspace/ode/ode_method_selector.py` (+14)
13. `src/math_app/presentation/components/workspace/ode/ode_state.py` (+36/-2)
14. `src/math_app/presentation/components/workspace/ode/ode_workspace.py` (+6/-1)
15. `src/math_app/solvers/calculus/ode/__init__.py` (+2)
16. `src/math_app/verification/calculus/ode_verifier.py` (+183/-3)
17. `tests/unit/presentation/test_design_system_and_catalog.py` (+2/-1)
18. `tests/unit/presentation/test_ode_pedagogical_solution_flow.py` (+79)
19. `tests/unit/presentation/test_operation_catalog.py` (+4/-4)
20. `tests/unit/presentation/test_ux3_1_ode_workspace.py` (+2/-2)

### Newly Created Source Files (1)
- `src/math_app/solvers/calculus/ode/euler_cauchy_solver.py` (2,037 lines)

### Newly Created Test Files (2)
- `tests/unit/solvers/calculus/test_euler_cauchy_solver.py` (1,108 lines)
- `tests/unit/presentation/test_ec1_ux1_euler_cauchy_presentation.py` (336 lines)

### Reports & Patch Artifacts (7)
- `reports/EC1_IMPLEMENTATION_REPORT.md`
- `reports/EC1_R1_IMPLEMENTATION_REPORT.md`
- `reports/EC1_UX1_IMPLEMENTATION_REPORT.md`
- `reports/ODE_FINAL_INTEGRATION_REVIEW.md` *(this report)*
- `reports/ec1_euler_cauchy.patch` (2,405 lines, 16 files — EC1 baseline)
- `reports/ec1_euler_cauchy_r1.patch` (4,723 lines, 19 files — EC1-R1 snapshot)
- `reports/ec1_euler_cauchy_ux1.patch` (1,710 lines, 8 files — UX1 delta)

### Screenshots (11)
- Pre-existing UX1 screenshots (`01`–`08`):
  - `reports/screenshots/01_euler_cauchy_workspace_before_solving.png`
  - `reports/screenshots/02_distinct_roots_solution.png`
  - `reports/screenshots/03_repeated_roots_solution.png`
  - `reports/screenshots/04_complex_roots_solution.png`
  - `reports/screenshots/05_negative_domain_solution.png`
  - `reports/screenshots/06_general_solution_mode.png`
  - `reports/screenshots/07_cauchy_ivp_mode.png`
  - `reports/screenshots/08_pedagogical_flow_all_4_stages.png`
- Audit verification screenshots (`09`–`11`):
  - `reports/screenshots/09_audit_cauchy_case_a_valid.png`
  - `reports/screenshots/10_audit_cauchy_case_b_missing.png`
  - `reports/screenshots/11_audit_cauchy_case_d_singular.png`

### Unrelated User Files
- **None.** All modified and untracked files belong exclusively to `ODE-EC1`, `ODE-EC1-R1`, `ODE-UX1`, and `ODE-FINAL`.

---

## 13. Current Git Status

- **Current Branch:** `feature/euler-cauchy-solver`
- **Tracking / Relationship to `origin/main`:** `0 ahead / 0 behind` `origin/main` (`c2f3f1d`)
- **Git State Mutation Check:** Zero staging, zero commits, zero pushes, zero merges/rebases/tags/resets executed.

```text
## feature/euler-cauchy-solver...origin/main
 M CHANGELOG.md
 M src/math_app/domain/models.py
 M src/math_app/input/ode_parser.py
 M src/math_app/main.py
 M src/math_app/presentation/components/domain_view.py
 M src/math_app/presentation/components/ode_pedagogical_enhancer.py
 M src/math_app/presentation/components/ode_staged_step_viewer.py
 M src/math_app/presentation/components/operation_catalog.py
 M src/math_app/presentation/components/problem_statement.py
 M src/math_app/presentation/components/solution_view.py
 M src/math_app/presentation/components/workspace/ode/ode_classification_selector.py
 M src/math_app/presentation/components/workspace/ode/ode_method_selector.py
 M src/math_app/presentation/components/workspace/ode/ode_state.py
 M src/math_app/presentation/components/workspace/ode/ode_workspace.py
 M src/math_app/solvers/calculus/ode/__init__.py
 M src/math_app/verification/calculus/ode_verifier.py
 M tests/unit/presentation/test_design_system_and_catalog.py
 M tests/unit/presentation/test_ode_pedagogical_solution_flow.py
 M tests/unit/presentation/test_operation_catalog.py
 M tests/unit/presentation/test_ux3_1_ode_workspace.py
?? reports/
?? src/math_app/solvers/calculus/ode/euler_cauchy_solver.py
?? tests/unit/presentation/test_ec1_ux1_euler_cauchy_presentation.py
?? tests/unit/solvers/calculus/test_euler_cauchy_solver.py
```

Recent `git log --oneline --decorate -10`:
```text
c2f3f1d (HEAD -> feature/euler-cauchy-solver, tag: v0.2.0, origin/main, origin/HEAD) Merge pull request #12 from TqvNoCode/test
5ec90b4 (origin/test, test) Merge remote-tracking branch 'origin/test' into test
7abb4fb docs: add README table of contents, fix documentation inconsistencies, and archive historical roadmap
b8033be Delete reports directory
3e030d2 Merge remote-tracking branch 'origin/main' into test
8fafdb0 chore(release): prepare MathWeave Studio v0.2.0
8edcf62 feat(ode): add second-order nonhomogeneous solvers, singular Cauchy extension verification, and fail-closed domain validation
0921d9e feat(presentation): introduce minimalist pedagogical workspaces, catalog, and design system
dba471a docs: add release deployment report for v0.1.1
269ac02 docs: update README with v0.1.1 direct release asset links
```

---

## 14. Remaining Risks

1. **Cross-module domain corruption (Blocker 1):** If committed/merged as-is, every non-Euler–Cauchy ODE with a singular point (Reduction of Order, First-Order Linear, Classical Homogeneous) displays mathematically wrong singular-point explanations and broken LaTeX (`0)`).
2. **Silent interval loss in UI (Blocker 2):** Users clicking Euler–Cauchy negative/positive interval chips or entering shifted intervals in Cauchy IVP mode silently lose their interval restriction before reaching the solver.
3. **Broken deep-link routing (Blocker 3):** Direct navigation to `/?op=ode_euler_cauchy` opens the wrong workspace (`Biểu thức toán học f(x)`).
4. **Confusing IVP validation & badge colors (Blocker 4):** Missing or mismatched Cauchy initial conditions render `"Phương trình không đúng cấp"` instead of an initial-condition error card, and verified Cauchy IVP branch badges render amber instead of green.
5. **Non-blocking maintainability risks:** Regex reverse-parsing of prose in `_extract_euler_cauchy_context()`, large monolithic `solve()` in `euler_cauchy_solver.py`, hardcoded `t`/`t_0` in Stage 3 Cauchy prose when `target_var == "x"`, and 36px horizontal overflow at 480px viewport width.

---

## 15. Explicit Final Decision: **`NOT_READY`**

The working-tree implementation is **NOT_READY** for commit or merge due to **4 concrete integration and cross-module regression blockers** in the presentation/workspace layer. The mathematical core (`ODEEulerCauchySolver`, `ode_parser.py`, `ODEVerifier`) requires **no changes**.

### Exact Blockers

1. **Blocker 1 — Global `"điểm kỳ dị"` Hijacking (`src/math_app/presentation/components/domain_view.py:19-27`):** Broad substring match corrupts Reduction of Order, First-Order Linear, and Classical Homogeneous ODE domain displays (wrong singular point `t = 0`, hardcoded `a(t) = At²`, unbalanced parenthesis `x = 0)`).
2. **Blocker 2 — Interval Stripping in Workspace & State (`src/math_app/presentation/components/workspace/ode/ode_workspace.py:338-357`, `src/math_app/presentation/components/workspace/ode/ode_state.py:421,443,691,755`):** Direct calls to `extract_second_order_ics_from_string()` without `extract_interval_from_string()` strip `, t < 0` / `, t > 0` on example chips and strip shifted intervals on mode switching and Cauchy IVP submission.
3. **Blocker 3 — Missing Deep-Link Routing (`src/math_app/presentation/app.py:344-354`):** `ProblemType.ODE_EULER_CAUCHY` is missing from `is_ode_op`, causing `/?op=ode_euler_cauchy` to render the generic calculus form.
4. **Blocker 4 — Cauchy IVP Validation Card Misclassification & Amber Branch Badge (`src/math_app/presentation/components/workspace/ode/ode_workspace.py:67-70`, `src/math_app/presentation/components/solution_view.py:330-334, 382-391`):** Error messages mentioning `"cấp hai"` (`Case B` missing IC, `Case C` mismatched base points) are misclassified as `"Phương trình không đúng cấp"` / `"Cần chuyển không gian làm việc"`, and verified Cauchy IVP branch badges render in `amber-8` because `integration_constant_val` is `None`.

### Proposed Smallest Corrective Milestone: **`ODE-FINAL-R1`** (Presentation & Routing Only)

Scope strictly to 5 presentation/state files + targeted regression tests (zero changes to `euler_cauchy_solver.py`, `ode_parser.py`, or `ode_verifier.py`):

1. **`domain_view.py`:** Scope `0a` Euler–Cauchy handler strictly to Euler–Cauchy singular-point strings (and dynamic `pt_var`, not hardcoded `t`), preserving original handling for Reduction of Order, First-Order Linear, and Classical Homogeneous ODEs.
2. **`ode_state.py` & `ode_workspace.py`:** Extract interval constraints via `extract_interval_from_string()` *before* `extract_second_order_ics_from_string()`, preserving `, t < 0` / `, t > 0` / shifted intervals across example chips, `with_mode()`, and `build_problem_request()`.
3. **`app.py`:** Replace the hardcoded `is_ode_op` set with `current_op.problem_type.is_ode` (which already includes `ProblemType.ODE_EULER_CAUCHY` via `_ODE_PROBLEM_TYPES`).
4. **`ode_workspace.py` & `solution_view.py`:** Tighten `render_ode_validation_card()` and `render_solution_view()` order-mismatch heuristics so Cauchy IVP errors (`"điều kiện ban đầu"`, `"cùng điểm khởi đầu"`) render as standard input-validation errors rather than `"Phương trình không đúng cấp"`; color verified Cauchy IVP branch badges (`b.verification.status == VERIFIED`) as `"positive"` instead of `"amber-8"` (and optionally neutralize `"Xóa điều kiện"` styling in `ode_mode_selector.py` so it isn't mistaken for an error badge).
5. **Regression Tests:** Add unit tests covering `format_domain_condition()` for non-Euler–Cauchy ODEs, `/?op=ode_euler_cauchy` routing, interval preservation on `ODEState` mode switches/IVP requests/example chips, and Cauchy IVP validation card classification for Cases B & C.
