"""Safe input normalization and parser for ordinary differential equations (ODE)."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any
import sympy as sp

from math_app.domain.exceptions import InvalidInputError
from math_app.input.parser import normalize_variable_name, parse_safe_expression

# Whitelisted symbolic parameters commonly appearing in textbook differential equations
ALLOWED_ODE_PARAMETERS = frozenset({"a", "b", "c", "k", "m", "n", "p", "q", "g", "r", "C", "C1", "C2", "x0", "y0", "t0", "v0"})


@dataclass(frozen=True)
class ParsedODE:
    """Structured representation of a parsed and validated differential equation."""

    raw_input: str
    canonical_eq: str
    independent_var: sp.Symbol
    dependent_var: sp.Symbol
    lhs_expr: sp.Expr
    rhs_expr: sp.Expr
    standard_expr: sp.Expr  # LHS - RHS (where y' is replaced by y_prime)
    initial_condition: tuple[sp.Expr, sp.Expr] | None = None  # (t0, y0)
    p_expr: sp.Expr | None = None
    g_expr: sp.Expr | None = None
    a_coeff: sp.Expr | None = None
    b_coeff: sp.Expr | None = None
    is_linear: bool = False
    is_constant_coeff: bool = False


@dataclass(frozen=True)
class ParsedSecondOrderODE:
    """Structured representation of a parsed second-order differential equation: ay'' + by' + cy = g(t)."""

    raw_input: str
    canonical_eq: str
    independent_var: sp.Symbol
    dependent_var: sp.Symbol
    lhs_expr: sp.Expr
    rhs_expr: sp.Expr
    standard_expr: sp.Expr  # LHS - RHS (where y'' is y_double_prime, y' is y_prime)
    a_coeff: sp.Expr  # coefficient of y''
    b_coeff: sp.Expr  # coefficient of y'
    c_coeff: sp.Expr  # coefficient of y
    p_expr: sp.Expr  # normalized coefficient p(t) = b(t)/a(t)
    q_expr: sp.Expr  # normalized coefficient q(t) = c(t)/a(t)
    rem_expr: sp.Expr  # nonhomogeneous term if any
    is_constant_coeff: bool
    is_homogeneous: bool
    initial_condition: tuple[sp.Expr, sp.Expr] | None = None  # (t0, y0)
    initial_derivative: tuple[sp.Expr, sp.Expr] | None = None  # (t0, v0)
    known_solution: sp.Expr | None = None


def extract_initial_condition_from_string(raw: str) -> tuple[str, str | None]:
    """Separate the main equation string from any initial condition like 'y(0) = 1'.

    Returns (clean_equation_string, initial_condition_string_or_None).
    """
    cleaned = raw.strip()
    if not cleaned:
        return "", None

    # Check if string ends with an initial condition like ', y(0) = 1' or '; y(0) = 1'
    m = re.search(r"[,;]\s*(y\s*\([^)]+\)\s*=\s*[^,;]+)\s*$", cleaned)
    if m:
        ic_part = m.group(1).strip()
        eq_part = cleaned[:m.start()].strip()
        return eq_part, ic_part

    # Check if there are multiple parts separated by comma or semicolon
    parts = [p.strip() for p in re.split(r"[,;]", cleaned) if p.strip()]
    if len(parts) == 1:
        # Check if an initial condition is embedded with 'with' or similar
        return cleaned, None

    # Identify which part is an initial condition e.g. y(0) = 1 or y(t0) = y0
    eq_parts: list[str] = []
    ic_part_found: str | None = None

    ic_pattern = re.compile(r"^y\s*\(\s*([^)]+)\s*\)\s*=\s*(.+)$")
    for part in parts:
        if ic_pattern.match(part) and ic_part_found is None:
            ic_part_found = part
        else:
            eq_parts.append(part)

    return ", ".join(eq_parts), ic_part_found


