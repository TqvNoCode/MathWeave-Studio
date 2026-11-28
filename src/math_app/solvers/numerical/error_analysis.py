"""Local one-step defect, global error, and Richardson step-halving analysis for Explicit Euler."""

from __future__ import annotations

from math_app.domain.numerical_ode import (
    NumericalErrorAnalysis,
    NumericalODEOrder,
    NumericalODERequest,
    NumericalODEResponse,
    NumericalODEStatus,
    StepHalvingEstimate,
    StepHalvingPoint,
)
from math_app.solvers.numerical.euler_engine import (
    FirstOrderEulerAdapter,
    SecondOrderEulerAdapter,
    integrate_explicit_euler,
)
from math_app.solvers.numerical.expression_adapter import (
    compile_safe_real_evaluator,
    parse_numeric_scalar,
    parse_numerical_ode_equation,
)
from math_app.solvers.numerical.time_grid import build_time_grid, subdivide_time_grid_half

_LOCAL_DEFECT_CONVENTION = (
    "Ứng dụng sử dụng quy ước sai số chặt cục bộ một bước chưa chuẩn hóa (unnormalized one-step local defect) δ_{n+1}. "
    "Đại lượng này đo phần dư sau đúng một bước từ nghiệm chính xác và có bậc O(h_n²); "
    "khác với sai số chặt cục bộ chuẩn hóa τ_{n+1} = δ_{n+1} / h_n = O(h_n) trong một số giáo trình giải tích số."
)

_STABILITY_NOTE = (
    "Explicit Euler có bậc hội tụ lý thuyết là O(h²) cho sai số chặt cục bộ chưa chuẩn hóa và O(h) cho sai số toàn cục "
    "dưới các giả thiết nghiệm đủ trơn (C²) và bài toán ổn định. Phương pháp KHÔNG ổn định với mọi bước nhảy h hay mọi phương trình: "
    "với phương trình cứng y' = λy (λ < 0) cần điều kiện |1 + hλ| ≤ 1, còn với hệ dao động như y'' = -y phương pháp không bảo toàn năng lượng."
)


