"""Pedagogical solution flow step viewer for Ordinary Differential Equations.

Presents derivations organized into 4 educational stages:
1. Giai đoạn 1: Nhận dạng / Nghiệm thuần nhất
2. Giai đoạn 2: Toán tử giải / Nghiệm riêng
3. Giai đoạn 3: Tích phân & tổng hợp nghiệm
4. Giai đoạn 4: Kiểm chứng toán học độc lập

Each derivation step displays the 4 pedagogical pillars:
- Mục đích (Purpose)
- Cơ sở toán học (Mathematical Foundation)
- Thực hiện & Biến đổi (Execution & Calculations)
- Kết quả trung gian (Intermediate Result)
"""

from __future__ import annotations

import re
from typing import Any

from nicegui import ui

from math_app.presentation.components.math_view import ui_math, ui_math_text
from math_app.presentation.components.ode_pedagogical_enhancer import (
    ODEPedagogicalStep,
    ODEStageSummary,
)
from math_app.presentation.components.step_viewer import render_substep_compact
from math_app.rendering.text_math_renderer import is_pure_latex_math


def _normalize_math(s: str) -> str:
    """Normalize LaTeX formula string for deduplication comparison."""
    if not s:
        return ""
    clean = s.strip()
    if clean.startswith("$") and clean.endswith("$"):
        clean = clean[1:-1].strip()
    return (
        re.sub(r"\s+", "", clean)
        .replace(r"\left", "")
        .replace(r"\right", "")
        .replace("{", "")
        .replace("}", "")
    )


def _is_meaningful_intermediate_result(step: ODEPedagogicalStep) -> bool:
    """Determine whether an intermediate result provides distinct, non-redundant value."""
    if not step.intermediate_result or not step.intermediate_result.strip():
        return False
    raw_ir = step.intermediate_result.strip()
    if raw_ir.startswith("$") and raw_ir.endswith("$"):
        raw_ir = raw_ir[1:-1].strip()

    # If intermediate result is identical to equation_latex or content after, it's redundant
    eq = (step.equation_latex or "").strip()
    if not eq and step.content and step.content.latex_after:
        eq = step.content.latex_after.strip()

    if _normalize_math(raw_ir) == _normalize_math(eq):
        return False

    # Always meaningful if verification status, failure, warning, or implication
    if any(
        tok in raw_ir
        for tok in (
            r"\implies",
            r"\\implies",
            "⇒",
            "Kiểm chứng",
            "thành công",
            "thất bại",
            "sai lệch",
        )
    ):
        return True

    return True


