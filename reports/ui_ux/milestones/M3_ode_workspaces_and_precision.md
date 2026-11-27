# Milestone 3 Report — First-Order & Second-Order ODE Workspaces & Mathematical Precision

**Milestone:** M3  
**Status:** Completed  
**Branch:** `feat/unified-math-ui-ux`

## 1. Scope & Objectives
Improve beginner clarity, progressive disclosure, mathematical notation precision, live detection, and mobile responsiveness across First-Order and Second-Order ODE workflows while preserving all protected solver/parser/verifier contracts and existing pedagogical explanations.

## 2. Changed Files
- `src/math_app/presentation/components/workspace/ode/first_order_classifier.py`: Replaced `$g(t) \neq 0$` with `$g(t) \not\equiv 0$` and clarified non-identically-zero prose (`"Vế phải không triệt tiêu (không đồng nhất bằng không)"`).
- `src/math_app/presentation/components/workspace/ode/ode_classification_selector.py`: Updated nonhomogeneous badge to `"g(t) ≢ 0"`, added visible focus rings, `aria-label`s, and equal-height button alignment (`h-full flex flex-col justify-between` + `mt-auto`).
- `src/math_app/presentation/components/workspace/ode/ode_state.py`: Updated `ODEClassification.SECOND_ORDER_NONHOMOGENEOUS.display_label` to `"Không thuần nhất: g(t) ≢ 0"`.
- `src/math_app/presentation/components/workspace/ode/ode_guided_classification_view.py`: Implemented progressive disclosure on `BƯỚC 3: CƠ SỞ VÀ LÝ LẼ PHÂN LOẠI TOÁN HỌC:` via a keyboard-accessible toggle button (`"Xem lý lẽ chi tiết"` / `"Ẩn lý lẽ chi tiết"`, `aria-expanded`), keeping explanations accessible on demand without adding `ui.expansion` elements; softened pre-solve card contrast weight.
- `src/math_app/presentation/components/workspace/ode/ode_mode_selector.py`: Added focus-visible rings and `min-h-[40px]` touch targets while preserving `"border-rose-300"` clear button state.
- `src/math_app/presentation/components/workspace/ode/ode_workspace.py`:
  - Adopted `render_workspace_header()`, `render_example_chips()`, `render_loading_card()`, `render_feedback_card()`, and `get_primary_action_spec()` (`GIẢI PHƯƠNG TRÌNH VI PHÂN`, `GIẢI PHƯƠNG TRÌNH VI PHÂN CẤP 2`, `TÍNH ĐỊNH THỨC WRONSKIAN`).
  - Added `detect_second_order_classification()` reusing read-only `ode_parser` functions to render a live non-intrusive sync banner (`so_detect_container`) when an equation matches another Second-Order family or Order 1, while keeping all manual classification cards and overrides intact.
  - Changed variable label to concise untruncated `"Biến số"` (`w-full sm:w-36`) and `eq_input` to `w-full sm:flex-1 sm:min-w-[220px]`.
  - Cleared stale `results_container` on `eq_input`, `var_input`, `y1_input`, `ic_input` changes and disabled `solve_btn` while submitting.
- `tests/unit/presentation/test_ode_screen_b.py` & `tests/unit/presentation/test_ux3_3_second_order_workspace.py`: Updated exact-equality button assertions to match module-specific primary action labels.

## 3. Verification Results
- Ran all 12 ODE presentation suites (`test_ec1_ux1`, `test_ode_final_r1`, `test_ux3_*`, `test_ode_screen_b`, `test_first_order_classifier`) + `ruff check` on `ode/` and updated tests.
