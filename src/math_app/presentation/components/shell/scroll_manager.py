"""Navigation scroll manager for MathWeave Studio.

Provides deterministic client-side scroll position isolation and restoration
between the main operation catalog (Screen A) and mathematical workspaces (Screen B).
"""

from __future__ import annotations

from typing import Any
from nicegui import ui


def _resolve_client(client: Any = None) -> Any:
    """Resolve an active NiceGUI Client instance even if the current slot has been deleted."""
    if client is not None:
        return client
    try:
        from nicegui import context

        # Try standard context.client
        try:
            return context.client
        except Exception:
            pass

        # If current slot's parent was deleted during screen clear(), search slot stack for a live element
        for slot in reversed(context.slot_stack):
            try:
                parent = slot.parent
                if parent is not None and not getattr(parent, "is_deleted", False):
                    return parent.client
            except Exception:
                continue
    except Exception:
        pass
    return None


def _run_js_safe(code: str, client: Any = None) -> None:
    """Safely execute JavaScript on the client, gracefully no-oping in headless test contexts."""
    try:
        from nicegui import core

        target_client = _resolve_client(client)
        if target_client is not None and hasattr(target_client, "outbox"):
            target_id = getattr(target_client, "_temporary_socket_id", None) or getattr(target_client, "id", None)
            target_client.outbox.enqueue_message("run_javascript", {"code": code}, target_id)
        elif target_client is not None and hasattr(target_client, "run_javascript"):
            target_client.run_javascript(code)
        elif getattr(core, "loop", None) is not None:
            ui.run_javascript(code)
    except Exception:
        pass


def capture_catalog_scroll(client: Any = None) -> None:
    """Capture and preserve the current Screen A catalog scroll position."""
    _run_js_safe(
        "window._mw_catalog_scroll = window.scrollY || window.pageYOffset || "
        "(document.scrollingElement ? document.scrollingElement.scrollTop : 0) || "
        "document.documentElement.scrollTop || document.body.scrollTop || 0;",
        client=client,
    )


def reset_workspace_scroll(client: Any = None) -> None:
    """Reset the scrolling container to top when entering a new workspace (Screen B).

    Guarantees the application header and workspace navigation bar are fully visible.
    Dispatches immediately, via macro-task (setTimeout), and via animation frame (rAF)
    for seamless compatibility across both visible interactive windows and headless/offscreen runners.
    """
    _run_js_safe(
        "(() => { "
        "  const resetScroll = () => { "
        "    window.scrollTo({top: 0, left: 0, behavior: 'instant'}); "
        "    if (document.scrollingElement) document.scrollingElement.scrollTop = 0; "
        "    if (document.documentElement) document.documentElement.scrollTop = 0; "
        "    if (document.body) document.body.scrollTop = 0; "
        "    const qPage = document.querySelector('.q-page'); if (qPage) qPage.scrollTop = 0; "
        "    const qContainer = document.querySelector('.q-page-container'); if (qContainer) qContainer.scrollTop = 0; "
        "  }; "
        "  resetScroll(); "
        "  setTimeout(resetScroll, 0); "
        "  if (typeof requestAnimationFrame === 'function') requestAnimationFrame(resetScroll); "
        "})();",
        client=client,
    )


def restore_catalog_scroll(client: Any = None) -> None:
    """Restore the previously captured Screen A catalog scroll position."""
    _run_js_safe(
        "(() => { "
        "  const restoreScroll = () => { "
        "    const pos = (typeof window._mw_catalog_scroll === 'number' && window._mw_catalog_scroll > 0) "
        "      ? window._mw_catalog_scroll : 0; "
        "    window.scrollTo({top: pos, left: 0, behavior: 'instant'}); "
        "    if (document.scrollingElement) document.scrollingElement.scrollTop = pos; "
        "    if (document.documentElement) document.documentElement.scrollTop = pos; "
        "    if (document.body) document.body.scrollTop = pos; "
        "    const qPage = document.querySelector('.q-page'); if (qPage) qPage.scrollTop = pos; "
        "    const qContainer = document.querySelector('.q-page-container'); if (qContainer) qContainer.scrollTop = pos; "
        "  }; "
        "  restoreScroll(); "
        "  setTimeout(restoreScroll, 0); "
        "  if (typeof requestAnimationFrame === 'function') requestAnimationFrame(restoreScroll); "
        "})();",
        client=client,
    )
