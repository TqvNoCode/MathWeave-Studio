"""Problem statement and mathematical notation formatting for UI presentation."""

from __future__ import annotations

from typing import Any
import sympy as sp

from math_app.domain.models import ProblemType
from math_app.input.parser import (
    normalize_expression_string,
    normalize_variable_name,
    parse_mathematical_input,
    parse_matrix_input,
)
from math_app.rendering.latex.formatter import expr_to_latex


def get_result_card_title(op_type: ProblemType) -> str:
    """Return the operation-specific title in uppercase Vietnamese.

    For all derivative orders, uses 'KẾT QUẢ ĐẠO HÀM' (never 'CẤP CAO').
    """
    titles: dict[ProblemType, str] = {
        ProblemType.DERIVATIVE: "KẾT QUẢ ĐẠO HÀM",
        ProblemType.HIGHER_ORDER_DERIVATIVE: "KẾT QUẢ ĐẠO HÀM",
        ProblemType.PARTIAL_DERIVATIVE: "KẾT QUẢ ĐẠO HÀM RIÊNG",
        ProblemType.INDEFINITE_INTEGRAL: "KẾT QUẢ NGUYÊN HÀM",
        ProblemType.INTEGRAL: "KẾT QUẢ NGUYÊN HÀM",
        ProblemType.DEFINITE_INTEGRAL: "KẾT QUẢ TÍCH PHÂN XÁC ĐỊNH",
        ProblemType.LINE_INTEGRAL: "KẾT QUẢ TÍCH PHÂN ĐƯỜNG",
        ProblemType.SURFACE_INTEGRAL: "KẾT QUẢ TÍCH PHÂN MẶT",
        ProblemType.TRIPLE_INTEGRAL: "KẾT QUẢ TÍCH PHÂN BỘI BA",
        ProblemType.ARC_LENGTH: "KẾT QUẢ ĐỘ DÀI CUNG",
        ProblemType.SURFACE_AREA: "KẾT QUẢ DIỆN TÍCH MẶT",
        ProblemType.SURFACE_OF_REVOLUTION: "KẾT QUẢ MẶT TRÒN XOAY",
        ProblemType.GREENS_THEOREM: "KẾT QUẢ ĐỊNH LÝ GREEN",
        ProblemType.STOKES_THEOREM: "KẾT QUẢ ĐỊNH LÝ STOKES",
        ProblemType.DIVERGENCE_THEOREM: "KẾT QUẢ ĐỊNH LÝ DIVERGENCE (GAUSS)",
        ProblemType.LIMIT: "KẾT QUẢ GIỚI HẠN",
        ProblemType.MATRIX_DETERMINANT: "KẾT QUẢ ĐỊNH THỨC",
        ProblemType.MATRIX_INVERSE: "KẾT QUẢ MA TRẬN NGHỊCH ĐẢO",
        ProblemType.MATRIX_REF: "KẾT QUẢ DẠNG BẬC THANG (REF)",
        ProblemType.MATRIX_RREF: "KẾT QUẢ DẠNG BẬC THANG RÚT GỌN (RREF)",
        ProblemType.MATRIX_TRANSPOSE: "KẾT QUẢ CHUYỂN VỊ MA TRẬN",
        ProblemType.MATRIX_RANK: "KẾT QUẢ HẠNG MA TRẬN",
        ProblemType.MATRIX_ADD_SUB: "KẾT QUẢ CỘNG / TRỪ MA TRẬN",
        ProblemType.MATRIX_MULTIPLY: "KẾT QUẢ NHÂN MA TRẬN",
        ProblemType.MATRIX_SOLVE_SYSTEM: "KẾT QUẢ GIẢI HỆ PHƯƠNG TRÌNH",
    }
    return titles.get(op_type, "KẾT QUẢ PHÉP TOÁN")


