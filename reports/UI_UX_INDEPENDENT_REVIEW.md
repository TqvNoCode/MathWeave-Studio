# Báo Cáo Rà Soát Độc Lập UI/UX (Independent Adversarial Review Round)

**Dự án:** MathWeave Studio (v0.2.0 / Euler–Cauchy Integration Track)
**Nhánh làm việc:** `feat/unified-math-ui-ux` (khởi tạo từ commit backup `3fdec2abf4071795a930ecaf12d31df8d02c3ad8` trên `feature/euler-cauchy-solver`)
**Đơn vị đánh giá độc lập:** Subagent `code-reviewer` (`f0eef423-d549-400a-bd40-8f09188ae65e`)

---

## 1. Phạm vi & Trọng tâm đánh giá

Vòng rà soát độc lập tập trung trả lời bốn câu hỏi trọng tâm theo yêu cầu:

1. **Các module cũ (Đạo hàm, Tích phân, Giới hạn, Đại số, Ma trận) có bị mất tính đơn giản không?**
2. **Các module Phương trình vi phân (ODE) có bị giảm chiều sâu sư phạm hoặc mất tính trung thực toán học không?**
3. **Việc dùng chung các component trong `shared/` và `shell/` có tạo ra trải nghiệm gượng ép hay trùng lặp giao diện không?**
4. **Ranh giới Clean Architecture, cô lập trạng thái (state isolation) và tính toàn vẹn của lõi toán học có được bảo vệ tuyệt đối không?**

---

## 2. Kết luận sơ bộ từ Reviewer & Phân loại xử lý

Reviewer độc lập đưa ra kết luận ban đầu **`REQUEST CHANGES`** với **2 lỗi Nghiêm trọng (Critical)**, **7 vấn đề Trung bình (Moderate)** và một số điểm **Nhỏ (Minor)**. Dưới đây là tổng hợp đầy đủ từng phát hiện, phân tích đối chiếu với hệ thống kiểm thử hiện hành và trạng thái xử lý sau hiệu chỉnh.

### 2.1. Các lỗi Nghiêm trọng (Critical)

| ID | Vị trí | Phát hiện từ Reviewer | Xử lý & Kết quả xác minh |
|---|---|---|---|
| **C1** | `src/math_app/presentation/components/workspace/ode/ode_workspace.py` | Trong `handle_submit()` cho ODE cấp 1, khi bộ nhận dạng phát hiện dạng phương trình khác với `state.classification`, lệnh gọi `state.with_classification(...)` thiếu `preserve_equation=True`, làm ghi đè phương trình người dùng vừa nhập bằng phương trình mẫu mặc định (ví dụ `y' = t*(y^2 - 1)` bị đổi về `y' = 2*t*y`). | **Đã sửa (Fixed):** Bổ sung `preserve_equation=True` khi đồng bộ phân loại lúc submit. Bổ sung unit test hồi quy `test_first_order_auto_align_preserves_user_equation_on_submit` trong [test_ui_ux_unification.py](../tests/unit/presentation/test_ui_ux_unification.py). |
| **C2** | `src/math_app/presentation/components/ode_pedagogical_enhancer.py` | Các builder ODE ngoài Euler–Cauchy và hàm `_synthesize_verification_step()` từng gán cứng Giai đoạn 4 là `is_completed=True`, `badge_color="emerald-7"`, `R(t) = 0`; đặc biệt `_build_wronskian_flow()` luôn xuất `W \not\equiv 0` ngay cả khi hai hàm phụ thuộc tuyến tính ($W = 0$). | **Đã sửa (Fixed):** Xây dựng `_resolve_stage4_stage_meta()`, `_build_stage4_summary()`, `_is_wronskian_dependent()` và cập nhật `_synthesize_verification_step()` để phản ánh trung thực `VerificationStatus` (`FAILED` $\rightarrow$ `rose-7` / chưa hoàn tất, `UNVERIFIED` $\rightarrow$ `amber-7`, Wronskian $W=0$ $\rightarrow$ $W(y_1, y_2) \equiv 0$). Kiểm chứng bằng `test_ode_stage4_verification_honesty_across_non_euler_builders`. |