def normalize_ode_equation_string(raw: str, indep_var: str = "t", dep_var: str = "y") -> str:
    """Normalize mathematical notation for derivatives and functions in ODEs.

    Converts:
    - M dx + N dy = 0 -> M + N*y_prime = 0
    - y''(t), y''(x), y'', \frac{d^2y}{dt^2} -> y_double_prime
    - y'(t), y'(x), y' -> y_prime
    - dy/dt, dy/dx, \frac{dy}{dt} -> y_prime
    - y(t), y(x) -> y
    - 2y -> 2*y, 0y -> 0*y
    """
    norm = raw.strip()

    # Normalize differential forms e.g. M dx + N dy = 0 or M*dx + N*dy = 0
    if ("dx" in norm or f"d{indep_var}" in norm) and ("dy" in norm or f"d{dep_var}" in norm):
        norm = re.sub(r"\*\s*d" + re.escape(indep_var) + r"\b", "", norm)
        norm = re.sub(r"\bd" + re.escape(indep_var) + r"\b", "1", norm)
        norm = re.sub(r"\*\s*d" + re.escape(dep_var) + r"\b", "*y_prime", norm)
        norm = re.sub(r"\bd" + re.escape(dep_var) + r"\b", "y_prime", norm)
        # Also clean up cases like (1) or *1
        norm = re.sub(r"\*\s*1\b", "", norm)

    # 1. Normalize LaTeX second derivative notations
    norm = re.sub(r"\\frac\{\s*d\^?\{?2\}?\s*" + re.escape(dep_var) + r"\s*\}\{\s*d\s*" + re.escape(indep_var) + r"\^?\{?2\}?\s*\}", "y_double_prime", norm)
    norm = re.sub(r"\\frac\{\s*d\^?\{?2\}?\s*y\s*\}\{\s*d\s*t\^?\{?2\}?\s*\}", "y_double_prime", norm)
    norm = re.sub(r"\\frac\{\s*d\^?\{?2\}?\s*y\s*\}\{\s*d\s*x\^?\{?2\}?\s*\}", "y_double_prime", norm)

    # Normalize d2y/dt2, d^2y/dt^2, d2y/dx2, d^2y/dx^2
    norm = re.sub(r"\bd\^?2?\s*y\s*/\s*d\s*t\^?2?\b", "y_double_prime", norm)
    norm = re.sub(r"\bd\^?2?\s*y\s*/\s*d\s*x\^?2?\b", "y_double_prime", norm)
    norm = re.sub(rf"\bd\^?2?\s*{re.escape(dep_var)}\s*/\s*d\s*{re.escape(indep_var)}\^?2?\b", "y_double_prime", norm)

    # Normalize double prime notation y''(t), y''(x), y'', y"(t), y"
    norm = re.sub(rf"\b{re.escape(dep_var)}''\s*\(\s*{re.escape(indep_var)}\s*\)", "y_double_prime", norm)
    norm = re.sub(r"\by''\s*\(\s*[a-zA-Z]\s*\)", "y_double_prime", norm)
    norm = re.sub(rf"\b{re.escape(dep_var)}''", "y_double_prime", norm)
    norm = re.sub(r"y\^\\prime\\prime|y\^\{\\prime\\prime\}|y\^\{''\}", "y_double_prime", norm)
    norm = re.sub(r"y''", "y_double_prime", norm)
    norm = re.sub(rf"\b{re.escape(dep_var)}\"\s*\(\s*{re.escape(indep_var)}\s*\)", "y_double_prime", norm)
    norm = re.sub(rf"\b{re.escape(dep_var)}\"", "y_double_prime", norm)
    norm = re.sub(r'y"', "y_double_prime", norm)

    # 2. Normalize LaTeX first derivative notations
    norm = re.sub(r"\\frac\{\s*d\s*" + re.escape(dep_var) + r"\s*\}\{\s*d\s*" + re.escape(indep_var) + r"\s*\}", "y_prime", norm)
    norm = re.sub(r"\\frac\{\s*d\s*y\s*\}\{\s*d\s*t\s*\}", "y_prime", norm)
    norm = re.sub(r"\\frac\{\s*d\s*y\s*\}\{\s*d\s*x\s*\}", "y_prime", norm)

    # Normalize dy/dt, dy/dx
    norm = re.sub(r"\bdy\s*/\s*dt\b", "y_prime", norm)
    norm = re.sub(r"\bdy\s*/\s*dx\b", "y_prime", norm)
    norm = re.sub(rf"\bd{re.escape(dep_var)}\s*/\s*d{re.escape(indep_var)}\b", "y_prime", norm)

    # Normalize prime notation y'(t), y'(x) or y'
    norm = re.sub(rf"\b{re.escape(dep_var)}'\s*\(\s*{re.escape(indep_var)}\s*\)", "y_prime", norm)
    norm = re.sub(r"\by'\s*\(\s*[a-zA-Z]\s*\)", "y_prime", norm)
    norm = re.sub(rf"\b{re.escape(dep_var)}'", "y_prime", norm)
    norm = re.sub(r"y\^\\prime|y\^\{'\}", "y_prime", norm)
    norm = re.sub(r"y'", "y_prime", norm)

    # 3. Normalize function notation y(t) -> y, y(x) -> y
    norm = re.sub(rf"\b{re.escape(dep_var)}\s*\(\s*{re.escape(indep_var)}\s*\)", dep_var, norm)
    norm = re.sub(r"\by\s*\(\s*[tx]\s*\)", "y", norm)

    # 4. Implicit multiplication with y_double_prime, y_prime, y:
    # 4a. Numbers followed by variables: e.g. 2y'' -> 2*y_double_prime, 2y' -> 2*y_prime, 2y -> 2*y
    norm = re.sub(r"(\d+)\s*y_double_prime\b", r"\1*y_double_prime", norm)
    norm = re.sub(r"(\d+)\s*y_prime\b", r"\1*y_prime", norm)
    norm = re.sub(r"(\d+)\s*y\b", r"\1*y", norm)

    # 4b. Variable expressions followed by y_double_prime, y_prime, y: e.g. 2t^2y'' -> 2t^2*y_double_prime, 3ty' -> 3t*y_prime
    norm = re.sub(r"([a-zA-Z0-9_\)\]])\s*y_double_prime\b", lambda m: m.group(1) + "*y_double_prime" if not m.group(1).endswith("*") and not m.group(1).endswith("_") else m.group(0), norm)
    norm = re.sub(r"([a-zA-Z0-9_\)\]])\s*y_prime\b", lambda m: m.group(1) + "*y_prime" if not m.group(1).endswith("*") and not m.group(1).endswith("_") and not m.group(1).endswith("double") else m.group(0), norm)
    norm = re.sub(r"([a-zA-Z0-9_\)\]])\s*y\b", lambda m: m.group(1) + "*y" if not m.group(1).endswith("*") and not m.group(1).endswith("_") and not m.group(1).endswith("prime") and not m.group(1).endswith("d") else m.group(0), norm)

    return norm