def format_problem_statement_latex(
    raw_input: str,
    op_type: ProblemType,
    target_var: str = "x",
    params: dict[str, Any] | None = None,
) -> str:
    """Format the problem statement into clean, textbook-grade LaTeX notation."""
    p = params or {}
    clean_var = normalize_variable_name(target_var)

    # 1. Ordinary and Higher-order Differentiation
    if op_type in (ProblemType.DERIVATIVE, ProblemType.HIGHER_ORDER_DERIVATIVE):
        try:
            expr, _ = parse_mathematical_input(raw_input, clean_var)
            expr_ltx = expr_to_latex(expr)
            return f"f({clean_var}) = {expr_ltx}"
        except Exception:
            return f"f({clean_var}) = {raw_input}"

    # 2. Partial Differentiation
    if op_type == ProblemType.PARTIAL_DERIVATIVE:
        try:
            expr, _ = parse_mathematical_input(raw_input, clean_var)
            expr_ltx = expr_to_latex(expr)
            free_symbols = sorted(list(expr.free_symbols), key=lambda s: s.name)
            vars_str = ", ".join(s.name for s in free_symbols) if free_symbols else clean_var
            return f"f({vars_str}) = {expr_ltx} \\quad \\left(\\text{{tính }} \\frac{{\\partial f}}{{\\partial {clean_var}}}\\right)"
        except Exception:
            return f"f({clean_var}) = {raw_input} \\quad \\left(\\text{{tính }} \\frac{{\\partial f}}{{\\partial {clean_var}}}\\right)"

    # 3. Indefinite Integral
    if op_type in (ProblemType.INDEFINITE_INTEGRAL, ProblemType.INTEGRAL):
        try:
            expr, _ = parse_mathematical_input(raw_input, clean_var)
            expr_ltx = expr_to_latex(expr)
            return f"\\int \\left( {expr_ltx} \\right) d{clean_var}"
        except Exception:
            return f"\\int \\left( {raw_input} \\right) d{clean_var}"

    # 4. Definite Integral
    if op_type == ProblemType.DEFINITE_INTEGRAL:
        try:
            expr, _ = parse_mathematical_input(raw_input, clean_var)
            expr_ltx = expr_to_latex(expr)
            a = p.get("lower_bound", "0")
            b = p.get("upper_bound", "1")
            a_ltx = expr_to_latex(a)
            b_ltx = expr_to_latex(b)
            return f"\\int_{{{a_ltx}}}^{{{b_ltx}}} \\left( {expr_ltx} \\right) d{clean_var}"
        except Exception:
            return f"\\int \\left( {raw_input} \\right) d{clean_var}"

    # Line Integral
    if op_type == ProblemType.LINE_INTEGRAL:
        param_var = p.get("param_var", "t")
        t_min = expr_to_latex(p.get("t_min", "0"))
        t_max = expr_to_latex(p.get("t_max", "1"))
        mode = p.get("mode", "scalar")
        orientation = str(p.get("orientation", "forward")).lower()
        is_reverse = orientation in ("backward", "reverse", "nghich", "negative", "-")

        xt = p.get("param_x", param_var)
        yt = p.get("param_y", "0")
        zt = p.get("param_z", "0")
        curve_parts = [expr_to_latex(xt), expr_to_latex(yt)]
        if str(zt).strip() not in ("0", ""):
            curve_parts.append(expr_to_latex(zt))
        curve_desc = rf"\mathbf{{r}}({param_var}) = \left({', '.join(curve_parts)}\right), \; {param_var} \in [{t_min}, {t_max}]"
        if is_reverse:
            curve_desc += r" \text{ (chiều nghịch)}"

        if mode == "vector" or ("," in raw_input and mode != "scalar"):
            return rf"\int_C \mathbf{{F}}\cdot d\mathbf{{r}} \quad \left( \mathbf{{F}} = ({raw_input}), \; C: {curve_desc} \right)"
        try:
            f_expr, _ = parse_mathematical_input(raw_input, param_var)
            f_ltx = expr_to_latex(f_expr)
        except Exception:
            f_ltx = raw_input
        return rf"\int_C \left( {f_ltx} \right) ds \quad \left( C: {curve_desc} \right)"

    # Surface Integral
    if op_type == ProblemType.SURFACE_INTEGRAL:
        u_var = p.get("u_var", "x")
        v_var = p.get("v_var", "y")
        u_min = expr_to_latex(p.get("u_min", "0"))
        u_max = expr_to_latex(p.get("u_max", "1"))
        v_min = expr_to_latex(p.get("v_min", "0"))
        v_max = expr_to_latex(p.get("v_max", "1"))
        mode = p.get("mode", "scalar")
        surf_type = str(p.get("surface_type", "explicit")).lower()
        orientation = str(p.get("orientation", "upward")).lower()

        if surf_type == "parametric":
            xu = expr_to_latex(p.get("param_x", u_var))
            yu = expr_to_latex(p.get("param_y", v_var))
            zu = expr_to_latex(p.get("param_z", "0"))
            surf_desc = rf"S: \mathbf{{r}}({u_var},{v_var}) = ({xu}, {yu}, {zu}), \; {u_var}\in[{u_min},{u_max}], \; {v_var}\in[{v_min},{v_max}]"
        else:
            surf_expr = p.get("surface_expr", "1 - x - y")
            surf_desc = rf"S: z = {expr_to_latex(surf_expr)}, \; {u_var}\in[{u_min},{u_max}], \; {v_var}\in[{v_min},{v_max}]"

        if mode in ("vector", "flux") or ("," in raw_input and mode != "scalar"):
            orient_txt = r", \mathbf{n} \text{ hướng xuống}" if orientation in ("downward", "down", "negative", "-") else r", \mathbf{n} \text{ hướng lên}"
            return rf"\iint_S \mathbf{{F}}\cdot\mathbf{{n}}\,dS \quad \left( \mathbf{{F}} = ({raw_input}), \; {surf_desc}{orient_txt} \right)"
        try:
            f_expr, _ = parse_mathematical_input(raw_input, u_var)
            f_ltx = expr_to_latex(f_expr)
        except Exception:
            f_ltx = raw_input
        return rf"\iint_S \left( {f_ltx} \right) dS \quad \left( {surf_desc} \right)"

    # Triple Integral
    if op_type == ProblemType.TRIPLE_INTEGRAL:
        coord = str(p.get("coord_system", "cartesian")).lower()
        try:
            f_expr, _ = parse_mathematical_input(raw_input, "x")
            f_ltx = expr_to_latex(f_expr)
        except Exception:
            f_ltx = raw_input

        if coord in ("cylindrical", "tru"):
            z_min = expr_to_latex(p.get("z_min", p.get("inner_min", "0")))
            z_max = expr_to_latex(p.get("z_max", p.get("inner_max", "1")))
            r_min = expr_to_latex(p.get("r_min", p.get("middle_min", "0")))
            r_max = expr_to_latex(p.get("r_max", p.get("middle_max", "1")))
            th_min = expr_to_latex(p.get("th_min", p.get("theta_min", p.get("outer_min", "0"))))
            th_max = expr_to_latex(p.get("th_max", p.get("theta_max", p.get("outer_max", "2*pi"))))
            return (
                rf"\iiint_V f\,dV = "
                rf"\int_{{{th_min}}}^{{{th_max}}} d\theta \int_{{{r_min}}}^{{{r_max}}} r\,dr "
                rf"\int_{{{z_min}}}^{{{z_max}}} \left( {f_ltx} \right) dz"
            )
        elif coord in ("spherical", "cau"):
            rho_min = expr_to_latex(p.get("rho_min", p.get("inner_min", "0")))
            rho_max = expr_to_latex(p.get("rho_max", p.get("inner_max", "1")))
            phi_min = expr_to_latex(p.get("phi_min", p.get("middle_min", "0")))
            phi_max = expr_to_latex(p.get("phi_max", p.get("middle_max", "pi")))
            th_min = expr_to_latex(p.get("th_min", p.get("theta_min", p.get("outer_min", "0"))))
            th_max = expr_to_latex(p.get("th_max", p.get("theta_max", p.get("outer_max", "2*pi"))))
            return (
                rf"\iiint_V f\,dV = "
                rf"\int_{{{th_min}}}^{{{th_max}}} d\theta \int_{{{phi_min}}}^{{{phi_max}}} d\phi "
                rf"\int_{{{rho_min}}}^{{{rho_max}}} \left( {f_ltx} \right) \rho^2 \sin(\phi)\,d\rho"
            )
        else:
            x_min = expr_to_latex(p.get("x_min", "0"))
            x_max = expr_to_latex(p.get("x_max", "1"))
            y_min = expr_to_latex(p.get("y_min", "0"))
            y_max = expr_to_latex(p.get("y_max", "2"))
            z_min = expr_to_latex(p.get("z_min", "0"))
            z_max = expr_to_latex(p.get("z_max", "3"))
            return (
                rf"\iiint_V \left( {f_ltx} \right) dV = "
                rf"\int_{{{x_min}}}^{{{x_max}}} dx \int_{{{y_min}}}^{{{y_max}}} dy \int_{{{z_min}}}^{{{z_max}}} \left( {f_ltx} \right) dz"
            )

    # Arc Length
    if op_type == ProblemType.ARC_LENGTH:
        a = expr_to_latex(p.get("lower_bound", "0"))
        b = expr_to_latex(p.get("upper_bound", "1"))
        return rf"L = \int_{{{a}}}^{{{b}}} ds \quad \left( f({clean_var}) = {raw_input}, \; {clean_var} \in [{a}, {b}] \right)"

    # Surface Area
    if op_type == ProblemType.SURFACE_AREA:
        return rf"A = \iint_D dS \quad \left( z = {raw_input} \right)"

    # Surface of Revolution
    if op_type == ProblemType.SURFACE_OF_REVOLUTION:
        axis = p.get("axis", "x")
        axis_str = "Ox" if axis == "x" else "Oy"
        a = expr_to_latex(p.get("lower_bound", "0"))
        b = expr_to_latex(p.get("upper_bound", "1"))
        return rf"y = {raw_input}, \quad {clean_var} \in [{a}, {b}] \quad \left(\text{{quay quanh }} {axis_str}\right)"

    # Green's Theorem
    if op_type == ProblemType.GREENS_THEOREM:
        x_min = expr_to_latex(p.get("x_min", "0"))
        x_max = expr_to_latex(p.get("x_max", "1"))
        y_min = expr_to_latex(p.get("y_min", "0"))
        y_max = expr_to_latex(p.get("y_max", "1"))
        return rf"\mathbf{{F}} = ({raw_input}), \quad D = [{x_min}, {x_max}] \times [{y_min}, {y_max}]"

    # Stokes' Theorem
    if op_type == ProblemType.STOKES_THEOREM:
        surf = p.get("surface_expr", "0")
        return rf"\mathbf{{F}} = ({raw_input}), \quad S: z = {surf}"

    # Divergence Theorem
    if op_type == ProblemType.DIVERGENCE_THEOREM:
        x_min = expr_to_latex(p.get("x_min", "0"))
        x_max = expr_to_latex(p.get("x_max", "1"))
        y_min = expr_to_latex(p.get("y_min", "0"))
        y_max = expr_to_latex(p.get("y_max", "1"))
        z_min = expr_to_latex(p.get("z_min", "0"))
        z_max = expr_to_latex(p.get("z_max", "1"))
        return rf"\mathbf{{F}} = ({raw_input}), \quad V = [{x_min}, {x_max}] \times [{y_min}, {y_max}] \times [{z_min}, {z_max}]"

    # 5. Limit
    if op_type == ProblemType.LIMIT:
        try:
            expr, _ = parse_mathematical_input(raw_input, clean_var)
            expr_ltx = expr_to_latex(expr)
            pt = p.get("limit_point", "0")
            pt_ltx = expr_to_latex(pt)
            direction = str(p.get("direction", "+-"))
            if "+" in direction and "+-" not in direction:
                lim_sub = f"{clean_var} \\to {pt_ltx}^+"
            elif "-" in direction and "+-" not in direction:
                lim_sub = f"{clean_var} \\to {pt_ltx}^-"
            else:
                lim_sub = f"{clean_var} \\to {pt_ltx}"
            return f"\\lim_{{{lim_sub}}} \\left( {expr_ltx} \\right)"
        except Exception:
            return f"\\lim_{{{clean_var} \\to 0}} \\left( {raw_input} \\right)"

    # 6. Matrix Operations
    try:
        if op_type in (
            ProblemType.MATRIX_DETERMINANT,
            ProblemType.MATRIX_INVERSE,
            ProblemType.MATRIX_RANK,
            ProblemType.MATRIX_RREF,
            ProblemType.MATRIX_TRANSPOSE,
        ):
            mat = parse_matrix_input(raw_input)
            mat_ltx = expr_to_latex(mat)
            return f"A = {mat_ltx}"

        if op_type in (ProblemType.MATRIX_ADD_SUB, ProblemType.MATRIX_MULTIPLY):
            # Might be A + B or A * B
            for op in ("+", "-", "*"):
                if op in raw_input:
                    parts = raw_input.split(op, 1)
                    A = parse_matrix_input(parts[0].strip())
                    B = parse_matrix_input(parts[1].strip())
                    op_sym = " \\cdot " if op == "*" else f" {op} "
                    return f"{expr_to_latex(A)}{op_sym}{expr_to_latex(B)}"
            return raw_input

        if op_type == ProblemType.MATRIX_SOLVE_SYSTEM:
            if "=" in raw_input:
                parts = raw_input.split("=", 1)
                A = parse_matrix_input(parts[0].strip())
                b = parse_matrix_input(parts[1].strip())
                return f"{expr_to_latex(A)} \\cdot x = {expr_to_latex(b)}"
            return f"A \\cdot x = b \\quad \\text{{với }} {raw_input}"
    except Exception:
        pass

    return raw_input


