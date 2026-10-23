"""Step builder for constructing serializable differentiation derivation steps."""

from __future__ import annotations

import sympy as sp

from math_app.application.dtos import SolutionStep
from math_app.domain.step_content import ExpressionStepContent
from math_app.rendering.latex.formatter import expr_to_latex


class DifferentiationStepBuilder:
    """Builder for accumulating discrete mathematical derivation steps."""

    def __init__(self, start_step: int = 1) -> None:
        self._current_step_number = start_step
        self._steps: list[SolutionStep] = []

    def add_step(
        self,
        rule_name: str,
        description: str,
        before: sp.Expr | str,
        after: sp.Expr | str,
        substeps: tuple[SolutionStep, ...] = (),
        notes: str | None = None,
        title: str = "",
        rule_name_vi: str = "",
        equation_latex: str = "",
        assumptions: tuple[str, ...] = (),
    ) -> SolutionStep:
        content = ExpressionStepContent(
            expression_before=str(before),
            expression_after=str(after),
            latex_before=expr_to_latex(before),
            latex_after=expr_to_latex(after),
        )

        step = SolutionStep(
            step_number=self._current_step_number,
            rule_name=rule_name,
            description=description,
            content=content,
            substeps=substeps,
            notes=notes,
            title=title,
            rule_name_vi=rule_name_vi,
            equation_latex=equation_latex,
            assumptions=assumptions,
        )
        self._steps.append(step)
        self._current_step_number += 1
        return step

    def create_sub_builder(self) -> DifferentiationStepBuilder:
        """Create an isolated step builder for recording nested sub-derivations."""
        return DifferentiationStepBuilder(start_step=1)

    def get_steps(self) -> tuple[SolutionStep, ...]:
        """Return the immutable tuple of recorded steps."""
        return tuple(self._steps)