def parse_initial_condition(
    ic_str: str,
    indep_var: str = "t",
    allowed_variables: set[str] | frozenset[str] | None = None,
) -> tuple[sp.Expr, sp.Expr]:
    """Safely parse an initial condition string like 'y(0) = 1' or 'y(t0) = y0' via safe AST.

    Returns (t0_expr, y0_expr).
    """
    ic_pattern = re.compile(r"^y\s*\(\s*([^)]+)\s*\)\s*=\s*(.+)$")
    match = ic_pattern.match(ic_str.strip())
    if not match:
        raise InvalidInputError(
            f"Điều kiện ban đầu '{ic_str}' không hợp lệ. Cú pháp chuẩn: y(t0) = y0 (Invalid initial condition format)."
        )

    t0_raw = match.group(1).strip()
    y0_raw = match.group(2).strip()

    extra = set(allowed_variables) if allowed_variables else set()
    extra_with_params = extra | ALLOWED_ODE_PARAMETERS | {"x", "t"}

    t0_expr = parse_safe_expression(t0_raw, target_variable=indep_var, allowed_variables=extra_with_params, evaluate=True)
    y0_expr = parse_safe_expression(y0_raw, target_variable=indep_var, allowed_variables=extra_with_params, evaluate=True)

    return t0_expr, y0_expr