def render_ode_pedagogical_step(step: ODEPedagogicalStep) -> None:
    """Render an individual ODE derivation step with a minimalist, high-readability structure."""
    card_classes = "w-full min-w-0 max-w-full p-3 md:p-4 my-1.5 shadow-xs border border-slate-200 rounded-xl bg-white gap-2"
    step_title = step.display_title
    rule_name_vi = step.display_rule_name

    with ui.card().classes(card_classes):
        # 1. Step Header: Step Number, Title & Rule Badge with responsive flex wrapping
        with ui.row().classes("items-center justify-between w-full flex-wrap gap-1.5 border-b border-slate-100 pb-2"):
            with ui.row().classes("items-center gap-2 min-w-[240px] flex-1 max-w-full"):
                ui.icon("check_circle_outline", size="1.15rem").classes("text-blue-600 shrink-0")
                step_num_disp = getattr(step, "presentation_step_number", getattr(step, "display_step_number", step.step_number))
                ui_math_text(f"Bước {step_num_disp}: {step_title}", classes="text-sm md:text-base font-bold text-slate-900 leading-snug")

            with ui.row().classes("items-center gap-1.5 flex-wrap justify-end"):
                with ui.badge(color="blue-1").classes("text-blue-800 text-xs px-2 py-0.5 rounded-full font-medium"):
                    ui_math_text(rule_name_vi)
                if step.stage_name and step.stage_name.lower() not in rule_name_vi.lower():
                    with ui.badge(color="slate-100").classes("text-slate-600 text-[11px] px-2 py-0.5 rounded-md font-medium"):
                        ui_math_text(step.stage_name)
                if step.notes:
                    with ui.badge(color="slate-200").classes("text-slate-700 text-xs px-2 py-0.5 rounded-md font-medium"):
                        ui_math_text(step.notes)

        # Assumptions / Conditions if present
        if step.assumptions:
            with ui.row().classes("items-center gap-2 px-2.5 py-1 bg-amber-50/70 border border-amber-200/60 rounded-lg text-xs text-amber-900"):
                ui.icon("info", size="1rem").classes("text-amber-600")
                for asmp in step.assumptions:
                    ui_math(asmp, block=False, classes="text-xs text-amber-950 font-medium")

        # 2. Integrated Pedagogical Explanation (WHY)
        explanation_texts: list[str] = []
        if step.purpose and step.purpose.strip():
            explanation_texts.append(step.purpose.strip())
        if step.math_basis and step.math_basis.strip() and step.math_basis.strip() != step.purpose.strip():
            explanation_texts.append(step.math_basis.strip())

        if explanation_texts:
            with ui.column().classes("w-full p-2.5 rounded-lg bg-slate-50/80 border-l-3 border-blue-500 border border-slate-200/60 gap-1 min-w-0"):
                for exp_txt in explanation_texts:
                    ui_math_text(exp_txt, classes="text-xs md:text-sm text-slate-700 leading-relaxed")

        # 3. Mathematical Derivation & Transformation (EXECUTION)
        has_eq = bool(step.equation_latex or (step.content and (step.content.latex_before or step.content.latex_after)))
        has_desc = bool(step.description and step.description.strip())

        if has_desc or has_eq:
            with ui.column().classes("w-full bg-slate-50/50 rounded-xl p-2.5 md:p-3 border border-slate-200/70 gap-1.5 min-w-0"):
                if has_desc:
                    ui_math_text(step.description, classes="text-xs md:text-sm text-slate-800 leading-relaxed font-medium")

                if step.equation_latex:
                    with ui.column().classes("w-full overflow-x-auto py-0.5 items-start min-w-0"):
                        ui_math(step.equation_latex, block=True, classes="text-base md:text-lg text-slate-900 font-semibold")
                elif step.content and (step.content.latex_before or step.content.latex_after):
                    with ui.column().classes("w-full overflow-x-auto py-0.5 items-start min-w-0"):
                        if step.content.latex_before and step.content.latex_after:
                            ui_math(f"{step.content.latex_before} \\implies {step.content.latex_after}", block=True, classes="text-base md:text-lg text-slate-900 font-semibold")
                        elif step.content.latex_after:
                            ui_math(step.content.latex_after, block=True, classes="text-base md:text-lg text-slate-900 font-semibold")

        # 4. Result / Outcome (Only when mathematically distinct or conveying verification status)
        if _is_meaningful_intermediate_result(step):
            raw_ir = step.intermediate_result.strip()
            if raw_ir.startswith("$") and raw_ir.endswith("$"):
                raw_ir = raw_ir[1:-1].strip()

            ir_text_lower = raw_ir.lower()
            is_failed = any(w in ir_text_lower for w in ("thất bại", "sai lệch", "failed"))
            is_warning = any(w in ir_text_lower for w in ("cảnh báo", "chưa kiểm chứng", "warning", "unverified"))

            if is_failed:
                ir_bg = "bg-rose-50/80 border-rose-200 text-rose-950"
                ir_title_cls = "text-rose-800"
                ir_icon = "error"
                ir_icon_cls = "text-rose-600"
            elif is_warning:
                ir_bg = "bg-amber-50/80 border-amber-200 text-amber-950"
                ir_title_cls = "text-amber-800"
                ir_icon = "warning"
                ir_icon_cls = "text-amber-600"
            else:
                ir_bg = "bg-emerald-50/80 border-emerald-200 text-emerald-950"
                ir_title_cls = "text-emerald-800"
                ir_icon = "verified"
                ir_icon_cls = "text-emerald-600"

            with ui.row().classes(f"w-full items-center gap-2 p-2 md:p-2.5 rounded-lg border {ir_bg} text-xs min-w-0 flex-wrap"):
                ui.icon(ir_icon, size="1.15rem").classes(f"{ir_icon_cls} shrink-0")
                ui.label("KẾT QUẢ:").classes(f"font-bold text-[10px] uppercase tracking-wider {ir_title_cls}")

                if (
                    (r"\implies" in raw_ir or r"\\implies" in raw_ir or "⇒" in raw_ir)
                    and r"\begin{aligned}" not in raw_ir
                    and r"\begin{cases}" not in raw_ir
                ):
                    parts = re.split(r"\\+implies|⇒", raw_ir, maxsplit=1)
                    math_part = parts[0].strip()
                    status_part = parts[1].strip() if len(parts) > 1 else ""
                    if math_part.startswith("$") and math_part.endswith("$"):
                        math_part = math_part[1:-1].strip()
                    if math_part:
                        ui_math(math_part, block=False, classes="text-xs md:text-sm font-semibold")
                    if status_part:
                        ui.icon("arrow_forward", size="0.95rem").classes(f"{ir_icon_cls} shrink-0")
                        ui_math_text(status_part, classes=f"text-xs md:text-sm font-semibold {ir_title_cls}")
                elif is_pure_latex_math(raw_ir):
                    ui_math(raw_ir, block=False, classes="text-xs md:text-sm font-semibold")
                else:
                    ui_math_text(raw_ir, classes=f"text-xs md:text-sm font-semibold leading-relaxed {ir_title_cls}")

        # Layer B: Substeps if any
        if step.substeps:
            with ui.expansion("Xem giải thích chi tiết các phép biến đổi", icon="unfold_more").classes(
                "w-full mt-2 text-xs md:text-sm text-slate-700 bg-slate-50/70 rounded-xl border border-slate-200/70"
            ):
                with ui.column().classes("w-full p-3 gap-2.5"):
                    for substep in step.substeps:
                        render_substep_compact(substep)


