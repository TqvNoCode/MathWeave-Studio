"""Safe expression parsing, real-valued evaluation, and singularity inspection for numerical ODEs."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import math
import re
from typing import Callable

import sympy as sp

from math_app.domain.exceptions import InvalidInputError
from math_app.domain.numerical_ode import NumericalODEOrder
from math_app.input.ode_parser import (
    ParsedIntervalConstraint,
    detect_ode_order,
    extract_initial_condition_from_string,
    extract_interval_from_string,
    extract_second_order_ics_from_string,
    extract_source_domain_constraints,
    normalize_ode_equation_string,
    parse_interval_constraint,
)
from math_app.input.parser import normalize_variable_name, parse_safe_expression
from math_app.rendering.latex.formatter import expr_to_latex

MAX_NUMERIC_MAGNITUDE = 1e150
_ZERO_TOL = 1e-15
_TRIG_POLE_TOL = 1e-14
_NUMERIC_LITERAL_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")


class NumericalSingularityError(Exception):
    """Raised when evaluation encounters division by zero, a pole, or a singular ODE point."""

    def __init__(self, message: str, failing_step: int | None = None) -> None:
        super().__init__(message)
        self.failing_step = failing_step


class NumericalDomainError(Exception):
    """Raised when evaluation leaves the real domain (e.g. log(<=0), sqrt(<0), non-real power)."""

    def __init__(self, message: str, failing_step: int | None = None) -> None:
        super().__init__(message)
        self.failing_step = failing_step


class NumericalOverflowError(Exception):
    """Raised when numerical evaluation overflows or produces NaN/Infinity."""

    def __init__(self, message: str, failing_step: int | None = None) -> None:
        super().__init__(message)
        self.failing_step = failing_step


@dataclass(frozen=True)
class ParsedNumericalODE:
    """Validated numerical ODE representation isolated into y' = f(t,y) or y'' = F(t,y,y')."""

    raw_input: str
    order: NumericalODEOrder
    indep_var: sp.Symbol
    dep_var: sp.Symbol
    yp_sym: sp.Symbol
    yp2_sym: sp.Symbol
    rhs_expr: sp.Expr
    rhs_str: str
    rhs_latex: str
    equation_latex: str
    lhs_expr: sp.Expr
    raw_rhs_expr: sp.Expr
    leading_coeff: sp.Expr
    is_euler_cauchy: bool
    euler_cauchy_original_latex: str
    domain_restrictions: tuple[str, ...]
    original_denominators: tuple[sp.Expr, ...]
    interval_spec: ParsedIntervalConstraint | None = None


def parse_numeric_scalar(raw: str | float | int | None, field_label: str) -> tuple[Decimal, float]:
    """Safely parse a finite real scalar parameter, preserving exact Decimal literals when possible."""
    if raw is None or isinstance(raw, bool):
        raise InvalidInputError(f"Thiếu giá trị cho '{field_label}' (Missing numeric value).")

    if isinstance(raw, int):
        dec_val = Decimal(raw)
        flt_val = float(raw)
    elif isinstance(raw, float):
        if not math.isfinite(raw):
            raise InvalidInputError(f"Giá trị '{field_label}' phải là số thực hữu hạn (non-finite float).")
        if abs(raw) > MAX_NUMERIC_MAGNITUDE:
            raise InvalidInputError(f"Giá trị '{field_label}' vượt quá giới hạn an toàn.")
        dec_val = Decimal(str(raw))
        flt_val = raw
    else:
        cleaned = str(raw).strip()
        if not cleaned:
            raise InvalidInputError(f"Trường '{field_label}' không được để trống.")

        lower = cleaned.lower()
        if lower in {"nan", "inf", "+inf", "-inf", "infinity", "+infinity", "-infinity", "oo", "+oo", "-oo"}:
            raise InvalidInputError(
                f"Giá trị '{field_label}' ('{cleaned}') phải là số thực hữu hạn (không chấp nhận NaN/vô cực)."
            )

        if _NUMERIC_LITERAL_RE.match(cleaned):
            try:
                dec_val = Decimal(cleaned)
                flt_val = float(dec_val)
            except (InvalidOperation, ValueError, OverflowError) as exc:
                raise InvalidInputError(f"Giá trị số '{cleaned}' ở '{field_label}' không hợp lệ: {exc}") from exc
            if not math.isfinite(flt_val) or abs(flt_val) > MAX_NUMERIC_MAGNITUDE:
                raise InvalidInputError(f"Giá trị '{field_label}' vượt quá giới hạn số học hữu hạn.")
            return dec_val, flt_val

        # Parse symbolic constant expressions such as pi/2, sqrt(2), exp(1), 1/3
        expr = parse_safe_expression(cleaned, target_variable="t", allowed_variables=set(), evaluate=True)
        if expr.free_symbols:
            syms = ", ".join(sorted(s.name for s in expr.free_symbols))
            raise InvalidInputError(
                f"Giá trị '{field_label}' phải là hằng số thực, không được chứa biến chưa gán ({syms})."
            )
        if expr.has(sp.oo, -sp.oo, sp.zoo, sp.nan, sp.I, sp.AccumBounds):
            raise InvalidInputError(f"Giá trị '{field_label}' không phải là số thực hữu hạn.")

        try:
            evaluated = complex(sp.N(expr, 30))
        except Exception as exc:
            raise InvalidInputError(f"Không thể định giá biểu thức số '{cleaned}' ở '{field_label}': {exc}") from exc

        if abs(evaluated.imag) > 1e-13 or not math.isfinite(evaluated.real):
            raise InvalidInputError(f"Giá trị '{field_label}' không phải là số thực hữu hạn.")

        flt_val = float(evaluated.real)
        if abs(flt_val) > MAX_NUMERIC_MAGNITUDE:
            raise InvalidInputError(f"Giá trị '{field_label}' vượt quá giới hạn an toàn.")
        try:
            dec_val = Decimal(str(sp.N(expr, 28)))
        except InvalidOperation:
            dec_val = Decimal(str(flt_val))

    if not math.isfinite(flt_val) or abs(flt_val) > MAX_NUMERIC_MAGNITUDE:
        raise InvalidInputError(f"Giá trị '{field_label}' vượt quá giới hạn số học hữu hạn.")
    return dec_val, flt_val


def _check_finite_real(val: float, context: str = "kết quả") -> float:
    if not math.isfinite(val):
        raise NumericalOverflowError(f"Giá trị {context} không hữu hạn (NaN/Infinity).")
    if abs(val) > MAX_NUMERIC_MAGNITUDE:
        raise NumericalOverflowError(f"Tràn số học tại {context}: |giá trị| vượt quá {MAX_NUMERIC_MAGNITUDE:.0e}.")
    return val


def compile_safe_real_evaluator(
    expr: sp.Expr,
    arg_symbols: tuple[sp.Symbol, ...],
) -> Callable[..., float]:
    """Compile a SymPy expression into a fast, AST-safe real-valued Python closure (zero eval/exec)."""
    sym_index = {sym.name: idx for idx, sym in enumerate(arg_symbols)}

    def _compile(node: sp.Expr) -> Callable[[tuple[float, ...]], float]:
        if node is sp.pi:
            return lambda _args: math.pi
        if node is sp.E:
            return lambda _args: math.e
        if node is sp.GoldenRatio:
            phi_val = (1.0 + math.sqrt(5.0)) / 2.0
            return lambda _args, v=phi_val: v
        if node is sp.EulerGamma:
            gamma_val = 0.5772156649015329
            return lambda _args, v=gamma_val: v
        if node is sp.I or node in (sp.oo, -sp.oo, sp.zoo, sp.nan):
            raise InvalidInputError("Biểu thức chứa hằng số phức hoặc vô cực không hợp lệ cho tính toán số thực.")

        if isinstance(node, sp.Symbol):
            if node.name == "I":
                raise InvalidInputError("Không hỗ trợ số phức (i) trong bộ giải số thực.")
            if node.name not in sym_index:
                raise InvalidInputError(f"Ký hiệu chưa xác định '{node.name}' trong biểu thức số.")
            idx = sym_index[node.name]
            return lambda args, i=idx: args[i]

        if isinstance(node, sp.Number):
            val = float(node.evalf())
            _check_finite_real(val, "hằng số")
            return lambda _args, v=val: v

        if isinstance(node, sp.Add):
            sub_fns = tuple(_compile(arg) for arg in node.args)

            def _eval_add(args: tuple[float, ...], fns=sub_fns) -> float:
                total = 0.0
                for fn in fns:
                    total += fn(args)
                return _check_finite_real(total, "phép cộng")

            return _eval_add

        if isinstance(node, sp.Mul):
            sub_fns = tuple(_compile(arg) for arg in node.args)

            def _eval_mul(args: tuple[float, ...], fns=sub_fns) -> float:
                prod = 1.0
                for fn in fns:
                    prod *= fn(args)
                    if not math.isfinite(prod) or abs(prod) > MAX_NUMERIC_MAGNITUDE:
                        raise NumericalOverflowError("Tràn số học trong phép nhân.")
                return _check_finite_real(prod, "phép nhân")

            return _eval_mul

        if isinstance(node, sp.Pow):
            base_expr, exp_expr = node.as_base_exp()
            base_fn = _compile(base_expr)
            exp_fn = _compile(exp_expr)

            if isinstance(exp_expr, sp.Integer):
                exp_int = int(exp_expr)

                def _eval_int_pow(args: tuple[float, ...], bf=base_fn, k=exp_int) -> float:
                    b = bf(args)
                    if k == 0:
                        return 1.0
                    if k < 0 and abs(b) <= _ZERO_TOL:
                        raise NumericalSingularityError("Phép chia cho 0 (mẫu số bằng 0).")
                    try:
                        res = b ** k
                    except OverflowError as exc:
                        raise NumericalOverflowError(f"Tràn số học khi tính ({b})^({k}).") from exc
                    except ZeroDivisionError as exc:
                        raise NumericalSingularityError("Phép chia cho 0 trong phép lũy thừa âm.") from exc
                    return _check_finite_real(float(res), "lũy thừa")

                return _eval_int_pow

            def _eval_pow(args: tuple[float, ...], bf=base_fn, ef=exp_fn) -> float:
                b = bf(args)
                e = ef(args)
                if abs(b) <= _ZERO_TOL:
                    if e < 0:
                        raise NumericalSingularityError("Phép chia cho 0 (cơ số 0 với số mũ âm).")
                    if e == 0:
                        return 1.0
                    return 0.0
                if b < 0:
                    e_round = round(e)
                    if abs(e - e_round) <= 1e-12:
                        try:
                            res = b ** int(e_round)
                        except OverflowError as exc:
                            raise NumericalOverflowError("Tràn số học trong phép lũy thừa.") from exc
                        return _check_finite_real(float(res), "lũy thừa")
                    raise NumericalDomainError(
                        f"Phép tính lũy thừa/căn thức của số âm ({b:.6g}) với số mũ ({e:.6g}) không cho giá trị thực."
                    )
                try:
                    res = math.pow(b, e)
                except OverflowError as exc:
                    raise NumericalOverflowError("Tràn số học trong phép lũy thừa.") from exc
                except ValueError as exc:
                    raise NumericalDomainError(f"Lỗi miền xác định trong phép lũy thừa: {exc}") from exc
                return _check_finite_real(res, "lũy thừa")

            return _eval_pow

        if isinstance(node, sp.sin):
            arg_fn = _compile(node.args[0])
            return lambda args, fn=arg_fn: math.sin(fn(args))

        if isinstance(node, sp.cos):
            arg_fn = _compile(node.args[0])
            return lambda args, fn=arg_fn: math.cos(fn(args))

        if isinstance(node, sp.tan):
            arg_fn = _compile(node.args[0])

            def _eval_tan(args: tuple[float, ...], fn=arg_fn) -> float:
                u = fn(args)
                if abs(math.cos(u)) <= _TRIG_POLE_TOL:
                    raise NumericalSingularityError(f"Điểm kỳ dị lượng giác của tan tại đối số {u:.6g} (cos ≈ 0).")
                return _check_finite_real(math.tan(u), "tan")

            return _eval_tan

        if isinstance(node, sp.sec):
            arg_fn = _compile(node.args[0])

            def _eval_sec(args: tuple[float, ...], fn=arg_fn) -> float:
                u = fn(args)
                c = math.cos(u)
                if abs(c) <= _TRIG_POLE_TOL:
                    raise NumericalSingularityError(f"Điểm kỳ dị của sec tại đối số {u:.6g} (cos ≈ 0).")
                return _check_finite_real(1.0 / c, "sec")

            return _eval_sec

        if isinstance(node, sp.csc):
            arg_fn = _compile(node.args[0])

            def _eval_csc(args: tuple[float, ...], fn=arg_fn) -> float:
                u = fn(args)
                s = math.sin(u)
                if abs(s) <= _TRIG_POLE_TOL:
                    raise NumericalSingularityError(f"Điểm kỳ dị của csc tại đối số {u:.6g} (sin ≈ 0).")
                return _check_finite_real(1.0 / s, "csc")

            return _eval_csc

        if isinstance(node, sp.cot):
            arg_fn = _compile(node.args[0])

            def _eval_cot(args: tuple[float, ...], fn=arg_fn) -> float:
                u = fn(args)
                s = math.sin(u)
                if abs(s) <= _TRIG_POLE_TOL:
                    raise NumericalSingularityError(f"Điểm kỳ dị của cot tại đối số {u:.6g} (sin ≈ 0).")
                return _check_finite_real(math.cos(u) / s, "cot")

            return _eval_cot

        if isinstance(node, sp.asin):
            arg_fn = _compile(node.args[0])

            def _eval_asin(args: tuple[float, ...], fn=arg_fn) -> float:
                u = fn(args)
                if u < -1.0 or u > 1.0:
                    raise NumericalDomainError(f"Giá trị ngoài miền xác định [-1, 1] của asin: {u:.6g}.")
                return math.asin(u)

            return _eval_asin

        if isinstance(node, sp.acos):
            arg_fn = _compile(node.args[0])

            def _eval_acos(args: tuple[float, ...], fn=arg_fn) -> float:
                u = fn(args)
                if u < -1.0 or u > 1.0:
                    raise NumericalDomainError(f"Giá trị ngoài miền xác định [-1, 1] của acos: {u:.6g}.")
                return math.acos(u)

            return _eval_acos

        if isinstance(node, sp.atan):
            arg_fn = _compile(node.args[0])
            return lambda args, fn=arg_fn: math.atan(fn(args))

        if isinstance(node, sp.exp):
            arg_fn = _compile(node.args[0])

            def _eval_exp(args: tuple[float, ...], fn=arg_fn) -> float:
                u = fn(args)
                if u > 345.0:
                    raise NumericalOverflowError(f"Tràn số học trong hàm exp({u:.6g}).")
                return _check_finite_real(math.exp(u), "exp")

            return _eval_exp

        if isinstance(node, sp.log):
            arg_fn = _compile(node.args[0])

            def _eval_log(args: tuple[float, ...], fn=arg_fn) -> float:
                u = fn(args)
                if u <= 0.0:
                    raise NumericalDomainError(
                        f"Đối số của logarit phải dương (> 0), nhận được {u:.6g}."
                    )
                return _check_finite_real(math.log(u), "log")

            return _eval_log

        if isinstance(node, sp.Abs):
            arg_fn = _compile(node.args[0])
            return lambda args, fn=arg_fn: abs(fn(args))

        raise InvalidInputError(f"Hàm hoặc biểu thức '{type(node).__name__}' chưa được hỗ trợ trong tính toán số.")

    root_fn = _compile(expr)

    def _evaluator(*values: float) -> float:
        if len(values) != len(arg_symbols):
            raise ValueError(f"Expected {len(arg_symbols)} arguments, got {len(values)}.")
        res = root_fn(values)
        return _check_finite_real(res, "định giá biểu thức")

    return _evaluator


def _is_euler_cauchy_structure(
    standard_expr: sp.Expr,
    t_sym: sp.Symbol,
    y_sym: sp.Symbol,
    yp_sym: sp.Symbol,
    yp2_sym: sp.Symbol,
) -> tuple[bool, sp.Expr, sp.Expr, sp.Expr, sp.Expr]:
    """Detect whether standard_expr represents At^2 y'' + Bty' + Cy - g(t) = 0 (A != 0)."""
    expanded = sp.expand(standard_expr)
    a_coeff = sp.simplify(expanded.coeff(yp2_sym, 1))
    rem1 = expanded.coeff(yp2_sym, 0)

    try:
        deg_yp = sp.Poly(rem1, yp_sym).degree() if rem1.has(yp_sym) else 0
    except Exception:
        return False, a_coeff, sp.Integer(0), sp.Integer(0), sp.Integer(0)
    if deg_yp > 1:
        return False, a_coeff, sp.Integer(0), sp.Integer(0), sp.Integer(0)

    b_coeff = sp.simplify(rem1.coeff(yp_sym, 1))
    rem2 = rem1.coeff(yp_sym, 0)

    try:
        deg_y = sp.Poly(rem2, y_sym).degree() if rem2.has(y_sym) else 0
    except Exception:
        return False, a_coeff, b_coeff, sp.Integer(0), sp.Integer(0)
    if deg_y > 1:
        return False, a_coeff, b_coeff, sp.Integer(0), sp.Integer(0)

    c_coeff = sp.simplify(rem2.coeff(y_sym, 1))
    rem3 = sp.simplify(rem2.coeff(y_sym, 0))

    forbidden = {y_sym, yp_sym, yp2_sym}
    if any(c.free_symbols & forbidden for c in (a_coeff, b_coeff, c_coeff, rem3)):
        return False, a_coeff, b_coeff, c_coeff, -rem3

    if a_coeff == 0 or not a_coeff.has(t_sym):
        return False, a_coeff, b_coeff, c_coeff, -rem3

    try:
        if sp.simplify(a_coeff.subs(t_sym, 0)) != 0:
            return False, a_coeff, b_coeff, c_coeff, -rem3
    except Exception:
        return False, a_coeff, b_coeff, c_coeff, -rem3

    ratio_b = sp.simplify(t_sym * b_coeff / a_coeff)
    ratio_c = sp.simplify((t_sym**2) * c_coeff / a_coeff)
    if t_sym in ratio_b.free_symbols or t_sym in ratio_c.free_symbols:
        return False, a_coeff, b_coeff, c_coeff, -rem3

    return True, a_coeff, b_coeff, c_coeff, -rem3