---

### 2.2. Các vấn đề Trung bình (Moderate)

| ID | Vị trí | Phát hiện từ Reviewer | Phân loại & Xử lý |
|---|---|---|---|
| **M1** | `sticky_nav_bar.py`, `app.py`, `ode_workspace.py` | `render_sticky_nav_bar()` lặp lại `math_icon` và badge lĩnh vực ngay phía trên `render_workspace_header()`, đồng thời thanh sticky nav bị đứng nguyên tiêu đề cũ khi chuyển loại ODE trong workspace (ví dụ sang Euler–Cauchy). | **Đã sửa (Fixed):** Tinh gọn [sticky_nav_bar.py](../src/math_app/presentation/components/shell/sticky_nav_bar.py) (bỏ badge/khung lặp), thêm callback `on_title_ready` kết nối với `on_title_change` của [ode_workspace.py](../src/math_app/presentation/components/workspace/ode/ode_workspace.py) qua [app.py](../src/math_app/presentation/app.py). Kiểm chứng bằng `test_sticky_nav_bar_deduplication_and_title_sync`. |
| **M2** | `src/math_app/presentation/app.py` | Tham số URL (`eq`, `ic`, `solve`) bị giữ trong closure của `main_page()`, có thể rò rỉ sang dạng toán khác sau khi người dùng quay về Catalog (`switch_to_catalog`). | **Đã sửa (Fixed):** Dùng `pending_eq`, `pending_ic`, `pending_auto_solve` dạng một lần (one-shot), giải phóng ngay khi render Screen B và khi chuyển màn hình. Kiểm chứng bằng `test_query_params_do_not_leak_after_returning_to_catalog`. |
| **M3** | `ode_guided_classification_view.py` | Giao diện ODE cấp 1 không hiển thị nút bấm chọn thủ công phương pháp phụ (`Tách biến`, `Vi phân toàn phần`, `Thuần nhất cấp 1`, `Thừa số tích phân`). | **Giữ nguyên có chủ đích (Contract-Preserved):** Bộ kiểm thử hiện hành [test_ux3_7_1_first_order_interface_simplification.py](../tests/unit/presentation/test_ux3_7_1_first_order_interface_simplification.py) nghiêm cấm các nút chọn phương pháp phụ dạng này trong luồng thường để tránh rối người mới học; hệ thống tự nhận dạng và phân nhánh đúng ở backend. |
| **M4** | `src/math_app/presentation/components/step_viewer.py` | Các phép toán 1 bước có tiền tố vế trái trong đáp số cuối (như `\det(A) = -2`, `f'(x) = 2x`) chưa được nhận diện trùng lặp với `latex_after`, dẫn tới thẻ `"Kết luận:"` dư thừa. | **Đã sửa (Fixed):** Bổ sung `_strip_outer_box()` đếm ngoặc cân bằng, chuẩn hóa `$...$`/`\,` và `_is_single_step_duplicate()` so sánh theo cả công thức đầy đủ lẫn vế phải sau dấu `=`. Kiểm chứng bằng `test_single_step_dedup_with_lhs_prefix_and_quasar_badge_mapping`. |
| **M5** | `src/math_app/presentation/components/ode_staged_step_viewer.py` | Một số `ui.badge(color=...)` truyền tên màu Tailwind (`emerald-7`, `rose-7`, `slate-400`, `slate-100`, `slate-200`) không thuộc bảng màu Quasar. | **Đã sửa (Fixed):** Giữ nguyên chuỗi trong `ODEStageSummary.badge_color` để bảo toàn hợp đồng test `test_ode_pedagogical_solution_flow.py`, đồng thời thêm `_QUASAR_BADGE_COLOR_MAP` & `_to_quasar_badge_color()` tại lớp UI để ánh xạ sang màu Quasar chuẩn (`green-7`, `red-7`, `grey-6`, `grey-3`, `grey-4`). |
| **M6** | `ode_workspace.py` | Khi đang ở chế độ Tổng quát (`ODEMode.GENERAL`), bấm chip ví dụ `"Bài toán Cauchy"` của Euler–Cauchy giữ nguyên chế độ Tổng quát và lọc bỏ điều kiện đầu thay vì tự ép đổi sang chế độ Cauchy. | **Giữ nguyên có chủ đích (Contract-Preserved):** Quy ước này được bảo vệ bởi [test_ode_final_r1_integration_fixes.py](../tests/unit/presentation/test_ode_final_r1_integration_fixes.py) nhằm tránh thay đổi bất ngờ chế độ làm việc hiện tại của người dùng khi thử phương trình từ chip ví dụ. |
| **M7** | `src/math_app/presentation/components/workspace/variable_selector.py` | `get_variable_pool_for_operation()` rơi vào nhánh mặc định `["x", "y", "t"]` cho ODE, cho phép chọn nhầm `y` (hàm phụ thuộc) làm biến độc lập. | **Đã sửa (Fixed):** Thêm nhánh riêng `if op.problem_type.is_ode: return ["t", "x"]`. Kiểm chứng bằng `test_ode_variable_selector_excludes_dependent_variable_y`. |