def parse_ode_input(
    raw_input: str,
    target_variable: str = "t",
    dependent_variable: str = "y",
    parameters: dict[str, Any] | None = None,
) -> ParsedODE:
    """Safely validate, normalize, and parse a differential equation and optional initial condition.

    Bypasses eval and sympy.sympify entirely to guarantee runtime safety.
    """
    cleaned = raw_input.strip()
    if not cleaned:
        raise InvalidInputError("Phương trình vi phân không được để trống (Differential equation cannot be empty).")

    params = parameters or {}
    clean_indep = normalize_variable_name(target_variable) if target_variable else "t"
    clean_dep = normalize_variable_name(dependent_variable) if dependent_variable else "y"

    # 1. Check for initial condition from parameters or string
    eq_str, ic_str = extract_initial_condition_from_string(cleaned)
    if "initial_condition" in params and params["initial_condition"]:
        ic_str = str(params["initial_condition"]).strip()
    elif "t0" in params and "y0" in params and str(params["t0"]).strip() and str(params["y0"]).strip():
        ic_str = f"y({params['t0']}) = {params['y0']}"

    # Auto-detect independent variable between 'x' and 't' when unambiguous in the ODE itself
    # Initial condition parameter values (e.g. y(0) = x) must not hijack the independent variable
    if clean_indep in {"t", "x"}:
        has_x = bool("dx" in eq_str or re.search(r"\bx\b", eq_str))
        has_t = bool("dt" in eq_str or re.search(r"\bt\b", eq_str))
        if has_x and not has_t:
            clean_indep = "x"
        elif has_t and not has_x:
            clean_indep = "t"

    t_sym = sp.Symbol(clean_indep)
    y_sym = sp.Symbol(clean_dep)
    yp_sym = sp.Symbol("y_prime")

    parsed_ic: tuple[sp.Expr, sp.Expr] | None = None
    if ic_str:
        parsed_ic = parse_initial_condition(
            ic_str,
            indep_var=clean_indep,
            allowed_variables={clean_indep, clean_dep},
        )

    # 2. Check for explicit equation parameters (a, b or p, g)
    if "a" in params and "b" in params and not eq_str:
        a_raw = str(params["a"]).strip()
        b_raw = str(params["b"]).strip()
        a_expr = parse_safe_expression(a_raw, target_variable=clean_indep, allowed_variables=ALLOWED_ODE_PARAMETERS, evaluate=True)
        b_expr = parse_safe_expression(b_raw, target_variable=clean_indep, allowed_variables=ALLOWED_ODE_PARAMETERS, evaluate=True)
        # y' = a*y + b
        p_expr = -a_expr
        g_expr = b_expr
        std_expr = yp_sym - (a_expr * y_sym + b_expr)
        canonical = f"y' = {a_expr}*y + {b_expr}" if b_expr >= 0 else f"y' = {a_expr}*y - {-b_expr}"
        return ParsedODE(
            raw_input=cleaned,
            canonical_eq=canonical,
            independent_var=t_sym,
            dependent_var=y_sym,
            lhs_expr=yp_sym,
            rhs_expr=a_expr * y_sym + b_expr,
            standard_expr=std_expr,
            initial_condition=parsed_ic,
            p_expr=p_expr,
            g_expr=g_expr,
            a_coeff=a_expr,
            b_coeff=b_expr,
            is_linear=True,
            is_constant_coeff=bool(t_sym not in a_expr.free_symbols and t_sym not in b_expr.free_symbols),
        )

    # 3. Parse equation string
    norm_eq = normalize_ode_equation_string(eq_str, indep_var=clean_indep, dep_var=clean_dep)

    if "=" in norm_eq:
        parts = norm_eq.split("=")
        if len(parts) != 2:
            raise InvalidInputError("Phương trình chỉ được chứa đúng một dấu '=' (Must contain exactly one '=').")
        lhs_raw, rhs_raw = parts[0].strip(), parts[1].strip()
        if not lhs_raw or not rhs_raw:
            raise InvalidInputError("Hai vế của phương trình không được để trống (LHS and RHS cannot be empty).")
    else:
        lhs_raw = norm_eq
        rhs_raw = "0"

    allowed_vars = {clean_indep, clean_dep, "y_prime", "x", "t"} | ALLOWED_ODE_PARAMETERS

    lhs_expr = parse_safe_expression(lhs_raw, target_variable=clean_indep, allowed_variables=allowed_vars, evaluate=False)
    rhs_expr = parse_safe_expression(rhs_raw, target_variable=clean_indep, allowed_variables=allowed_vars, evaluate=False)

    standard_expr = sp.simplify(lhs_expr - rhs_expr)

    # 4. Check for presence of first derivative
    if yp_sym not in standard_expr.free_symbols:
        raise InvalidInputError(
            "Phương trình không chứa đạo hàm cấp 1 y' hoặc dy/dt (No first-order derivative found in equation)."
        )

    # 5. Analyze linearity in y_prime and y
    deg_yp = sp.degree(standard_expr, yp_sym)
    if deg_yp != 1:
        # Non-linear in y' (e.g. (y')^2 or higher)
        return ParsedODE(
            raw_input=cleaned,
            canonical_eq=f"{lhs_expr} = {rhs_expr}",
            independent_var=t_sym,
            dependent_var=y_sym,
            lhs_expr=lhs_expr,
            rhs_expr=rhs_expr,
            standard_expr=standard_expr,
            initial_condition=parsed_ic,
            is_linear=False,
            is_constant_coeff=False,
        )

    # standard_expr = A(t)*y_prime + rem(t, y) = 0
    expanded_std = sp.expand(standard_expr)
    A_coeff = expanded_std.coeff(yp_sym, 1)
    rem_expr = expanded_std.coeff(yp_sym, 0)

    # A(t) must be independent of y and y_prime
    if y_sym in A_coeff.free_symbols or yp_sym in A_coeff.free_symbols:
        return ParsedODE(
            raw_input=cleaned,
            canonical_eq=f"{lhs_expr} = {rhs_expr}",
            independent_var=t_sym,
            dependent_var=y_sym,
            lhs_expr=lhs_expr,
            rhs_expr=rhs_expr,
            standard_expr=standard_expr,
            initial_condition=parsed_ic,
            is_linear=False,
            is_constant_coeff=False,
        )

    # Check linearity of rem_expr in y: rem_expr = B(t)*y - C(t)
    deg_y = sp.degree(rem_expr, y_sym)
    if deg_y > 1:
        return ParsedODE(
            raw_input=cleaned,
            canonical_eq=f"{lhs_expr} = {rhs_expr}",
            independent_var=t_sym,
            dependent_var=y_sym,
            lhs_expr=lhs_expr,
            rhs_expr=rhs_expr,
            standard_expr=standard_expr,
            initial_condition=parsed_ic,
            is_linear=False,
            is_constant_coeff=False,
        )

    B_coeff = rem_expr.coeff(y_sym, 1)
    neg_C_coeff = rem_expr.coeff(y_sym, 0)
    C_coeff = -neg_C_coeff

    # Verify that rem_expr == B*y - C and that B and C are free of y
    diff = sp.simplify(rem_expr - (B_coeff * y_sym + neg_C_coeff))
    if diff != 0 or y_sym in B_coeff.free_symbols or y_sym in C_coeff.free_symbols:
        return ParsedODE(
            raw_input=cleaned,
            canonical_eq=f"{lhs_expr} = {rhs_expr}",
            independent_var=t_sym,
            dependent_var=y_sym,
            lhs_expr=lhs_expr,
            rhs_expr=rhs_expr,
            standard_expr=standard_expr,
            initial_condition=parsed_ic,
            is_linear=False,
            is_constant_coeff=False,
        )

    # Standard linear form: y' + p(t)*y = g(t)
    p_expr = sp.simplify(B_coeff / A_coeff)
    g_expr = sp.simplify(C_coeff / A_coeff)

    # Constant coefficient check: p(t) and g(t) do not contain t
    is_const = bool(t_sym not in p_expr.free_symbols and t_sym not in g_expr.free_symbols)
    a_coeff = -p_expr if is_const else None
    b_coeff = g_expr if is_const else None

    return ParsedODE(
        raw_input=cleaned,
        canonical_eq=f"{lhs_expr} = {rhs_expr}",
        independent_var=t_sym,
        dependent_var=y_sym,
        lhs_expr=lhs_expr,
        rhs_expr=rhs_expr,
        standard_expr=standard_expr,
        initial_condition=parsed_ic,
        p_expr=p_expr,
        g_expr=g_expr,
        a_coeff=a_coeff,
        b_coeff=b_coeff,
        is_linear=True,
        is_constant_coeff=is_const,
    )


