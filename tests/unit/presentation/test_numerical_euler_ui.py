"""Presentation and NiceGUI client interaction tests for Explicit Euler numerical ODE mode."""

from __future__ import annotations

import asyncio

from nicegui import Client, app, core, ui

from math_app.domain.models import ProblemType
from math_app.domain.numerical_ode import NumericalODEOrder, NumericalODERequest
from math_app.main import build_application
from math_app.presentation.app import create_app
from math_app.presentation.components.operation_catalog import get_operation_by_type
from math_app.presentation.components.workspace.ode.numerical_result_view import render_numerical_euler_result
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


def test_numerical_parameters_hidden_by_default_and_mode_switch_works() -> None:
    """Analytical mode stays clean by default; selecting Explicit Euler reveals numerical inputs cleanly."""
    uc = build_application()
    op = get_operation_by_type(ProblemType.ODE_FIRST_ORDER_LINEAR)

    client = Client(ui.page("/test_num_default_hidden"))
    with client:
        render_ode_workspace(op, uc)

    labels = [el._props.get("label", "") for el in client.elements.values() if isinstance(el, ui.input)]
    assert not any("Bước nhảy" in lbl for lbl in labels)
    assert not any("Điểm kết thúc" in lbl for lbl in labels)

    num_btn = _find_button_containing(client, "Phương pháp Euler tiến (Explicit Euler)")
    assert num_btn is not None
    _click_button(client, num_btn)

    num_labels = [el._props.get("label", "") for el in client.elements.values() if isinstance(el, ui.input)]
    assert any("Điểm bắt đầu t₀" in lbl for lbl in num_labels)
    assert any("Giá trị ban đầu y₀" in lbl for lbl in num_labels)
    assert any("Điểm kết thúc T" in lbl for lbl in num_labels)
    assert any("Bước nhảy h" in lbl for lbl in num_labels)

    # Switch back to analytical
    ana_btn = _find_button_containing(client, "Giải tích (Nghiệm chính xác)")
    assert ana_btn is not None
    _click_button(client, ana_btn)
    restored_labels = [el._props.get("label", "") for el in client.elements.values() if isinstance(el, ui.input)]
    assert not any("Bước nhảy" in lbl for lbl in restored_labels)


def test_first_order_and_second_order_numerical_submission_in_nicegui_client() -> None:
    """Verify full async solve, 7-section display, analytical comparison, invalid error, and stale clearing."""
    async def _run() -> None:
        core.loop = asyncio.get_running_loop()
        uc = build_application()
        create_app(uc)
        route = [r for r in app.routes if getattr(r, "path", None) == "/"][0]

        # 1. Deep-link numerical mode
        client = Client(ui.page("/test_num_e2e_1st"))
        with client:
            route.endpoint.__wrapped__(op=ProblemType.ODE_FIRST_ORDER_LINEAR.value, mode="numerical")

        solve_btn = _find_button_containing(client, "TÍNH XẤP XỈ EULER TIẾN")
        assert solve_btn is not None
        _click_button(client, solve_btn)

        body_txt = await _wait_for_text(client, "1. Tóm tắt bài toán")
        for expected in (
            "1. Tóm tắt bài toán",
            "2. Phương pháp số áp dụng",
            "3. Tham số đã chọn",
            "4. Kết quả xấp xỉ cuối cùng",
            "5. Bảng giá trị lặp",
            "6. Đồ thị xấp xỉ số",
            "7. Giải thích sư phạm chi tiết",
            "2.593742",
            "Đối chiếu giải tích",
        ):
            assert expected in body_txt, f"Missing '{expected}' in numerical 1st-order result"

        # Verify Plotly element created from actual solver data
        plots = [el for el in client.elements.values() if isinstance(el, ui.plotly)]
        assert len(plots) == 1
        assert len(plots[0].figure["data"][0]["x"]) == 11

        # Verify editing parameter clears stale result
        inputs = {el._props.get("label", ""): el for el in client.elements.values() if isinstance(el, ui.input)}
        h_inp = next(v for k, v in inputs.items() if "Bước nhảy" in k)
        with client:
            h_inp.set_value("0.2")
        cleared_txt = "\n".join(_collect_texts(client.layout))
        assert "1. Tóm tắt bài toán" not in cleared_txt

        # 2. Switch to 2nd-order inside numerical mode & verify distinct v0 label
        ord2_btn = _find_button_containing(client, "PTVP Cấp 2")
        assert ord2_btn is not None
        _click_button(client, ord2_btn)

        inputs2 = {el._props.get("label", ""): el for el in client.elements.values() if isinstance(el, ui.input)}
        assert any("Đạo hàm ban đầu v₀ = y'(t₀)" in k for k in inputs2)
        assert any("Vị trí ban đầu y₀ = y(t₀)" in k for k in inputs2)

        solve_btn2 = _find_button_containing(client, "TÍNH XẤP XỈ EULER TIẾN")
        assert solve_btn2 is not None
        _click_button(client, solve_btn2)
        body2 = await _wait_for_text(client, "1. Tóm tắt bài toán")
        assert "Giai đoạn 1: Chuyển PTVP cấp 2 về hệ phương trình cấp 1" in body2
        plots2 = [el for el in client.elements.values() if isinstance(el, ui.plotly)]
        assert len(plots2) >= 1

        # 3. Invalid input (h = 0) renders error card without crash
        h_inp2 = next(v for k, v in inputs2.items() if "Bước nhảy" in k)
        with client:
            h_inp2.set_value("0")
        _click_button(client, solve_btn2)
        err_txt = await _wait_for_text(client, "h > 0")
        assert "h > 0" in err_txt

    asyncio.run(_run())


def test_long_table_pagination_and_plotly_figure_service() -> None:
    """Verify table preview/expand/pagination for N=100 and Plotly figure data consistency."""
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

    client = Client(ui.page("/test_num_pagination"))
    with client:
        render_numerical_euler_result(resp)

    txt_preview = "\n".join(_collect_texts(client.layout))
    assert "Mở rộng bảng đầy đủ (101 hàng)" in txt_preview
    assert "độ chính xác dấu phẩy động đầy đủ" in txt_preview

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

    resp_2 = num_uc.execute(
        NumericalODERequest(
            raw_equation="y'' = -y",
            order=NumericalODEOrder.SECOND_ORDER,
            t0="0",
            y0="0",
            v0="1",
            t_end="1",
            step_size="0.1",
            compute_analytical_comparison=False,
        )
    )
    fig_v = create_numerical_derivative_plot(resp_2)
    assert fig_v is not None and len(fig_v.data[0].y) == len(resp_2.rows)
