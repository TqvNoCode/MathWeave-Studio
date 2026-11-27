"""Authoritative, strongly typed immutable state model for ODE workspaces."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from math_app.application.dtos import ProblemRequest
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType
from math_app.input.ode_parser import (
    extract_initial_condition_from_string,
    extract_interval_from_string,
    extract_second_order_ics_from_string,
    parse_initial_condition,
    parse_second_order_initial_conditions,
)
import sympy as sp


def split_second_order_equation_clauses(
    raw: str,
) -> tuple[str, str | None, str | None, str | None, str | None]:
    """Split second-order ODE input into (eq_with_interval, y_ic, yp_ic, y1, interval_str).

    Extracts explicit interval constraints before stripping initial conditions so
    connected domain intervals (e.g., t < 0, t > 2, 1 < t < 5) are preserved.
    """
    no_interval, interval_str = extract_interval_from_string(raw)
    clean_eq, y_ic, yp_ic, y1_str = extract_second_order_ics_from_string(no_interval)
    eq_with_interval = f"{clean_eq}, {interval_str}" if interval_str else clean_eq
    return eq_with_interval, y_ic, yp_ic, y1_str, interval_str


def split_first_order_equation_clauses(
    raw: str,
) -> tuple[str, str | None, str | None]:
    """Split first-order ODE input into (eq_with_interval, inline_ic, interval_str)."""
    no_interval, interval_str = extract_interval_from_string(raw)
    clean_eq, inline_ic = extract_initial_condition_from_string(no_interval)
    eq_with_interval = f"{clean_eq}, {interval_str}" if interval_str else clean_eq
    return eq_with_interval, inline_ic, interval_str


class ODEOrder(str, Enum):
    """Supported ODE orders."""

    FIRST_ORDER = "first_order"
    SECOND_ORDER = "second_order"

    @property
    def display_label(self) -> str:
        if self == ODEOrder.FIRST_ORDER:
            return "Cấp 1 (First-Order)"
        return "Cấp 2 (Second-Order)"


class ODEClassification(str, Enum):
    """Detailed mathematical classification of the differential equation."""

    # First-order classifications
    FIRST_ORDER_LINEAR = "first_order_linear"
    FIRST_ORDER_HOMOGENEOUS = "first_order_homogeneous"
    SEPARABLE = "separable"
    EXACT = "exact"
    INTEGRATING_FACTOR = "integrating_factor"

    # Second-order classifications
    SECOND_ORDER_HOMOGENEOUS = "second_order_homogeneous"
    SECOND_ORDER_NONHOMOGENEOUS = "second_order_nonhomogeneous"
    EULER_CAUCHY = "euler_cauchy"

    # Advanced second-order tools
    REDUCTION_OF_ORDER = "reduction_of_order"
    WRONSKIAN = "wronskian"

    @property
    def order(self) -> ODEOrder:
        if self in {
            ODEClassification.FIRST_ORDER_LINEAR,
            ODEClassification.FIRST_ORDER_HOMOGENEOUS,
            ODEClassification.SEPARABLE,
            ODEClassification.EXACT,
            ODEClassification.INTEGRATING_FACTOR,
        }:
            return ODEOrder.FIRST_ORDER
        return ODEOrder.SECOND_ORDER

    @property
    def display_label(self) -> str:
        labels = {
            ODEClassification.FIRST_ORDER_LINEAR: "Tuyến tính cấp 1",
            ODEClassification.FIRST_ORDER_HOMOGENEOUS: "Thuần nhất cấp 1 (y/x)",
            ODEClassification.SEPARABLE: "Tách biến (Separable)",
            ODEClassification.EXACT: "Vi phân toàn phần (Exact)",
            ODEClassification.INTEGRATING_FACTOR: "Thừa số tích phân (μ)",
            ODEClassification.SECOND_ORDER_HOMOGENEOUS: "Thuần nhất: g(t) = 0",
            ODEClassification.SECOND_ORDER_NONHOMOGENEOUS: "Không thuần nhất: g(t) ≢ 0",
            ODEClassification.EULER_CAUCHY: "Euler–Cauchy",
            ODEClassification.REDUCTION_OF_ORDER: "Hạ bậc nghiệm (y₂ = v·y₁)",
            ODEClassification.WRONSKIAN: "Định thức Wronskian",
        }
        return labels[self]

    @property
    def math_subtitle(self) -> str:
        return self.math_subtitle_for_var("t")

    def math_subtitle_for_var(self, var: str = "t") -> str:
        v = var.strip() or "t"
        subtitles = {
            ODEClassification.FIRST_ORDER_LINEAR: f"y' + p({v})y = g({v})",
            ODEClassification.FIRST_ORDER_HOMOGENEOUS: f"y' = F(y/{v})",
            ODEClassification.SEPARABLE: f"y' = f({v})g(y)",
            ODEClassification.EXACT: f"M({v},y)d{v} + N({v},y)dy = 0",
            ODEClassification.INTEGRATING_FACTOR: f"μ({v}) hoặc μ(y)",
            ODEClassification.SECOND_ORDER_HOMOGENEOUS: "ay'' + by' + cy = 0",
            ODEClassification.SECOND_ORDER_NONHOMOGENEOUS: f"ay'' + by' + cy = g({v})",
            ODEClassification.EULER_CAUCHY: f"a{v}^2y'' + b{v}y' + cy = 0",
            ODEClassification.REDUCTION_OF_ORDER: f"y'' + p({v})y' + q({v})y = 0",
            ODEClassification.WRONSKIAN: "W(y₁, y₂) = y₁y₂' - y₁'y₂",
        }
        return subtitles.get(self, f"y' = F({v}, y)")

    @property
    def is_advanced_tool(self) -> bool:
        return self in {ODEClassification.REDUCTION_OF_ORDER, ODEClassification.WRONSKIAN}


class ODEMode(str, Enum):
    """Problem objective mode."""

    GENERAL = "GENERAL"
    CAUCHY_IVP = "CAUCHY_IVP"

    @property
    def display_label(self) -> str:
        if self == ODEMode.GENERAL:
            return "Tìm nghiệm tổng quát"
        return "Bài toán Cauchy (IVP)"


class ODEMethodPreference(str, Enum):
    """Solution method preference for nonhomogeneous second-order ODEs."""

    AUTO = "AUTO"
    UNDETERMINED_COEFFICIENTS = "UNDETERMINED_COEFFICIENTS"
    VARIATION_OF_PARAMETERS = "VARIATION_OF_PARAMETERS"

    @property
    def display_label(self) -> str:
        labels = {
            ODEMethodPreference.AUTO: "Tự động (Khuyến nghị theo vế phải g(t))",
            ODEMethodPreference.UNDETERMINED_COEFFICIENTS: "Hệ số bất định (Undetermined Coefficients)",
            ODEMethodPreference.VARIATION_OF_PARAMETERS: "Biến thiên hằng số (Variation of Parameters)",
        }
        return labels[self]


# Default configurations per classification
DEFAULT_CONFIGS: dict[ODEClassification, dict[str, Any]] = {
    ODEClassification.FIRST_ORDER_LINEAR: {
        "equation": "y' + (1/2)*y = t + 2",
        "target_var": "t",
        "examples": (
            ("Hệ số hằng: y' = 2y + 3", "y' = 2*y + 3"),
            ("Bài toán Cauchy: y' = 2y + 3, y(0) = 1", "y' = 2*y + 3, y(0) = 1"),
            ("Thừa số tích phân: y' + 1/2*y = t + 2", "y' + (1/2)*y = t + 2"),
            ("Thuần nhất: y' + 2ty = 0", "y' + 2*t*y = 0"),
        ),
    },
    ODEClassification.FIRST_ORDER_HOMOGENEOUS: {
        "equation": "y' = (x + y)/x",
        "target_var": "x",
        "examples": (
            ("Cơ bản: y' = (x+y)/x", "y' = (x + y)/x"),
            ("Bậc 2: y' = y/x + (y/x)^2", "y' = y/x + (y/x)^2"),
            ("Bài toán Cauchy: y(1) = 2", "y' = (x + y)/x, y(1) = 2"),
        ),
    },
    ODEClassification.SEPARABLE: {
        "equation": "y' = 2*t*y",
        "target_var": "t",
        "examples": (
            ("Tách biến y' = 2ty", "y' = 2*t*y"),
            ("Nghiệm cân bằng y' = t*(y^2 - 1)", "y' = t*(y^2 - 1)"),
            ("Cauchy y' = 2ty, y(0) = 5", "y' = 2*t*y, y(0) = 5"),
        ),
    },
    ODEClassification.EXACT: {
        "equation": "(2*x*y + 3)*dx + (x^2 + 4*y)*dy = 0",
        "target_var": "x",
        "examples": (
            ("Dạng vi phân (2xy + 3)dx + (x^2 + 4y)dy = 0", "(2*x*y + 3)*dx + (x^2 + 4*y)*dy = 0"),
            ("Dạng đạo hàm (2xy + 3) + (x^2 + 4y)y' = 0", "(2*x*y + 3) + (x^2 + 4*y)*y' = 0"),
            ("Bài toán Cauchy y(0) = 1", "(2*x*y + 3)*dx + (x^2 + 4*y)*dy = 0, y(0) = 1"),
        ),
    },
    ODEClassification.INTEGRATING_FACTOR: {
        "equation": "(3*x*y + y^2)*dx + (x^2 + x*y)*dy = 0",
        "target_var": "x",
        "examples": (
            ("Phụ thuộc x: (3xy + y^2)dx + (x^2 + xy)dy = 0", "(3*x*y + y^2)*dx + (x^2 + x*y)*dy = 0"),
            ("Phụ thuộc y: y*dx + (2*x*y - exp(-2*y))*dy = 0", "y*dx + (2*x*y - exp(-2*y))*dy = 0"),
            ("Bài toán Cauchy: y(1) = 1", "(3*x*y + y^2)*dx + (x^2 + x*y)*dy = 0, y(1) = 1"),
        ),
    },
    ODEClassification.SECOND_ORDER_HOMOGENEOUS: {
        "equation": "y'' - 3*y' - 4*y = 0",
        "target_var": "t",
        "examples": (
            ("Nghiệm thực phân biệt: y'' - 3y' - 4y = 0", "y'' - 3*y' - 4*y = 0"),
            ("Nghiệm kép thực: y'' + 4y' + 4y = 0", "y'' + 4*y' + 4*y = 0"),
            ("Nghiệm thuần ảo: y'' + 4y = 0", "y'' + 4*y = 0"),
            ("Nghiệm phức liên hợp: y'' + 2y' + 5y = 0", "y'' + 2*y' + 5*y = 0"),
            ("Cauchy dao động: y'' + 4y = 0, y(0)=0, y'(0)=2", "y'' + 4*y = 0, y(0) = 0, y'(0) = 2"),
        ),
    },
    ODEClassification.SECOND_ORDER_NONHOMOGENEOUS: {
        "equation": "y'' - 3*y' - 4*y = 3*exp(2*t)",
        "target_var": "t",
        "examples": (
            ("Đa thức mũ: y'' - 3y' - 4y = 3e^(2t)", "y'' - 3*y' - 4*y = 3*exp(2*t)"),
            ("Cộng hưởng đơn mũ: y'' - 3y' - 4y = 2e^(-t)", "y'' - 3*y' - 4*y = 2*exp(-t)"),
            ("Cộng hưởng điều hòa: y'' + 4y = 3cos(2t)", "y'' + 4*y = 3*cos(2*t)"),
            ("Biến thiên hằng số (tan): y'' + y = tan(t)", "y'' + y = tan(t)"),
            ("Biến thiên hằng số (ln): y'' + y = ln(t)", "y'' + y = log(t)"),
            ("Bài toán Cauchy (IVP)", "y'' - 3*y' - 4*y = 3*exp(2*t), y(0) = 1, y'(0) = 0"),
        ),
    },
    ODEClassification.EULER_CAUCHY: {
        "equation": "t^2*y'' + 4*t*y' + 2*y = 0, t > 0",
        "target_var": "t",
        "examples": (
            ("Nghiệm thực phân biệt: t^2*y'' + 4*t*y' + 2*y = 0, t > 0", "t^2*y'' + 4*t*y' + 2*y = 0, t > 0"),
            ("Nghiệm kép thực: t^2*y'' - 3*t*y' + 4*y = 0, t > 0", "t^2*y'' - 3*t*y' + 4*y = 0, t > 0"),
            ("Nghiệm phức liên hợp: t^2*y'' + t*y' + y = 0, t > 0", "t^2*y'' + t*y' + y = 0, t > 0"),
            ("Miền âm: t^2*y'' + 4*t*y' + 2*y = 0, t < 0", "t^2*y'' + 4*t*y' + 2*y = 0, t < 0"),
            ("Bài toán Cauchy (IVP)", "t^2*y'' + 4*t*y' + 2*y = 0, y(1) = 3, y'(1) = 0"),
        ),
    },
    ODEClassification.REDUCTION_OF_ORDER: {
        "equation": "2*t^2*y'' + 3*t*y' - y = 0, y1 = 1/t",
        "target_var": "t",
        "examples": (
            ("Euler-Cauchy: 2t^2*y'' + 3t*y' - y = 0", "2*t^2*y'' + 3*t*y' - y = 0, y1 = 1/t"),
            ("Nghiệm kép: y'' - 2y' + y = 0", "y'' - 2*y' + y = 0, y1 = exp(t)"),
            ("Lượng giác: y'' + y = 0", "y'' + y = 0, y1 = cos(t)"),
            ("Hệ số biến: y'' - (2/t^2)y = 0", "y'' - (2/t^2)*y = 0, y1 = t^2"),
        ),
    },
    ODEClassification.WRONSKIAN: {
        "equation": "cos(t), sin(t)",
        "target_var": "t",
        "examples": (
            ("Lượng giác", "cos(t), sin(t)"),
            ("Hàm mũ", "exp(t), t*exp(t)"),
            ("Hệ lũy thừa", "1/t, sqrt(t)"),
            ("Phụ thuộc tuyến tính", "2*t, 5*t"),
        ),
    },
}


@dataclass(frozen=True)
class ODEState:
    """Strongly typed, immutable state representation for ODE workspaces."""

    order: ODEOrder = ODEOrder.SECOND_ORDER
    classification: ODEClassification = ODEClassification.SECOND_ORDER_NONHOMOGENEOUS
    mode: ODEMode = ODEMode.GENERAL
    equation: str = "y'' - 3*y' - 4*y = 3*exp(2*t)"
    target_var: str = "t"
    initial_condition: str = ""
    known_solution: str = ""
    method_preference: ODEMethodPreference = ODEMethodPreference.AUTO
    initial_condition_draft: str = ""

    @property
    def is_cauchy(self) -> bool:
        """Convenience property indicating whether Cauchy IVP mode is active."""
        return self.mode == ODEMode.CAUCHY_IVP

    @classmethod
    def default_for_classification(cls, classification: ODEClassification) -> ODEState:
        cfg = DEFAULT_CONFIGS[classification]
        return cls(
            order=classification.order,
            classification=classification,
            mode=ODEMode.GENERAL,
            equation=cfg["equation"],
            target_var=cfg["target_var"],
            initial_condition="",
            known_solution="",
            method_preference=ODEMethodPreference.AUTO,
            initial_condition_draft="",
        )

    @classmethod
    def from_operation(cls, op: Any) -> ODEState:
        """Create initial state matching any of the 9 ODE operations.

        F1: Preserves Cauchy initial conditions and known solution from OperationDef.default_input.
        F2: Strictly validates operation type and rejects non-ODE operations.
        """
        pt = op.problem_type if hasattr(op, "problem_type") else op

        mapping = {
            ProblemType.ODE_FIRST_ORDER_LINEAR: (ODEOrder.FIRST_ORDER, ODEClassification.FIRST_ORDER_LINEAR, ODEMode.GENERAL),
            ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS: (ODEOrder.FIRST_ORDER, ODEClassification.FIRST_ORDER_HOMOGENEOUS, ODEMode.GENERAL),
            ProblemType.ODE_SEPARABLE: (ODEOrder.FIRST_ORDER, ODEClassification.SEPARABLE, ODEMode.GENERAL),
            ProblemType.ODE_EXACT: (ODEOrder.FIRST_ORDER, ODEClassification.EXACT, ODEMode.GENERAL),
            ProblemType.ODE_INTEGRATING_FACTOR: (ODEOrder.FIRST_ORDER, ODEClassification.INTEGRATING_FACTOR, ODEMode.GENERAL),
            ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF: (ODEOrder.SECOND_ORDER, ODEClassification.SECOND_ORDER_HOMOGENEOUS, ODEMode.GENERAL),
            ProblemType.ODE_SECOND_ORDER_IVP: (ODEOrder.SECOND_ORDER, ODEClassification.SECOND_ORDER_NONHOMOGENEOUS, ODEMode.CAUCHY_IVP),
            ProblemType.ODE_EULER_CAUCHY: (ODEOrder.SECOND_ORDER, ODEClassification.EULER_CAUCHY, ODEMode.GENERAL),
            ProblemType.ODE_REDUCTION_OF_ORDER: (ODEOrder.SECOND_ORDER, ODEClassification.REDUCTION_OF_ORDER, ODEMode.GENERAL),
            ProblemType.WRONSKIAN: (ODEOrder.SECOND_ORDER, ODEClassification.WRONSKIAN, ODEMode.GENERAL),
        }

        if pt not in mapping:
            op_name = getattr(op, "title", str(pt))
            raise ValueError(f"Thao tác '{op_name}' không phải là phương trình vi phân (ODE) được hỗ trợ.")

        order, classification, mode = mapping[pt]
        cfg = DEFAULT_CONFIGS[classification]

        raw_default = getattr(op, "default_input", "") or cfg["equation"]
        target_v = getattr(op, "target_var", "") or cfg["target_var"]

        clean_eq = raw_default
        extracted_ic = ""
        extracted_y1 = ""

        if order == ODEOrder.SECOND_ORDER:
            c_eq, y_cand, yp_cand, y1_cand, _ = split_second_order_equation_clauses(raw_default)
            if y_cand and yp_cand:
                extracted_ic = f"{y_cand}, {yp_cand}"
                clean_eq = c_eq
            if y1_cand:
                extracted_y1 = y1_cand
                clean_eq = c_eq
            if pt == ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF and raw_default == "y'' - 3*y' - 4*y = 3*exp(2*t)":
                clean_eq = cfg["equation"]
        else:  # FIRST_ORDER
            c_eq, inline_ic, _ = split_first_order_equation_clauses(raw_default)
            if inline_ic:
                extracted_ic = inline_ic
                clean_eq = c_eq

        # If mode is CAUCHY_IVP or if IC was extracted from default_input
        if mode == ODEMode.CAUCHY_IVP:
            final_eq = clean_eq
            final_ic = extracted_ic
            final_draft = extracted_ic
        elif extracted_ic:
            mode = ODEMode.CAUCHY_IVP
            final_eq = clean_eq
            final_ic = extracted_ic
            final_draft = extracted_ic
        else:
            final_eq = clean_eq
            final_ic = ""
            final_draft = ""

        return cls(
            order=order,
            classification=classification,
            mode=mode,
            equation=final_eq,
            target_var=target_v,
            initial_condition=final_ic,
            known_solution=extracted_y1,
            method_preference=ODEMethodPreference.AUTO,
            initial_condition_draft=final_draft,
        )

    def with_order(self, new_order: ODEOrder, preserve_equation: bool = False) -> ODEState:
        """Transition order cleanly, adopting the default classification for that order."""
        if new_order == self.order:
            return self

        if new_order == ODEOrder.FIRST_ORDER:
            st = self.default_for_classification(ODEClassification.FIRST_ORDER_LINEAR)
        else:
            st = self.default_for_classification(ODEClassification.SECOND_ORDER_NONHOMOGENEOUS)

        if preserve_equation and self.equation.strip():
            st = st.with_equation(self.equation.strip())
        return st

    def with_classification(self, new_classification: ODEClassification, preserve_equation: bool = False) -> ODEState:
        """Transition classification within or across orders with appropriate defaults."""
        if new_classification == self.classification:
            return self

        cfg = DEFAULT_CONFIGS[new_classification]

        # Never preserve equation when switching to or from Wronskian (non-ODE pair input)
        if (
            new_classification == ODEClassification.WRONSKIAN
            or self.classification == ODEClassification.WRONSKIAN
        ):
            preserve_equation = False

        # Preserve custom user equation if switching between homogeneous and nonhomogeneous or if explicitly requested
        is_so_pair = (
            self.classification in {ODEClassification.SECOND_ORDER_HOMOGENEOUS, ODEClassification.SECOND_ORDER_NONHOMOGENEOUS}
            and new_classification in {ODEClassification.SECOND_ORDER_HOMOGENEOUS, ODEClassification.SECOND_ORDER_NONHOMOGENEOUS}
        )
        cur_eq = self.equation.strip()
        default_so_eqs = {
            "y'' - 3*y' - 4*y = 0",
            "y'' - 3*y' - 4*y = 3*exp(2*t)",
            "y'' + 5*y' + 6*y = 0",
            "",
        }
        if preserve_equation or (is_so_pair and cur_eq not in default_so_eqs):
            eq_to_use = self.equation
            target_v = self.target_var
        else:
            eq_to_use = cfg["equation"]
            target_v = self.target_var if is_so_pair else cfg["target_var"]

        return ODEState(
            order=new_classification.order,
            classification=new_classification,
            mode=ODEMode.GENERAL if new_classification.is_advanced_tool else self.mode,
            equation=eq_to_use,
            target_var=target_v,
            initial_condition="" if (self.mode == ODEMode.GENERAL or new_classification.is_advanced_tool) else self.initial_condition,
            known_solution=self.known_solution if (preserve_equation and new_classification == ODEClassification.REDUCTION_OF_ORDER) else "",
            method_preference=self.method_preference,
            initial_condition_draft=self.initial_condition_draft or self.initial_condition,
        )

    def with_mode(self, new_mode: ODEMode) -> ODEState:
        """Switch between GENERAL and CAUCHY_IVP while strictly preventing parameter leakage."""
        if new_mode == self.mode:
            return self

        if new_mode == ODEMode.GENERAL:
            # Stash active initial condition into draft and clear active IC
            draft = self.initial_condition if self.initial_condition else self.initial_condition_draft
            # Clean any inline ICs from equation while preserving interval constraints
            clean_eq = self.equation
            if self.order == ODEOrder.SECOND_ORDER:
                clean_e, _, _, _, _ = split_second_order_equation_clauses(self.equation)
                clean_eq = clean_e
            else:
                clean_e, _, _ = split_first_order_equation_clauses(self.equation)
                clean_eq = clean_e

            return ODEState(
                order=self.order,
                classification=self.classification,
                mode=ODEMode.GENERAL,
                equation=clean_eq,
                target_var=self.target_var,
                initial_condition="",  # Strictly empty in GENERAL mode!
                known_solution=self.known_solution,
                method_preference=self.method_preference,
                initial_condition_draft=draft,
            )

        # Transitioning to CAUCHY_IVP: restore from draft if available or extract from equation
        restored_ic = self.initial_condition_draft
        clean_eq = self.equation
        if self.order == ODEOrder.SECOND_ORDER:
            clean_e, y_cand, yp_cand, _, _ = split_second_order_equation_clauses(self.equation)
            if y_cand and yp_cand and not restored_ic:
                restored_ic = f"{y_cand}, {yp_cand}"
            clean_eq = clean_e
        else:
            clean_e, inline_ic, _ = split_first_order_equation_clauses(self.equation)
            if inline_ic and not restored_ic:
                restored_ic = inline_ic
            clean_eq = clean_e

        return ODEState(
            order=self.order,
            classification=self.classification,
            mode=ODEMode.CAUCHY_IVP,
            equation=clean_eq,
            target_var=self.target_var,
            initial_condition=restored_ic,
            known_solution=self.known_solution,
            method_preference=self.method_preference,
            initial_condition_draft=restored_ic,
        )

    def with_equation(self, new_equation: str) -> ODEState:
        return ODEState(
            order=self.order,
            classification=self.classification,
            mode=self.mode,
            equation=new_equation,
            target_var=self.target_var,
            initial_condition=self.initial_condition,
            known_solution=self.known_solution,
            method_preference=self.method_preference,
            initial_condition_draft=self.initial_condition_draft,
        )

    def with_target_var(self, new_var: str) -> ODEState:
        return ODEState(
            order=self.order,
            classification=self.classification,
            mode=self.mode,
            equation=self.equation,
            target_var=new_var.strip() or "t",
            initial_condition=self.initial_condition,
            known_solution=self.known_solution,
            method_preference=self.method_preference,
            initial_condition_draft=self.initial_condition_draft,
        )

    def with_initial_condition(self, new_ic: str) -> ODEState:
        val = new_ic.strip()
        return ODEState(
            order=self.order,
            classification=self.classification,
            mode=ODEMode.CAUCHY_IVP if val else self.mode,
            equation=self.equation,
            target_var=self.target_var,
            initial_condition=val,
            known_solution=self.known_solution,
            method_preference=self.method_preference,
            initial_condition_draft=val if val else self.initial_condition_draft,
        )

    def with_known_solution(self, new_y1: str) -> ODEState:
        return ODEState(
            order=self.order,
            classification=self.classification,
            mode=self.mode,
            equation=self.equation,
            target_var=self.target_var,
            initial_condition=self.initial_condition,
            known_solution=new_y1.strip(),
            method_preference=self.method_preference,
            initial_condition_draft=self.initial_condition_draft,
        )

    def with_method_preference(self, new_pref: ODEMethodPreference) -> ODEState:
        return ODEState(
            order=self.order,
            classification=self.classification,
            mode=self.mode,
            equation=self.equation,
            target_var=self.target_var,
            initial_condition=self.initial_condition,
            known_solution=self.known_solution,
            method_preference=new_pref,
            initial_condition_draft=self.initial_condition_draft,
        )

    def reset(self) -> ODEState:
        """Reset active workspace to clean defaults for the current classification."""
        return self.default_for_classification(self.classification)

    @property
    def problem_type(self) -> ProblemType:
        """Resolve current state to authoritative ProblemType."""
        if self.classification == ODEClassification.FIRST_ORDER_LINEAR:
            return ProblemType.ODE_FIRST_ORDER_LINEAR
        if self.classification == ODEClassification.FIRST_ORDER_HOMOGENEOUS:
            return ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS
        if self.classification == ODEClassification.SEPARABLE:
            return ProblemType.ODE_SEPARABLE
        if self.classification == ODEClassification.EXACT:
            return ProblemType.ODE_EXACT
        if self.classification == ODEClassification.INTEGRATING_FACTOR:
            return ProblemType.ODE_INTEGRATING_FACTOR
        if self.classification == ODEClassification.REDUCTION_OF_ORDER:
            return ProblemType.ODE_REDUCTION_OF_ORDER
        if self.classification == ODEClassification.WRONSKIAN:
            return ProblemType.WRONSKIAN
        if self.classification == ODEClassification.EULER_CAUCHY:
            return ProblemType.ODE_EULER_CAUCHY

        # Second-order constant coefficient
        if self.mode == ODEMode.CAUCHY_IVP:
            return ProblemType.ODE_SECOND_ORDER_IVP
        return ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF

    def build_problem_request(self) -> ProblemRequest:
        """Construct the authoritative ProblemRequest ensuring zero parameter leakage."""
        cleaned_eq = self.equation.strip()
        if not cleaned_eq:
            raise InvalidInputError("Phương trình không được để trống. Vui lòng nhập dữ liệu trước khi thực hiện.")

        pt = self.problem_type
        target_v = self.target_var.strip() or ("x" if self.classification in {
            ODEClassification.FIRST_ORDER_HOMOGENEOUS,
            ODEClassification.EXACT,
            ODEClassification.INTEGRATING_FACTOR,
        } else "t")

        # 1. Advanced Tools
        if self.classification == ODEClassification.WRONSKIAN:
            return ProblemRequest(
                raw_input=cleaned_eq,
                problem_type=ProblemType.WRONSKIAN,
                target_variable=target_v,
                parameters={},
            )

        # Context-aware equation order pre-flight validation
        from math_app.input.ode_parser import validate_ode_order
        expected_order = 1 if self.order == ODEOrder.FIRST_ORDER else 2
        validate_ode_order(cleaned_eq, expected_order=expected_order, indep_var=target_v)

        if self.classification == ODEClassification.REDUCTION_OF_ORDER:
            params: dict[str, Any] = {}
            if self.known_solution:
                params["y1"] = self.known_solution.strip()
            return ProblemRequest(
                raw_input=cleaned_eq,
                problem_type=ProblemType.ODE_REDUCTION_OF_ORDER,
                target_variable=target_v,
                parameters=params,
            )

        # 2. First-Order ODEs
        if self.order == ODEOrder.FIRST_ORDER:
            clean_eq, inline_ic, _ = split_first_order_equation_clauses(cleaned_eq)
            dedicated_ic = self.initial_condition.strip()

            # Deterministic mathematical classification drives solver routing
            from math_app.presentation.components.workspace.ode.first_order_classifier import classify_first_order_ode
            clf = classify_first_order_ode(clean_eq, target_var=target_v)
            if clf.is_valid_ode:
                valid_types = {clf.target_problem_type} if clf.target_problem_type else set()
                for alt in clf.alternative_methods:
                    if "problem_type" in alt:
                        valid_types.add(alt["problem_type"])
                if clf.is_linear:
                    valid_types.add(ProblemType.ODE_FIRST_ORDER_LINEAR)
                if clf.is_separable:
                    valid_types.add(ProblemType.ODE_SEPARABLE)
                if clf.is_exact:
                    valid_types.add(ProblemType.ODE_EXACT)
                if clf.is_classical_homogeneous:
                    valid_types.add(ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS)
                auth_pt = pt if pt in valid_types else (clf.target_problem_type or pt)
            else:
                auth_pt = pt

            if self.mode == ODEMode.GENERAL:
                if inline_ic:
                    raise InvalidInputError(
                        f"Phương trình đang ở chế độ 'Tìm nghiệm tổng quát' nhưng chứa điều kiện ban đầu '{inline_ic}'. "
                        "Vui lòng xóa điều kiện ban đầu khỏi phương trình hoặc chuyển sang chế độ 'Bài toán Cauchy (IVP)'."
                    )
                return ProblemRequest(
                    raw_input=cleaned_eq,
                    problem_type=auth_pt,
                    target_variable=target_v,
                    parameters={},
                )

            # Mode is CAUCHY_IVP
            has_inline = bool(inline_ic)
            has_dedicated = bool(dedicated_ic)

            if not has_inline and not has_dedicated:
                raise InvalidInputError(
                    "Bài toán Cauchy (IVP) yêu cầu cung cấp điều kiện ban đầu y(t0) = y0."
                )

            if has_inline and has_dedicated:
                try:
                    t0_in, y0_in = parse_initial_condition(inline_ic, indep_var=target_v)
                    t0_ded, y0_ded = parse_initial_condition(dedicated_ic, indep_var=target_v)
                except InvalidInputError as err:
                    raise InvalidInputError(f"Lỗi phân tích điều kiện ban đầu: {err}") from err

                same_t0 = sp.simplify(t0_in - t0_ded) == 0
                same_y0 = sp.simplify(y0_in - y0_ded) == 0
                if not (same_t0 and same_y0):
                    raise InvalidInputError(
                        f"Phát hiện xung đột điều kiện ban đầu: Phương trình chứa điều kiện '{inline_ic}', "
                        f"nhưng ô điều kiện ban đầu lại chứa '{dedicated_ic}'. "
                        "Vui lòng chỉ nhập điều kiện ban đầu tại một nơi duy nhất hoặc đồng nhất dữ liệu giữa hai nguồn."
                    )
                auth_ic = dedicated_ic
            elif has_dedicated:
                try:
                    parse_initial_condition(dedicated_ic, indep_var=target_v)
                except InvalidInputError as err:
                    raise InvalidInputError(f"Lỗi phân tích điều kiện ban đầu: {err}") from err
                auth_ic = dedicated_ic
            else:  # has_inline
                try:
                    parse_initial_condition(inline_ic, indep_var=target_v)
                except InvalidInputError as err:
                    raise InvalidInputError(f"Lỗi phân tích điều kiện ban đầu: {err}") from err
                auth_ic = inline_ic

            return ProblemRequest(
                raw_input=clean_eq,
                problem_type=auth_pt,
                target_variable=target_v,
                parameters={"initial_condition": auth_ic},
            )

        # 3. Second-Order Constant Coefficient, Cauchy IVP & Euler-Cauchy
        if self.classification == ODEClassification.EULER_CAUCHY:
            cat = "EULER_CAUCHY"
        elif self.classification == ODEClassification.SECOND_ORDER_HOMOGENEOUS:
            cat = "HOMOGENEOUS"
        else:
            cat = "NONHOMOGENEOUS"
        md = self.mode.value
        pref = self.method_preference.value

        clean_eq, inline_y_ic, inline_yp_ic, _, _ = split_second_order_equation_clauses(cleaned_eq)
        has_inline = bool(inline_y_ic or inline_yp_ic)
        complete_inline = bool(inline_y_ic and inline_yp_ic)

        dedicated_ic = self.initial_condition.strip()
        ded_y_ic: str | None = None
        ded_yp_ic: str | None = None
        if dedicated_ic:
            _, ded_y_ic, ded_yp_ic, _ = extract_second_order_ics_from_string("dummy = 0, " + dedicated_ic)
            if not ded_y_ic and not ded_yp_ic and "=" in dedicated_ic:
                if "'" in dedicated_ic or "prime" in dedicated_ic:
                    ded_yp_ic = dedicated_ic
                else:
                    ded_y_ic = dedicated_ic

        has_dedicated = bool(ded_y_ic or ded_yp_ic)
        complete_dedicated = bool(ded_y_ic and ded_yp_ic)

        if md == "CAUCHY_IVP":
            if has_inline and has_dedicated:
                if not complete_inline or not complete_dedicated:
                    raise InvalidInputError(
                        "Phát hiện xung đột hoặc không đồng nhất điều kiện ban đầu: "
                        "Vui lòng cung cấp đầy đủ cả y(t0) và y'(t0) tại một nơi duy nhất."
                    )
                try:
                    ((t0_in, y0_in), (_, v0_in)) = parse_second_order_initial_conditions(
                        inline_y_ic, inline_yp_ic, target_v  # type: ignore[arg-type]
                    )
                    ((t0_ded, y0_ded), (_, v0_ded)) = parse_second_order_initial_conditions(
                        ded_y_ic, ded_yp_ic, target_v  # type: ignore[arg-type]
                    )
                except InvalidInputError as e:
                    raise InvalidInputError(f"Lỗi phân tích điều kiện ban đầu: {e}") from e

                same_t0 = sp.simplify(t0_in - t0_ded) == 0
                same_y0 = sp.simplify(y0_in - y0_ded) == 0
                same_v0 = sp.simplify(v0_in - v0_ded) == 0
                if not (same_t0 and same_y0 and same_v0):
                    raise InvalidInputError(
                        f"Phát hiện xung đột điều kiện ban đầu: Phương trình chứa điều kiện '{inline_y_ic}, {inline_yp_ic}', "
                        f"nhưng ô điều kiện ban đầu chuyên biệt lại chứa '{ded_y_ic}, {ded_yp_ic}'. "
                        "Vui lòng chỉ nhập điều kiện ban đầu tại một nơi duy nhất hoặc đồng nhất dữ liệu giữa hai nguồn."
                    )
                auth_ic = f"{ded_y_ic}, {ded_yp_ic}"
            elif has_dedicated:
                if not complete_dedicated:
                    raise InvalidInputError(
                        "Bài toán Cauchy (IVP) cấp hai yêu cầu cung cấp đầy đủ hai điều kiện ban đầu: y(t0) = y0 và y'(t0) = v0."
                    )
                parse_second_order_initial_conditions(ded_y_ic, ded_yp_ic, target_v)  # type: ignore[arg-type]
                auth_ic = f"{ded_y_ic}, {ded_yp_ic}"
            elif has_inline:
                if not complete_inline:
                    raise InvalidInputError(
                        "Bài toán Cauchy (IVP) cấp hai yêu cầu cung cấp đầy đủ hai điều kiện ban đầu: y(t0) = y0 và y'(t0) = v0."
                    )
                parse_second_order_initial_conditions(inline_y_ic, inline_yp_ic, target_v)  # type: ignore[arg-type]
                auth_ic = f"{inline_y_ic}, {inline_yp_ic}"
            else:
                raise InvalidInputError(
                    "Bài toán Cauchy (IVP) cấp hai yêu cầu cung cấp đầy đủ hai điều kiện ban đầu: y(t0) = y0 và y'(t0) = v0."
                )

            req_raw = clean_eq
            req_pt = (
                ProblemType.ODE_EULER_CAUCHY
                if self.classification == ODEClassification.EULER_CAUCHY
                else ProblemType.ODE_SECOND_ORDER_IVP
            )
            so_params: dict[str, Any] = {
                "expected_classification": cat,
                "problem_mode": md,
                "initial_condition": auth_ic,
            }
        else:  # GENERAL
            req_raw = cleaned_eq
            req_pt = (
                ProblemType.ODE_EULER_CAUCHY
                if self.classification == ODEClassification.EULER_CAUCHY
                else ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF
            )
            so_params = {
                "expected_classification": cat,
                "problem_mode": md,
            }

        if cat == "NONHOMOGENEOUS":
            so_params["method_preference"] = pref

        return ProblemRequest(
            raw_input=req_raw,
            problem_type=req_pt,
            target_variable=target_v,
            parameters=so_params,
        )
