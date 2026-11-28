"""Shared drift-free Decimal time-grid builder and step-halving grid subdivision."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from math_app.domain.exceptions import InvalidInputError


class GridLimitExceededError(Exception):
    """Raised when the requested interval and step size exceed max_steps."""

    def __init__(self, required_steps: int, max_steps: int, min_step_size: float) -> None:
        self.required_steps = required_steps
        self.max_steps = max_steps
        self.min_step_size = min_step_size
        super().__init__(
            f"Số bước lặp yêu cầu ({required_steps:,}) vượt quá giới hạn an toàn tối đa "
            f"({max_steps:,} bước). Hệ thống không tự ý cắt bớt phép tính; "
            f"vui lòng tăng bước nhảy lên tối thiểu h ≥ {min_step_size:.6g} hoặc thu hẹp khoảng [t₀, T]."
        )


@dataclass(frozen=True)
class TimeGrid:
    """Immutable drift-free numerical integration time grid."""

    t0: float
    t_end: float
    step_size: float
    direction: int
    total_steps: int
    has_shortened_final_step: bool
    final_step_size: float
    t_nodes: tuple[float, ...]
    step_deltas: tuple[float, ...]
    t_nodes_dec: tuple[Decimal, ...]


def build_time_grid(
    t0_dec: Decimal,
    t_end_dec: Decimal,
    h_dec: Decimal,
    max_steps: int,
) -> TimeGrid:
    """Construct a drift-free Decimal time grid from t0 to T with positive step magnitude h."""
    if h_dec <= 0:
        raise InvalidInputError("Bước nhảy h phải là số dương (h > 0).")
    if t0_dec == t_end_dec:
        raise InvalidInputError("Điểm bắt đầu t₀ và điểm kết thúc T phải khác nhau (t₀ ≠ T).")
    if max_steps <= 0:
        raise InvalidInputError("Giới hạn số bước lặp tối đa phải dương.")

    direction = 1 if t_end_dec > t0_dec else -1
    span = abs(t_end_dec - t0_dec)
    full_steps = int(span // h_dec)
    rem = span - (Decimal(full_steps) * h_dec)
    tol_dec = h_dec * Decimal("1e-12")
    if rem <= tol_dec:
        rem = Decimal(0)
    elif abs(h_dec - rem) <= tol_dec:
        full_steps += 1
        rem = Decimal(0)

    has_shortened_final_step = rem > 0
    total_steps = full_steps + (1 if has_shortened_final_step else 0)
    if total_steps <= 0:
        total_steps = 1
        has_shortened_final_step = True

    if total_steps > max_steps:
        min_h = float(span / Decimal(max_steps))
        raise GridLimitExceededError(total_steps, max_steps, min_h)

    signed_h_dec = h_dec if direction > 0 else -h_dec
    t_dec_nodes: list[Decimal] = [
        t0_dec + (Decimal(i) * signed_h_dec) for i in range(full_steps + 1)
    ]
    if has_shortened_final_step:
        t_dec_nodes.append(t_end_dec)
    else:
        t_dec_nodes[-1] = t_end_dec

    t_nodes = tuple(float(d) for d in t_dec_nodes)
    step_deltas = tuple(float(t_dec_nodes[i + 1] - t_dec_nodes[i]) for i in range(total_steps))
    final_step_mag = abs(step_deltas[-1])

    return TimeGrid(
        t0=float(t0_dec),
        t_end=float(t_end_dec),
        step_size=float(h_dec),
        direction=direction,
        total_steps=total_steps,
        has_shortened_final_step=has_shortened_final_step,
        final_step_size=final_step_mag,
        t_nodes=t_nodes,
        step_deltas=step_deltas,
        t_nodes_dec=tuple(t_dec_nodes),
    )


def subdivide_time_grid_half(grid: TimeGrid) -> TimeGrid:
    """Subdivide every interval [t_n, t_{n+1}] in half so fine.t_nodes[2*n] == grid.t_nodes[n]."""
    fine_dec: list[Decimal] = []
    nodes_dec = grid.t_nodes_dec
    for i in range(len(nodes_dec) - 1):
        t_left = nodes_dec[i]
        t_right = nodes_dec[i + 1]
        t_mid = (t_left + t_right) / Decimal(2)
        fine_dec.append(t_left)
        fine_dec.append(t_mid)
    fine_dec.append(nodes_dec[-1])

    total_steps = len(fine_dec) - 1
    t_nodes = tuple(float(d) for d in fine_dec)
    step_deltas = tuple(float(fine_dec[i + 1] - fine_dec[i]) for i in range(total_steps))
    return TimeGrid(
        t0=grid.t0,
        t_end=grid.t_end,
        step_size=grid.step_size / 2.0,
        direction=grid.direction,
        total_steps=total_steps,
        has_shortened_final_step=grid.has_shortened_final_step,
        final_step_size=abs(step_deltas[-1]),
        t_nodes=t_nodes,
        step_deltas=step_deltas,
        t_nodes_dec=tuple(fine_dec),
    )
