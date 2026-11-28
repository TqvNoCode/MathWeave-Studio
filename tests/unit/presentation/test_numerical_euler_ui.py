"""Presentation and NiceGUI client interaction tests for separated Explicit Euler ODE workflows."""

from __future__ import annotations

import asyncio

from nicegui import Client, app, core, ui

from math_app.domain.models import ProblemType
from math_app.domain.numerical_ode import NumericalODEOrder, NumericalODERequest
from math_app.main import build_application
from math_app.presentation.app import create_app
from math_app.presentation.components.operation_catalog import get_operation_by_type
from math_app.presentation.components.workspace.ode.numerical_result_view import (
    render_numerical_euler_result,
)
from math_app.presentation.components.workspace.ode.ode_workspace import render_ode_workspace
from math_app.presentation.services.numerical_plot_service import (
    create_numerical_derivative_plot,
    create_numerical_euler_plot,
)


def _collect_texts(root: ui.element) -> list[str]:
    out: list[str] = []

    def _walk(el: ui.element) -> None:
        for attr in ("text", "content"):
            val = getattr(el, attr, None)
            if isinstance(val, str) and val.strip():
                out.append(val.strip())
        for child in el.default_slot.children:
            if isinstance(child, ui.element):
                _walk(child)

    _walk(root)
    return out


def _find_button_containing(client: Client, needle: str) -> ui.button | None:
    for el in client.elements.values():
        if isinstance(el, ui.button):
            if needle in (el.text or ""):
                return el
            if needle in "\n".join(_collect_texts(el)):
                return el
    return None


def _click_button(client: Client, btn: ui.button) -> None:
    for listener in list(btn._event_listeners.values()):
        if listener.type in ("click", None):
            with client:
                listener.handler(None)
            return


async def _wait_for_text(client: Client, marker: str, max_ticks: int = 80) -> str:
    for _ in range(max_ticks):
        txt = "\n".join(_collect_texts(client.layout))
        if marker in txt:
            return txt
        await asyncio.sleep(0.05)
    return "\n".join(_collect_texts(client.layout))


def test_separated_first_order_and_second_order_numerical_panels_have_no_redundant_order_selector() -> None:
    """First-order Euler panel has no order switcher or v0; second-order Euler panel has no order switcher and has v0."""
    uc = build_application()
    op1 = get_operation_by_type(ProblemType.ODE_FIRST_ORDER_LINEAR)
    op2 = get_operation_by_type(ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF)

    # 1. First-order ODE module
    client1 = Client(ui.page("/test_sep_1st"))
    with client1:
        render_ode_workspace(op1, uc)

    labels_ana1 = [el._props.get("label", "") for el in client1.elements.values() if isinstance(el, ui.input)]
    assert not any("Bước nhảy" in lbl for lbl in labels_ana1)

    num_btn1 = _find_button_containing(client1, "Phương pháp Euler tiến (Explicit Euler)")
    assert num_btn1 is not None
    _click_button(client1, num_btn1)

    labels_num1 = [el._props.get("label", "") for el in client1.elements.values() if isinstance(el, ui.input)]
    assert any("Điểm bắt đầu t₀" in lbl for lbl in labels_num1)
    assert any("Giá trị ban đầu y₀" in lbl for lbl in labels_num1)
    assert any("Điểm kết thúc T" in lbl for lbl in labels_num1)
    assert any("Bước nhảy h" in lbl for lbl in labels_num1)
    assert not any("v₀" in lbl for lbl in labels_num1)
    # Must NOT have redundant order-switcher buttons inside the 1st-order numerical panel
    assert _find_button_containing(client1, "PTVP Cấp 2") is None
    assert _find_button_containing(client1, "TÍNH XẤP XỈ EULER CẤP 1") is not None

    # Switch back to analytical cleanly
    ana_btn1 = _find_button_containing(client1, "Giải tích (Nghiệm chính xác)")
    assert ana_btn1 is not None
    _click_button(client1, ana_btn1)
    restored1 = [el._props.get("label", "") for el in client1.elements.values() if isinstance(el, ui.input)]
    assert not any("Bước nhảy" in lbl for lbl in restored1)

    # 2. Second-order ODE module
    client2 = Client(ui.page("/test_sep_2nd"))
    with client2:
        render_ode_workspace(op2, uc)

    num_btn2 = _find_button_containing(client2, "Phương pháp Euler tiến (Explicit Euler)")
    assert num_btn2 is not None
    _click_button(client2, num_btn2)

    labels_num2 = [el._props.get("label", "") for el in client2.elements.values() if isinstance(el, ui.input)]
    assert any("Vị trí ban đầu y₀ = y(t₀)" in lbl for lbl in labels_num2)
    assert any("Đạo hàm ban đầu v₀ = y'(t₀)" in lbl for lbl in labels_num2)
    assert _find_button_containing(client2, "PTVP Cấp 1") is None
    assert _find_button_containing(client2, "TÍNH XẤP XỈ EULER CẤP 2") is not None


