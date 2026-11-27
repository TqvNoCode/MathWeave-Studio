"""Method selector and educational guidance component for ODE workspace."""

from __future__ import annotations

from typing import Callable
from nicegui import ui

from math_app.presentation.components.workspace.ode.ode_state import (
    ODEClassification,
    ODEMethodPreference,
    ODEOrder,
)


def render_ode_method_selector(
    order: ODEOrder,
    classification: ODEClassification,
    method_preference: ODEMethodPreference,
    on_method_change: Callable[[ODEMethodPreference], None],
    recommended_method_hint: str | None = None,
    is_nonhomogeneous_euler: bool = False,
) -> None:
    """Render solution method selector for Nonhomogeneous Second-Order ODEs."""
    # 1. Nonhomogeneous Second-Order ODE Method Selection
    if order == ODEOrder.SECOND_ORDER and classification == ODEClassification.SECOND_ORDER_NONHOMOGENEOUS:
        with ui.column().classes("w-full gap-2 p-3.5 bg-slate-50 border border-slate-200 rounded-xl mt-1 min-w-0"):
            with ui.row().classes("items-center justify-between w-full flex-wrap gap-2"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("stars", size="1.1rem").classes("text-blue-600")
                    ui.label("PHƯƠNG PHÁP ĐỀ XUẤT — TÌM NGHIỆM RIÊNG Y_p(t):").classes(
                        "text-xs font-bold text-slate-700 uppercase tracking-wider"
                    )
                if recommended_method_hint:
                    ui.badge(f"Gợi ý: {recommended_method_hint.split(' (')[0]}", color="blue-7").classes(
                        "text-xs font-medium"
                    )
                else:
                    ui.badge("Tùy chọn phương pháp", color="blue-7").classes("text-xs font-medium")

            radio_options = {
                ODEMethodPreference.AUTO.value: "Tự động (Khuyến nghị theo vế phải g(t))",
                ODEMethodPreference.UNDETERMINED_COEFFICIENTS.value: "Hệ số bất định (Undetermined Coefficients)",
                ODEMethodPreference.VARIATION_OF_PARAMETERS.value: "Biến thiên hằng số (Variation of Parameters)",
            }
            method_radio = ui.radio(
                options=radio_options,
                value=method_preference.value,
            ).props("inline").classes("text-sm text-slate-800")
            method_radio.on_value_change(
                lambda e: on_method_change(ODEMethodPreference(e.value or "AUTO"))
            )

            ui.label(
                "Chế độ tự động ưu tiên Hệ số bất định cho đa thức, hàm mũ, sin/cos; "
                "tự động kích hoạt Biến thiên hằng số (Lagrange) cho tan, cot, sec, csc, ln, phân thức..."
            ).classes("text-xs text-slate-600 italic")
        return

    # 2. Homogeneous Second-Order ODE Guidance
    if order == ODEOrder.SECOND_ORDER and classification == ODEClassification.SECOND_ORDER_HOMOGENEOUS:
        with ui.row().classes("w-full p-3.5 bg-slate-50 border border-slate-200 rounded-xl items-center gap-3 mt-1"):
            ui.icon("info", color="primary", size="1.5rem")
            with ui.column().classes("gap-0.5"):
                ui.label("Phương pháp giải: Phương trình đặc trưng ar² + br + c = 0").classes(
                    "text-xs font-bold text-slate-800"
                )
                ui.label(
                    "Hệ thống tự động giải phương trình đặc trưng, phân tích dấu biệt thức Δ = b² - 4ac "
                    "và áp dụng công thức tương ứng (nghiệm thực phân biệt, nghiệm kép thực, hoặc cặp nghiệm phức liên hợp)."
                ).classes("text-xs text-slate-500 leading-snug")
        return

    # 2b. Euler-Cauchy Second-Order ODE Guidance
    if order == ODEOrder.SECOND_ORDER and classification == ODEClassification.EULER_CAUCHY:
        if is_nonhomogeneous_euler:
            with ui.column().classes("w-full gap-1.5 p-3.5 bg-slate-50 border border-slate-200 rounded-xl mt-1 min-w-0"):
                with ui.row().classes("items-center justify-between w-full flex-wrap gap-2"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("stars", size="1.1rem").classes("text-blue-600")
                        ui.label("PHƯƠNG PHÁP ĐỀ XUẤT — EULER–CAUCHY KHÔNG THUẦN NHẤT:").classes(
                            "text-xs font-bold text-slate-700 uppercase tracking-wider"
                        )
                    ui.badge(
                        recommended_method_hint or "Phương pháp tự động (Khuyến nghị)",
                        color="blue-7",
                    ).classes("text-xs font-medium")
                ui.label(
                    "Giải phương trình thuần nhất liên kết tìm hệ nghiệm cơ bản {y₁, y₂}, "
                    "sau đó áp dụng Biến thiên hằng số (Lagrange) để tìm y_p(t) (bảo toàn tích phân chính xác khi cần)."
                ).classes("text-xs text-slate-600 leading-snug")
            return
        with ui.row().classes("w-full p-3.5 bg-slate-50 border border-slate-200 rounded-xl items-center gap-3 mt-1"):
            ui.icon("functions", color="primary", size="1.5rem")
            with ui.column().classes("gap-0.5"):
                ui.label("Phương pháp giải: Phương trình chỉ số Am(m - 1) + Bm + C = 0").classes(
                    "text-xs font-bold text-slate-800"
                )
                ui.label(
                    "Đặt y = t^m để đưa phương trình về phương trình chỉ số Am² + (B - A)m + C = 0. "
                    "Hệ thống giải biệt thức Δ = (B - A)² - 4AC và thiết lập hệ nghiệm cơ bản cho miền xác định tương ứng."
                ).classes("text-xs text-slate-500 leading-snug")
        return

    # 3. Contextual First-Order Pedagogical Notices
    if order == ODEOrder.FIRST_ORDER:
        notices = {
            ODEClassification.FIRST_ORDER_LINEAR: (
                "Phương trình tuyến tính cấp 1: y' + p(t)y = g(t)",
                "Áp dụng phương pháp thừa số tích phân μ(t) = exp(∫ p(t) dt) để đưa vế trái về dạng đạo hàm đúng (μ·y)' = μ·g(t).",
            ),
            ODEClassification.SEPARABLE: (
                "Phương trình tách biến: dy / g(y) = f(t) dt",
                "Phân tách biến số về hai vế và lấy tích phân hai vế; đồng thời kiểm tra và bảo toàn các nghiệm cân bằng g(y) = 0.",
            ),
            ODEClassification.EXACT: (
                "Phương trình vi phân toàn phần: M(x, y) dx + N(x, y) dy = 0",
                "Kiểm tra điều kiện toàn phần ∂M/∂y = ∂N/∂x và xác định hàm thế vị F(x, y) sao cho dF = 0, cho nghiệm ẩn F(x, y) = C.",
            ),
            ODEClassification.INTEGRATING_FACTOR: (
                "Thừa số tích phân cho phương trình không toàn phần",
                "Xác định thừa số tích phân Euler μ(x) hoặc μ(y) để biến đổi phương trình không toàn phần thành phương trình toàn phần.",
            ),
            ODEClassification.FIRST_ORDER_HOMOGENEOUS: (
                "Phương trình thuần nhất bậc 0: y' = F(y/x)",
                "Sử dụng phép đổi biến số y = v·x (với y' = v + x·v') để đưa phương trình về dạng tách biến đối với v và x.",
            ),
        }
        if classification in notices:
            title, desc = notices[classification]
            with ui.row().classes("w-full p-3 bg-slate-50 border border-slate-200 rounded-xl items-center gap-2.5 mt-1"):
                ui.icon("school", color="primary", size="1.3rem")
                with ui.column().classes("gap-0.5"):
                    ui.label(title).classes("text-xs font-bold text-slate-800")
                    ui.label(desc).classes("text-xs text-slate-500 leading-snug")