def extract_second_order_ics_from_string(raw: str) -> tuple[str, str | None, str | None, str | None]:
    """Separate the main equation string from initial conditions and known solution.

    Returns (clean_equation_string, y_ic_str_or_None, yp_ic_str_or_None, y1_str_or_None).
    """
    cleaned = raw.strip()
    if not cleaned:
        return "", None, None, None

    parts = [p.strip() for p in re.split(r"[,;]", cleaned) if p.strip()]
    if len(parts) == 1:
        return cleaned, None, None, None

    eq_parts: list[str] = []
    y_ic_str: str | None = None
    yp_ic_str: str | None = None
    y1_str: str | None = None

    y1_pattern = re.compile(r"^y_?1\s*(?:\(\s*[^)]+\s*\))?\s*=\s*(.+)$")
    yp_pattern = re.compile(r"^(?:y'|y_prime|y\^\\prime|dy/d[a-zA-Z])\s*\(\s*([^)]+)\s*\)\s*=\s*(.+)$")
    y_pattern = re.compile(r"^y\s*\(\s*([^)]+)\s*\)\s*=\s*(.+)$")

    for part in parts:
        if y1_pattern.match(part) and y1_str is None:
            y1_str = part
        elif yp_pattern.match(part) and yp_ic_str is None:
            yp_ic_str = part
        elif y_pattern.match(part) and y_ic_str is None:
            y_ic_str = part
        else:
            eq_parts.append(part)

    clean_eq = ", ".join(eq_parts) if eq_parts else parts[0]
    return clean_eq, y_ic_str, yp_ic_str, y1_str


