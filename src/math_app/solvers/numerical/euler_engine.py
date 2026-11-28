"""Shared Explicit Euler integration core with first- and second-order ODE adapters."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable

from math_app.domain.numerical_ode import NumericalIterationRow
from math_app.solvers.numerical.expression_adapter import (
    MAX_NUMERIC_MAGNITUDE,
    NumericalDomainError,
    NumericalOverflowError,
    NumericalSingularityError,
)
from math_app.solvers.numerical.time_grid import TimeGrid


@dataclass(frozen=True)
class EulerStepRecord:
    """Raw state vector and derivative vector recorded by the shared Explicit Euler core."""

    step_index: int
    t: float
    state: tuple[float, ...]
    derivatives: tuple[float, ...]
    step_used: float | None


def integrate_explicit_euler(
    grid: TimeGrid,
    initial_state: tuple[float, ...],
    rhs_system: Callable[[float, tuple[float, ...]], tuple[float, ...]],
    max_magnitude: float = MAX_NUMERIC_MAGNITUDE,
) -> tuple[EulerStepRecord, ...]:
    """Execute Explicit Euler integration on a vector ODE z' = G(t, z) over the provided grid.

    Every component of z_{n+1} = z_n + h_n * G(t_n, z_n) is computed strictly from the
    previous step's state z_n (simultaneous update, never semi-implicit).
    """
    if any(not math.isfinite(val) or abs(val) > max_magnitude for val in initial_state):
        raise NumericalOverflowError(
            "Giá trị ban đầu không hữu hạn hoặc vượt quá giới hạn số học an toàn.",
            failing_step=0,
        )

    records: list[EulerStepRecord] = []
    state_curr = initial_state

    for n in range(grid.total_steps):
        t_curr = grid.t_nodes[n]
        h_n = grid.step_deltas[n]

        try:
            deriv = rhs_system(t_curr, state_curr)
        except (NumericalSingularityError, NumericalDomainError, NumericalOverflowError) as exc:
            if exc.failing_step is None:
                exc.failing_step = n
            raise

        if any(not math.isfinite(d) or abs(d) > max_magnitude for d in deriv):
            raise NumericalOverflowError(
                f"Đạo hàm không hữu hạn hoặc tràn số học tại bước n = {n} (t = {t_curr:.6g}).",
                failing_step=n,
            )

        records.append(
            EulerStepRecord(
                step_index=n,
                t=t_curr,
                state=state_curr,
                derivatives=deriv,
                step_used=h_n,
            )
        )

        # Simultaneous Explicit Euler update strictly using previous state_curr
        next_state = tuple(z_i + h_n * d_i for z_i, d_i in zip(state_curr, deriv))
        if any(not math.isfinite(val) or abs(val) > max_magnitude for val in next_state):
            raise NumericalOverflowError(
                f"Tràn số học hoặc giá trị không hữu hạn tại bước n = {n} (t = {t_curr:.6g}).",
                failing_step=n,
            )
        state_curr = next_state

    t_final = grid.t_nodes[-1]
    try:
        final_deriv = rhs_system(t_final, state_curr)
    except (NumericalSingularityError, NumericalDomainError, NumericalOverflowError) as exc:
        if exc.failing_step is None:
            exc.failing_step = grid.total_steps
        raise

    if any(not math.isfinite(d) or abs(d) > max_magnitude for d in final_deriv):
        raise NumericalOverflowError(
            f"Đạo hàm không hữu hạn hoặc tràn số học tại điểm cuối n = {grid.total_steps} (t = {t_final:.6g}).",
            failing_step=grid.total_steps,
        )

    records.append(
        EulerStepRecord(
            step_index=grid.total_steps,
            t=t_final,
            state=state_curr,
            derivatives=final_deriv,
            step_used=None,
        )
    )
    return tuple(records)


class FirstOrderEulerAdapter:
    """Adapter mapping scalar first-order IVP y' = f(t, y) onto the shared Euler engine."""

    def __init__(self, rhs_eval: Callable[[float, float], float], y0: float) -> None:
        self._rhs_eval = rhs_eval
        self._y0 = y0

    @property
    def initial_state(self) -> tuple[float, ...]:
        return (self._y0,)

    def rhs_system(self, t: float, state: tuple[float, ...]) -> tuple[float, ...]:
        return (self._rhs_eval(t, state[0]),)

    @staticmethod
    def to_rows(records: tuple[EulerStepRecord, ...]) -> tuple[NumericalIterationRow, ...]:
        return tuple(
            NumericalIterationRow(
                step_index=rec.step_index,
                t=rec.t,
                y=rec.state[0],
                slope_y=rec.derivatives[0],
                step_used=rec.step_used,
            )
            for rec in records
        )


class SecondOrderEulerAdapter:
    """Adapter transforming y'' = F(t, y, y') into z1' = z2, z2' = F(t, z1, z2)."""

    def __init__(self, rhs_eval: Callable[[float, float, float], float], y0: float, v0: float) -> None:
        self._rhs_eval = rhs_eval
        self._y0 = y0
        self._v0 = v0

    @property
    def initial_state(self) -> tuple[float, ...]:
        return (self._y0, self._v0)

    def rhs_system(self, t: float, state: tuple[float, ...]) -> tuple[float, ...]:
        y_val, v_val = state[0], state[1]
        return (v_val, self._rhs_eval(t, y_val, v_val))

    @staticmethod
    def to_rows(records: tuple[EulerStepRecord, ...]) -> tuple[NumericalIterationRow, ...]:
        return tuple(
            NumericalIterationRow(
                step_index=rec.step_index,
                t=rec.t,
                y=rec.state[0],
                slope_y=rec.derivatives[0],
                step_used=rec.step_used,
                v=rec.state[1],
                slope_v=rec.derivatives[1],
            )
            for rec in records
        )
