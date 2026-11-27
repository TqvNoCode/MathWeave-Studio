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
        problem_type=ProblemType.SOLVE_EQUATION,
        title="Giải phương trình",
        domain="Đại số & Giải tích",
        description="Tìm nghiệm chính xác của phương trình đại số, kèm các bước phân tích nhân tử và kiểm chứng nghiệm.",
        icon="calculate",
        math_icon=r"f(x) = 0",
        default_input="x^2 - 5*x + 6 = 0",
        target_var="x",
        examples=(
            ("Bậc hai: x^2 - 5x + 6 = 0", "x^2 - 5*x + 6 = 0"),
            ("Bậc nhất: 2x + 4 = 0", "2*x + 4 = 0"),
            ("Hằng đẳng thức: x^2 - 4 = 0", "x^2 - 4 = 0"),
            ("Vô nghiệm: x + 1 = x", "x + 1 = x"),
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

    # --- Differential Equations Domain ---
    OperationDef(
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        title="Phương trình vi phân (ODE)",
        domain="Phương trình vi phân (Differential Equations)",
        description="Giải phương trình vi phân tuyến tính cấp 1 (hệ số hằng & biến số), phương trình tách biến và vi phân toàn phần.",
        icon="show_chart",
        math_icon=r"y' + p(t)y = g(t)",
        default_input="y' + (1/2)*y = t + 2",
        target_var="t",
        extra_fields=("initial_condition",),
        examples=(
            ("Hệ số hằng: y' = 2y + 3", "y' = 2*y + 3"),
            ("Bài toán Cauchy: y' = 2y + 3, y(0) = 1", "y' = 2*y + 3, y(0) = 1"),
            ("Thừa số tích phân: y' + 1/2*y = t + 2", "y' + (1/2)*y = t + 2"),
            ("Thuần nhất: y' + 2ty = 0", "y' + 2*t*y = 0"),
            ("Tách biến: y' = 2ty", "y' = 2*t*y"),
            ("Toàn phần: (2xy + 3)dx + (x^2 + 4y)dy = 0", "(2*x*y + 3)*dx + (x^2 + 4*y)*dy = 0"),
        ),
        is_menu_card=True,
    ),
    OperationDef(
        problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
        title="Phương trình thuần nhất cấp 1 (Classical Homogeneous)",
        domain="Phương trình vi phân (Differential Equations)",
        description="Giải phương trình vi phân thuần nhất bậc 0: y' = F(y/x) bằng phép thế y = vx.",
        icon="functions",
        math_icon=r"y' = F\left(\frac{y}{x}\right)",
        default_input="y' = (x + y)/x",
        target_var="x",
        extra_fields=("initial_condition",),
        examples=(
            ("Cơ bản: y' = (x+y)/x", "y' = (x + y)/x"),
            ("Bậc 2: y' = y/x + (y/x)^2", "y' = y/x + (y/x)^2"),
            ("Bài toán Cauchy: y(1) = 2", "y' = (x + y)/x, y(1) = 2"),
        ),
        is_menu_card=False,
    ),
    OperationDef(
        problem_type=ProblemType.ODE_SEPARABLE,
        title="Phương trình tách biến (Separable)",
        domain="Phương trình vi phân (Differential Equations)",
        description="Giải phương trình vi phân dạng y' = f(t)g(y), bảo toàn các nghiệm cân bằng.",
        icon="splitscreen",
        math_icon=r"\frac{dy}{g(y)} = f(t)dt",
        default_input="y' = 2*t*y",
        target_var="t",
        extra_fields=("initial_condition",),
        examples=(
            ("Tách biến y' = 2ty", "y' = 2*t*y"),
            ("Nghiệm cân bằng y' = t*(y^2 - 1)", "y' = t*(y^2 - 1)"),
            ("Cauchy y' = 2ty, y(0) = 5", "y' = 2*t*y, y(0) = 5"),
        ),
        is_menu_card=False,
    ),
    OperationDef(
        problem_type=ProblemType.ODE_EXACT,
        title="Phương trình vi phân toàn phần (Exact)",
        domain="Phương trình vi phân (Differential Equations)",
        description="Kiểm tra điều kiện ∂M/∂y = ∂N/∂x và xác định nghiệm ẩn F(x, y) = C.",
        icon="shape_line",
        math_icon=r"M\,dx + N\,dy = 0",
        default_input="(2*x*y + 3)*dx + (x^2 + 4*y)*dy = 0",
        target_var="x",
        extra_fields=("initial_condition",),
        examples=(
            ("Dạng vi phân (2xy + 3)dx + (x^2 + 4y)dy = 0", "(2*x*y + 3)*dx + (x^2 + 4*y)*dy = 0"),
            ("Dạng đạo hàm (2xy + 3) + (x^2 + 4y)y' = 0", "(2*x*y + 3) + (x^2 + 4*y)*y' = 0"),
            ("Bài toán Cauchy y(0) = 1", "(2*x*y + 3)*dx + (x^2 + 4*y)*dy = 0, y(0) = 1"),
        ),
        is_menu_card=False,
    ),
    OperationDef(
        problem_type=ProblemType.ODE_INTEGRATING_FACTOR,
        title="Thừa số tích phân (Integrating Factor)",
        domain="Phương trình vi phân (Differential Equations)",
        description="Tìm thừa số tích phân μ(x) hoặc μ(y) cho phương trình không toàn phần M dx + N dy = 0.",
        icon="calculate",
        math_icon=r"\mu(x), \; \mu(y)",
        default_input="(3*x*y + y^2)*dx + (x^2 + x*y)*dy = 0",
        target_var="x",
        extra_fields=("initial_condition",),
        examples=(
            ("Phụ thuộc x: (3xy + y^2)dx + (x^2 + xy)dy = 0", "(3*x*y + y^2)*dx + (x^2 + x*y)*dy = 0"),
            ("Phụ thuộc y: y*dx + (2*x*y - exp(-2*y))*dy = 0", "y*dx + (2*x*y - exp(-2*y))*dy = 0"),
            ("Bài toán Cauchy: (3xy + y^2)dx + (x^2 + xy)dy = 0, y(1) = 1", "(3*x*y + y^2)*dx + (x^2 + x*y)*dy = 0, y(1) = 1"),
        ),
        is_menu_card=False,
    ),
    OperationDef(
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        title="Phương trình vi phân cấp 2 (Second-Order)",
        domain="Phương trình vi phân (Differential Equations)",
        description="Giải phương trình vi phân tuyến tính cấp 2 thuần nhất và không thuần nhất, hệ số hằng; hỗ trợ phương pháp hệ số bất định, biến thiên hằng số và bài toán Cauchy.",
        icon="insights",
        math_icon=r"ay'' + by' + cy = g(t)",
        default_input="y'' - 3*y' - 4*y = 3*exp(2*t)",
        target_var="t",
        extra_fields=("initial_condition", "method_preference"),
        examples=(
            ("Hệ số bất định (Đa thức)", "y'' + y' - 2*y = 2*t"),
            ("Hệ số bất định (Mũ)", "y'' - 3*y' - 4*y = 3*exp(2*t)"),
            ("Cộng hưởng mũ", "y'' - 3*y' - 4*y = 3*exp(4*t)"),
            ("Cộng hưởng lượng giác", "y'' + 4*y = cos(2*t)"),
            ("Biến thiên hằng số (tan)", "y'' + y = tan(t)"),
            ("Biến thiên hằng số (ln)", "y'' + y = log(t)"),
            ("Biến thiên hằng số (1/t)", "y'' + y = 1/t"),
            ("Bài toán Cauchy (IVP)", "y'' - 3*y' - 4*y = 3*exp(2*t), y(0) = 1, y'(0) = 0"),
            ("Thuần nhất (Delta > 0)", "y'' + 5*y' + 6*y = 0"),
            ("Thuần nhất (Phức)", "y'' + 4*y = 0"),
        ),
        is_menu_card=True,
    ),
    OperationDef(
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        title="Bài toán Cauchy cấp 2 (Second-Order IVP)",
        domain="Phương trình vi phân (Differential Equations)",
        description="Giải bài toán Cauchy cho phương trình vi phân cấp 2 thuần nhất hoặc không thuần nhất kèm hai điều kiện ban đầu: y(t0) = y0 và y'(t0) = v0.",
        icon="alt_route",
        math_icon=r"y(t_0)=y_0,\, y'(t_0)=v_0",
        default_input="y'' - 3*y' - 4*y = 3*exp(2*t), y(0) = 1, y'(0) = 0",
        target_var="t",
        extra_fields=("initial_condition", "method_preference"),
        examples=(
            ("IVP Hệ số bất định", "y'' - 3*y' - 4*y = 3*exp(2*t), y(0) = 1, y'(0) = 0"),
            ("IVP Biến thiên hằng số (tan)", "y'' + y = tan(t), y(0) = 1, y'(0) = 2"),
            ("IVP Biến thiên hằng số (ln)", "y'' + y = log(t), y(1) = 0, y'(1) = 1"),
            ("IVP Thuần nhất chuẩn tắc", "y'' + 5*y' + 6*y = 0, y(0) = 2, y'(0) = 3"),
            ("IVP Dao động điều hòa", "y'' + 9*y = 0, y(0) = 2, y'(0) = 3"),
            ("IVP Nghiệm kép", "y'' - 2*y' + y = 0, y(0) = 1, y'(0) = 4"),
        ),
        is_menu_card=False,
    ),
    OperationDef(
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        title="Phương trình Euler–Cauchy (Euler–Cauchy)",
        domain="Phương trình vi phân (Differential Equations)",
        description="Giải phương trình vi phân thuần nhất Euler–Cauchy cấp 2: a*t^2*y'' + b*t*y' + c*y = 0 bằng phương trình chỉ số, hỗ trợ nghiệm tổng quát và bài toán Cauchy.",
        icon="functions",
        math_icon=r"a\,t^2y'' + b\,ty' + c\,y = 0",
        default_input="t^2*y'' + 4*t*y' + 2*y = 0, t > 0",
        target_var="t",
        extra_fields=("initial_condition",),
        examples=(
            ("Nghiệm thực phân biệt", "t^2*y'' + 4*t*y' + 2*y = 0, t > 0"),
            ("Nghiệm kép thực", "t^2*y'' - 3*t*y' + 4*y = 0, t > 0"),
            ("Nghiệm phức liên hợp", "t^2*y'' + t*y' + y = 0, t > 0"),
            ("Miền âm", "t^2*y'' + 4*t*y' + 2*y = 0, t < 0"),
            ("Bài toán Cauchy", "t^2*y'' + 4*t*y' + 2*y = 0, y(1) = 3, y'(1) = 0"),
        ),
        is_menu_card=False,
    ),
    OperationDef(
        problem_type=ProblemType.ODE_REDUCTION_OF_ORDER,
        title="Hạ bậc phương trình cấp 2 (Reduction of Order)",
        domain="Phương trình vi phân (Differential Equations)",
        description="Tìm nghiệm cơ bản thứ hai y2(t) = v(t)y1(t) khi đã biết một nghiệm y1(t) của y'' + p(t)y' + q(t)y = 0.",
        icon="trending_down",
        math_icon=r"y_2(t) = v(t)y_1(t)",
        default_input="2*t^2*y'' + 3*t*y' - y = 0, y1 = 1/t",
        target_var="t",
        extra_fields=("known_solution",),
        examples=(
            ("Euler-Cauchy: 2t^2*y'' + 3t*y' - y = 0", "2*t^2*y'' + 3*t*y' - y = 0, y1 = 1/t"),
            ("Nghiệm kép: y'' - 2y' + y = 0", "y'' - 2*y' + y = 0, y1 = exp(t)"),
            ("Lượng giác: y'' + y = 0", "y'' + y = 0, y1 = cos(t)"),
            ("Hệ số biến: y'' - (2/t^2)y = 0", "y'' - (2/t^2)*y = 0, y1 = t^2"),
        ),
        is_menu_card=False,
    ),
    OperationDef(
        problem_type=ProblemType.WRONSKIAN,
        title="Định thức Wronskian & Độc lập tuyến tính",
        domain="Phương trình vi phân (Differential Equations)",
        description="Tính định thức Wronskian W(y1, y2) = y1*y2' - y1'*y2 và kiểm tra tính độc lập tuyến tính của hai nghiệm.",
        icon="grid_view",
        math_icon=r"W(y_1, y_2)",
        default_input="cos(t), sin(t)",
        target_var="t",
        extra_fields=(),
        examples=(
            ("Lượng giác", "cos(t), sin(t)"),
            ("Hàm mũ", "exp(t), t*exp(t)"),
            ("Hệ lũy thừa", "1/t, sqrt(t)"),
            ("Phụ thuộc tuyến tính", "2*t, 5*t"),
        ),
        is_menu_card=False,
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


def get_second_order_examples(
    category: str = "HOMOGENEOUS",
    mode: str = "GENERAL",
) -> list[tuple[str, str]]:
    """Return contextual example problems for second-order ODE interface based on
    classification category ('HOMOGENEOUS' or 'NONHOMOGENEOUS') and problem mode ('GENERAL' or 'CAUCHY_IVP').
    """
    cat = category.strip().upper()
    m = mode.strip().upper()
    if cat in ("HOMOGENEOUS", "THUẦN NHẤT", "THUAN_NHAT"):
        if m in ("CAUCHY_IVP", "IVP", "CAUCHY"):
            return [
                ("Dao động điều hòa: y'' + 4y = 0, y(0)=0, y'(0)=2", "y'' + 4*y = 0, y(0) = 0, y'(0) = 2"),
                ("Nghiệm thực: y'' - 3y' + 2y = 0, y(0)=1, y'(0)=0", "y'' - 3*y' + 2*y = 0, y(0) = 1, y'(0) = 0"),
                ("Tắt dần: y'' + 2y' + 2y = 0, y(0)=1, y'(0)=1", "y'' + 2*y' + 2*y = 0, y(0) = 1, y'(0) = 1"),
                ("Nghiệm kép: y'' - 4y' + 4y = 0, y(0)=2, y'(0)=1", "y'' - 4*y' + 4*y = 0, y(0) = 2, y'(0) = 1"),
            ]
        else:
            return [
                ("Nghiệm thực phân biệt: y'' - 3y' - 4y = 0", "y'' - 3*y' - 4*y = 0"),
                ("Nghiệm kép thực: y'' + 4y' + 4y = 0", "y'' + 4*y' + 4*y = 0"),
                ("Nghiệm thuần ảo: y'' + 4y = 0", "y'' + 4*y = 0"),
                ("Nghiệm phức liên hợp: y'' + 2y' + 5y = 0", "y'' + 2*y' + 5*y = 0"),
                ("Đối xứng r = ±1: y'' - y = 0", "y'' - y = 0"),
                ("Bậc hai thuần túy: y'' = 0", "y'' = 0"),
            ]
    else:  # NONHOMOGENEOUS
        if m in ("CAUCHY_IVP", "IVP", "CAUCHY"):
            return [
                ("IVP Mũ: y'' - 3y' - 4y = 3e^(2t), y(0)=1, y'(0)=0", "y'' - 3*y' - 4*y = 3*exp(2*t), y(0) = 1, y'(0) = 0"),
                ("IVP Đa thức: y'' + 4y = 4t, y(0)=1, y'(0)=2", "y'' + 4*y = 4*t, y(0) = 1, y'(0) = 2"),
                ("IVP Lượng giác: y'' + y = tan(t), y(0)=1, y'(0)=0", "y'' + y = tan(t), y(0) = 1, y'(0) = 0"),
                ("IVP Cộng hưởng: y'' - 2y' + y = t*e^t, y(0)=0, y'(0)=1", "y'' - 2*y' + y = t*exp(t), y(0) = 0, y'(0) = 1"),
            ]
        else:
            return [
                ("Đa thức mũ: y'' - 3y' - 4y = 3e^(2t)", "y'' - 3*y' - 4*y = 3*exp(2*t)"),
                ("Cộng hưởng đơn mũ: y'' - 3y' - 4y = 2e^(-t)", "y'' - 3*y' - 4*y = 2*exp(-t)"),
                ("Cộng hưởng điều hòa: y'' + 4y = 3cos(2t)", "y'' + 4*y = 3*cos(2*t)"),
                ("Cộng hưởng bội hai: y'' - 2y' + y = t*e^t", "y'' - 2*y' + y = t*exp(t)"),
                ("Biến thiên hằng số (tan): y'' + y = tan(t)", "y'' + y = tan(t)"),
                ("Biến thiên hằng số (ln): y'' + y = ln(t)", "y'' + y = ln(t)"),
                ("Hàm đặc biệt: y'' + y = 1/t", "y'' + y = 1/t"),
            ]
