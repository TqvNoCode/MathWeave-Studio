"""Pedagogical derivation step viewer component for NiceGUI.

Presents derivations as a unified, continuous mathematical argument (Layer A),
with on-demand expandable detailed reasoning for individual terms (Layer B).
"""

from __future__ import annotations

from nicegui import ui

from math_app.application.dtos import SolutionStep
from math_app.presentation.components.math_view import ui_math


def render_substep_compact(substep: SolutionStep) -> None:
    """Render a term-level calculation (Layer B) in a clean, compact item without heavy card nesting."""
    with ui.column().classes("w-full p-2.5 rounded-lg bg-white border border-slate-200/80 gap-1.5 shadow-none"):
        # Term Header
        with ui.row().classes("items-center gap-2 flex-wrap"):
            ui.icon("fiber_manual_record", size="0.55rem").classes("text-blue-500")
            raw_title = substep.title or f"Phép biến đổi {substep.step_number}"
            if raw_title.startswith("Số hạng "):
                term_part = raw_title[len("Số hạng "):].strip()
                ui.label("Số hạng:").classes("font-semibold text-xs md:text-sm text-slate-800")
                ui_math(term_part, block=False, classes="text-xs md:text-sm font-semibold text-slate-900")
            else:
                ui.label(raw_title).classes("font-semibold text-xs md:text-sm text-slate-800")
            rn = substep.display_rule_name
            if rn and rn != raw_title:
                ui.badge(rn, color="slate-100").classes("text-slate-600 text-[11px] px-2 py-0.5 rounded-md font-medium")

        # Pedagogical term explanation
        if substep.description:
            ui.label(substep.description).classes("text-xs md:text-sm text-slate-600 pl-3 leading-relaxed")

        # Mathematical term equation
        if substep.equation_latex:
            with ui.row().classes("w-full pl-3 py-0.5 items-center overflow-x-auto overflow-y-hidden"):
                ui_math(substep.equation_latex, block=False, classes="text-sm md:text-base text-slate-900")
        elif substep.content and substep.content.latex_before and substep.content.latex_after:
            with ui.row().classes("w-full pl-3 py-0.5 items-center gap-2 overflow-x-auto overflow-y-hidden"):
                ui_math(
                    f"{substep.content.latex_before} = {substep.content.latex_after}",
                    block=False,
                    classes="text-sm md:text-base text-slate-900",
                )

        # Deeper nested reasoning only when strictly necessary
        if substep.substeps:
            with ui.expansion("Chi tiết bổ sung", icon="more_horiz").classes("w-full text-xs text-slate-600 ml-3"):
                for deep_sub in substep.substeps:
                    render_substep_compact(deep_sub)