def parse_second_order_initial_conditions(
    y_ic_str: str,
    yp_ic_str: str,
    indep_var: str = "t",
    allowed_variables: set[str] | frozenset[str] | None = None,
) -> tuple[tuple[sp.Expr, sp.Expr], tuple[sp.Expr, sp.Expr]]:
    """Safely parse both initial conditions: y(t0) = y0 and y'(t0) = v0.

    Returns ((t0_expr, y0_expr), (t0_expr, v0_expr)).
    """
    ic_y_pattern = re.compile(r"^y\s*\(\s*([^)]+)\s*\)\s*=\s*(.+)$")
    m_y = ic_y_pattern.match(y_ic_str.strip())
    if not m_y:
        raise InvalidInputError(
            f"Điều kiện ban đầu '{y_ic_str}' không hợp lệ. Cú pháp chuẩn: y(t0) = y0."
        )

    ic_yp_pattern = re.compile(r"^(?:y'|y_prime|y\^\\prime|dy/d[a-zA-Z])\s*\(\s*([^)]+)\s*\)\s*=\s*(.+)$")
    m_yp = ic_yp_pattern.match(yp_ic_str.strip())
    if not m_yp:
        raise InvalidInputError(
            f"Điều kiện đạo hàm ban đầu '{yp_ic_str}' không hợp lệ. Cú pháp chuẩn: y'(t0) = v0."
        )

    t0_raw = m_y.group(1).strip()
    y0_raw = m_y.group(2).strip()

    t1_raw = m_yp.group(1).strip()
    v0_raw = m_yp.group(2).strip()

    extra = set(allowed_variables) if allowed_variables else set()
    extra_with_params = extra | ALLOWED_ODE_PARAMETERS | {"x", "t"}

    t0_expr = parse_safe_expression(t0_raw, target_variable=indep_var, allowed_variables=extra_with_params, evaluate=True)
    y0_expr = parse_safe_expression(y0_raw, target_variable=indep_var, allowed_variables=extra_with_params, evaluate=True)
    t1_expr = parse_safe_expression(t1_raw, target_variable=indep_var, allowed_variables=extra_with_params, evaluate=True)
    v0_expr = parse_safe_expression(v0_raw, target_variable=indep_var, allowed_variables=extra_with_params, evaluate=True)

    if sp.simplify(t0_expr - t1_expr) != 0:
        raise InvalidInputError(
            f"Bài toán giá trị ban đầu cấp hai (IVP) yêu cầu hai điều kiện tại cùng một điểm t0: y({t0_expr}) và y'({t1_expr}) không cùng điểm khởi đầu."
        )

    return ((t0_expr, y0_expr), (t0_expr, v0_expr))


def parse_known_solution(
    raw_y1: str,
    indep_var: str = "t",
    allowed_variables: set[str] | frozenset[str] | None = None,
) -> sp.Expr:
    """Safely parse known solution y1(t) for Reduction of Order."""
    cleaned = raw_y1.strip()
    if not cleaned:
        raise InvalidInputError("Nghiệm đã biết y1(t) không được để trống (Known solution y1 cannot be empty).")

    m = re.match(r"^y_?1\s*(?:\(\s*[^)]+\s*\))?\s*=\s*(.+)$", cleaned)
    if m:
        cleaned = m.group(1).strip()

    extra = set(allowed_variables) if allowed_variables else set()
    extra_with_params = extra | ALLOWED_ODE_PARAMETERS | {indep_var, "x", "t"}

    y1_expr = parse_safe_expression(cleaned, target_variable=indep_var, allowed_variables=extra_with_params, evaluate=True)

    if sp.simplify(y1_expr) == 0:
        raise InvalidInputError("Nghiệm đã cho y1(t) không được là hàm hằng 0 (Known fundamental solution cannot be identically zero).")

    return y1_expr


