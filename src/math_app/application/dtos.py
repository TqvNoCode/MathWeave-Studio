"""Data Transfer Objects across application and presentation boundaries."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.domain.step_content import ExpressionStepContent


@dataclass(frozen=True)
class VerificationResult:
    """Carries the outcome of independent mathematical verification."""

    status: VerificationStatus
    method: str
    details: str


VIETNAMESE_RULE_NAMES: dict[str, str] = {
    # Differentiation rules
    "Power Rule": "Quy tắc đạo hàm của lũy thừa",
    "Product Rule": "Quy tắc đạo hàm của tích",
    "Quotient Rule": "Quy tắc đạo hàm của thương",
    "Chain Rule": "Quy tắc đạo hàm của hàm hợp",
    "Constant Rule": "Quy tắc đạo hàm của hằng số",
    "Constant Multiple Rule": "Quy tắc nhân với hằng số",
    "Sum Rule": "Quy tắc đạo hàm của tổng",
    "Difference Rule": "Quy tắc đạo hàm của hiệu",
    "Sum / Difference Rule": "Quy tắc đạo hàm của tổng và hiệu",
    "Trigonometric Rule": "Quy tắc đạo hàm của hàm lượng giác",
    "Exponential Rule": "Quy tắc đạo hàm của hàm mũ",
    "Logarithmic Rule": "Quy tắc đạo hàm của hàm logarit",
    "Square Root Rule": "Quy tắc đạo hàm của căn bậc hai",
    "Identity Variable Rule": "Quy tắc đạo hàm của hàm đồng nhất",
    "Simplification": "Rút gọn biểu thức",
    "Symbolic Differentiation Engine": "Tính toán ký hiệu trực tiếp",
    "Term-by-term Differentiation": "Quy tắc đạo hàm cho từng số hạng",
    "Term-by-term Integration": "Quy tắc nguyên hàm cho từng số hạng",
    "Linearity of Integration": "Tính chất tuyến tính của nguyên hàm",
    # Integration rules
    "Quy tắc hằng số": "Quy tắc tích phân của hằng số",
    "Quy tắc lũy thừa cơ bản": "Quy tắc tích phân của lũy thừa",
    "Quy tắc lũy thừa": "Quy tắc tích phân của lũy thừa",
    "Quy tắc tuyến tính / Tổng hiệu": "Tính chất tuyến tính của nguyên hàm",
    "Quy tắc nghịch đảo": "Quy tắc tích phân hàm phân thức",
    "Quy tắc hàm mũ cơ số e": "Quy tắc tích phân hàm mũ",
    "Quy tắc lượng giác": "Quy tắc tích phân hàm lượng giác",
    "Công cụ tích phân giải tích": "Tích phân giải tích ký hiệu",
    "Hằng số tích phân": "Bổ sung hằng số tích phân C",
    "Định lý cơ bản của Giải tích": "Định lý Newton–Leibniz",
    # Limit rules
    "Thay số trực tiếp": "Thay số trực tiếp",
    "Nhận dạng dạng vô định": "Nhận dạng dạng vô định",
    "Khử dạng vô định và tính giới hạn": "Khử dạng vô định và tính giới hạn",
    # Linear Algebra rules
    "Chuyển vị ma trận": "Chuyển vị ma trận",
    "Công thức định thức cấp 2": "Công thức định thức cấp hai",
    "Định thức cấp hai": "Định thức cấp hai",
    "Kiểm tra định thức": "Kiểm tra tính khả nghịch qua định thức",
    "Ma trận nghịch đảo": "Ma trận nghịch đảo",
    "Biến đổi hàng sơ cấp": "Biến đổi hàng sơ cấp",
    "Xác định hạng ma trận": "Xác định hạng ma trận",
    "Ma trận ban đầu": "Khởi tạo ma trận ban đầu",
    "Hoán đổi hàng": "Hoán đổi hàng",
    "Chuẩn hóa hệ số trụ": "Chuẩn hóa hệ số trụ",
    "Khử phần tử trong cột trụ": "Khử hàng",
    "Khử hàng": "Khử hàng",
    "Phép Cộng hai ma trận": "Cộng hai ma trận",
    "Phép Trừ hai ma trận": "Trừ hai ma trận",
    "Phép nhân ma trận": "Nhân hai ma trận",
    "Lập ma trận mở rộng": "Lập ma trận mở rộng",
}


@dataclass(frozen=True)
class SolutionStep:
    """A discrete pedagogical step in mathematical derivation."""

    step_number: int
    rule_name: str
    description: str
    content: ExpressionStepContent
    substeps: tuple[SolutionStep, ...] = ()
    notes: str | None = None
    title: str = ""
    rule_name_vi: str = ""
    equation_latex: str = ""
    assumptions: tuple[str, ...] = ()

    @property
    def display_rule_name(self) -> str:
        """User-facing Vietnamese rule name without English labels."""
        raw = self.rule_name_vi or self.rule_name
        clean = re.sub(r"\s*\([A-Za-z0-9_\s/+-]+\)$", "", raw).strip()
        if clean in VIETNAMESE_RULE_NAMES:
            return VIETNAMESE_RULE_NAMES[clean]
        if self.rule_name in VIETNAMESE_RULE_NAMES:
            return VIETNAMESE_RULE_NAMES[self.rule_name]
        return clean

    @property
    def display_title(self) -> str:
        """User-facing Vietnamese step title without English labels."""
        if self.title:
            return re.sub(r"\s*\([A-Za-z0-9_\s/+-]+\)$", "", self.title).strip()
        rn = self.display_rule_name
        if rn.lower().startswith("áp dụng") or rn.lower().startswith("tính") or rn.lower().startswith("khử") or rn.lower().startswith("bổ sung"):
            return rn
        return f"Áp dụng {rn.lower()}"


@dataclass(frozen=True)
class ProblemRequest:
    """Input payload dispatched to application use cases."""

    raw_input: str
    problem_type: ProblemType
    target_variable: str = "x"
    assumptions: tuple[str, ...] = ()
    parameters: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SolutionResponse:
    """Normalized, serializable response returned across application boundaries."""

    status: SolutionStatus
    verification: VerificationResult
    raw_input: str
    canonical_input: str
    final_result: str
    final_latex: str
    steps: tuple[SolutionStep, ...] = ()
    domain_restrictions: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    execution_time_ms: float = 0.0