def _build_equation_latex(
    lhs_expr: sp.Expr,
    rhs_expr: sp.Expr,
    t_sym: sp.Symbol,
    y_sym: sp.Symbol,
    yp_sym: sp.Symbol,
    yp2_sym: sp.Symbol,
) -> str:
    """Format ODE equation cleanly in LaTeX with y'(t) and y''(t) symbols."""
    raw = f"{expr_to_latex(lhs_expr)} = {expr_to_latex(rhs_expr)}"
    raw = raw.replace(r"y_{double prime}", f"{y_sym.name}''").replace("y_{double prime}", f"{y_sym.name}''")
    raw = raw.replace(r"y_{prime}", f"{y_sym.name}'").replace("y_{prime}", f"{y_sym.name}'")
    return raw


def parse_numerical_ode_equation(
    raw_equation: str,
    order: NumericalODEOrder,
    indep_var: str = "t",
    dep_var: str = "y",
) -> ParsedNumericalODE:
    """Parse and validate a 1st- or 2nd-order ODE for numerical explicit Euler integration."""
    cleaned = raw_equation.strip()
    if not cleaned:
        raise InvalidInputError("Phương trình vi phân không được để trống.")

    clean_indep = normalize_variable_name(indep_var) if indep_var else "t"
    clean_dep = normalize_variable_name(dep_var) if dep_var else "y"
    if not clean_indep.isidentifier():
        raise InvalidInputError(f"Biến độc lập '{indep_var}' không hợp lệ.")
    if clean_indep == clean_dep:
        raise InvalidInputError("Biến độc lập và biến phụ thuộc không được trùng nhau.")

    eq_without_int, interval_str = extract_interval_from_string(cleaned)
    interval_spec: ParsedIntervalConstraint | None = None
    if interval_str:
        interval_spec = parse_interval_constraint(interval_str, variable=clean_indep)
        if not interval_spec.is_supported:
            raise InvalidInputError(interval_spec.error or f"Khoảng xác định '{interval_str}' không hợp lệ.")

    # Reject inline initial conditions pasted inside the equation input so dedicated IVP fields remain authoritative
    if order == NumericalODEOrder.SECOND_ORDER:
        eq_pure, y_ic, yp_ic, y1_str = extract_second_order_ics_from_string(eq_without_int)
        if y_ic or yp_ic or y1_str:
            raise InvalidInputError(
                "Vui lòng nhập các điều kiện ban đầu (t₀, y₀, v₀) vào các ô tham số chuyên biệt thay vì viết kèm trong ô phương trình."
            )
    else:
        eq_pure, inline_ic = extract_initial_condition_from_string(eq_without_int)
        if inline_ic:
            raise InvalidInputError(
                "Vui lòng nhập điều kiện ban đầu (t₀, y₀) vào các ô tham số chuyên biệt thay vì viết kèm trong ô phương trình."
            )

    eq_pure = eq_pure.strip()
    if not eq_pure:
        raise InvalidInputError("Phương trình vi phân không được để trống.")

    detected_order = detect_ode_order(eq_pure, indep_var=clean_indep, dep_var=clean_dep)
    if detected_order >= 3:
        raise InvalidInputError(
            "Phương trình vi phân cấp 3 trở lên chưa được hỗ trợ. Bộ giải Euler tiến chỉ hỗ trợ cấp 1 và cấp 2."
        )
    if order == NumericalODEOrder.FIRST_ORDER and detected_order != 1:
        if detected_order == 2:
            raise InvalidInputError(
                "Phương trình chứa đạo hàm cấp 2 y''. Vui lòng chuyển sang chế độ PTVP cấp 2 để giải xấp xỉ."
            )
        raise InvalidInputError(
            "Phương trình không chứa đạo hàm cấp 1 (ví dụ: y' = t + y hoặc dy/dt = -2*y)."
        )
    if order == NumericalODEOrder.SECOND_ORDER and detected_order != 2:
        if detected_order == 1:
            raise InvalidInputError(
                "Phương trình chỉ chứa đạo hàm cấp 1 y'. Vui lòng chuyển sang chế độ PTVP cấp 1 để giải xấp xỉ."
            )
        raise InvalidInputError(
            "Phương trình không chứa đạo hàm cấp 2 (ví dụ: y'' = -y hoặc t^2*y'' + 4*t*y' + 2*y = 0)."
        )

    norm_eq = normalize_ode_equation_string(eq_pure, indep_var=clean_indep, dep_var=clean_dep)
    if "=" in norm_eq:
        parts = norm_eq.split("=")
        if len(parts) != 2:
            raise InvalidInputError("Phương trình chỉ được chứa đúng một dấu '='.")
        lhs_raw, rhs_raw = parts[0].strip(), parts[1].strip()
        if not lhs_raw or not rhs_raw:
            raise InvalidInputError("Hai vế của phương trình không được để trống.")
    else:
        lhs_raw, rhs_raw = norm_eq, "0"

    t_sym = sp.Symbol(clean_indep)
    y_sym = sp.Symbol(clean_dep)
    yp_sym = sp.Symbol("y_prime")
    yp2_sym = sp.Symbol("y_double_prime")

    allowed_vars = {clean_indep, clean_dep, "y_prime"}
    if order == NumericalODEOrder.SECOND_ORDER:
        allowed_vars.add("y_double_prime")

    lhs_expr = parse_safe_expression(lhs_raw, target_variable=clean_indep, allowed_variables=allowed_vars, evaluate=False)
    rhs_expr = parse_safe_expression(rhs_raw, target_variable=clean_indep, allowed_variables=allowed_vars, evaluate=False)

    orig_restrictions, orig_denoms, _ = extract_source_domain_constraints([lhs_expr, rhs_expr], t_sym, y_sym)
    restrictions_list = list(orig_restrictions)
    denoms_list = list(orig_denoms)

    standard_expr = sp.simplify(lhs_expr - rhs_expr)

    # Ensure no extraneous unknown symbols exist (no symbolic parameters in numerical solving)
    permitted_syms = {t_sym, y_sym, yp_sym} if order == NumericalODEOrder.FIRST_ORDER else {t_sym, y_sym, yp_sym, yp2_sym}
    extra_syms = standard_expr.free_symbols - permitted_syms
    if extra_syms:
        names = ", ".join(sorted(s.name for s in extra_syms))
        raise InvalidInputError(
            f"Phương pháp số yêu cầu các hệ số phải là số thực xác định; phát hiện tham số chưa gán giá trị: {names}."
        )

    highest_sym = yp_sym if order == NumericalODEOrder.FIRST_ORDER else yp2_sym
    if highest_sym not in standard_expr.free_symbols:
        raise InvalidInputError("Không tìm thấy đạo hàm bậc cao nhất hợp lệ sau khi chuẩn hóa phương trình.")

    try:
        poly = sp.Poly(sp.expand(standard_expr), highest_sym)
        deg = poly.degree()
    except Exception:
        deg = None

    if deg != 1:
        deriv_lbl = "y'" if order == NumericalODEOrder.FIRST_ORDER else "y''"
        raise InvalidInputError(
            f"Phương trình phải tuyến tính bậc nhất theo {deriv_lbl} để cô lập dạng hiển {deriv_lbl} = F(...)."
        )

    expanded_std = sp.expand(standard_expr)
    leading_coeff = sp.simplify(expanded_std.coeff(highest_sym, 1))
    remainder = expanded_std.coeff(highest_sym, 0)

    if leading_coeff == 0:
        raise InvalidInputError("Hệ số dẫn của đạo hàm bậc cao nhất bằng 0.")

    isolated_rhs = sp.simplify(-remainder / leading_coeff)
    if isolated_rhs.has(highest_sym):
        raise InvalidInputError("Không thể cô lập hoàn toàn đạo hàm bậc cao nhất về vế phải.")

    if leading_coeff != 1 and not leading_coeff.is_number:
        denoms_list.append(leading_coeff)
        restrictions_list.append(f"Hệ số dẫn {leading_coeff} ≠ 0.")

    is_euler_cauchy = False
    ec_orig_latex = ""
    if order == NumericalODEOrder.SECOND_ORDER:
        is_ec, a_c, b_c, c_c, g_c = _is_euler_cauchy_structure(standard_expr, t_sym, y_sym, yp_sym, yp2_sym)
        if is_ec:
            is_euler_cauchy = True
            ec_orig_latex = _build_equation_latex(lhs_expr, rhs_expr, t_sym, y_sym, yp_sym, yp2_sym)
            if t_sym not in denoms_list:
                denoms_list.append(t_sym)
            restrictions_list.append(f"Điểm kỳ dị Euler–Cauchy: {clean_indep} ≠ 0.")

    eq_latex = _build_equation_latex(lhs_expr, rhs_expr, t_sym, y_sym, yp_sym, yp2_sym)
    rhs_latex = expr_to_latex(isolated_rhs)
    rhs_latex = rhs_latex.replace(r"y_{prime}", f"{clean_dep}'").replace("y_{prime}", f"{clean_dep}'")

    return ParsedNumericalODE(
        raw_input=cleaned,
        order=order,
        indep_var=t_sym,
        dep_var=y_sym,
        yp_sym=yp_sym,
        yp2_sym=yp2_sym,
        rhs_expr=isolated_rhs,
        rhs_str=str(isolated_rhs),
        rhs_latex=rhs_latex,
        equation_latex=eq_latex,
        lhs_expr=lhs_expr,
        raw_rhs_expr=rhs_expr,
        leading_coeff=leading_coeff,
        is_euler_cauchy=is_euler_cauchy,
        euler_cauchy_original_latex=ec_orig_latex,
        domain_restrictions=tuple(dict.fromkeys(restrictions_list)),
        original_denominators=tuple(denoms_list),
        interval_spec=interval_spec,
    )