class ExplicitEulerErrorAnalyzer:
    """Computes consistent local/global error summaries and step-halving (h/2) Richardson estimates."""

    def _compute_step_halving(
        self,
        request: NumericalODERequest,
        response: NumericalODEResponse,
    ) -> StepHalvingEstimate:
        """Run an independent Explicit Euler solve on a halved grid (h/2) and apply Richardson scaling p=1."""
        coarse_h = response.step_size
        fine_h = coarse_h / 2.0

        if 2 * response.total_steps > request.max_steps:
            return StepHalvingEstimate(
                available=False,
                coarse_step_size=coarse_h,
                fine_step_size=fine_h,
                notes=(
                    f"Không thể tính ước lượng giảm nửa bước h/2 vì lưới mịn cần {2 * response.total_steps:,} bước, "
                    f"vượt quá giới hạn an toàn {request.max_steps:,} bước."
                ),
            )

        try:
            t0_dec, t0_flt = parse_numeric_scalar(request.t0, "t₀")
            _, y0_flt = parse_numeric_scalar(request.y0, "y₀")
            t_end_dec, _ = parse_numeric_scalar(request.t_end, "T")
            h_dec, _ = parse_numeric_scalar(request.step_size, "h")
            v0_flt: float | None = None
            if request.order == NumericalODEOrder.SECOND_ORDER:
                _, v0_flt = parse_numeric_scalar(request.v0, "v₀")

            coarse_grid = build_time_grid(t0_dec, t_end_dec, h_dec, request.max_steps)
            fine_grid = subdivide_time_grid_half(coarse_grid)

            parsed = parse_numerical_ode_equation(
                request.raw_equation,
                order=request.order,
                indep_var=request.independent_var,
                dep_var=request.dependent_var,
            )

            if request.order == NumericalODEOrder.FIRST_ORDER:
                rhs_eval = compile_safe_real_evaluator(parsed.rhs_expr, (parsed.indep_var, parsed.dep_var))
                adapter: FirstOrderEulerAdapter | SecondOrderEulerAdapter = FirstOrderEulerAdapter(rhs_eval, y0_flt)
            else:
                rhs_eval = compile_safe_real_evaluator(
                    parsed.rhs_expr, (parsed.indep_var, parsed.dep_var, parsed.yp_sym)
                )
                adapter = SecondOrderEulerAdapter(rhs_eval, y0_flt, v0_flt if v0_flt is not None else 0.0)

            fine_records = integrate_explicit_euler(fine_grid, adapter.initial_state, adapter.rhs_system)
            fine_rows = adapter.to_rows(fine_records)
        except Exception as exc:
            return StepHalvingEstimate(
                available=False,
                coarse_step_size=coarse_h,
                fine_step_size=fine_h,
                notes=f"Không thể hoàn tất lưới tham chiếu h/2 để ước lượng Richardson: {exc}",
            )

        if len(fine_rows) != (2 * len(response.rows) - 1):
            return StepHalvingEstimate(
                available=False,
                coarse_step_size=coarse_h,
                fine_step_size=fine_h,
                notes="Không thể căn chỉnh chính xác lưới thô h và lưới mịn h/2.",
            )

        points: list[StepHalvingPoint] = []
        max_est_y = 0.0
        max_est_v: float | None = 0.0 if request.order == NumericalODEOrder.SECOND_ORDER else None

        for idx, coarse_row in enumerate(response.rows):
            fine_row = fine_rows[2 * idx]
            est_y = 2.0 * abs(fine_row.y - coarse_row.y)
            max_est_y = max(max_est_y, est_y)

            v_c: float | None = None
            v_f: float | None = None
            est_v: float | None = None
            if request.order == NumericalODEOrder.SECOND_ORDER:
                v_c = coarse_row.v
                v_f = fine_row.v
                if v_c is not None and v_f is not None:
                    est_v = 2.0 * abs(v_f - v_c)
                    if max_est_v is not None:
                        max_est_v = max(max_est_v, est_v)

            points.append(
                StepHalvingPoint(
                    step_index=idx,
                    t=coarse_row.t,
                    y_coarse=coarse_row.y,
                    y_fine=fine_row.y,
                    estimated_error_y=est_y,
                    v_coarse=v_c,
                    v_fine=v_f,
                    estimated_error_v=est_v,
                )
            )

        return StepHalvingEstimate(
            available=True,
            coarse_step_size=coarse_h,
            fine_step_size=fine_h,
            richardson_factor=2.0,
            points=tuple(points),
            final_estimated_error_y=points[-1].estimated_error_y if points else None,
            max_estimated_error_y=max_est_y,
            final_estimated_error_v=points[-1].estimated_error_v if points else None,
            max_estimated_error_v=max_est_v,
            notes=(
                "Ước lượng sai số Richardson cho phương pháp bậc p = 1: E_h ≈ 2 × |y_(h/2) - y_h|. "
                "Đây là ước lượng số tiệm cận khi chưa dùng hoặc không phụ thuộc nghiệm giải tích, không phải sai số tuyệt đối chính xác."
            ),
        )

    def analyze(
        self,
        request: NumericalODERequest,
        response: NumericalODEResponse,
    ) -> NumericalErrorAnalysis:
        """Analyze local defect, global error, theoretical convergence orders, and h/2 Richardson estimate."""
        t_v = response.independent_var or "t"
        y_v = response.dependent_var or "y"
        is_second = response.order == NumericalODEOrder.SECOND_ORDER

        if is_second:
            local_latex = (
                f"\\begin{{aligned}}"
                f"\\delta^y_{{n+1}} &= {y_v}({t_v}_{{n+1}}) - {y_v}({t_v}_n) - h_n {y_v}'({t_v}_n) = O(h_n^2) \\\\ "
                f"\\delta^v_{{n+1}} &= {y_v}'({t_v}_{{n+1}}) - {y_v}'({t_v}_n) - h_n F({t_v}_n, {y_v}({t_v}_n), {y_v}'({t_v}_n)) = O(h_n^2)"
                f"\\end{{aligned}}"
            )
            global_latex = (
                f"\\begin{{aligned}}"
                f"E^y_n &= |{y_v}_{{\\text{{exact}}}}({t_v}_n) - {y_v}_n| = O(h) \\\\ "
                f"E^v_n &= |{y_v}'_{{\\text{{exact}}}}({t_v}_n) - v_n| = O(h)"
                f"\\end{{aligned}}"
            )
        else:
            local_latex = (
                f"\\delta_{{n+1}} = {y_v}({t_v}_{{n+1}}) - {y_v}({t_v}_n) - h_n f({t_v}_n, {y_v}({t_v}_n)) = O(h_n^2)"
            )
            global_latex = f"E^y_n = |{y_v}_{{\\text{{exact}}}}({t_v}_n) - {y_v}_n| = O(h)"

        if response.status != NumericalODEStatus.SUCCESS or not response.rows:
            return NumericalErrorAnalysis(
                has_exact_reference=False,
                local_error_convention=_LOCAL_DEFECT_CONVENTION,
                local_defect_formula_latex=local_latex,
                global_error_formula_latex=global_latex,
                stability_note=_STABILITY_NOTE,
                interpretation_notes=("Không có dữ liệu lưới thành công để phân tích sai số.",),
            )

        step_halving = self._compute_step_halving(request, response)
        ana = response.analytical_comparison
        has_exact = bool(ana is not None and ana.available and len(ana.points) == len(response.rows))

        if has_exact and ana is not None:
            notes = [
                "Đã tính sai số toàn cục thực tế và sai số chặt cục bộ một bước từ nghiệm giải tích chính xác.",
            ]
            if step_halving.available:
                notes.append(
                    "Ước lượng Richardson từ bước giảm nửa h/2 cũng được cung cấp để đối chiếu độc lập với sai số thực."
                )
            return NumericalErrorAnalysis(
                has_exact_reference=True,
                local_error_convention=_LOCAL_DEFECT_CONVENTION,
                local_defect_formula_latex=local_latex,
                global_error_formula_latex=global_latex,
                final_global_error_y=ana.final_abs_error,
                max_global_error_y=ana.max_abs_error,
                final_global_error_v=ana.final_v_abs_error,
                max_global_error_v=ana.max_v_abs_error,
                final_local_defect_y=ana.final_local_defect_y,
                max_abs_local_defect_y=ana.max_local_defect_y,
                final_local_defect_v=ana.final_local_defect_v,
                max_abs_local_defect_v=ana.max_local_defect_v,
                step_halving=step_halving,
                stability_note=_STABILITY_NOTE,
                interpretation_notes=tuple(notes),
            )

        notes = [
            "Không có nghiệm giải tích chính xác để đối chiếu trực tiếp nên hệ thống không bịa đặt sai số cục bộ hay sai số toàn cục chính xác.",
            "Bậc hội tụ lý thuyết của Explicit Euler là O(h²) đối với sai số chặt cục bộ một bước và O(h) đối với sai số toàn cục dưới điều kiện đủ trơn và ổn định.",
        ]
        if step_halving.available:
            notes.append(
                "Ước lượng sai số toàn cục bằng cách giảm nửa bước h/2 (E_h ≈ 2·|y_{h/2} - y_h|) là giá trị ước lượng số, không phải sai số chính xác."
            )

        return NumericalErrorAnalysis(
            has_exact_reference=False,
            local_error_convention=_LOCAL_DEFECT_CONVENTION,
            local_defect_formula_latex=local_latex,
            global_error_formula_latex=global_latex,
            final_global_error_y=None,
            max_global_error_y=None,
            final_global_error_v=None,
            max_global_error_v=None,
            final_local_defect_y=None,
            max_abs_local_defect_y=None,
            final_local_defect_v=None,
            max_abs_local_defect_v=None,
            step_halving=step_halving,
            stability_note=_STABILITY_NOTE,
            interpretation_notes=tuple(notes),
        )