def test_first_order_and_second_order_numerical_submission_and_error_analysis_ui() -> None:
    """Verify async solve, Level 1/2/3 progressive disclosure, exact & h/2 error display, error recovery, and stale clear."""
    async def _run() -> None:
        core.loop = asyncio.get_running_loop()
        uc = build_application()
        create_app(uc)
        route = [r for r in app.routes if getattr(r, "path", None) == "/"][0]

        # 1. Deep-link 1st-order numerical mode
        client1 = Client(ui.page("/test_num_e2e_1st_sep"))
        with client1:
            route.endpoint.__wrapped__(op=ProblemType.ODE_FIRST_ORDER_LINEAR.value, mode="numerical")

        solve_btn1 = _find_button_containing(client1, "TÍNH XẤP XỈ EULER CẤP 1")
        assert solve_btn1 is not None
        _click_button(client1, solve_btn1)

        body_txt1 = await _wait_for_text(client1, "Kết quả xấp xỉ số — Euler tiến (Cấp 1)")
        for expected in (
            "Kết quả xấp xỉ số tại T = 1",
            "Tóm tắt bài toán & Tham số đã chọn",
            "Phân tích sai số số học",
            "1. Sai số chặt cục bộ một bước (O(h²))",
            "2. Sai số toàn cục (O(h))",
            "3. Bậc hội tụ lý thuyết & Giới hạn ổn định",
            "4. So sánh giảm nửa bước h/2",
            "Đồ thị xấp xỉ số",
            "Bảng giá trị lặp",
            "Giải thích sư phạm chi tiết",
            "2.593742",
        ):
            assert expected in body_txt1, f"Missing '{expected}' in 1st-order numerical UI"

        plots1 = [el for el in client1.elements.values() if isinstance(el, ui.plotly)]
        assert len(plots1) == 1
        assert len(plots1[0].figure["data"][0]["x"]) == 11

        # Editing parameter clears stale result
        inputs1 = {el._props.get("label", ""): el for el in client1.elements.values() if isinstance(el, ui.input)}
        h_inp1 = next(v for k, v in inputs1.items() if "Bước nhảy" in k)
        with client1:
            h_inp1.set_value("0.2")
        cleared_txt1 = "\n".join(_collect_texts(client1.layout))
        assert "Kết quả xấp xỉ số — Euler tiến" not in cleared_txt1

        # Typing 2nd-order equation inside 1st-order Euler shows structured error + order-switch button
        eq_inp1 = next(v for k, v in inputs1.items() if "Phương trình vi phân cấp 1" in k)
        with client1:
            eq_inp1.set_value("y'' = -y")
        _click_button(client1, solve_btn1)
        mismatch_txt = await _wait_for_text(client1, "Chuyển sang PTVP cấp 2")
        assert "Chuyển sang PTVP cấp 2" in mismatch_txt

        # 2. Deep-link 2nd-order numerical mode
        client2 = Client(ui.page("/test_num_e2e_2nd_sep"))
        with client2:
            route.endpoint.__wrapped__(op=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF.value, mode="numerical")

        solve_btn2 = _find_button_containing(client2, "TÍNH XẤP XỈ EULER CẤP 2")
        assert solve_btn2 is not None
        _click_button(client2, solve_btn2)
        body_txt2 = await _wait_for_text(client2, "Kết quả xấp xỉ số — Euler tiến (Cấp 2)")
        assert "Giai đoạn 1: Chuyển PTVP cấp 2 về hệ phương trình cấp 1" in body_txt2
        assert "E^y_n" in body_txt2 and "E^v_n" in body_txt2

        plots2 = [el for el in client2.elements.values() if isinstance(el, ui.plotly)]
        assert len(plots2) == 2
        # Main y(t) plot + derivative y'(t) plot both have exact analytical overlays
        assert len(plots2[0].figure["data"]) == 2
        assert len(plots2[1].figure["data"]) == 2

        # 3. Invalid h = 0 renders error card cleanly
        inputs2 = {el._props.get("label", ""): el for el in client2.elements.values() if isinstance(el, ui.input)}
        h_inp2 = next(v for k, v in inputs2.items() if "Bước nhảy" in k)
        with client2:
            h_inp2.set_value("0")
        _click_button(client2, solve_btn2)
        err_txt = await _wait_for_text(client2, "h > 0")
        assert "h > 0" in err_txt

    asyncio.run(_run())


