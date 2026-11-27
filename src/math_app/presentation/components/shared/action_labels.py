"""Authoritative primary action button labels and icons per ProblemType."""

from __future__ import annotations

from dataclasses import dataclass

from math_app.domain.models import ProblemType


@dataclass(frozen=True)
class PrimaryActionSpec:
    """Display label, Material icon, and accessible description for a module's primary CTA."""

    label: str
    icon: str
    aria_label: str


_ACTION_SPECS: dict[ProblemType, PrimaryActionSpec] = {
    # Traditional Calculus & Algebra
    ProblemType.DERIVATIVE: PrimaryActionSpec(
        label="TÍNH ĐẠO HÀM",
        icon="functions",
        aria_label="Tính đạo hàm của biểu thức đã nhập",
    ),
    ProblemType.HIGHER_ORDER_DERIVATIVE: PrimaryActionSpec(
        label="TÍNH ĐẠO HÀM",
        icon="functions",
        aria_label="Tính đạo hàm cấp cao của biểu thức đã nhập",
    ),
    ProblemType.PARTIAL_DERIVATIVE: PrimaryActionSpec(
        label="TÍNH ĐẠO HÀM RIÊNG",
        icon="alt_route",
        aria_label="Tính đạo hàm riêng theo biến đã chọn",
    ),
    ProblemType.INDEFINITE_INTEGRAL: PrimaryActionSpec(
        label="TÍNH NGUYÊN HÀM",
        icon="stacked_line_chart",
        aria_label="Tính tích phân bất định (nguyên hàm)",
    ),
    ProblemType.INTEGRAL: PrimaryActionSpec(
        label="TÍNH NGUYÊN HÀM",
        icon="stacked_line_chart",
        aria_label="Tính tích phân bất định (nguyên hàm)",
    ),
    ProblemType.DEFINITE_INTEGRAL: PrimaryActionSpec(
        label="TÍNH TÍCH PHÂN",
        icon="straighten",
        aria_label="Tính tích phân xác định trên khoảng đã chọn",
    ),
    ProblemType.LINE_INTEGRAL: PrimaryActionSpec(
        label="TÍNH TÍCH PHÂN ĐƯỜNG",
        icon="timeline",
        aria_label="Tính tích phân đường dọc cung C",
    ),
    ProblemType.SURFACE_INTEGRAL: PrimaryActionSpec(
        label="TÍNH TÍCH PHÂN MẶT",
        icon="layers",
        aria_label="Tính tích phân mặt trên mặt cong S",
    ),
    ProblemType.TRIPLE_INTEGRAL: PrimaryActionSpec(
        label="TÍNH TÍCH PHÂN KHỐI",
        icon="view_in_ar",
        aria_label="Tính tích phân bội ba trong không gian V",
    ),
    ProblemType.LIMIT: PrimaryActionSpec(
        label="TÍNH GIỚI HẠN",
        icon="filter_tilt_shift",
        aria_label="Tính giới hạn hàm số tại điểm đã chọn",
    ),
    ProblemType.SOLVE_EQUATION: PrimaryActionSpec(
        label="GIẢI PHƯƠNG TRÌNH",
        icon="calculate",
        aria_label="Giải phương trình đại số",
    ),
    ProblemType.ARC_LENGTH: PrimaryActionSpec(
        label="TÍNH ĐỘ DÀI CUNG",
        icon="gesture",
        aria_label="Tính độ dài cung đường cong",
    ),
    ProblemType.SURFACE_AREA: PrimaryActionSpec(
        label="TÍNH DIỆN TÍCH MẶT CONG",
        icon="crop_free",
        aria_label="Tính diện tích mặt cong S",
    ),
    ProblemType.SURFACE_OF_REVOLUTION: PrimaryActionSpec(
        label="TÍNH MẶT & KHỐI TRÒN XOAY",
        icon="autorenew",
        aria_label="Tính diện tích mặt tròn xoay và thể tích khối tròn xoay",
    ),
    # Vector Calculus Theorems
    ProblemType.GREENS_THEOREM: PrimaryActionSpec(
        label="KIỂM CHỨNG ĐỊNH LÝ GREEN",
        icon="all_inclusive",
        aria_label="Kiểm chứng định lý Green trên miền đã chọn",
    ),
    ProblemType.STOKES_THEOREM: PrimaryActionSpec(
        label="KIỂM CHỨNG ĐỊNH LÝ STOKES",
        icon="rotate_right",
        aria_label="Kiểm chứng định lý Stokes trên mặt cong S",
    ),
    ProblemType.DIVERGENCE_THEOREM: PrimaryActionSpec(
        label="KIỂM CHỨNG ĐỊNH LÝ DIVERGENCE",
        icon="hub",
        aria_label="Kiểm chứng định lý Divergence (Gauss–Ostrogradsky)",
    ),
    # Differential Equations
    ProblemType.ODE_FIRST_ORDER_LINEAR: PrimaryActionSpec(
        label="GIẢI PHƯƠNG TRÌNH VI PHÂN",
        icon="calculate",
        aria_label="Giải phương trình vi phân cấp 1",
    ),
    ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS: PrimaryActionSpec(
        label="GIẢI PHƯƠNG TRÌNH VI PHÂN",
        icon="calculate",
        aria_label="Giải phương trình vi phân thuần nhất cấp 1",
    ),
    ProblemType.ODE_SEPARABLE: PrimaryActionSpec(
        label="GIẢI PHƯƠNG TRÌNH VI PHÂN",
        icon="calculate",
        aria_label="Giải phương trình vi phân tách biến",
    ),
    ProblemType.ODE_EXACT: PrimaryActionSpec(
        label="GIẢI PHƯƠNG TRÌNH VI PHÂN",
        icon="calculate",
        aria_label="Giải phương trình vi phân toàn phần",
    ),
    ProblemType.ODE_INTEGRATING_FACTOR: PrimaryActionSpec(
        label="GIẢI PHƯƠNG TRÌNH VI PHÂN",
        icon="calculate",
        aria_label="Giải phương trình vi phân bằng thừa số tích phân",
    ),
    ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF: PrimaryActionSpec(
        label="GIẢI PHƯƠNG TRÌNH VI PHÂN CẤP 2",
        icon="calculate",
        aria_label="Giải phương trình vi phân cấp 2",
    ),
    ProblemType.ODE_SECOND_ORDER_IVP: PrimaryActionSpec(
        label="GIẢI PHƯƠNG TRÌNH VI PHÂN CẤP 2",
        icon="calculate",
        aria_label="Giải bài toán Cauchy cho phương trình vi phân cấp 2",
    ),
    ProblemType.ODE_EULER_CAUCHY: PrimaryActionSpec(
        label="GIẢI PHƯƠNG TRÌNH VI PHÂN CẤP 2",
        icon="calculate",
        aria_label="Giải phương trình vi phân Euler–Cauchy cấp 2",
    ),
    ProblemType.ODE_REDUCTION_OF_ORDER: PrimaryActionSpec(
        label="GIẢI PHƯƠNG TRÌNH VI PHÂN CẤP 2",
        icon="calculate",
        aria_label="Hạ bậc phương trình vi phân cấp 2",
    ),
    ProblemType.WRONSKIAN: PrimaryActionSpec(
        label="TÍNH ĐỊNH THỨC WRONSKIAN",
        icon="grid_view",
        aria_label="Tính định thức Wronskian và kiểm tra độc lập tuyến tính",
    ),
    # Linear Algebra / Matrices
    ProblemType.MATRIX_DETERMINANT: PrimaryActionSpec(
        label="TÍNH ĐỊNH THỨC",
        icon="grid_on",
        aria_label="Tính định thức của ma trận A",
    ),
    ProblemType.MATRIX_INVERSE: PrimaryActionSpec(
        label="TÌM MA TRẬN NGHỊCH ĐẢO",
        icon="swap_horiz",
        aria_label="Tìm ma trận nghịch đảo của A",
    ),
    ProblemType.MATRIX_REF: PrimaryActionSpec(
        label="BIẾN ĐỔI BẬC THANG (REF)",
        icon="stairs",
        aria_label="Đưa ma trận về dạng bậc thang bằng khử Gauss",
    ),
    ProblemType.MATRIX_RREF: PrimaryActionSpec(
        label="BIẾN ĐỔI BẬC THANG RÚT GỌN",
        icon="table_view",
        aria_label="Đưa ma trận về dạng bậc thang rút gọn Gauss–Jordan",
    ),
    ProblemType.MATRIX_TRANSPOSE: PrimaryActionSpec(
        label="TÍNH MA TRẬN CHUYỂN VỊ",
        icon="flip",
        aria_label="Tính ma trận chuyển vị của A",
    ),
    ProblemType.MATRIX_RANK: PrimaryActionSpec(
        label="TÍNH HẠNG MA TRẬN",
        icon="format_list_bulleted",
        aria_label="Tính hạng của ma trận A",
    ),
    ProblemType.MATRIX_ADD_SUB: PrimaryActionSpec(
        label="TÍNH TỔNG / HIỆU MA TRẬN",
        icon="add_circle_outline",
        aria_label="Tính tổng hoặc hiệu hai ma trận",
    ),
    ProblemType.MATRIX_MULTIPLY: PrimaryActionSpec(
        label="TÍNH TÍCH MA TRẬN",
        icon="close",
        aria_label="Tính tích hai ma trận A và B",
    ),
    ProblemType.MATRIX_SOLVE_SYSTEM: PrimaryActionSpec(
        label="GIẢI HỆ PHƯƠNG TRÌNH TUYẾN TÍNH",
        icon="calculate",
        aria_label="Giải hệ phương trình tuyến tính Ax = b",
    ),
}


def get_primary_action_spec(problem_type: ProblemType) -> PrimaryActionSpec:
    """Return the exact primary action label, icon, and aria-label for a ProblemType."""
    if problem_type in _ACTION_SPECS:
        return _ACTION_SPECS[problem_type]
    if problem_type.is_matrix:
        return PrimaryActionSpec(
            label="THỰC HIỆN PHÉP TOÁN MA TRẬN",
            icon="grid_view",
            aria_label="Thực hiện phép toán ma trận",
        )
    return PrimaryActionSpec(
        label="THỰC HIỆN PHÉP TÍNH",
        icon="functions",
        aria_label="Thực hiện phép tính toán học",
    )