def render_step(step: SolutionStep) -> None:
    """Render an individual main derivation step (Layer A) with optional Layer B details."""
    card_classes = "w-full p-5 my-2.5 shadow-xs border border-slate-200 rounded-xl bg-white gap-3"
    step_title = step.display_title
    rule_name_vi = step.display_rule_name

    with ui.card().classes(card_classes):
        # 1. Step Header: Step Number, Vietnamese Title & Applied Rule Badge
        with ui.row().classes("items-center justify-between w-full flex-wrap gap-2 border-b border-slate-100 pb-2.5"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("check_circle_outline", size="1.25rem").classes("text-blue-600")
                ui.label(f"Bước {step.step_number}: {step_title}").classes("text-base font-bold text-slate-900")

            with ui.row().classes("items-center gap-2"):
                ui.badge(rule_name_vi, color="blue-1").classes("text-blue-800 text-xs px-2.5 py-0.5 rounded-full font-medium")
                if step.notes:
                    ui.badge(step.notes, color="slate-200").classes("text-slate-700 text-xs px-2 py-0.5 rounded-md font-medium")

        # 2. Concise Pedagogical Explanation in Vietnamese (Layer A)
        if step.description:
            ui.label(step.description).classes("text-xs md:text-sm text-slate-700 leading-relaxed mt-1")

        # 3. Step Assumptions / Conditions (e.g. Với n != -1)
        if step.assumptions:
            with ui.row().classes("items-center gap-2 px-3 py-1.5 bg-amber-50/70 border border-amber-200/60 rounded-lg text-xs text-amber-900"):
                ui.icon("info", size="1rem").classes("text-amber-600")
                for asmp in step.assumptions:
                    ui_math(asmp, block=False, classes="text-xs text-amber-950 font-medium")

        # 4. Continuous Mathematical Transformation (Layer A - Always Visible)
        if step.equation_latex:
            with ui.column().classes("w-full bg-slate-50/90 rounded-xl p-4 my-1 border border-slate-200/80 items-start overflow-x-auto"):
                ui_math(step.equation_latex, block=True, classes="text-base md:text-lg text-slate-900 font-medium py-1")
        else:
            with ui.column().classes("w-full bg-slate-50/90 rounded-xl p-3.5 my-1 border border-slate-200/80 gap-2"):
                with ui.row().classes("items-center justify-between w-full flex-wrap gap-4"):
                    with ui.column().classes("gap-1 min-w-[200px] flex-1"):
                        ui.label("Trước biến đổi:").classes("text-[11px] font-bold text-slate-500 uppercase tracking-wider")
                        ui_math(step.content.latex_before, block=False, classes="text-base text-slate-900 py-0.5")

                    ui.icon("arrow_forward", size="1.25rem").classes("text-blue-500 self-center hidden sm:block")

                    with ui.column().classes("gap-1 min-w-[200px] flex-1"):
                        ui.label("Sau biến đổi:").classes("text-[11px] font-bold text-blue-700 uppercase tracking-wider")
                        ui_math(step.content.latex_after, block=False, classes="text-base font-semibold text-blue-800 py-0.5")

        # 5. Layer B: Detailed Reasoning on Demand (Compact Substeps)
        if step.substeps:
            with ui.expansion("Xem giải thích chi tiết các phép biến đổi", icon="unfold_more").classes(
                "w-full mt-2 text-xs md:text-sm text-slate-700 bg-slate-50/70 rounded-xl border border-slate-200/70"
            ):
                with ui.column().classes("w-full p-3 gap-2.5"):
                    for substep in step.substeps:
                        render_substep_compact(substep)


def render_steps_container(
    steps: tuple[SolutionStep, ...],
    final_answer_latex: str = "",
) -> None:
    """Render the full sequence of continuous derivation steps and final boxed conclusion."""
    if not steps:
        with ui.card().classes("w-full p-4 border border-slate-200 bg-slate-50 rounded-xl text-center"):
            ui.label("Không có bước phân rã nào được tạo cho phép toán này.").classes("text-slate-500 italic text-sm")
        return

    with ui.column().classes("w-full gap-2 mt-4"):
        # Section Header with Accurate Step Count
        with ui.row().classes("items-center justify-between w-full border-b border-slate-200 pb-2"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("format_list_numbered", size="1.4rem").classes("text-blue-600")
                ui.label("Trình tự giải chi tiết từng bước").classes("text-base md:text-lg font-bold text-slate-900")
            ui.badge(f"{len(steps)} bước", color="blue-1").classes("text-blue-800 text-xs px-2.5 py-0.5 rounded-full font-semibold")

        # Derivation Sequence (Layer A & Layer B)
        for step in steps:
            render_step(step)

        # Final Boxed Conclusion in the Derivation Sequence
        if final_answer_latex and final_answer_latex.strip():
            with ui.card().classes("w-full p-4.5 my-2 border-2 border-blue-200 bg-gradient-to-r from-blue-50/80 to-indigo-50/60 rounded-xl gap-2 shadow-xs"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("task_alt", color="primary", size="1.3rem")
                    ui.label("Kết luận:").classes("text-base font-bold text-blue-950")
                boxed_latex = f"\\boxed{{{final_answer_latex}}}"
                ui_math(boxed_latex, block=True, classes="text-xl md:text-2xl font-bold text-blue-900 py-1")