def parse_second_order_ode_input(
    raw_input: str,
    target_variable: str = "t",
    dependent_variable: str = "y",
    parameters: dict[str, Any] | None = None,
) -> ParsedSecondOrderODE:
    """Safely validate, normalize, and parse a second-order ODE and optional initial conditions."""
    cleaned = raw_input.strip()
    if not cleaned:
        raise InvalidInputError("Phương trình vi phân không được để trống (Differential equation cannot be empty).")

    params = dict(parameters) if parameters else {}
    clean_indep = normalize_variable_name(target_variable) if target_variable else "t"
    clean_dep = normalize_variable_name(dependent_variable) if dependent_variable else "y"

    # 1. Extract initial conditions and known solution from string or parameters
    eq_str, y_ic_str, yp_ic_str, y1_str = extract_second_order_ics_from_string(cleaned)

    # Auto-detect independent variable between 'x' and 't' when unambiguous in the ODE itself
    # Initial condition parameter values (e.g. y'(0) = x) must not hijack the independent variable
    if clean_indep in {"t", "x"}:
        has_x = bool("dx" in eq_str or re.search(r"\bx\b", eq_str))
        has_t = bool("dt" in eq_str or re.search(r"\bt\b", eq_str))
        if has_x and not has_t:
            clean_indep = "x"
        elif has_t and not has_x:
            clean_indep = "t"

    t_sym = sp.Symbol(clean_indep)
    y_sym = sp.Symbol(clean_dep)
    yp_sym = sp.Symbol("y_prime")
    yp2_sym = sp.Symbol("y_double_prime")

    # Check parameters overrides
    if "y1" in params and params["y1"]:
        y1_str = str(params["y1"]).strip()
    elif "known_solution" in params and params["known_solution"]:
        y1_str = str(params["known_solution"]).strip()

    # Check IC parameters
    if "t0" in params and "y0" in params and str(params["t0"]).strip() and str(params["y0"]).strip():
        y_ic_str = f"y({params['t0']}) = {params['y0']}"
    if "t0" in params and "v0" in params and str(params["t0"]).strip() and str(params["v0"]).strip():
        yp_ic_str = f"y'({params['t0']}) = {params['v0']}"
    elif "t0" in params and "yp0" in params and str(params["t0"]).strip() and str(params["yp0"]).strip():
        yp_ic_str = f"y'({params['t0']}) = {params['yp0']}"

    # Also check if user provided a combined initial_condition parameter
    if "initial_condition" in params and params["initial_condition"]:
        ic_comb = str(params["initial_condition"]).strip()
        _, p_y_ic, p_yp_ic, _ = extract_second_order_ics_from_string("dummy = 0, " + ic_comb)
        if p_y_ic:
            y_ic_str = p_y_ic
        if p_yp_ic:
            yp_ic_str = p_yp_ic
        if not p_y_ic and not p_yp_ic and "=" in ic_comb:
            if "'" in ic_comb:
                yp_ic_str = ic_comb
            else:
                y_ic_str = ic_comb

    parsed_ic: tuple[sp.Expr, sp.Expr] | None = None
    parsed_deriv_ic: tuple[sp.Expr, sp.Expr] | None = None
    if y_ic_str and yp_ic_str:
        (parsed_ic, parsed_deriv_ic) = parse_second_order_initial_conditions(
            y_ic_str, yp_ic_str, indep_var=clean_indep, allowed_variables={clean_indep, clean_dep}
        )
    elif y_ic_str:
        parsed_ic = parse_initial_condition(y_ic_str, indep_var=clean_indep, allowed_variables={clean_indep, clean_dep})
    elif yp_ic_str:
        m_yp = re.match(r"^(?:y'|y_prime|dy/d[tx])\s*\(\s*([^)]+)\s*\)\s*=\s*(.+)$", yp_ic_str.strip())
        if m_yp:
            extra_with_params = {clean_indep, clean_dep, "x", "t"} | ALLOWED_ODE_PARAMETERS
            t0_e = parse_safe_expression(m_yp.group(1).strip(), target_variable=clean_indep, allowed_variables=extra_with_params, evaluate=True)
            v0_e = parse_safe_expression(m_yp.group(2).strip(), target_variable=clean_indep, allowed_variables=extra_with_params, evaluate=True)
            parsed_deriv_ic = (t0_e, v0_e)

    parsed_y1: sp.Expr | None = None
    if y1_str:
        parsed_y1 = parse_known_solution(y1_str, indep_var=clean_indep, allowed_variables={clean_indep, clean_dep})

    # 2. Normalize equation string
    norm_eq = normalize_ode_equation_string(eq_str, indep_var=clean_indep, dep_var=clean_dep)

    if "=" in norm_eq:
        parts = norm_eq.split("=")
        if len(parts) != 2:
            raise InvalidInputError("Phương trình chỉ được chứa đúng một dấu '=' (Must contain exactly one '=').")
        lhs_raw, rhs_raw = parts[0].strip(), parts[1].strip()
        if not lhs_raw or not rhs_raw:
            raise InvalidInputError("Hai vế của phương trình không được để trống (LHS and RHS cannot be empty).")
    else:
        lhs_raw = norm_eq
        rhs_raw = "0"

    allowed_vars = {clean_indep, clean_dep, "y_prime", "y_double_prime", "x", "t"} | ALLOWED_ODE_PARAMETERS

    lhs_expr = parse_safe_expression(lhs_raw, target_variable=clean_indep, allowed_variables=allowed_vars, evaluate=False)
    rhs_expr = parse_safe_expression(rhs_raw, target_variable=clean_indep, allowed_variables=allowed_vars, evaluate=False)

    standard_expr = sp.simplify(lhs_expr - rhs_expr)

    # 3. Check for presence of second derivative
    if yp2_sym not in standard_expr.free_symbols:
        raise InvalidInputError(
            "Phương trình không chứa đạo hàm cấp 2 y'' hoặc d2y/dt2 (No second-order derivative found in equation)."
        )

    # 4. Analyze linearity in y_double_prime, y_prime, and y
    deg_yp2 = sp.degree(standard_expr, yp2_sym)
    if deg_yp2 != 1:
        raise InvalidInputError(
            "Phương trình phi tuyến đối với đạo hàm cấp hai y'' (Nonlinear ODE in y'')."
        )

    expanded = sp.expand(standard_expr)
    a_coeff = expanded.coeff(yp2_sym, 1)
    rem1 = expanded.coeff(yp2_sym, 0)

    if sp.simplify(a_coeff) == 0:
        raise InvalidInputError("Hệ số của đạo hàm cấp hai y'' bằng 0; không phải phương trình cấp hai (a = 0).")

    if y_sym in a_coeff.free_symbols or yp_sym in a_coeff.free_symbols or yp2_sym in a_coeff.free_symbols:
        raise InvalidInputError("Hệ số của y'' không được phụ thuộc vào y hoặc đạo hàm của y (Nonlinear ODE).")

    deg_yp = sp.degree(rem1, yp_sym)
    if deg_yp > 1:
        raise InvalidInputError("Phương trình phi tuyến đối với đạo hàm cấp một y' (Nonlinear ODE in y').")

    b_coeff = rem1.coeff(yp_sym, 1)
    rem2 = rem1.coeff(yp_sym, 0)

    if y_sym in b_coeff.free_symbols or yp_sym in b_coeff.free_symbols or yp2_sym in b_coeff.free_symbols:
        raise InvalidInputError("Hệ số của y' không được phụ thuộc vào y hoặc đạo hàm của y (Nonlinear ODE).")

    deg_y = sp.degree(rem2, y_sym)
    if deg_y > 1:
        raise InvalidInputError("Phương trình phi tuyến đối với hàm y (Nonlinear ODE in y).")

    c_coeff = rem2.coeff(y_sym, 1)
    rem3 = rem2.coeff(y_sym, 0)

    if y_sym in c_coeff.free_symbols or yp_sym in c_coeff.free_symbols or yp2_sym in c_coeff.free_symbols:
        raise InvalidInputError("Hệ số của y không được phụ thuộc vào y hoặc đạo hàm của y (Nonlinear ODE).")

    rem_expr = sp.simplify(rem3)
    is_homo = bool(rem_expr == 0)

    is_const = bool(
        t_sym not in a_coeff.free_symbols and
        t_sym not in b_coeff.free_symbols and
        t_sym not in c_coeff.free_symbols
    )

    p_expr = sp.simplify(b_coeff / a_coeff)
    q_expr = sp.simplify(c_coeff / a_coeff)

    return ParsedSecondOrderODE(
        raw_input=cleaned,
        canonical_eq=f"{lhs_expr} = {rhs_expr}",
        independent_var=t_sym,
        dependent_var=y_sym,
        lhs_expr=lhs_expr,
        rhs_expr=rhs_expr,
        standard_expr=standard_expr,
        a_coeff=a_coeff,
        b_coeff=b_coeff,
        c_coeff=c_coeff,
        p_expr=p_expr,
        q_expr=q_expr,
        rem_expr=rem_expr,
        is_constant_coeff=is_const,
        is_homogeneous=is_homo,
        initial_condition=parsed_ic,
        initial_derivative=parsed_deriv_ic,
        known_solution=parsed_y1,
    )


