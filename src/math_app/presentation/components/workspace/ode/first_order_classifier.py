"""Authoritative, AST-grounded First-Order ODE Mathematical Classifier.

Provides deterministic mathematical classification, extracted components,
multi-classification detection, educational explanations, and intelligent
solving-method recommendations for first-order differential equations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import sympy as sp

from math_app.domain.models import ProblemType
from math_app.input.ode_parser import (
    check_classical_homogeneous_ode,
    detect_ode_order,
    extract_initial_condition_from_string,
    extract_interval_from_string,
    extract_second_order_ics_from_string,
    parse_ode_input,
    ParsedODE,
)
from math_app.rendering.latex.formatter import expr_to_latex


@dataclass(frozen=True)
class FirstOrderClassificationResult:
    """Detailed mathematical classification output for a first-order differential equation."""

    # Validation & Order
    is_valid_ode: bool
    detected_order: int  # 0: algebraic, 1: first-order, 2: second-order, >=3: higher-order
    error_message: str | None = None
    order_mismatch_recommendation: str | None = None

    # Primary Mathematical Classification
    primary_category: str = "UNKNOWN"
    primary_title: str = "Phương trình vi phân cấp 1"
    canonical_form_latex: str = ""
    target_problem_type: ProblemType = ProblemType.ODE_FIRST_ORDER_LINEAR

    # Linearity and Homogeneity details
    is_linear: bool = False
    is_linear_homogeneous: bool = False
    p_expr_latex: str | None = None
    g_expr_latex: str | None = None
    reference_homogeneous_latex: str | None = None

    # Separability details
    is_separable: bool = False
    f_expr_latex: str | None = None
    g_sep_latex: str | None = None

    # Exactness details
    is_exact_form: bool = False  # Has M dt + N dy structure
    is_exact: bool = False       # Satisfies ∂M/∂y == ∂N/∂t
    M_expr_latex: str | None = None
    N_expr_latex: str | None = None
    dM_dy_latex: str | None = None
    dN_dt_latex: str | None = None

    # Classical Homogeneous (Ratio form F(y/t))
    is_classical_homogeneous: bool = False
    F_v_latex: str | None = None

    # Multi-classification capabilities
    additional_categories: list[dict[str, str]] = field(default_factory=list)

    # Recommended and Alternative Solving Methods
    recommended_method_id: str = "INTEGRATING_FACTOR"
    recommended_method_title: str = "Thừa số tích phân (Integrating Factor)"
    recommended_method_reason: str = ""
    alternative_methods: list[dict[str, str]] = field(default_factory=list)

    # Pedagogical explanation of why classification is valid
    explanation_points: list[str] = field(default_factory=list)

    # Educational guide ("Help me identify this equation")
    identification_guide: list[str] = field(default_factory=list)

    # Variable and Parameter breakdown
    detected_independent_var: str = "t"
    detected_dependent_var: str = "y"
    detected_parameters: list[str] = field(default_factory=list)


def classify_first_order_ode(
    raw_equation: str,
    target_var: str = "t",
    dep_var: str = "y",
) -> FirstOrderClassificationResult:
    """Classify a differential equation using deterministic AST and mathematical properties.

    Bypasses external LLMs to ensure strict reproducibility, exact mathematical
    invariants, and zero hallucination.
    """
    clean_eq = raw_equation.strip()
    if not clean_eq:
        return FirstOrderClassificationResult(
            is_valid_ode=False,
            detected_order=0,
            error_message="Phương trình không được để trống. Vui lòng nhập phương trình vi phân cấp 1.",
        )

    # 1. Clean out intervals and initial conditions before order detection
    eq_no_int, _ = extract_interval_from_string(clean_eq)
    eq_pure, _, _, _ = extract_second_order_ics_from_string(eq_no_int)
    eq_pure, _ = extract_initial_condition_from_string(eq_pure)
    eq_pure = eq_pure.strip()

    c_indep = target_var.strip() if target_var else "t"
    c_dep = dep_var.strip() if dep_var else "y"

    # 2. Equation Order Detection
    detected_order = detect_ode_order(eq_pure, indep_var=c_indep, dep_var=c_dep)

    if detected_order == 2:
        return FirstOrderClassificationResult(
            is_valid_ode=False,
            detected_order=2,
            error_message="Bạn đang nhập phương trình vi phân cấp 2, nhưng không gian làm việc hiện tại chỉ hỗ trợ phương trình cấp 1.",
            order_mismatch_recommendation="Vui lòng chuyển sang không gian làm việc Phương trình vi phân cấp 2.",
        )
    if detected_order >= 3:
        return FirstOrderClassificationResult(
            is_valid_ode=False,
            detected_order=detected_order,
            error_message="Bạn đang nhập phương trình vi phân cấp cao (cấp 3 trở lên), nhưng ứng dụng hiện tại chỉ hỗ trợ phương trình vi phân cấp 1 và cấp 2.",
        )
    if detected_order == 0:
        return FirstOrderClassificationResult(
            is_valid_ode=False,
            detected_order=0,
            error_message=f"Không phát hiện đạo hàm cấp 1 ({c_dep}' hoặc d{c_dep}/d{c_indep}) trong phương trình.",
            order_mismatch_recommendation="Vui lòng nhập phương trình vi phân có chứa đạo hàm hoặc chuyển sang danh mục giải phương trình đại số.",
        )

    # 3. Parse Equation with parse_ode_input
    try:
        parsed: ParsedODE = parse_ode_input(
            eq_pure,
            target_variable=c_indep,
            dependent_variable=c_dep,
        )
    except Exception as exc:
        return FirstOrderClassificationResult(
            is_valid_ode=False,
            detected_order=1,
            error_message=f"Lỗi cú pháp toán học: {exc}",
        )

    var = parsed.independent_var
    dep = parsed.dependent_var
    yp_sym = sp.Symbol("y_prime")
    var_name = str(var)
    dep_name = str(dep)
    raw_params = sorted([str(s) for s in parsed.standard_expr.free_symbols if s not in (var, dep, yp_sym, sp.Symbol("y_double_prime"))])

    # 4. Property Detection: Linearity, Separability, Exactness, Ratio Homogeneity
    is_linear = parsed.is_linear
    is_linear_homog = False
    p_expr = parsed.p_expr
    g_expr = parsed.g_expr
    p_latex = None
    g_latex = None
    ref_homog_latex = None

    if is_linear and p_expr is not None and g_expr is not None:
        is_linear_homog = bool(sp.simplify(g_expr) == 0)
        p_latex = expr_to_latex(p_expr)
        g_latex = expr_to_latex(g_expr)
        # Reference homogeneous counterpart: y' + p(t)y = 0
        if not is_linear_homog:
            ref_homog_latex = f"{dep_name}' + ({p_latex}){dep_name} = 0" if p_latex != "1" else f"{dep_name}' + {dep_name} = 0"

    # Separability Analysis
    is_separable = False
    f_sep_latex = None
    g_sep_latex = None

    try:
        yp_sols = sp.solve(parsed.standard_expr, yp_sym)
        if yp_sols:
            real_branches = [sp.simplify(s) for s in yp_sols if not s.has(sp.I)]
            if real_branches:
                rhs_expr = real_branches[0]
                # Factor RHS into f(t) * g(y)
                factored = sp.factor(rhs_expr)
                f_cand, g_cand = factored.as_independent(dep, as_Add=False)
                if not (dep not in f_cand.free_symbols and var not in g_cand.free_symbols and sp.simplify(f_cand * g_cand - rhs_expr) == 0):
                    f_cand, g_cand = sp.factor_terms(rhs_expr).as_independent(dep, as_Add=False)
                if dep not in f_cand.free_symbols and var not in g_cand.free_symbols and sp.simplify(f_cand * g_cand - rhs_expr) == 0:
                    is_separable = True
                    f_sep_latex = expr_to_latex(f_cand)
                    g_sep_latex = expr_to_latex(g_cand)
    except Exception:
        pass

    # Exactness Analysis: M(t, y) dt + N(t, y) dy = 0  <=>  M(t, y) + N(t, y)*y' = 0
    is_exact_form = False
    is_exact = False
    M_expr = None
    N_expr = None
    dM_dy = None
    dN_dt = None
    M_latex = None
    N_latex = None
    dM_dy_latex = None
    dN_dt_latex = None

    try:
        expanded_std = sp.expand(parsed.standard_expr)
        N_cand = expanded_std.coeff(yp_sym, 1)
        M_cand = expanded_std.coeff(yp_sym, 0)
        if N_cand != 0 and yp_sym not in M_cand.free_symbols:
            is_exact_form = True
            M_expr = sp.simplify(M_cand)
            N_expr = sp.simplify(N_cand)
            dM_dy = sp.simplify(sp.diff(M_expr, dep))
            dN_dt = sp.simplify(sp.diff(N_expr, var))
            is_exact = bool(sp.simplify(dM_dy - dN_dt) == 0)

            M_latex = expr_to_latex(M_expr)
            N_latex = expr_to_latex(N_expr)
            dM_dy_latex = expr_to_latex(dM_dy)
            dN_dt_latex = expr_to_latex(dN_dt)
    except Exception:
        pass

    # Classical Homogeneous Analysis: y' = F(y/t)
    is_classical_homog = False
    F_v_latex = None
    try:
        is_ch, F_v = check_classical_homogeneous_ode(parsed.standard_expr, var, dep)
        if is_ch and F_v is not None:
            is_classical_homog = True
            F_v_latex = expr_to_latex(sp.Symbol("F(v)"))
    except Exception:
        pass

    # 5. Determine Primary Classification, Explanations, and Recommendations
    additional_cats: list[dict[str, str]] = []
    explanation: list[str] = []
    guide: list[str] = []
    alt_methods: list[dict[str, str]] = []

    # Case A: Linear Differential Equation
    if is_linear:
        explanation.append("Bậc cao nhất của đạo hàm trong phương trình là cấp một ($y'$).")
        explanation.append(f"Hàm số chưa biết ${dep_name}$ và đạo hàm ${dep_name}'$ xuất hiện tuyến tính bậc nhất.")

        if is_linear_homog:
            primary_cat = "LINEAR_HOMOGENEOUS"
            primary_title = "Phương trình vi phân tuyến tính thuần nhất cấp 1"
            canon_latex = f"{dep_name}' + p({var_name}){dep_name} = 0"
            target_pt = ProblemType.ODE_FIRST_ORDER_LINEAR
            explanation.append(f"Vế phải (số hạng tự do) triệt tiêu: $g({var_name}) = 0$.")
            explanation.append(f"Hệ số xác định: $p({var_name}) = {p_latex}$.")

            rec_method_id = "INTEGRATING_FACTOR"
            rec_method_title = "Thừa số tích phân (Integrating Factor)"
            rec_method_reason = (
                f"Phương trình có dạng chuẩn $y' + p({var_name})y = 0$. "
                f"Sử dụng thừa số tích phân $\\mu({var_name}) = e^{{\\int p({var_name})\\,d{var_name}}} = e^{{\\int ({p_latex})\\,d{var_name}}}$ "
                "để tích phân trực tiếp nghiệm tổng quát."
            )

            if is_separable:
                additional_cats.append({
                    "category": "SEPARABLE",
                    "title": "Phương trình tách biến (Separable ODE)",
                    "reason": f"Có thể viết lại dưới dạng $\\frac{{d{dep_name}}}{{{dep_name}}} = -({p_latex})\\,d{var_name}$ để tách biến.",
                })
                alt_methods.append({
                    "method_id": "SEPARATION_OF_VARIABLES",
                    "title": "Phân tách biến số (Separation of Variables)",
                    "description": f"Chuyển {dep_name} về vế trái và {var_name} về vế phải: $\\int \\frac{{d{dep_name}}}{{{dep_name}}} = -\\int ({p_latex})\\,d{var_name}$.",
                    "problem_type": ProblemType.ODE_SEPARABLE,
                })

            guide.extend([
                "Dấu hiệu nhận biết: $y$ và $y'$ đều có bậc 1, không nhân với nhau, không nằm trong hàm phi tuyến (như $\\sin(y), e^y$), và vế phải bằng 0.",
                "Tránh nhầm lẫn: Thuần nhất ở đây có nghĩa là 'vế phải bằng 0' ($g(t)=0$), khác hoàn toàn với phương trình thuần nhất tỷ số $y' = F(y/t)$.",
            ])
        else:
            primary_cat = "LINEAR_NONHOMOGENEOUS"
            primary_title = "Phương trình vi phân tuyến tính không thuần nhất cấp 1"
            canon_latex = f"{dep_name}' + p({var_name}){dep_name} = g({var_name})"
            target_pt = ProblemType.ODE_FIRST_ORDER_LINEAR
            explanation.append(f"Vế phải khác không: $g({var_name}) = {g_latex} \\neq 0$ (phương trình có ngoại lực/hàm cưỡng bức).")
            explanation.append(f"Các thành phần trích xuất: $p({var_name}) = {p_latex}$ và $g({var_name}) = {g_latex}$.")

            rec_method_id = "INTEGRATING_FACTOR"
            rec_method_title = "Thừa số tích phân (Integrating Factor)"
            rec_method_reason = (
                f"Đây là phương pháp tổng quát và tối ưu nhất cho PTVP tuyến tính cấp 1. "
                f"Nhân hai vế với thừa số tích phân $\\mu({var_name}) = e^{{\\int p({var_name})\\,d{var_name}}}$ "
                f"giúp biến đổi vế trái thành đạo hàm tích $(\\mu \\cdot y)' = \\mu \\cdot g({var_name})$."
            )

            # If it happens to also be classical homogeneous (e.g. y' = (x+y)/x)
            if is_classical_homog:
                additional_cats.append({
                    "category": "CLASSICAL_HOMOGENEOUS",
                    "title": "Thuần nhất dạng tỷ số (Homogeneous Ratio)",
                    "reason": "Vế phải đồng thời biểu diễn được dưới dạng hàm tỷ số $y/x$.",
                })
                alt_methods.append({
                    "method_id": "HOMOGENEOUS_SUBSTITUTION",
                    "title": "Đổi biến số tỷ số (y = v·x)",
                    "description": "Đặt $y = v \\cdot x$ để đưa về phương trình tách biến theo $v$ và $x$.",
                    "problem_type": ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
                })

            guide.extend([
                "Dấu hiệu nhận biết: Có dạng $y' + p(t)y = g(t)$. Số hạng tự do $g(t) \\neq 0$.",
                "Quy tắc giải chuẩn: 1. Tìm $\\mu(t) = e^{\\int p(t)dt}$; 2. Nhân hai vế với $\\mu(t)$; 3. Tích phân hai vế: $\\mu(t)y = \\int \\mu(t)g(t)dt + C$.",
            ])

    # Case B: Exact Differential Equation
    elif is_exact and is_exact_form:
        primary_cat = "EXACT"
        primary_title = "Phương trình vi phân toàn phần (Exact ODE)"
        canon_latex = f"M({var_name},{dep_name})\\,d{var_name} + N({var_name},{dep_name})\\,d{dep_name} = 0"
        target_pt = ProblemType.ODE_EXACT

        explanation.append(f"Phương trình được biểu diễn ở dạng vi phân $M\\,d{var_name} + N\\,d{dep_name} = 0$.")
        if raw_params:
            explanation.append(f"Xác định vai trò biến số: Biến độc lập là ${var_name}$, hàm số chưa biết là ${dep_name}$, và tham số hằng là {', '.join(f'${p}$' for p in raw_params)}.")
        explanation.append(f"Hàm $M({var_name}, {dep_name}) = {M_latex}$ và $N({var_name}, {dep_name}) = {N_latex}$.")
        explanation.append(
            f"Thỏa mãn điều kiện vi phân toàn phần (Euler-Cauchy exactness test): "
            f"$\\frac{{\\partial M}}{{\\partial {dep_name}}} = {dM_dy_latex}$ bằng "
            f"$\\frac{{\\partial N}}{{\\partial {var_name}}} = {dN_dt_latex}$."
        )

        rec_method_id = "POTENTIAL_FUNCTION"
        rec_method_title = "Tích phân hàm thế vị (Potential Function)"
        rec_method_reason = (
            f"Do $\\frac{{\\partial M}}{{\\partial {dep_name}}} = \\frac{{\\partial N}}{{\\partial {var_name}}}$, "
            f"tồn tại hàm thế vị $\\Psi({var_name}, {dep_name})$ sao cho $d\\Psi = M\\,d{var_name} + N\\,d{dep_name} = 0$. "
            "Nghiệm tổng quát có dạng $\\Psi(t, y) = C$."
        )

        if is_separable:
            additional_cats.append({
                "category": "SEPARABLE",
                "title": "Phương trình tách biến (Separable ODE)",
                "reason": "Phương trình toàn phần này đồng thời phân tách được thành tích $f(t)g(y)$.",
            })
            alt_methods.append({
                "method_id": "SEPARATION_OF_VARIABLES",
                "title": "Phân tách biến số",
                "description": "Tách biến và tích phân hai vế trực tiếp.",
                "problem_type": ProblemType.ODE_SEPARABLE,
            })

        guide.extend([
            f"Dấu hiệu nhận biết: Thường viết dưới dạng $M({var_name},{dep_name})d{var_name} + N({var_name},{dep_name})d{dep_name} = 0$.",
            f"Điều kiện then chốt: Đạo hàm riêng chéo phải bằng nhau: $\\partial M / \\partial {dep_name} = \\partial N / \\partial {var_name}$.",
            "Nếu hai đạo hàm riêng chéo KHÔNG bằng nhau, phương trình không phải là toàn phần (cần tìm thừa số tích phân $\\mu$).",
        ])

    # Case C: Separable (Nonlinear) Equation
    elif is_separable:
        primary_cat = "SEPARABLE"
        primary_title = "Phương trình vi phân tách biến (Separable ODE)"
        canon_latex = f"\\frac{{d{dep_name}}}{{d{var_name}}} = f({var_name}) \\cdot g({dep_name})"
        target_pt = ProblemType.ODE_SEPARABLE

        explanation.append("Bậc cao nhất của đạo hàm là cấp một.")
        explanation.append(
            f"Vế phải phân tích được thành tích độc lập của hàm theo ${var_name}$ và hàm theo ${dep_name}$: "
            f"$f({var_name}) = {f_sep_latex}$ và $g({dep_name}) = {g_sep_latex}$."
        )
        explanation.append(f"Phương trình phi tuyến tính theo ${dep_name}$, không áp dụng được công thức tuyến tính.")

        rec_method_id = "SEPARATION_OF_VARIABLES"
        rec_method_title = "Phân tách biến số (Separation of Variables)"
        rec_method_reason = (
            f"Chuyển toàn bộ biểu thức chứa ${dep_name}$ sang vế trái và ${var_name}$ sang vế phải: "
            f"$\\frac{{d{dep_name}}}{{{g_sep_latex}}} = ({f_sep_latex})\\,d{var_name}$. "
            "Lấy tích phân hai vế để tìm nghiệm tổng quát."
        )

        guide.extend([
            "Dấu hiệu nhận biết: Có thể cô lập $y'$ thành tích $f(t) \\cdot g(y)$, ví dụ $y' = t \\cdot y^2$ hoặc $y' = y(1-y)$.",
            "Lưu ý quan trọng: Khi chia hai vế cho $g(y)$, cần kiểm tra các nghiệm cân bằng $g(y) = 0$ (nghiệm kỳ dị) để tránh bỏ sót nghiệm.",
        ])

    # Case D: Classical Homogeneous (Ratio Form y/t)
    elif is_classical_homog:
        primary_cat = "CLASSICAL_HOMOGENEOUS"
        primary_title = "Phương trình vi phân thuần nhất cấp 1 (Dạng tỷ số y/t)"
        canon_latex = f"{dep_name}' = F\\left(\\frac{{{dep_name}}}{{{var_name}}}\\right)"
        target_pt = ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS

        explanation.append("Bậc cao nhất của đạo hàm là cấp một.")
        explanation.append(f"Vế phải có dạng phân thức đồng bậc, có thể viết lại theo biến tỷ số $v = \\frac{{{dep_name}}}{{{var_name}}}$.")
        explanation.append("Phân biệt rõ ràng: Đây là phương trình thuần nhất bậc 0 theo nghĩa hàm số, KHÔNG phải phương trình tuyến tính vế phải bằng 0.")

        rec_method_id = "HOMOGENEOUS_SUBSTITUTION"
        rec_method_title = f"Đổi biến số thuần nhất (y = v·{var_name})"
        rec_method_reason = (
            f"Đặt ${dep_name} = v \\cdot {var_name}$ (phép thế $y = v \\cdot x$ khi biến là $x$) $\\implies {dep_name}' = v + {var_name}\\frac{{dv}}{{d{var_name}}}$. "
            f"Thay vào phương trình để triệt tiêu tỷ số và chuyển đổi thành phương trình tách biến theo $v$ và ${var_name}$."
        )

        guide.extend([
            "Dấu hiệu nhận biết: Mỗi số hạng ở tử số và mẫu số có tổng số mũ bằng nhau (đồng bậc), ví dụ $(x+y)/x$ hoặc $(x^2+y^2)/(xy)$.",
            f"Phép thế chuẩn tắc: Luôn đặt $y = v \\cdot {var_name}$ ($y = v \\cdot x$) $\\implies y' = v + {var_name} v'$.",
        ])

    # Case E: Non-exact Differential Form with Integrating Factor Opportunity
    elif is_exact_form and not is_exact:
        primary_cat = "INTEGRATING_FACTOR"
        primary_title = "Phương trình vi phân dạng vi phân (Không toàn phần)"
        canon_latex = f"M({var_name},{dep_name})\\,d{var_name} + N({var_name},{dep_name})\\,d{dep_name} = 0"
        target_pt = ProblemType.ODE_INTEGRATING_FACTOR

        explanation.append("Phương trình có dạng vi phân $M\\,dt + N\\,dy = 0$.")
        explanation.append(f"Hàm $M({var_name}, {dep_name}) = {M_latex}$ và $N({var_name}, {dep_name}) = {N_latex}$.")
        explanation.append(
            f"Kiểm tra tính toàn phần THẤT BẠI: "
            f"$\\frac{{\\partial M}}{{\\partial {dep_name}}} = {dM_dy_latex} \\neq "
            f"\\frac{{\\partial N}}{{\\partial {var_name}}} = {dN_dt_latex}$."
        )
        explanation.append("Phương trình chưa phải là vi phân toàn phần; cần tìm thừa số tích phân $\\mu$ để quy về dạng toàn phần.")

        rec_method_id = "INTEGRATING_FACTOR_SEARCH"
        rec_method_title = f"Tìm thừa số tích phân μ({var_name}) hoặc μ({dep_name})"
        rec_method_reason = (
            f"Tính hiệu đạo hàm riêng $\\frac{{\\partial M}}{{\\partial {dep_name}}} - \\frac{{\\partial N}}{{\\partial {var_name}}}$. "
            f"Nếu $\\frac{{M_{dep_name} - N_{var_name}}}{{N}}$ chỉ phụ thuộc vào ${var_name}$, ta có $\\mu({var_name}) = e^{{\\int \\frac{{M_{dep_name} - N_{var_name}}}{{N}} d{var_name}}}$."
        )

        guide.extend([
            f"Dấu hiệu nhận biết: Dạng $M d{var_name} + N d{dep_name} = 0$ nhưng $\\partial M/\\partial {dep_name} \\neq \\partial N/\\partial {var_name}$.",
            f"Bước xử lý tiếp theo: Kiểm tra xem $(M_{dep_name} - N_{var_name})/N$ có chỉ chứa ${var_name}$ không, hoặc $(N_{var_name} - M_{dep_name})/M$ có chỉ chứa ${dep_name}$ không.",
        ])

    # Case F: General / Fallback First-Order Equation
    else:
        primary_cat = "GENERAL_FIRST_ORDER"
        primary_title = "Phương trình vi phân cấp 1 tổng quát"
        canon_latex = f"F({var_name}, {dep_name}, {dep_name}') = 0"
        target_pt = ProblemType.ODE_FIRST_ORDER_LINEAR

        explanation.append("Bậc cao nhất của đạo hàm là cấp một.")
        explanation.append("Phương trình không thuộc các dạng đặc biệt đơn giản (tách biến trực tiếp hay toàn phần).")

        rec_method_id = "GENERAL_SOLVER"
        rec_method_title = "Thuật toán giải cấp 1 tổng quát"
        rec_method_reason = "Ứng dụng sẽ áp dụng các thuật toán phân tích và biến đổi đại số ký hiệu để tìm họ nghiệm."

        guide.extend([
            "Kiểm tra xem phương trình có thể biến đổi đại số về dạng tách biến, tuyến tính hoặc thuần nhất hay không.",
        ])

    return FirstOrderClassificationResult(
        is_valid_ode=True,
        detected_order=1,
        primary_category=primary_cat,
        primary_title=primary_title,
        canonical_form_latex=canon_latex,
        target_problem_type=target_pt,
        is_linear=is_linear,
        is_linear_homogeneous=is_linear_homog,
        p_expr_latex=p_latex,
        g_expr_latex=g_latex,
        reference_homogeneous_latex=ref_homog_latex,
        is_separable=is_separable,
        f_expr_latex=f_sep_latex,
        g_sep_latex=g_sep_latex,
        is_exact_form=is_exact_form,
        is_exact=is_exact,
        M_expr_latex=M_latex,
        N_expr_latex=N_latex,
        dM_dy_latex=dM_dy_latex,
        dN_dt_latex=dN_dt_latex,
        is_classical_homogeneous=is_classical_homog,
        F_v_latex=F_v_latex,
        additional_categories=additional_cats,
        recommended_method_id=rec_method_id,
        recommended_method_title=rec_method_title,
        recommended_method_reason=rec_method_reason,
        alternative_methods=alt_methods,
        explanation_points=explanation,
        identification_guide=guide,
        detected_independent_var=var_name,
        detected_dependent_var=dep_name,
        detected_parameters=raw_params,
    )
