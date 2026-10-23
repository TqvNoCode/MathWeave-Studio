"""Operation catalog and mathematical domain configuration for MathWeave Studio UI."""

from __future__ import annotations

from dataclasses import dataclass
from math_app.domain.models import ProblemType


@dataclass(frozen=True)
class OperationDef:
    """Definition of an interactive mathematical operation."""

    problem_type: ProblemType
    title: str
    domain: str
    description: str
    icon: str
    default_input: str
    target_var: str = "x"
    extra_fields: tuple[str, ...] = ()
    examples: tuple[tuple[str, str], ...] = ()
    math_icon: str | None = None
    is_menu_card: bool = True

    @property
    def is_matrix(self) -> bool:
        """Return True if this operation is a linear algebra / matrix operation."""
        return self.problem_type.is_matrix

    @property
    def is_calculus(self) -> bool:
        """Return True if this operation is a calculus operation."""
        return self.problem_type.is_calculus


OPERATIONS: list[OperationDef] = [
    # --- Calculus Domain ---
    OperationDef(
        problem_type=ProblemType.DERIVATIVE,
        title="Đạo hàm",
        domain="Giải tích (Calculus)",
        description="Tính đạo hàm bậc 1 hoặc bậc cao, kèm các quy tắc biến đổi và lời giải từng bước.",
        icon="functions",
        math_icon=r"\frac{d^n f}{dx^n}",
        default_input="cos(x) - tan(x)",
        target_var="x",
        extra_fields=("order",),
        examples=(
            ("Đa thức 2x^3 + 6x - 8", "2*x^3 + 6*x - 8"),
            ("cos(x) - tan(x)", "cos(x) - tan(x)"),
            ("Tích x^2 * sin(x)", "x^2 * sin(x)"),
            ("Thương x / (x + 1)", "x / (x + 1)"),
            ("Hợp sin(x^2)", "sin(x^2)"),
            ("Đa thức x^4 - 3x^3 + 2x", "x^4 - 3*x^3 + 2*x"),
        ),
    ),
    OperationDef(
        problem_type=ProblemType.PARTIAL_DERIVATIVE,
        title="Đạo hàm riêng",
        domain="Giải tích (Calculus)",
        description="Tính đạo hàm của hàm nhiều biến theo biến được chọn.",
        icon="alt_route",
        math_icon=r"\frac{\partial f}{\partial x}",
        default_input="x^2*y + sin(x*y) + y^3",
        target_var="x",
        examples=(
            ("∂/∂x [ x^2*y + y^3 ]", "x^2*y + y^3"),
            ("∂/∂y [ x^2 + 3*x*y + y^2 ]", "x^2 + 3*x*y + y^2"),
        ),
    ),
    OperationDef(
        problem_type=ProblemType.INDEFINITE_INTEGRAL,
        title="Tích phân bất định (Nguyên hàm)",
        domain="Giải tích (Calculus)",
        description="Tìm nguyên hàm, giải thích quy tắc sử dụng và bổ sung hằng số tích phân C.",
        icon="stacked_line_chart",
        math_icon=r"\int",
        default_input="x^2",
        target_var="x",
        examples=(
            ("Đa thức 2x^3 + 6x - 8", "2*x^3 + 6*x - 8"),
            ("Lũy thừa x^2", "x^2"),
            ("Lượng giác sin(x)", "sin(x)"),
            ("Tổng đa thức 3*x^2 + 2*x", "3*x^2 + 2*x"),
            ("Hàm mũ exp(x)", "exp(x)"),
        ),
    ),
    OperationDef(
        problem_type=ProblemType.DEFINITE_INTEGRAL,
        title="Tích phân xác định",
        domain="Giải tích (Calculus)",
        description="Tính tích phân xác định một biến, tích phân đường, tích phân mặt và tích phân khối (bội ba).",
        icon="straighten",
        math_icon=r"\int_a^b",
        default_input="x^2",
        target_var="x",
        extra_fields=("lower_bound", "upper_bound"),
        examples=(
            ("∫_0^1 x^2 dx", "x^2"),
            ("∫_0^pi sin(x) dx", "sin(x)"),
            ("∫_1^2 (3*x^2 + 1) dx", "3*x^2 + 1"),
        ),
        is_menu_card=True,
    ),
    OperationDef(
        problem_type=ProblemType.LINE_INTEGRAL,
        title="Tích phân đường",
        domain="Giải tích (Calculus)",
        description="Tính tích phân đường vô hướng ds và tích phân đường trường vectơ F·dr dọc cung C.",
        icon="timeline",
        math_icon=r"\int_C \mathbf{F}\cdot d\mathbf{r}",
        default_input="x + y",
        target_var="t",
        extra_fields=("mode", "param_var", "t_min", "t_max", "param_x", "param_y", "param_z", "orientation"),
        examples=(
            ("Đoạn thẳng: x + y dọc (3t, 4t)", "x + y"),
            ("Trường vectơ: y, -x dọc parabol", "y, -x"),
            ("Đường tròn: 1 ds", "1"),
        ),
        is_menu_card=False,
    ),
    OperationDef(
        problem_type=ProblemType.SURFACE_INTEGRAL,
        title="Tích phân mặt",
        domain="Giải tích (Calculus)",
        description="Tính tích phân mặt vô hướng dS và thông lượng trường vectơ F·n dS qua mặt cong S.",
        icon="layers",
        math_icon=r"\iint_S \mathbf{F}\cdot d\mathbf{S}",
        default_input="z",
        target_var="x",
        extra_fields=("mode", "surface_type", "surface_expr", "u_var", "u_min", "u_max", "v_var", "v_min", "v_max", "orientation"),
        examples=(
            ("Mặt phẳng z = 1 - x - y", "1"),
            ("Thông lượng z dS qua z = x^2 + y^2", "0, 0, z"),
        ),
        is_menu_card=False,
    ),
    OperationDef(
        problem_type=ProblemType.TRIPLE_INTEGRAL,
        title="Tích phân khối",
        domain="Giải tích (Calculus)",
        description="Tính tích phân bội ba f(x, y, z) dV trên khối hộp hoặc miền không gian tọa độ Descartes, trụ, cầu.",
        icon="view_in_ar",
        math_icon=r"\iiint_V f\,dV",
        default_input="x*y*z",
        target_var="x",
        extra_fields=("coord_system", "x_min", "x_max", "y_min", "y_max", "z_min", "z_max"),
        examples=(
            ("Khối hộp [0,1]x[0,2]x[0,3] với x*y*z", "x*y*z"),
            ("Thể tích: 1 dV", "1"),
        ),
        is_menu_card=False,
    ),
    OperationDef(
        problem_type=ProblemType.LIMIT,
        title="Giới hạn hàm số (Limit)",
        domain="Giải tích (Calculus)",
        description="Tính giới hạn một phía hoặc hai phía và giải thích các phép biến đổi cần thiết.",
        icon="filter_tilt_shift",
        math_icon=r"\lim_{x \to a}",
        default_input="sin(x)/x",
        target_var="x",
        extra_fields=("limit_point", "direction"),
        examples=(
            ("lim sin(x)/x khi x->0", "sin(x)/x"),
            ("lim (x^2 - 1)/(x - 1) khi x->1", "(x^2 - 1)/(x - 1)"),
            ("lim 1/x khi x->oo", "1/x"),
        ),
    ),
    OperationDef(
        problem_type=ProblemType.ARC_LENGTH,
        title="Độ dài cung (Arc Length)",
        domain="Giải tích (Calculus)",
        description="Tính độ dài cung đường cong đồ thị y = f(x) hoặc đường cong tham số r(t).",
        icon="gesture",
        math_icon=r"L = \int ds",
        default_input="2*x",
        target_var="x",
        extra_fields=("lower_bound", "upper_bound"),
        examples=(
            ("Đoạn thẳng: y = 2x trên [0, 3]", "2*x"),
            ("Cung tròn tham số: (cos(t), sin(t))", "cos(t), sin(t)"),
        ),
    ),
    OperationDef(
        problem_type=ProblemType.SURFACE_AREA,
        title="Diện tích mặt cong",
        domain="Giải tích (Calculus)",
        description="Tính diện tích mặt cong hiển z = f(x, y) hoặc mặt cong tham số r(u, v).",
        icon="crop_free",
        math_icon=r"A = \iint dS",
        default_input="1 - x - y",
        target_var="x",
        extra_fields=("u_var", "v_var", "u_min", "u_max", "v_min", "v_max"),
        examples=(
            ("Mặt phẳng z = 1 - x - y", "1 - x - y"),
            ("Mặt nón / chỏm cầu", "sqrt(1 - x^2 - y^2)"),
        ),
    ),
    OperationDef(
        problem_type=ProblemType.SURFACE_OF_REVOLUTION,
        title="Mặt & Khối tròn xoay",
        domain="Giải tích (Calculus)",
        description="Tính diện tích mặt tròn xoay và thể tích khối tròn xoay khi quay đồ thị quanh trục Ox hoặc Oy.",
        icon="autorenew",
        math_icon=r"S_{\text{rev}}, V_{\text{rev}}",
        default_input="x",
        target_var="x",
        extra_fields=("axis", "lower_bound", "upper_bound"),
        examples=(
            ("Hình nón: y = x quanh Ox trên [0, 1]", "x"),
            ("Paraboloid: y = x^2 quanh Ox trên [0, 2]", "x^2"),
        ),
    ),

    # --- Vector Calculus Theorems Domain ---
    OperationDef(
        problem_type=ProblemType.GREENS_THEOREM,
        title="Định lý Green",
        domain="Giải tích vectơ (Vector Calculus)",
        description="Kiểm chứng định lý Green: Đối chiếu tích phân đường biên kín và tích phân bội hai (dạng lưu thông / thông lượng).",
        icon="all_inclusive",
        math_icon=r"\oint_{\partial D} = \iint_D",
        default_input="-y, x",
        target_var="x",
        extra_fields=("form", "x_min", "x_max", "y_min", "y_max"),
        examples=(
            ("Trường quay F = (-y, x) trên [0, 1]x[0, 1]", "-y, x"),
            ("Thông lượng F = (x, y) trên [0, 1]x[0, 1]", "x, y"),
        ),
    ),
    OperationDef(
        problem_type=ProblemType.STOKES_THEOREM,
        title="Định lý Stokes",
        domain="Giải tích vectơ (Vector Calculus)",
        description="Kiểm chứng định lý Stokes: Tích phân lưu thông trên biên kín ∂S bằng thông lượng của curl(F) qua mặt S.",
        icon="rotate_right",
        math_icon=r"\oint_{\partial S} = \iint_S \text{curl}",
        default_input="y, -x, 0",
        target_var="x",
        extra_fields=("surface_expr", "x_min", "x_max", "y_min", "y_max"),
        examples=(
            ("F = (y, -x, 0) trên mặt phẳng z = 0", "y, -x, 0"),
            ("F = (y, z, x) trên paraboloid z = 1 - x^2 - y^2", "y, z, x"),
        ),
    ),
    OperationDef(
        problem_type=ProblemType.DIVERGENCE_THEOREM,
        title="Định lý Divergence (Gauss)",
        domain="Giải tích vectơ (Vector Calculus)",
        description="Kiểm chứng định lý Gauss–Ostrogradsky: Thông lượng qua mặt kín bằng tích phân thể tích của div(F).",
        icon="hub",
        math_icon=r"\iint_{\partial V} = \iiint_V \text{div}",
        default_input="x, y, z",
        target_var="x",
        extra_fields=("x_min", "x_max", "y_min", "y_max", "z_min", "z_max"),
        examples=(
            ("Trường xuyên tâm F = (x, y, z) trên lập phương", "x, y, z"),
            ("Trường F = (x^2, y^2, z^2)", "x^2, y^2, z^2"),
        ),
    ),

    # --- Linear Algebra Domain ---
    OperationDef(
        problem_type=ProblemType.MATRIX_DETERMINANT,
        title="Định thức ma trận (Det)",
        domain="Đại số tuyến tính (Linear Algebra)",
        description="Tính định thức ma trận vuông, hiển thị công thức khai triển và các bước tính toán chi tiết.",
        icon="grid_on",
        math_icon=r"\det(A)",
        default_input="[[1, 2], [3, 4]]",
        examples=(
            ("Ma trận vuông 2x2", "[[1, 2], [3, 4]]"),
            ("Ma trận vuông 3x3", "[[1, 2, 3], [0, 1, 4], [5, 6, 0]]"),
        ),
    ),
    OperationDef(
        problem_type=ProblemType.MATRIX_INVERSE,
        title="Ma trận nghịch đảo (A^(-1))",
        domain="Đại số tuyến tính (Linear Algebra)",
        description="Tìm ma trận nghịch đảo qua định thức và ma trận phụ hợp, kiểm tra tính khả nghịch.",
        icon="swap_horiz",
        math_icon=r"A^{-1}",
        default_input="[[1, 2], [3, 4]]",
        examples=(
            ("Ma trận khả nghịch 2x2", "[[1, 2], [3, 4]]"),
            ("Ma trận 3x3", "[[1, 0, 2], [2, -1, 3], [4, 1, 8]]"),
            ("Ma trận suy biến (det=0)", "[[1, 2], [2, 4]]"),
        ),
    ),
    OperationDef(
        problem_type=ProblemType.MATRIX_REF,
        title="Dạng bậc thang (REF)",
        domain="Đại số tuyến tính (Linear Algebra)",
        description="Đưa ma trận về dạng bậc thang bằng thuật toán khử Gauss với các phép biến đổi hàng sơ cấp.",
        icon="stairs",
        math_icon=r"\text{ref}",
        default_input="[[1, 2, -1, -4], [2, 3, -1, -11], [-2, 0, -3, 22]]",
        examples=(
            ("Khử Gauss 3x4", "[[1, 2, -1, -4], [2, 3, -1, -11], [-2, 0, -3, 22]]"),
            ("Ma trận vuông 3x3", "[[2, 1, -1], [-3, -1, 2], [-2, 1, 2]]"),
        ),
    ),
    OperationDef(
        problem_type=ProblemType.MATRIX_RREF,
        title="Dạng bậc thang rút gọn (RREF)",
        domain="Đại số tuyến tính (Linear Algebra)",
        description="Đưa ma trận về dạng bậc thang rút gọn bằng thuật toán khử Gauss–Jordan từng bước.",
        icon="table_view",
        math_icon=r"\text{rref}",
        default_input="[[1, 2, -1, -4], [2, 3, -1, -11], [-2, 0, -3, 22]]",
        examples=(
            ("Hệ 3x4 Gauss-Jordan", "[[1, 2, -1, -4], [2, 3, -1, -11], [-2, 0, -3, 22]]"),
            ("Ma trận 2x2 phụ thuộc tuyến tính", "[[1, 2], [2, 4]]"),
            ("Ma trận 3x3 độc lập", "[[1, 2, 3], [0, 1, 4], [5, 6, 0]]"),
        ),
    ),
    OperationDef(
        problem_type=ProblemType.MATRIX_TRANSPOSE,
        title="Chuyển vị ma trận (A^T)",
        domain="Đại số tuyến tính (Linear Algebra)",
        description="Hoán đổi các hàng thành các cột của ma trận với kích thước bất kỳ.",
        icon="flip",
        math_icon=r"A^T",
        default_input="[[1, 2, 3], [4, 5, 6]]",
        examples=(
            ("Ma trận 2x3", "[[1, 2, 3], [4, 5, 6]]"),
            ("Ma trận vuông 2x2", "[[1, 2], [3, 4]]"),
        ),
    ),
    OperationDef(
        problem_type=ProblemType.MATRIX_RANK,
        title="Hạng ma trận (Rank)",
        domain="Đại số tuyến tính (Linear Algebra)",
        description="Xác định số hàng độc lập tuyến tính thông qua các vị trí trụ của ma trận bậc thang.",
        icon="format_list_bulleted",
        math_icon=r"\text{rank}",
        default_input="[[1, 2, 3], [2, 4, 6], [1, 1, 1]]",
        examples=(
            ("Ma trận 3x3 (Rank 2)", "[[1, 2, 3], [2, 4, 6], [1, 1, 1]]"),
            ("Ma trận độc lập tuyến tính", "[[1, 0, 0], [0, 1, 0], [0, 0, 1]]"),
        ),
    ),
    OperationDef(
        problem_type=ProblemType.MATRIX_ADD_SUB,
        title="Cộng / Trừ ma trận (A ± B)",
        domain="Đại số tuyến tính (Linear Algebra)",
        description="Thực hiện phép cộng hoặc trừ từng phần tử tương ứng của hai ma trận cùng kích thước.",
        icon="add_circle_outline",
        math_icon=r"A \pm B",
        default_input="[[1, 2], [3, 4]] + [[5, 6], [7, 8]]",
        examples=(
            ("Cộng hai ma trận 2x2", "[[1, 2], [3, 4]] + [[5, 6], [7, 8]]"),
            ("Trừ hai ma trận 2x2", "[[5, 6], [7, 8]] - [[1, 2], [3, 4]]"),
        ),
    ),
    OperationDef(
        problem_type=ProblemType.MATRIX_MULTIPLY,
        title="Nhân hai ma trận (A × B)",
        domain="Đại số tuyến tính (Linear Algebra)",
        description="Tính tích hai ma trận tương thích thông qua tích vô hướng giữa hàng và cột.",
        icon="close",
        math_icon=r"A \cdot B",
        default_input="[[1, 2], [3, 4]] * [[5, 6], [7, 8]]",
        examples=(
            ("Nhân hai ma trận 2x2", "[[1, 2], [3, 4]] * [[5, 6], [7, 8]]"),
            ("Nhân (2x3) với (3x2)", "[[1, 2, 3], [4, 5, 6]] * [[1, 2], [3, 4], [5, 6]]"),
        ),
    ),
    OperationDef(
        problem_type=ProblemType.MATRIX_SOLVE_SYSTEM,
        title="Giải hệ phương trình tuyến tính (Ax = b)",
        domain="Đại số tuyến tính (Linear Algebra)",
        description="Giải hệ phương trình tuyến tính bằng ma trận mở rộng và phương pháp Gauss–Jordan.",
        icon="calculate",
        math_icon=r"A\mathbf{x} = \mathbf{b}",
        default_input="[[1, 2], [3, 4]] = [5, 11]",
        examples=(
            ("Hệ 2 ẩn duy nhất nghiệm", "[[1, 2], [3, 4]] = [5, 11]"),
            ("Hệ 3 ẩn 3 phương trình", "[[1, 1, 1], [0, 2, 5], [2, 5, -1]] = [6, -4, 27]"),
        ),
    ),
]


MAIN_OPERATIONS: list[OperationDef] = [op for op in OPERATIONS if op.is_menu_card]


def get_operation_by_type(problem_type: ProblemType) -> OperationDef:
    """Find operation definition by ProblemType."""
    for op in OPERATIONS:
        if op.problem_type == problem_type:
            return op
    return OPERATIONS[0]