def test_long_table_pagination_nonlinear_no_fabrication_and_plot_service() -> None:
    """Verify table pagination (N=100), nonlinear non-fabricated UI display, and Plotly figure data consistency."""
    uc = build_application()
    num_uc = uc._numerical_ode_use_case  # type: ignore[attr-defined]

    resp = num_uc.execute(
        NumericalODERequest(
            raw_equation="y' = -y",
            order=NumericalODEOrder.FIRST_ORDER,
            t0="0",
            y0="1",
            t_end="1",
            step_size="0.01",
            compute_analytical_comparison=True,
        )
    )
    assert len(resp.rows) == 101

    client = Client(ui.page("/test_num_pagination_v2"))
    with client:
        render_numerical_euler_result(resp)

    txt_preview = "\n".join(_collect_texts(client.layout))
    assert "Mở rộng bảng đầy đủ (101 hàng)" in txt_preview

    expand_btn = _find_button_containing(client, "Mở rộng bảng đầy đủ")
    assert expand_btn is not None
    _click_button(client, expand_btn)

    txt_expanded = "\n".join(_collect_texts(client.layout))
    assert "Trang 1/5 (hiển thị n = 0..24)" in txt_expanded

    next_btn = _find_button_containing(client, "Sau")
    assert next_btn is not None
    _click_button(client, next_btn)
    txt_page2 = "\n".join(_collect_texts(client.layout))
    assert "Trang 2/5 (hiển thị n = 25..49)" in txt_page2

    # Check plot services directly
    fig_y = create_numerical_euler_plot(resp, show_exact=True)
    assert fig_y is not None and len(fig_y.data) == 2
    assert list(fig_y.data[0].x) == [r.t for r in resp.rows]
    assert list(fig_y.data[0].y) == [r.y for r in resp.rows]

    # Nonlinear ODE without exact analytical solution omits exact overlay & labels Richardson as estimate
    resp_nl = num_uc.execute(
        NumericalODERequest(
            raw_equation="y' = sin(t*y)",
            order=NumericalODEOrder.FIRST_ORDER,
            t0="0",
            y0="1",
            t_end="0.5",
            step_size="0.1",
            compute_analytical_comparison=True,
        )
    )
    client_nl = Client(ui.page("/test_num_nonlinear_ui"))
    with client_nl:
        render_numerical_euler_result(resp_nl)
    nl_txt = "\n".join(_collect_texts(client_nl.layout))
    assert "Ước lượng sai số bằng giảm nửa bước" in nl_txt
    assert "không phải sai số thực" in nl_txt
    fig_nl = create_numerical_euler_plot(resp_nl, show_exact=True)
    assert fig_nl is not None and len(fig_nl.data) == 1

    # 2nd-order derivative plot with exact overlay
    resp_2 = num_uc.execute(
        NumericalODERequest(
            raw_equation="y'' = -y",
            order=NumericalODEOrder.SECOND_ORDER,
            t0="0",
            y0="0",
            v0="1",
            t_end="1",
            step_size="0.1",
            compute_analytical_comparison=True,
        )
    )
    fig_v = create_numerical_derivative_plot(resp_2, show_exact=True)
    assert fig_v is not None and len(fig_v.data) == 2
    assert list(fig_v.data[0].y) == [r.v for r in resp_2.rows]