def render_ode_staged_steps_container(
    stages: tuple[ODEStageSummary, ...],
    final_answer_latex: str = "",
) -> None:
    """Render the ODE solution organized into 4 educational stages with interactive controls."""
    if not stages:
        with ui.card().classes("w-full p-4 border border-slate-200 bg-slate-50 rounded-xl text-center"):
            ui.label("Không có bước phân rã nào được tạo cho phép toán này.").classes("text-slate-500 italic text-sm")
        return

    total_steps = sum(len(stg.steps) for stg in stages)

    with ui.column().classes("w-full gap-2.5 mt-3 min-w-0"):
        # 1. Section Header & Global Expansion Controls
        expansion_refs: list[Any] = []

        with ui.row().classes("items-center justify-between w-full border-b border-slate-200 pb-2 flex-wrap gap-2"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("account_tree", size="1.4rem").classes("text-blue-600")
                ui.label("Trình tự giải chi tiết theo 4 giai đoạn sư phạm").classes("text-base md:text-lg font-bold text-slate-900")
            with ui.row().classes("items-center gap-2 flex-wrap"):
                ui.badge(f"{len(stages)} giai đoạn", color="blue-1").classes("text-blue-800 text-xs px-2.5 py-0.5 rounded-full font-semibold")
                ui.badge(f"{total_steps} bước chi tiết", color="indigo-1").classes("text-indigo-800 text-xs px-2.5 py-0.5 rounded-full font-semibold")

                def expand_all() -> None:
                    for exp in expansion_refs:
                        exp.value = True

                def collapse_all() -> None:
                    for exp in expansion_refs:
                        exp.value = False

                ui.button("Mở rộng tất cả", icon="unfold_more", on_click=expand_all).props("flat dense").classes("text-xs text-blue-700")
                ui.button("Thu gọn tất cả", icon="unfold_less", on_click=collapse_all).props("flat dense").classes("text-xs text-slate-600")

        # 2. Visual 4-Stage Stepper / Progress Bar
        with ui.row().classes("w-full items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-200/90 gap-1.5 flex-wrap min-w-0"):
            for idx, stage in enumerate(stages):
                with ui.row().classes("items-center gap-1.5 min-w-0"):
                    if stage.is_applicable:
                        if stage.is_completed:
                            stepper_icon = "check_circle"
                        elif "thất bại" in stage.badge_text.lower() or "rose" in stage.badge_color:
                            stepper_icon = "error"
                        else:
                            stepper_icon = "warning"
                        with ui.badge(color=stage.badge_color).classes("text-xs px-2.5 py-1 rounded-lg font-semibold flex items-center gap-1"):
                            ui.icon(stepper_icon, size="0.9rem")
                            ui_math_text(f"{stage.stage_index}. {stage.badge_text}")
                    else:
                        with ui.badge(color="slate-400").classes("text-xs px-2.5 py-1 rounded-lg font-medium text-white flex items-center gap-1"):
                            ui.icon("remove_circle_outline", size="0.9rem")
                            ui.label(f"{stage.stage_index}. Bỏ qua (Thuần nhất)")

                if idx < len(stages) - 1:
                    ui.icon("arrow_forward", size="1rem").classes("text-slate-400 hidden sm:block")

        # 3. Stage Expansions with Rich MathML Headers via Slots
        for stage in stages:
            badge_text = f"{len(stage.steps)} bước" if stage.is_applicable else "Không áp dụng"
            badge_color = stage.badge_color if stage.is_applicable else "slate-400"

            is_verification_stage = (stage.stage_index == 4 or "kiểm chứng" in stage.title.lower())
            default_expanded = stage.stage_index == 1

            with ui.expansion(value=default_expanded).classes(
                "w-full bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden"
            ) as stage_exp:
                expansion_refs.append(stage_exp)

                # Custom Header Slot: Renders Icon, Vietnamese Title, MathML Subtitle & Badge without raw LaTeX
                with stage_exp.add_slot("header"):
                    with ui.row().classes("items-center justify-between w-full flex-wrap gap-2 py-1"):
                        with ui.row().classes("items-center gap-2.5 min-w-0 flex-1"):
                            ui.icon(stage.icon, size="1.35rem").classes("text-blue-600 shrink-0")
                            with ui.column().classes("gap-0.5 min-w-0 flex-1"):
                                ui_math_text(stage.title, classes="font-bold text-sm md:text-base text-slate-900")
                                if stage.subtitle:
                                    ui_math_text(stage.subtitle, classes="text-xs text-slate-600 leading-snug")
                        with ui.row().classes("items-center gap-2 shrink-0"):
                            if is_verification_stage:
                                if stage.is_completed:
                                    with ui.badge(color="emerald-1").classes("text-emerald-800 text-xs px-2.5 py-0.5 rounded-full font-semibold border border-emerald-300 flex items-center gap-1"):
                                        ui.icon("verified", size="0.95rem").classes("text-emerald-600")
                                        ui.label("Đã kiểm chứng độc lập")
                                elif "thất bại" in stage.badge_text.lower() or "rose" in stage.badge_color:
                                    with ui.badge(color="rose-1").classes("text-rose-800 text-xs px-2.5 py-0.5 rounded-full font-semibold border border-rose-300 flex items-center gap-1"):
                                        ui.icon("error", size="0.95rem").classes("text-rose-600")
                                        ui.label("Kiểm chứng thất bại")
                                else:
                                    with ui.badge(color="amber-1").classes("text-amber-800 text-xs px-2.5 py-0.5 rounded-full font-semibold border border-amber-300 flex items-center gap-1"):
                                        ui.icon("warning", size="0.95rem").classes("text-amber-600")
                                        ui.label("Chưa xác minh đầy đủ")
                            ui.badge(badge_text, color=badge_color).classes("text-xs font-semibold px-2.5 py-1 rounded-md shrink-0")

                with ui.column().classes("w-full p-2.5 md:p-3 gap-2 min-w-0"):
                    # Non-applicable stage explanation (e.g. Stage 2 for homogeneous ODEs)
                    if not stage.is_applicable:
                        with ui.row().classes("w-full p-3.5 rounded-xl bg-slate-50 border border-slate-200 items-start gap-3 min-w-0"):
                            ui.icon("info", size="1.35rem").classes("text-blue-600 shrink-0 mt-0.5")
                            with ui.column().classes("gap-1 flex-1 min-w-0"):
                                ui_math_text("Phương trình thuần nhất (vế phải $g(t) = 0$):", classes="font-bold text-xs md:text-sm text-slate-800")
                                ui_math_text(
                                    "Phương trình không có hàm cưỡng bức ở vế phải, do đó nghiệm riêng triệt tiêu đồng nhất: $y_p(t) \\equiv 0$. "
                                    "Toàn bộ cấu trúc nghiệm được xác định hoàn toàn bởi nghiệm thuần nhất $y_c(t)$ tìm được ở Giai đoạn 1.",
                                    classes="text-xs text-slate-600 leading-relaxed",
                                )
                                with ui.row().classes("w-full overflow-x-auto py-1 min-w-0"):
                                    ui_math(stage.summary_latex, block=False, classes="text-sm font-semibold text-slate-900")
                    else:
                        # Render each pedagogical step in this stage
                        for step in stage.steps:
                            render_ode_pedagogical_step(step)

                        # Stage Summary Box - Only when non-duplicate and meaningful
                        if stage.summary_latex:
                            last_step_eq = stage.steps[-1].equation_latex if stage.steps else ""
                            is_dup_step = _normalize_math(stage.summary_latex) == _normalize_math(last_step_eq)
                            is_dup_final = _normalize_math(stage.summary_latex) == _normalize_math(final_answer_latex)
                            if not is_dup_step and not is_dup_final:
                                summary_caption = stage.summary_label if stage.summary_label else f"Tổng kết {stage.title}"
                                with ui.card().classes(
                                    "w-full p-2.5 my-1 rounded-lg bg-slate-50/90 border border-blue-200/80 gap-1 shadow-none min-w-0"
                                ):
                                    with ui.row().classes("items-center justify-between w-full flex-wrap gap-2"):
                                        with ui.row().classes("items-center gap-1.5"):
                                            ui.icon("stars", size="1.1rem").classes("text-blue-600")
                                            ui_math_text(f"Tổng kết: {summary_caption}", classes="text-xs font-bold uppercase tracking-wider text-blue-900")
                                        ui.badge(badge_text, color=badge_color).classes("text-[11px] font-semibold")
                                    with ui.row().classes("w-full overflow-x-auto py-0.5 min-w-0"):
                                        ui_math(stage.summary_latex, block=False, classes="text-sm md:text-base font-bold text-slate-900")

                    # Pedagogical Transition Link to Next Stage
                    if stage.transition_note:
                        with ui.row().classes("w-full p-2.5 rounded-lg bg-blue-50/60 border border-blue-100 items-center gap-2 mt-1"):
                            ui.icon("arrow_downward", size="1rem").classes("text-blue-600 shrink-0")
                            ui_math_text(stage.transition_note, classes="text-xs text-blue-900 italic font-medium leading-relaxed")

        # 4. Final Boxed Conclusion
        if final_answer_latex and final_answer_latex.strip():
            clean_conclusion = final_answer_latex.strip()
            if clean_conclusion.startswith(r"\boxed{") and clean_conclusion.endswith("}"):
                clean_conclusion = clean_conclusion[7:-1].strip()
            elif clean_conclusion.startswith(r"\fbox{") and clean_conclusion.endswith("}"):
                clean_conclusion = clean_conclusion[6:-1].strip()

            with ui.card().classes(
                "w-full p-4.5 my-2 border-2 border-blue-200 bg-gradient-to-r from-blue-50/80 to-indigo-50/60 rounded-xl gap-2 shadow-xs min-w-0"
            ):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("task_alt", color="primary", size="1.3rem")
                    ui.label("Kết luận:").classes("text-base font-bold text-blue-950")

                with ui.column().classes("w-full overflow-x-auto min-w-0 py-1"):
                    ui_math(clean_conclusion, block=True, classes="text-lg md:text-xl font-bold text-blue-950 py-1")