---

### 2.3. Các điểm Nhỏ (Minor) đã được xử lý đồng bộ

1. **Khả năng truy cập bàn phím cho Example Chips ([example_chips.py](../src/math_app/presentation/components/shared/example_chips.py)):** Escape `aria-label` bằng `html.escape(..., quote=True)` và bổ sung `keydown.space.prevent`.
2. **Gửi bài bằng phím Enter & Reset ghi đè thủ công ODE ([ode_workspace.py](../src/math_app/presentation/components/workspace/ode/ode_workspace.py)):** Hỗ trợ `keydown.enter` trên `ic_input_ref[0]` và reset `is_manual_override = False` trong `handle_switch_order()`.
3. **Dọn mã chết & gắn sự kiện động ([app.py](../src/math_app/presentation/app.py)):** Xóa đoạn reset `initial_condition`/`y1` thừa ở nhánh non-ODE, gộp đăng ký sự kiện thông qua `_bind_dynamic_input()` + `_bound_ctrl_ids` để tránh đăng ký trùng và hỗ trợ Enter/xóa kết quả cũ cho các ô tọa độ động của Tích phân mặt & Tích phân khối.
4. **Tái sử dụng Empty State & Giữ an toàn kiểm thử responsive ([ode_staged_step_viewer.py](../src/math_app/presentation/components/ode_staged_step_viewer.py)):** Tái sử dụng `render_empty_state_card()`, di chuyển import lên đầu file chuẩn PEP 8, và giữ `min-w-0 sm:min-w-[240px]` để vừa không tràn màn hình 360px vừa vượt qua kiểm tra `test_responsive_step_header_classes`.

---

## 3. Đánh giá sau hiệu chỉnh theo 4 tiêu chí trọng tâm

- **Tính đơn giản của module cũ:** Đạt — Đạo hàm, Tích phân, Giới hạn, Đại số và Ma trận giữ nguyên bố cục một thẻ gọn nhẹ, không có thành phần ODE dư thừa, thanh điều hướng sticky hết lặp icon/badge và phép toán 1 bước không bị lặp thẻ Kết luận.
- **Chiều sâu sư phạm ODE:** Đạt — Không chỉ bảo toàn chiều sâu của Euler–Cauchy và PTVP cấp 1/cấp 2, sửa lỗi C1 & C2 giúp hệ thống không bao giờ làm mất phương trình của người học hoặc báo kiểm chứng thành công giả tạo.
- **Trải nghiệm component dùng chung:** Tự nhiên — Các primitive `workspace_header`, `action_labels`, `example_chips`, `feedback_cards`, `status_badge` đồng nhất phong cách trực quan nhưng vẫn tôn trọng đặc thù từng nhóm bài toán.
- **Lõi toán học & Clean Architecture:** Bảo toàn 100% — Không có thay đổi nào chạm tới `src/math_app/solvers/`, `src/math_app/input/`, `src/math_app/verification/`, `src/math_app/domain/` hay `pyproject.toml`.