def _solve_real_roots_in_interval(expr: sp.Expr, var: sp.Symbol, t_low: float, t_high: float) -> list[float]:
    """Find real roots of univariate expression in [t_low, t_high], safely ignoring failures."""
    if not expr.has(var) or expr.free_symbols - {var}:
        return []
    try:
        roots = sp.solve(expr, var)
    except Exception:
        return []
    hits: list[float] = []
    for r in roots:
        try:
            c_val = complex(sp.N(r, 20))
            if abs(c_val.imag) <= 1e-12 and math.isfinite(c_val.real):
                rv = float(c_val.real)
                if t_low - 1e-12 <= rv <= t_high + 1e-12:
                    hits.append(rv)
        except Exception:
            continue
    return hits


def check_interval_singularities(
    parsed: ParsedNumericalODE,
    t0: float,
    t_end: float,
) -> str | None:
    """Detect singularities, branch violations, and pure-t domain violations on [min(t0, T), max(t0, T)]."""
    t_low = min(t0, t_end)
    t_high = max(t0, t_end)
    t_sym = parsed.indep_var

    # 1. Explicit interval constraint validation if user provided e.g. 't > 0'
    if parsed.interval_spec is not None and parsed.interval_spec.interval is not None:
        iv = parsed.interval_spec.interval
        if iv.contains(sp.Float(t0)) is False or iv.contains(sp.Float(t_end)) is False:
            return (
                f"Khoảng tích phân [{t0:g}, {t_end:g}] nằm ngoài miền xác định '{parsed.interval_spec.raw}' đã chỉ định."
            )

    # 2. Euler-Cauchy singularity guard at t = 0
    if parsed.is_euler_cauchy:
        if abs(t0) <= _ZERO_TOL or abs(t_end) <= _ZERO_TOL or (t_low < 0.0 < t_high):
            return (
                f"Phương trình Euler–Cauchy có điểm kỳ dị chính quy tại {t_sym.name} = 0. "
                f"Khoảng tích phân [{t0:g}, {t_end:g}] chạm hoặc đi qua {t_sym.name} = 0 nên không hợp lệ; "
                f"vui lòng chọn khoảng hoàn toàn nằm trong {t_sym.name} > 0 hoặc {t_sym.name} < 0."
            )

    # 3. Pure-t denominators from source AST and isolated RHS
    denoms_to_check = list(parsed.original_denominators)
    _, rhs_denom = parsed.rhs_expr.as_numer_denom()
    if rhs_denom != 1:
        denoms_to_check.append(rhs_denom)

    for d_expr in denoms_to_check:
        if d_expr.free_symbols <= {t_sym} and d_expr.has(t_sym):
            hits = _solve_real_roots_in_interval(d_expr, t_sym, t_low, t_high)
            if hits:
                pts = ", ".join(f"{r:g}" for r in hits)
                return (
                    f"Phát hiện điểm kỳ dị (mẫu số {d_expr} = 0) tại {t_sym.name} = {pts} "
                    f"trong khoảng tích phân [{t_low:g}, {t_high:g}]."
                )

    # 4. Pure-t logarithms, even roots, and tangent/secant/cotangent/cosecant poles
    for node in sp.preorder_traversal(parsed.rhs_expr):
        if isinstance(node, sp.log):
            arg = node.args[0]
            if arg.free_symbols <= {t_sym} and arg.has(t_sym):
                hits = _solve_real_roots_in_interval(arg, t_sym, t_low, t_high)
                if hits:
                    pts = ", ".join(f"{r:g}" for r in hits)
                    return (
                        f"Đối số logarit {arg} triệt tiêu tại {t_sym.name} = {pts} trong khoảng [{t_low:g}, {t_high:g}]."
                    )
        elif isinstance(node, (sp.tan, sp.sec)):
            arg = node.args[0]
            if arg.free_symbols <= {t_sym} and arg.has(t_sym):
                # Check if cos(arg) changes sign or vanishes at endpoints/sample points
                try:
                    fn = compile_safe_real_evaluator(arg, (t_sym,))
                    a_min = min(fn(t_low), fn(t_high))
                    a_max = max(fn(t_low), fn(t_high))
                    k_min = math.floor((a_min / math.pi) - 0.5) - 1
                    k_max = math.ceil((a_max / math.pi) - 0.5) + 1
                    if k_max - k_min <= 200:
                        for k in range(k_min, k_max + 1):
                            pole_arg = (k + 0.5) * math.pi
                            if a_min - 1e-12 <= pole_arg <= a_max + 1e-12:
                                hits = _solve_real_roots_in_interval(arg - sp.Float(pole_arg), t_sym, t_low, t_high)
                                if hits:
                                    return (
                                        f"Phát hiện điểm kỳ dị của hàm {type(node).__name__} tại {t_sym.name} ≈ {hits[0]:g} "
                                        f"trong khoảng [{t_low:g}, {t_high:g}]."
                                    )
                except Exception:
                    pass
        elif isinstance(node, (sp.cot, sp.csc)):
            arg = node.args[0]
            if arg.free_symbols <= {t_sym} and arg.has(t_sym):
                try:
                    fn = compile_safe_real_evaluator(arg, (t_sym,))
                    a_min = min(fn(t_low), fn(t_high))
                    a_max = max(fn(t_low), fn(t_high))
                    k_min = math.floor(a_min / math.pi) - 1
                    k_max = math.ceil(a_max / math.pi) + 1
                    if k_max - k_min <= 200:
                        for k in range(k_min, k_max + 1):
                            pole_arg = k * math.pi
                            if a_min - 1e-12 <= pole_arg <= a_max + 1e-12:
                                hits = _solve_real_roots_in_interval(arg - sp.Float(pole_arg), t_sym, t_low, t_high)
                                if hits:
                                    return (
                                        f"Phát hiện điểm kỳ dị của hàm {type(node).__name__} tại {t_sym.name} ≈ {hits[0]:g} "
                                        f"trong khoảng [{t_low:g}, {t_high:g}]."
                                    )
                except Exception:
                    pass

    return None
