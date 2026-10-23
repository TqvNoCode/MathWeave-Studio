"""Verification status badge component for NiceGUI."""

from __future__ import annotations

from nicegui import ui

from math_app.application.dtos import VerificationResult
from math_app.domain.models import VerificationStatus


def render_verification_badge(verification: VerificationResult, has_valid_result: bool = True) -> None:
    """Render a visual badge communicating verification confidence and audit method.

    Enforces that a green verified badge is ONLY rendered when a non-empty valid result
    exists AND the verifier actually confirmed mathematical validity.
    """
    if not has_valid_result:
        with ui.badge("Chưa có kết quả", color="grey").classes("text-sm px-2.5 py-1 font-medium"):
            ui.tooltip("Chưa có kết quả hợp lệ để tiến hành kiểm định toán học.")
        return

    if verification.status == VerificationStatus.VERIFIED:
        with ui.badge("✓ Đã kiểm chứng toán học", color="positive").classes("text-sm px-2.5 py-1 font-medium shadow-sm"):
            ui.tooltip(f"Phương pháp: {verification.method} — {verification.details}")
    elif verification.status == VerificationStatus.FAILED:
        with ui.badge("✗ Phát hiện sai lệch toán học", color="negative").classes("text-sm px-2.5 py-1 font-medium shadow-sm"):
            ui.tooltip(f"Cảnh báo kiểm định: {verification.details}")
    elif verification.status == VerificationStatus.UNVERIFIED:
        with ui.badge("⚠ Chưa kiểm chứng độc lập", color="amber-7").classes("text-sm px-2.5 py-1 font-medium text-white shadow-sm"):
            ui.tooltip(f"Giới hạn kiểm chứng: {verification.details}")
    else:
        with ui.badge("Không áp dụng kiểm chứng", color="grey").classes("text-sm px-2.5 py-1 font-medium"):
            ui.tooltip(verification.details)