def parse_wronskian_input(
    raw_input: str,
    target_variable: str = "t",
    parameters: dict[str, Any] | None = None,
) -> tuple[sp.Expr, sp.Expr, sp.Symbol]:
    """Safely parse two functions y1, y2 for Wronskian computation."""
    params = dict(parameters) if parameters else {}
    clean_indep = normalize_variable_name(target_variable) if target_variable else "t"

    y1_raw = str(params.get("y1", "")).strip()
    y2_raw = str(params.get("y2", "")).strip()

    if not y1_raw or not y2_raw:
        cleaned = raw_input.strip()
        parts = [p.strip() for p in re.split(r"[,;]", cleaned) if p.strip()]
        if len(parts) >= 2:
            p1, p2 = parts[0], parts[1]
            m1 = re.match(r"^y_?1\s*(?:\(\s*[^)]+\s*\))?\s*=\s*(.+)$", p1)
            if m1:
                p1 = m1.group(1).strip()
            m2 = re.match(r"^y_?2\s*(?:\(\s*[^)]+\s*\))?\s*=\s*(.+)$", p2)
            if m2:
                p2 = m2.group(1).strip()
            if not y1_raw:
                y1_raw = p1
            if not y2_raw:
                y2_raw = p2

    if not y1_raw or not y2_raw:
        raise InvalidInputError(
            "Cần cung cấp đủ hai hàm số y1 và y2 để tính Wronskian. Cú pháp: y1 = f(t), y2 = g(t) hoặc f(t), g(t)."
        )

    t_sym = sp.Symbol(clean_indep)
    allowed = {clean_indep, "x", "t"} | ALLOWED_ODE_PARAMETERS
    y1_expr = parse_safe_expression(y1_raw, target_variable=clean_indep, allowed_variables=allowed, evaluate=True)
    y2_expr = parse_safe_expression(y2_raw, target_variable=clean_indep, allowed_variables=allowed, evaluate=True)

    return y1_expr, y2_expr, t_sym