def format_final_answer_latex(
    raw_final_latex: str,
    op_type: ProblemType,
    target_var: str = "x",
    params: dict[str, Any] | None = None,
) -> str:
    """Decorate the final result with appropriate LHS operator notation."""
    p = params or {}
    clean_var = normalize_variable_name(target_var)

    if op_type in (ProblemType.DERIVATIVE, ProblemType.HIGHER_ORDER_DERIVATIVE):
        order = int(p.get("order", 1))
        if order == 1:
            lhs = f"f'({clean_var}) = "
        elif order == 2:
            lhs = f"f''({clean_var}) = "
        elif order == 3:
            lhs = f"f'''({clean_var}) = "
        else:
            lhs = f"f^{{({order})}}({clean_var}) = "
        return f"{lhs}{raw_final_latex}"

    if op_type == ProblemType.PARTIAL_DERIVATIVE:
        lhs = f"\\frac{{\\partial f}}{{\\partial {clean_var}}} = "
        return f"{lhs}{raw_final_latex}"

    if op_type in (ProblemType.INDEFINITE_INTEGRAL, ProblemType.INTEGRAL):
        return f"\\int f({clean_var})\\,d{clean_var} = {raw_final_latex}"

    if op_type == ProblemType.DEFINITE_INTEGRAL:
        a = p.get("lower_bound", "0")
        b = p.get("upper_bound", "1")
        a_ltx = expr_to_latex(a)
        b_ltx = expr_to_latex(b)
        return f"\\int_{{{a_ltx}}}^{{{b_ltx}}} f({clean_var})\\,d{clean_var} = {raw_final_latex}"

    if op_type == ProblemType.LINE_INTEGRAL:
        mode = p.get("mode", "scalar")
        if mode == "vector":
            return rf"\int_C \mathbf{{F}}\cdot d\mathbf{{r}} = {raw_final_latex}"
        return rf"\int_C f\,ds = {raw_final_latex}"

    if op_type == ProblemType.SURFACE_INTEGRAL:
        mode = p.get("mode", "scalar")
        if mode == "vector":
            return rf"\iint_S \mathbf{{F}}\cdot d\mathbf{{S}} = {raw_final_latex}"
        return rf"\iint_S f\,dS = {raw_final_latex}"

    if op_type == ProblemType.TRIPLE_INTEGRAL:
        return rf"\iiint_V f\,dV = {raw_final_latex}"

    if op_type == ProblemType.ARC_LENGTH:
        return rf"L = {raw_final_latex}"

    if op_type == ProblemType.SURFACE_AREA:
        return rf"A = {raw_final_latex}"

    if op_type == ProblemType.SURFACE_OF_REVOLUTION:
        return raw_final_latex

    if op_type == ProblemType.GREENS_THEOREM:
        form = p.get("form", "circulation")
        if form == "flux":
            return rf"\oint_{{\partial D}} (P\,dy - Q\,dx) = \iint_D \text{{div}} = {raw_final_latex}"
        return rf"\oint_{{\partial D}} (P\,dx + Q\,dy) = \iint_D \text{{curl}} = {raw_final_latex}"

    if op_type == ProblemType.STOKES_THEOREM:
        return rf"\oint_{{\partial S}} \mathbf{{F}}\cdot d\mathbf{{r}} = \iint_S (\nabla\times\mathbf{{F}})\cdot d\mathbf{{S}} = {raw_final_latex}"

    if op_type == ProblemType.DIVERGENCE_THEOREM:
        return rf"\iint_{{\partial V}} \mathbf{{F}}\cdot d\mathbf{{S}} = \iiint_V (\nabla\cdot\mathbf{{F}})\,dV = {raw_final_latex}"

    if op_type == ProblemType.MATRIX_INVERSE:
        return f"A^{{-1}} = {raw_final_latex}"

    if op_type == ProblemType.MATRIX_TRANSPOSE:
        return f"A^T = {raw_final_latex}"

    if op_type == ProblemType.MATRIX_DETERMINANT:
        return f"\\det(A) = {raw_final_latex}"

    if op_type == ProblemType.MATRIX_RANK:
        return f"\\text{{rank}}(A) = {raw_final_latex}"

    if op_type == ProblemType.MATRIX_RREF:
        return f"\\text{{RREF}}(A) = {raw_final_latex}"

    if op_type == ProblemType.MATRIX_SOLVE_SYSTEM:
        return f"x = {raw_final_latex}"

    return raw_final_latex
