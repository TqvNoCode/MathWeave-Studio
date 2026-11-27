"""Safe input normalization and parser for ordinary differential equations (ODE)."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Literal
import sympy as sp

from math_app.domain.exceptions import InvalidInputError
from math_app.input.parser import normalize_variable_name, parse_safe_expression

# Whitelisted symbolic parameters commonly appearing in textbook differential equations
ALLOWED_ODE_PARAMETERS = frozenset({"a", "b", "c", "k", "m", "n", "p", "q", "g", "r", "C", "C1", "C2", "x0", "y0", "t0", "v0", "I"})


@dataclass(frozen=True)
class SourceDomainConstraint:
    """Structured symbolic domain constraint extracted from unsimplified source AST."""

    relation: Literal["ne", "ge", "gt"]
    expr: sp.Expr
    description: str


@dataclass(frozen=True)
class ParsedIntervalConstraint:
    """Structured representation of a requested connected interval constraint."""

    raw: str
    interval: sp.Interval | None
    variable: str | None = None
    is_supported: bool = True
    error: str | None = None


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
    is_homogeneous: bool = False
    is_classical_homogeneous: bool = False
    homogeneous_F_v: sp.Expr | None = None
    interval: str | None = None
    original_domain_restrictions: tuple[str, ...] = ()
    original_denominators: tuple[sp.Expr, ...] = ()
    leading_coeffs: tuple[sp.Expr, ...] = ()
    original_domain_constraints: tuple[SourceDomainConstraint, ...] = ()
    interval_spec: ParsedIntervalConstraint | None = None


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
    interval: str | None = None
    original_domain_restrictions: tuple[str, ...] = ()
    original_denominators: tuple[sp.Expr, ...] = ()
    leading_coeffs: tuple[sp.Expr, ...] = ()
    original_domain_constraints: tuple[SourceDomainConstraint, ...] = ()
    interval_spec: ParsedIntervalConstraint | None = None


def _safe_degree(expr: sp.Expr, sym: sp.Symbol) -> int | None:
    """Safely return polynomial degree of expr in sym, or None if expr is not polynomial in sym.

    Never raises PolynomialError on transcendental functions like sin(y), exp(y), etc.
    """
    if not expr.has(sym):
        return 0
    try:
        poly = expr.as_poly(sym)
        if poly is not None:
            return poly.degree()
    except Exception:
        pass
    try:
        return sp.degree(expr, sym)
    except Exception:
        pass
    return None


def _split_top_level_clauses(raw: str) -> list[str]:
    """Split input by ',' or ';' only at top-level bracket depth 0."""
    clauses: list[str] = []
    buf: list[str] = []
    depth = 0
    for ch in raw:
        if ch in "([{":
            depth += 1
        elif ch in ")]}" and depth > 0:
            depth -= 1
        if ch in ",;" and depth == 0:
            part = "".join(buf).strip()
            if part:
                clauses.append(part)
            buf = []
        else:
            buf.append(ch)
    tail = "".join(buf).strip()
    if tail:
        clauses.append(tail)
    return clauses


def _is_interval_clause(clause: str) -> bool:
    """Detect whether a top-level clause expresses a domain or interval constraint."""
    c = clause.strip()
    if not c:
        return False
    # Never treat derivative expressions or equations / ICs (standalone '=') as interval clauses
    if re.search(r"y'|y\"|y_prime|y_double_prime|y_higher_prime|\bdy/d|\bdiff\s*\(", c):
        return False
    if re.search(r"(?<![<>!])=(?!=)", c):
        return False
    if any(op in c for op in ("<=", ">=", "!=", "<", ">")):
        return True
    if re.search(r"\bin\b|∈", c):
        return True
    if c.startswith(("(", "[")) and c.endswith((")", "]")) and "," in c:
        return True
    return False


def _parse_interval_endpoint(
    token: str,
    target_variable: str,
    *,
    allow_neg_inf: bool = False,
    allow_pos_inf: bool = False,
) -> tuple[sp.Expr | None, str | None]:
    """Parse a single interval endpoint into an exact real/infinite SymPy expression."""
    tok = token.strip().replace("∞", "oo")
    if not tok:
        return None, "Cận khoảng xác định không được để trống."
    if tok in ("oo", "+oo", "inf", "+inf", "infinity", "+infinity"):
        if allow_pos_inf:
            return sp.oo, None
        return None, "Khoảng đóng không được chứa cận +oo."
    if tok in ("-oo", "-inf", "-infinity"):
        if allow_neg_inf:
            return -sp.oo, None
        return None, "Khoảng đóng không được chứa cận -oo."

    try:
        if re.fullmatch(r"[+-]?\d+", tok):
            val: sp.Expr = sp.Integer(int(tok))
        elif re.fullmatch(r"[+-]?\d+\.\d+", tok):
            val = sp.Rational(tok)
        else:
            val = parse_safe_expression(
                tok,
                target_variable=target_variable,
                allowed_variables=set(),
                evaluate=True,
            )
    except Exception as exc:
        return None, f"Không thể phân tích cận khoảng '{token}': {exc}"

    if val.free_symbols:
        return None, f"Cận khoảng '{token}' chứa ký hiệu chưa xác định {tuple(val.free_symbols)}."
    if val.has(sp.oo, -sp.oo, sp.zoo, sp.nan, sp.I, sp.AccumBounds):
        return None, f"Cận khoảng '{token}' không phải là số thực hữu hạn."
    if val.is_real is not True or val.is_finite is not True:
        return None, f"Cận khoảng '{token}' không được chứng minh là số thực hữu hạn."
    return val, None


def _build_validated_interval(
    raw: str,
    left: sp.Expr,
    right: sp.Expr,
    *,
    left_open: bool,
    right_open: bool,
    variable: str | None,
) -> ParsedIntervalConstraint:
    """Validate endpoint ordering (left < right) and construct ParsedIntervalConstraint."""
    if left == sp.oo or right == -sp.oo:
        return ParsedIntervalConstraint(
            raw=raw,
            interval=None,
            variable=variable,
            is_supported=False,
            error=f"Khoảng xác định '{raw}' có cận vô cực không hợp lệ.",
        )
    if left != -sp.oo and right != sp.oo:
        diff = sp.simplify(right - left)
        if diff.is_positive is not True:
            return ParsedIntervalConstraint(
                raw=raw,
                interval=None,
                variable=variable,
                is_supported=False,
                error=f"Khoảng xác định '{raw}' rỗng hoặc suy biến (yêu cầu cận dưới < cận trên).",
            )
    iv = sp.Interval(
        left,
        right,
        left_open=left_open or (left == -sp.oo),
        right_open=right_open or (right == sp.oo),
    )
    if iv == sp.S.EmptySet or isinstance(iv, sp.FiniteSet):
        return ParsedIntervalConstraint(
            raw=raw,
            interval=None,
            variable=variable,
            is_supported=False,
            error=f"Khoảng xác định '{raw}' không phải là khoảng liên thông có độ dài dương.",
        )
    return ParsedIntervalConstraint(
        raw=raw,
        interval=iv,
        variable=variable,
        is_supported=True,
        error=None,
    )


def parse_interval_constraint(
    interval_raw: str,
    variable: str | None = None,
) -> ParsedIntervalConstraint:
    """Parse an explicit connected real interval constraint into a structured sp.Interval.

    Supports single inequalities (t > 2, 2 < t, t <= -1), double inequalities (-1 < t < 1),
    and bracketed intervals ((2, 5), [1, 4], t in (0, oo)). Returns is_supported=False for
    unrecognized, multi-component, symbolic, or degenerate interval syntax.
    """
    cleaned = interval_raw.strip()
    target_var = normalize_variable_name(variable) if variable else None
    ep_var = target_var or "t"

    if not cleaned:
        return ParsedIntervalConstraint(
            raw=interval_raw,
            interval=None,
            variable=target_var,
            is_supported=False,
            error="Khoảng xác định không được để trống.",
        )

    # 1. Membership prefix: e.g. "t in (1, 5)" or "t ∈ [2, oo)"
    body = cleaned
    m_mem = re.match(r"^([a-zA-Z][a-zA-Z0-9_]*)\s*(?:in|∈)\s*(.+)$", cleaned)
    if m_mem:
        mem_var = normalize_variable_name(m_mem.group(1))
        if target_var and mem_var != target_var:
            return ParsedIntervalConstraint(
                raw=interval_raw,
                interval=None,
                variable=target_var,
                is_supported=False,
                error=f"Biến trong khoảng xác định '{mem_var}' không khớp biến độc lập '{target_var}'.",
            )
        target_var = target_var or mem_var
        ep_var = target_var
        body = m_mem.group(2).strip()

    # 2. Explicit bracketed interval: (a, b), [a, b], (a, b], [a, b)
    if len(body) >= 5 and body[0] in "([ " and body[0] in "([" and body[-1] in ")]":
        lb, rb = body[0], body[-1]
        inner = body[1:-1].strip()
        parts = _split_top_level_clauses(inner)
        if len(parts) == 2 and "," in inner and ";" not in inner:
            left_open = lb == "("
            right_open = rb == ")"
            left_val, left_err = _parse_interval_endpoint(
                parts[0], ep_var, allow_neg_inf=left_open, allow_pos_inf=False
            )
            if left_err or left_val is None:
                return ParsedIntervalConstraint(
                    raw=interval_raw,
                    interval=None,
                    variable=target_var,
                    is_supported=False,
                    error=left_err,
                )
            right_val, right_err = _parse_interval_endpoint(
                parts[1], ep_var, allow_neg_inf=False, allow_pos_inf=right_open
            )
            if right_err or right_val is None:
                return ParsedIntervalConstraint(
                    raw=interval_raw,
                    interval=None,
                    variable=target_var,
                    is_supported=False,
                    error=right_err,
                )
            return _build_validated_interval(
                interval_raw,
                left_val,
                right_val,
                left_open=left_open,
                right_open=right_open,
                variable=target_var,
            )

    # If membership notation didn't yield a single bracketed interval, reject conservatively
    if m_mem:
        return ParsedIntervalConstraint(
            raw=interval_raw,
            interval=None,
            variable=target_var,
            is_supported=False,
            error=f"Cú pháp khoảng xác định '{interval_raw}' không được hỗ trợ.",
        )

    # 3. Double inequality: a < t < b, a <= t < b, b > t > a, etc.
    m_dbl = re.match(
        r"^(.+?)\s*(<=|<|>=|>)\s*([a-zA-Z][a-zA-Z0-9_]*)\s*(<=|<|>=|>)\s*(.+)$",
        cleaned,
    )
    if m_dbl:
        lhs_tok, op1, var_tok, op2, rhs_tok = (
            m_dbl.group(1),
            m_dbl.group(2),
            normalize_variable_name(m_dbl.group(3)),
            m_dbl.group(4),
            m_dbl.group(5),
        )
        if target_var and var_tok != target_var:
            return ParsedIntervalConstraint(
                raw=interval_raw,
                interval=None,
                variable=target_var,
                is_supported=False,
                error=f"Biến trong khoảng xác định '{var_tok}' không khớp biến độc lập '{target_var}'.",
            )
        target_var = target_var or var_tok
        ep_var = target_var
        if op1 in ("<", "<=") and op2 in ("<", "<="):
            left_tok, right_tok = lhs_tok, rhs_tok
            left_open, right_open = op1 == "<", op2 == "<"
        elif op1 in (">", ">=") and op2 in (">", ">="):
            left_tok, right_tok = rhs_tok, lhs_tok
            left_open, right_open = op2 == ">", op1 == ">"
        else:
            return ParsedIntervalConstraint(
                raw=interval_raw,
                interval=None,
                variable=target_var,
                is_supported=False,
                error=f"Chuỗi bất đẳng thức '{interval_raw}' có hướng không nhất quán.",
            )
        left_val, left_err = _parse_interval_endpoint(
            left_tok, ep_var, allow_neg_inf=left_open, allow_pos_inf=False
        )
        if left_err or left_val is None:
            return ParsedIntervalConstraint(
                raw=interval_raw,
                interval=None,
                variable=target_var,
                is_supported=False,
                error=left_err,
            )
        right_val, right_err = _parse_interval_endpoint(
            right_tok, ep_var, allow_neg_inf=False, allow_pos_inf=right_open
        )
        if right_err or right_val is None:
            return ParsedIntervalConstraint(
                raw=interval_raw,
                interval=None,
                variable=target_var,
                is_supported=False,
                error=right_err,
            )
        return _build_validated_interval(
            interval_raw,
            left_val,
            right_val,
            left_open=left_open,
            right_open=right_open,
            variable=target_var,
        )

    # 4. Single inequality: var > a, var <= b, a < var, etc.
    m_left = re.match(r"^([a-zA-Z][a-zA-Z0-9_]*)\s*(<=|<|>=|>)\s*(.+)$", cleaned)
    if m_left:
        var_tok = normalize_variable_name(m_left.group(1))
        op = m_left.group(2)
        bound_tok = m_left.group(3)
    else:
        m_right = re.match(r"^(.+?)\s*(<=|<|>=|>)\s*([a-zA-Z][a-zA-Z0-9_]*)$", cleaned)
        if not m_right:
            return ParsedIntervalConstraint(
                raw=interval_raw,
                interval=None,
                variable=target_var,
                is_supported=False,
                error=f"Cú pháp khoảng xác định '{interval_raw}' không được hỗ trợ.",
            )
        bound_tok = m_right.group(1)
        flip = {"<": ">", "<=": ">=", ">": "<", ">=": "<="}
        op = flip[m_right.group(2)]
        var_tok = normalize_variable_name(m_right.group(3))

    if target_var and var_tok != target_var:
        return ParsedIntervalConstraint(
            raw=interval_raw,
            interval=None,
            variable=target_var,
            is_supported=False,
            error=f"Biến trong khoảng xác định '{var_tok}' không khớp biến độc lập '{target_var}'.",
        )
    target_var = target_var or var_tok
    ep_var = target_var
    bound_val, bound_err = _parse_interval_endpoint(
        bound_tok, ep_var, allow_neg_inf=False, allow_pos_inf=False
    )
    if bound_err or bound_val is None:
        return ParsedIntervalConstraint(
            raw=interval_raw,
            interval=None,
            variable=target_var,
            is_supported=False,
            error=bound_err,
        )

    if op in (">", ">="):
        return _build_validated_interval(
            interval_raw,
            bound_val,
            sp.oo,
            left_open=(op == ">"),
            right_open=True,
            variable=target_var,
        )
    return _build_validated_interval(
        interval_raw,
        -sp.oo,
        bound_val,
        left_open=True,
        right_open=(op == "<"),
        variable=target_var,
    )


def extract_interval_from_string(raw: str) -> tuple[str, str | None]:
    """Separate string from interval constraint like 't > 0', '-1 < t < 1', 't in (1, 5)', etc.

    Returns (cleaned_string, interval_str_or_None).
    """
    cleaned = raw.strip()
    if not cleaned:
        return "", None

    parts = _split_top_level_clauses(cleaned)
    if len(parts) <= 1:
        return cleaned, None

    eq_parts: list[str] = []
    found_interval: str | None = None

    for p in parts:
        if _is_interval_clause(p) and found_interval is None:
            found_interval = p
        else:
            eq_parts.append(p)

    return ", ".join(eq_parts), found_interval


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

    # 0. Normalize LaTeX and text higher derivative notations (order >= 3)
    # e.g. \frac{d^3y}{dt^3}, d3y/dt3, d^3y/dt^3, y''', y'''', y^(3) -> y_higher_prime
    norm = re.sub(r"\\frac\{\s*d\^?\{?(?:[3-9]|\d{2,})\}?\s*" + re.escape(dep_var) + r"\s*\}\{\s*d\s*" + re.escape(indep_var) + r"\^?\{?(?:[3-9]|\d{2,})\}?\s*\}", "y_higher_prime", norm)
    norm = re.sub(r"\\frac\{\s*d\^?\{?(?:[3-9]|\d{2,})\}?\s*y\s*\}\{\s*d\s*[tx]\^?\{?(?:[3-9]|\d{2,})\}?\s*\}", "y_higher_prime", norm)
    norm = re.sub(r"\bd(?:\^?(?:[3-9]|\d{2,}))\s*y\s*/\s*d\s*[tx](?:\^?(?:[3-9]|\d{2,}))\b", "y_higher_prime", norm)
    norm = re.sub(rf"\bd(?:\^?(?:[3-9]|\d{{2,}}))\s*{re.escape(dep_var)}\s*/\s*d\s*{re.escape(indep_var)}(?:\^?(?:[3-9]|\d{{2,}}))\b", "y_higher_prime", norm)
    norm = re.sub(rf"\b{re.escape(dep_var)}'{{3,}}\s*\(\s*{re.escape(indep_var)}\s*\)", "y_higher_prime", norm)
    norm = re.sub(r"\by'{3,}\s*\(\s*[a-zA-Z]\s*\)", "y_higher_prime", norm)
    norm = re.sub(rf"\b{re.escape(dep_var)}'{{3,}}", "y_higher_prime", norm)
    norm = re.sub(r"y'{3,}", "y_higher_prime", norm)
    norm = re.sub(rf'\b{re.escape(dep_var)}"{{2,}}', "y_higher_prime", norm)
    norm = re.sub(r'y"{2,}', "y_higher_prime", norm)

    # 1. Normalize LaTeX second derivative notations
    norm = re.sub(r"\\frac\{\s*d\^?\{?2\}?\s*" + re.escape(dep_var) + r"\s*\}\{\s*d\s*" + re.escape(indep_var) + r"\^?\{?2\}?\s*\}", "y_double_prime", norm)
    norm = re.sub(r"\\frac\{\s*d\^?\{?2\}?\s*y\s*\}\{\s*d\s*t\^?\{?2\}?\s*\}", "y_double_prime", norm)
    norm = re.sub(r"\\frac\{\s*d\^?\{?2\}?\s*y\s*\}\{\s*d\s*x\^?\{?2\}?\s*\}", "y_double_prime", norm)

    # Normalize d2y/dt2, d^2y/dt^2, d2y/dx2, d^2y/dx^2
    norm = re.sub(r"\bd(?:\^2|2)\s*y\s*/\s*d\s*t(?:\^2|2)\b", "y_double_prime", norm)
    norm = re.sub(r"\bd(?:\^2|2)\s*y\s*/\s*d\s*x(?:\^2|2)\b", "y_double_prime", norm)
    norm = re.sub(rf"\bd(?:\^2|2)\s*{re.escape(dep_var)}\s*/\s*d\s*{re.escape(indep_var)}(?:\^2|2)\b", "y_double_prime", norm)

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

    # 4. Normalize differential forms e.g. M dx + N dy = 0 or M*dx + N*dy = 0
    # Must run AFTER derivative quotients like \frac{dy}{dx} are converted
    if re.search(r"\bd" + re.escape(indep_var) + r"\b", norm) and re.search(r"\bd" + re.escape(dep_var) + r"\b", norm):
        norm = re.sub(r"([a-zA-Z0-9_\)\]])\s*d" + re.escape(indep_var) + r"\b", r"\1*d" + indep_var, norm)
        norm = re.sub(r"([a-zA-Z0-9_\)\]])\s*d" + re.escape(dep_var) + r"\b", r"\1*d" + dep_var, norm)
        norm = re.sub(r"\*\s*d" + re.escape(indep_var) + r"\b", "", norm)
        norm = re.sub(r"\bd" + re.escape(indep_var) + r"\b", "1", norm)
        norm = re.sub(r"\*\s*d" + re.escape(dep_var) + r"\b", "*y_prime", norm)
        norm = re.sub(r"\bd" + re.escape(dep_var) + r"\b", "y_prime", norm)
        # Also clean up cases like (1) or *1
        norm = re.sub(r"\*\s*1\b", "", norm)

    # 5. Implicit multiplication with y_higher_prime, y_double_prime, y_prime, y:
    # 5a. Numbers followed by variables: e.g. 2y''' -> 2*y_higher_prime, 2y'' -> 2*y_double_prime, 2y' -> 2*y_prime, 2y -> 2*y
    norm = re.sub(r"(\d+)\s*y_higher_prime\b", r"\1*y_higher_prime", norm)
    norm = re.sub(r"(\d+)\s*y_double_prime\b", r"\1*y_double_prime", norm)
    norm = re.sub(r"(\d+)\s*y_prime\b", r"\1*y_prime", norm)
    norm = re.sub(r"(\d+)\s*y\b", r"\1*y", norm)

    # 5b. Variable expressions followed by y_higher_prime, y_double_prime, y_prime, y: e.g. 2t^2y'' -> 2t^2*y_double_prime, 3ty' -> 3t*y_prime
    norm = re.sub(r"([a-zA-Z0-9_\)\]])\s*y_higher_prime\b", lambda m: m.group(1) + "*y_higher_prime" if not m.group(1).endswith("*") and not m.group(1).endswith("_") else m.group(0), norm)
    norm = re.sub(r"([a-zA-Z0-9_\)\]])\s*y_double_prime\b", lambda m: m.group(1) + "*y_double_prime" if not m.group(1).endswith("*") and not m.group(1).endswith("_") else m.group(0), norm)
    norm = re.sub(r"([a-zA-Z0-9_\)\]])\s*y_prime\b", lambda m: m.group(1) + "*y_prime" if not m.group(1).endswith("*") and not m.group(1).endswith("_") and not m.group(1).endswith("double") and not m.group(1).endswith("higher") else m.group(0), norm)
    norm = re.sub(r"([a-zA-Z0-9_\)\]])\s*y\b", lambda m: m.group(1) + "*y" if not m.group(1).endswith("*") and not m.group(1).endswith("_") and not m.group(1).endswith("prime") and not m.group(1).endswith("d") else m.group(0), norm)

    return norm


def detect_ode_order(raw: str, indep_var: str = "t", dep_var: str = "y") -> int:
    """Detect the highest derivative order in an ordinary differential equation string.

    Returns:
        0: No derivatives found (ordinary algebraic equation or expression).
        1: First-order differential equation (contains y', dy/dt, M dx + N dy = 0).
        2: Second-order differential equation (contains y'', d2y/dt2, etc.).
        >=3: Higher-order differential equation (contains y''', d3y/dt3, etc.).
    """
    clean = raw.strip()
    if not clean:
        return 0

    # 1. Clean out intervals like 't > 0'
    eq_without_int, _ = extract_interval_from_string(clean)

    # 2. Clean out initial conditions so initial derivatives like y'(0)=2 in a second order IVP
    # (e.g. y'' + 4y = 4t, y(0)=1, y'(0)=2) don't confuse the equation's own highest order.
    eq_pure, _, _, _ = extract_second_order_ics_from_string(eq_without_int)
    eq_pure, _ = extract_initial_condition_from_string(eq_pure)
    eq_pure = eq_pure.strip()

    c_indep = indep_var.strip() if indep_var else "t"
    c_dep = dep_var.strip() if dep_var else "y"

    esc_dep = re.escape(c_dep)
    esc_indep = re.escape(c_indep)
    var_pat = r"(?:" + esc_indep + r"|[a-zA-Z])"

    # A. Check Higher Order (>= 3)
    higher_order_patterns = [
        r"\b" + esc_dep + r"'{3,}",
        r'\b' + esc_dep + r'"{2,}',
        r"\b" + esc_dep + r"['\"]{3,}",
        r"\b" + esc_dep + r"\^\{?\((?:[3-9]|\d{2,})\)\}?",
        r"\\frac\{\s*d\^?\{?(?:[3-9]|\d{2,})\}?\s*" + esc_dep + r"\s*\}\{\s*d\s*" + var_pat + r"\^?\{?(?:[3-9]|\d{2,})\}?\s*\}",
        r"\bd(?:\^?(?:[3-9]|\d{2,}))\s*" + esc_dep + r"\s*/\s*d\s*" + var_pat + r"(?:\^?(?:[3-9]|\d{2,}))\b",
        r"\bd(?:[3-9]|\d{2,})\s*" + esc_dep + r"\s*/\s*d\s*" + var_pat + r"(?:[3-9]|\d{2,})\b",
        r"\bdiff\s*\(\s*" + esc_dep + r"\s*,\s*" + var_pat + r"\s*,\s*(?:[3-9]|\d{2,})\s*\)",
    ]
    for pat in higher_order_patterns:
        if re.search(pat, eq_pure):
            return 3

    # B. Check Second Order (= 2)
    second_order_patterns = [
        r"\b" + esc_dep + r"''(?!')",
        r'\b' + esc_dep + r'"(?!"|\')',
        r"\b" + esc_dep + r"\^\{?''\}?",
        r"\b" + esc_dep + r"\^\{?\\prime\\prime\}?",
        r"\b" + esc_dep + r"\^?\{?\(2\)\}?",
        r"\\frac\{\s*d\^?\{?2\}?\s*" + esc_dep + r"\s*\}\{\s*d\s*" + var_pat + r"\^?\{?2\}?\s*\}",
        r"\bd(?:\^2|2)\s*" + esc_dep + r"\s*/\s*d\s*" + var_pat + r"(?:\^2|2)\b",
        r"\bdiff\s*\(\s*" + esc_dep + r"\s*,\s*" + var_pat + r"\s*,\s*2\s*\)",
    ]
    for pat in second_order_patterns:
        if re.search(pat, eq_pure):
            return 2

    norm = normalize_ode_equation_string(eq_pure, indep_var=c_indep, dep_var=c_dep)
    if "y_double_prime" in norm:
        return 2

    # C. Check First Order (= 1)
    first_order_patterns = [
        r"\b" + esc_dep + r"'(?!')",
        r"\b" + esc_dep + r"\^\{?\\prime\}?",
        r"\b" + esc_dep + r"\^?\{?\(1\)\}?",
        r"\\frac\{\s*d\s*" + esc_dep + r"\s*\}\{\s*d\s*" + var_pat + r"\s*\}",
        r"\bd\s*" + esc_dep + r"\s*/\s*d\s*" + var_pat + r"\b",
        r"\bdiff\s*\(\s*" + esc_dep + r"\s*,\s*" + var_pat + r"\s*(?:,\s*1\s*)?\)",
    ]
    for pat in first_order_patterns:
        if re.search(pat, eq_pure):
            return 1

    if re.search(r"\bd" + esc_dep + r"\b", eq_pure) and re.search(r"\bd[a-zA-Z]\b", eq_pure):
        return 1

    if "y_prime" in norm:
        return 1

    return 0


def validate_ode_order(raw: str, expected_order: int, indep_var: str = "t", dep_var: str = "y") -> None:
    """Validate that the differential equation in raw matches the expected order (1 or 2).

    Raises:
        InvalidInputError: If order is mismatched or unsupported higher-order, with
        actionable, educational Vietnamese guidance.
    """
    clean = raw.strip()
    if not clean:
        raise InvalidInputError("Phương trình không được để trống. Vui lòng nhập dữ liệu trước khi thực hiện.")

    eq_without_int, _ = extract_interval_from_string(clean)
    eq_pure, _, _, _ = extract_second_order_ics_from_string(eq_without_int)
    eq_pure, _ = extract_initial_condition_from_string(eq_pure)
    eq_pure = eq_pure.strip()

    c_indep = indep_var.strip() if indep_var else "t"
    c_dep = dep_var.strip() if dep_var else "y"

    # Step 0: Immediate check for unsupported higher-order ODEs (order >= 3)
    detected = detect_ode_order(eq_pure, indep_var=c_indep, dep_var=c_dep)
    if detected >= 3:
        raise InvalidInputError(
            "Phương trình không đúng cấp: Bạn đang nhập phương trình vi phân cấp cao (cấp 3 trở lên), "
            "nhưng ứng dụng hiện tại chỉ hỗ trợ phương trình vi phân cấp 1 và cấp 2."
        )

    # Step 1: Preliminary syntax check
    # We normalize equation and run parse_safe_expression with extended allowed variables
    # so genuine syntax errors (unbalanced parenthesis, invalid operators) are raised first.
    norm_eq = normalize_ode_equation_string(eq_pure, indep_var=c_indep, dep_var=c_dep)
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

    allowed_vars = {c_indep, c_dep, "y_prime", "y_double_prime", "y_higher_prime", "x", "t"} | ALLOWED_ODE_PARAMETERS
    parse_safe_expression(lhs_raw, target_variable=c_indep, allowed_variables=allowed_vars, evaluate=False)
    parse_safe_expression(rhs_raw, target_variable=c_indep, allowed_variables=allowed_vars, evaluate=False)

    # Step 2: Context-aware order check
    if expected_order == 1:
        if detected == 2:
            raise InvalidInputError(
                "Phương trình không đúng cấp: Bạn đang nhập phương trình vi phân cấp 2, nhưng không gian làm việc hiện tại chỉ hỗ trợ phương trình cấp 1. "
                "Vui lòng quay lại danh mục toán học và chọn Phương trình vi phân cấp 2."
            )
        elif detected == 0:
            raise InvalidInputError(
                "Phương trình không chứa đạo hàm cấp 1 y' hoặc dy/dt. "
                "Vui lòng nhập phương trình vi phân cấp 1 hoặc chuyển sang danh mục giải phương trình đại số."
            )
    elif expected_order == 2:
        if detected == 1:
            raise InvalidInputError(
                "Phương trình không đúng cấp: Bạn đang nhập phương trình vi phân cấp 1, nhưng không gian làm việc hiện tại chỉ hỗ trợ phương trình vi phân cấp 2 (không chứa đạo hàm cấp 2). "
                "Vui lòng chuyển sang không gian làm việc Phương trình vi phân cấp 1."
            )
        elif detected == 0:
            raise InvalidInputError(
                "Phương trình không chứa đạo hàm cấp 2 y'' hoặc d2y/dt2 (No second-order derivative found in equation). "
                "Vui lòng nhập phương trình vi phân cấp 2."
            )


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

    t0_expr = t0_expr.subs(sp.Symbol("I"), sp.I)
    y0_expr = y0_expr.subs(sp.Symbol("I"), sp.I)

    return t0_expr, y0_expr


def extract_source_domain_constraints(
    exprs: list[sp.Expr] | tuple[sp.Expr, ...],
    var: sp.Symbol,
    dep_var: sp.Symbol,
) -> tuple[tuple[str, ...], tuple[sp.Expr, ...], tuple[SourceDomainConstraint, ...]]:
    """Extract domain restrictions, denominators, and structured constraints before simplification."""
    restrictions: list[str] = []
    denominators: list[sp.Expr] = []
    constraints: list[SourceDomainConstraint] = []
    seen_denoms: set[str] = set()
    seen_constraints: set[tuple[str, str]] = set()
    target_syms = {var, dep_var}
    diff_syms = {sp.Symbol(f"d{var.name}"), sp.Symbol(f"d{dep_var.name}")}

    def _record_constraint(relation: Literal["ne", "ge", "gt"], expr_val: sp.Expr, desc: str) -> None:
        key = (relation, str(expr_val))
        if key not in seen_constraints:
            seen_constraints.add(key)
            constraints.append(SourceDomainConstraint(relation=relation, expr=expr_val, description=desc))

    for expr in exprs:
        for node in sp.preorder_traversal(expr):
            if isinstance(node, sp.Pow):
                b, e = node.as_base_exp()
                e_simp = sp.simplify(e)
                if e_simp.is_negative:
                    b_simp = sp.simplify(b)
                    b_str = str(b_simp)
                    if b_str not in seen_denoms and b_simp != 1:
                        seen_denoms.add(b_str)
                        denominators.append(b_simp)
                        if b_simp.free_symbols & target_syms:
                            desc = f"Điều kiện xác định ban đầu: {b_simp} khác 0 (mẫu số)."
                            restrictions.append(desc)
                            _record_constraint("ne", b_simp, desc)
                        elif not (b_simp.free_symbols & diff_syms) and (
                            bool(b_simp.free_symbols) or b_simp.is_zero is not False
                        ):
                            desc = f"Điều kiện xác định ban đầu: {b_simp} khác 0 (mẫu số)."
                            _record_constraint("ne", b_simp, desc)
                if e_simp.is_Rational and e_simp.q % 2 == 0:
                    b_simp = sp.simplify(b)
                    if b_simp.free_symbols & target_syms:
                        desc = f"Điều kiện xác định ban đầu: {b_simp} >= 0 (căn bậc chẵn)."
                        restrictions.append(desc)
                        _record_constraint("ge", b_simp, desc)
                    elif not (b_simp.free_symbols & diff_syms) and (
                        bool(b_simp.free_symbols) or b_simp.is_nonnegative is not True
                    ):
                        desc = f"Điều kiện xác định ban đầu: {b_simp} >= 0 (căn bậc chẵn)."
                        _record_constraint("ge", b_simp, desc)
            elif isinstance(node, sp.log):
                arg_simp = sp.simplify(node.args[0])
                if arg_simp.free_symbols & target_syms:
                    desc = f"Điều kiện xác định ban đầu: {arg_simp} > 0 (logarit)."
                    restrictions.append(desc)
                    _record_constraint("gt", arg_simp, desc)
                elif not (arg_simp.free_symbols & diff_syms) and (
                    bool(arg_simp.free_symbols) or arg_simp.is_positive is not True
                ):
                    desc = f"Điều kiện xác định ban đầu: {arg_simp} > 0 (logarit)."
                    _record_constraint("gt", arg_simp, desc)

    return tuple(dict.fromkeys(restrictions)), tuple(denominators), tuple(constraints)


def extract_source_domain_info(
    exprs: list[sp.Expr] | tuple[sp.Expr, ...],
    var: sp.Symbol,
    dep_var: sp.Symbol,
) -> tuple[tuple[str, ...], tuple[sp.Expr, ...]]:
    """Extract domain restrictions and original denominators from unsimplified ASTs before simplification."""
    restrictions, denominators, _ = extract_source_domain_constraints(exprs, var, dep_var)
    return restrictions, denominators


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

    # 1. Check for initial condition and interval from parameters or string
    eq_without_int, interval_str = extract_interval_from_string(cleaned)
    if "interval" in params and params["interval"]:
        interval_str = str(params["interval"]).strip()

    eq_str, ic_str = extract_initial_condition_from_string(eq_without_int)
    if "initial_condition" in params and params["initial_condition"]:
        ic_str = str(params["initial_condition"]).strip()
    elif "t0" in params and "y0" in params and str(params["t0"]).strip() and str(params["y0"]).strip():
        ic_str = f"y({params['t0']}) = {params['y0']}"

    # Auto-detect independent variable between 'x' and 't' when unambiguous in the ODE itself
    # Explicit user target_variable should be preserved unless equation clearly specifies otherwise
    if clean_indep in {"t", "x"}:
        has_x = bool("dx" in eq_str or re.search(r"\\b(?:y\(x\)|y'\(x\)|d\^?2?y/dx\^?2?)\b", eq_str) or (target_variable == "x" and "x" in eq_str))
        has_t = bool("dt" in eq_str or re.search(r"\\b(?:y\(t\)|y'\(t\)|d\^?2?y/dt\^?2?)\b", eq_str) or (target_variable == "t" and "t" in eq_str))
        if has_x and not has_t:
            clean_indep = "x"
        elif has_t and not has_x:
            clean_indep = "t"

    t_sym = sp.Symbol(clean_indep)
    y_sym = sp.Symbol(clean_dep)
    yp_sym = sp.Symbol("y_prime")
    interval_spec = parse_interval_constraint(interval_str, variable=clean_indep) if interval_str else None

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
            is_homogeneous=bool(b_expr == 0),
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

    allowed_vars = {clean_indep, clean_dep, "y_prime", "y_double_prime", "y_higher_prime", "x", "t"} | ALLOWED_ODE_PARAMETERS

    lhs_expr = parse_safe_expression(lhs_raw, target_variable=clean_indep, allowed_variables=allowed_vars, evaluate=False)
    rhs_expr = parse_safe_expression(rhs_raw, target_variable=clean_indep, allowed_variables=allowed_vars, evaluate=False)

    # Extract source-domain information before simplify or cancellation
    orig_restrictions, orig_denoms, orig_constraints = extract_source_domain_constraints(
        [lhs_expr, rhs_expr], t_sym, y_sym
    )
    orig_restrictions_list = list(orig_restrictions)
    orig_denoms_list = list(orig_denoms)
    leading_coeffs_list: list[sp.Expr] = []

    standard_expr = sp.simplify(lhs_expr - rhs_expr)

    # Context-aware equation order detection and validation for First-Order ODE
    yp_higher_sym = sp.Symbol("y_higher_prime")
    if yp_higher_sym in standard_expr.free_symbols or detect_ode_order(eq_str, clean_indep, clean_dep) >= 3:
        raise InvalidInputError(
            "Phương trình không đúng cấp: Bạn đang nhập phương trình vi phân cấp cao (cấp 3 trở lên), "
            "nhưng ứng dụng hiện tại chỉ hỗ trợ phương trình vi phân cấp 1 và cấp 2."
        )

    yp2_sym = sp.Symbol("y_double_prime")
    if yp2_sym in standard_expr.free_symbols or detect_ode_order(eq_str, clean_indep, clean_dep) == 2:
        raise InvalidInputError(
            "Phương trình không đúng cấp: Bạn đang nhập phương trình vi phân cấp 2, nhưng không gian làm việc hiện tại chỉ hỗ trợ phương trình cấp 1. "
            "Vui lòng quay lại danh mục toán học và chọn Phương trình vi phân cấp 2."
        )

    # Detect classical degree-0 homogeneous ODE: y' = F(y/x)
    is_classical_homog = False
    F_v: sp.Expr | None = None
    try:
        if lhs_expr == yp_sym:
            is_classical_homog, F_v = check_classical_homogeneous_ode(rhs_expr, t_sym, y_sym)
        elif rhs_expr == yp_sym:
            is_classical_homog, F_v = check_classical_homogeneous_ode(lhs_expr, t_sym, y_sym)
        else:
            yp_sols = sp.solve(standard_expr, yp_sym)
            if yp_sols:
                is_classical_homog, F_v = check_classical_homogeneous_ode(yp_sols[0], t_sym, y_sym)
    except Exception:
        pass

    # 4. Check for presence of first derivative
    if yp_sym not in standard_expr.free_symbols:
        raise InvalidInputError(
            "Phương trình không chứa đạo hàm cấp 1 y' hoặc dy/dt (No first-order derivative found in equation)."
        )

    # 5. Analyze linearity in y_prime and y
    deg_yp = _safe_degree(standard_expr, yp_sym)
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
            is_classical_homogeneous=is_classical_homog,
            homogeneous_F_v=F_v,
            interval=interval_str,
            original_domain_restrictions=tuple(orig_restrictions_list),
            original_denominators=tuple(orig_denoms_list),
            leading_coeffs=tuple(leading_coeffs_list),
            original_domain_constraints=orig_constraints,
            interval_spec=interval_spec,
        )

    # standard_expr = A(t)*y_prime + rem(t, y) = 0
    expanded_std = sp.expand(standard_expr)
    A_coeff = expanded_std.coeff(yp_sym, 1)
    rem_expr = expanded_std.coeff(yp_sym, 0)

    # Preserve leading coefficient singularity of y'
    if A_coeff != 0 and not A_coeff.is_number and (t_sym in A_coeff.free_symbols or y_sym in A_coeff.free_symbols):
        leading_coeffs_list.append(A_coeff)
        orig_restrictions_list.append(f"Điều kiện xác định ban đầu: Hệ số dẫn {A_coeff} khác 0.")

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
            is_classical_homogeneous=is_classical_homog,
            homogeneous_F_v=F_v,
            interval=interval_str,
            original_domain_restrictions=tuple(orig_restrictions_list),
            original_denominators=tuple(orig_denoms_list),
            leading_coeffs=tuple(leading_coeffs_list),
            original_domain_constraints=orig_constraints,
            interval_spec=interval_spec,
        )

    # Check linearity of rem_expr in y: rem_expr = B(t)*y - C(t)
    deg_y = _safe_degree(rem_expr, y_sym)
    if deg_y is None or deg_y > 1:
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
            is_classical_homogeneous=is_classical_homog,
            homogeneous_F_v=F_v,
            interval=interval_str,
            original_domain_restrictions=tuple(orig_restrictions_list),
            original_denominators=tuple(orig_denoms_list),
            leading_coeffs=tuple(leading_coeffs_list),
            original_domain_constraints=orig_constraints,
            interval_spec=interval_spec,
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
            is_classical_homogeneous=is_classical_homog,
            homogeneous_F_v=F_v,
            interval=interval_str,
            original_domain_restrictions=tuple(orig_restrictions_list),
            original_denominators=tuple(orig_denoms_list),
            leading_coeffs=tuple(leading_coeffs_list),
            original_domain_constraints=orig_constraints,
            interval_spec=interval_spec,
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
        is_homogeneous=bool(sp.simplify(g_expr) == 0),
        is_classical_homogeneous=is_classical_homog,
        homogeneous_F_v=F_v,
        interval=interval_str,
        original_domain_restrictions=tuple(orig_restrictions_list),
        original_denominators=tuple(orig_denoms_list),
        leading_coeffs=tuple(leading_coeffs_list),
        original_domain_constraints=orig_constraints,
        interval_spec=interval_spec,
    )


def check_classical_homogeneous_ode(
    rhs_expr: sp.Expr,
    indep_var: sp.Symbol,
    dep_var: sp.Symbol,
) -> tuple[bool, sp.Expr | None]:
    """Check if the first-order differential equation y' = F(x, y) is homogeneous of degree 0 in the classical function sense: F(tx, ty) = F(x, y) <=> F(x, y) = f(y/x).

    Returns (is_homogeneous, substituted_f_of_v) where v = y/x.
    """
    v = sp.Symbol("_v_ratio", real=True)
    try:
        sub_expr = sp.simplify(rhs_expr.subs(dep_var, v * indep_var))
        if not sub_expr.has(indep_var):
            return True, sub_expr
    except Exception:
        pass
    return False, None


def extract_second_order_ics_from_string(raw: str) -> tuple[str, str | None, str | None, str | None]:
    """Separate the main equation string from initial conditions and known solution.

    Returns (clean_equation_string, y_ic_str_or_None, yp_ic_str_or_None, y1_str_or_None).
    """
    cleaned = raw.strip()
    if not cleaned:
        return "", None, None, None

    parts = _split_top_level_clauses(cleaned)
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
        elif _is_interval_clause(part):
            continue
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

    t0_expr = t0_expr.subs(sp.Symbol("I"), sp.I)
    y0_expr = y0_expr.subs(sp.Symbol("I"), sp.I)
    t1_expr = t1_expr.subs(sp.Symbol("I"), sp.I)
    v0_expr = v0_expr.subs(sp.Symbol("I"), sp.I)

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

    # 1. Extract interval constraint, initial conditions and known solution from string or parameters
    eq_without_int, interval_str = extract_interval_from_string(cleaned)
    if "interval" in params and params["interval"]:
        interval_str = str(params["interval"]).strip()

    eq_str, y_ic_str, yp_ic_str, y1_str = extract_second_order_ics_from_string(eq_without_int)

    # Auto-detect independent variable between 'x' and 't' when unambiguous in the ODE itself
    # Explicit user target_variable should be preserved unless equation clearly specifies otherwise
    if clean_indep in {"t", "x"}:
        has_x = bool("dx" in eq_str or re.search(r"\\b(?:y\(x\)|y'\(x\)|y''\(x\)|d\^?2?y/dx\^?2?)\b", eq_str) or (target_variable == "x" and "x" in eq_str))
        has_t = bool("dt" in eq_str or re.search(r"\\b(?:y\(t\)|y'\(t\)|y''\(t\)|d\^?2?y/dt\^?2?)\b", eq_str) or (target_variable == "t" and "t" in eq_str))
        if has_x and not has_t:
            clean_indep = "x"
        elif has_t and not has_x:
            clean_indep = "t"

    t_sym = sp.Symbol(clean_indep)
    y_sym = sp.Symbol(clean_dep)
    yp_sym = sp.Symbol("y_prime")
    interval_spec = parse_interval_constraint(interval_str, variable=clean_indep) if interval_str else None
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

    allowed_vars = {clean_indep, clean_dep, "y_prime", "y_double_prime", "y_higher_prime", "x", "t"} | ALLOWED_ODE_PARAMETERS

    lhs_expr = parse_safe_expression(lhs_raw, target_variable=clean_indep, allowed_variables=allowed_vars, evaluate=False)
    rhs_expr = parse_safe_expression(rhs_raw, target_variable=clean_indep, allowed_variables=allowed_vars, evaluate=False)

    # Extract source-domain information before simplify or cancellation
    orig_restrictions, orig_denoms, orig_constraints = extract_source_domain_constraints(
        [lhs_expr, rhs_expr], t_sym, y_sym
    )
    orig_restrictions_list = list(orig_restrictions)
    orig_denoms_list = list(orig_denoms)
    leading_coeffs_list: list[sp.Expr] = []

    standard_expr = sp.simplify(lhs_expr - rhs_expr)

    # 3. Check for higher-order and presence of second derivative
    yp_higher_sym = sp.Symbol("y_higher_prime")
    if yp_higher_sym in standard_expr.free_symbols or detect_ode_order(eq_str, clean_indep, clean_dep) >= 3:
        raise InvalidInputError(
            "Phương trình không đúng cấp: Bạn đang nhập phương trình vi phân cấp cao (cấp 3 trở lên), "
            "nhưng ứng dụng hiện tại chỉ hỗ trợ phương trình vi phân cấp 1 và cấp 2."
        )

    if yp2_sym not in standard_expr.free_symbols:
        if yp_sym in standard_expr.free_symbols or detect_ode_order(eq_str, clean_indep, clean_dep) == 1:
            raise InvalidInputError(
                "Phương trình không đúng cấp: Bạn đang nhập phương trình vi phân cấp 1, nhưng không gian làm việc hiện tại chỉ hỗ trợ phương trình vi phân cấp 2 (không chứa đạo hàm cấp 2). "
                "Vui lòng chuyển sang không gian làm việc Phương trình vi phân cấp 1."
            )
        raise InvalidInputError(
            "Phương trình không chứa đạo hàm cấp 2 y'' hoặc d2y/dt2 (No second-order derivative found in equation)."
        )

    # 4. Analyze linearity in y_double_prime, y_prime, and y
    deg_yp2 = _safe_degree(standard_expr, yp2_sym)
    if deg_yp2 != 1:
        raise InvalidInputError(
            "Phương trình phi tuyến đối với đạo hàm cấp hai y'' (Nonlinear ODE in y'')."
        )

    expanded = sp.expand(standard_expr)
    a_coeff = sp.simplify(expanded.coeff(yp2_sym, 1))
    rem1 = expanded.coeff(yp2_sym, 0)

    if a_coeff == 0:
        raise InvalidInputError("Hệ số của đạo hàm cấp hai y'' bằng 0; không phải phương trình cấp hai (a = 0).")

    if y_sym in a_coeff.free_symbols or yp_sym in a_coeff.free_symbols or yp2_sym in a_coeff.free_symbols:
        raise InvalidInputError("Hệ số của y'' không được phụ thuộc vào y hoặc đạo hàm của y (Nonlinear ODE).")

    deg_yp = _safe_degree(rem1, yp_sym)
    if deg_yp is None or deg_yp > 1:
        raise InvalidInputError("Phương trình phi tuyến đối với đạo hàm cấp một y' (Nonlinear ODE in y').")

    b_coeff = sp.simplify(rem1.coeff(yp_sym, 1))
    rem2 = rem1.coeff(yp_sym, 0)

    if y_sym in b_coeff.free_symbols or yp_sym in b_coeff.free_symbols or yp2_sym in b_coeff.free_symbols:
        raise InvalidInputError("Hệ số của y' không được phụ thuộc vào y hoặc đạo hàm của y (Nonlinear ODE).")

    deg_y = _safe_degree(rem2, y_sym)
    if deg_y is None or deg_y > 1:
        raise InvalidInputError("Phương trình phi tuyến đối với hàm y (Nonlinear ODE in y).")

    c_coeff = sp.simplify(rem2.coeff(y_sym, 1))
    rem3 = rem2.coeff(y_sym, 0)

    if y_sym in c_coeff.free_symbols or yp_sym in c_coeff.free_symbols or yp2_sym in c_coeff.free_symbols:
        raise InvalidInputError("Hệ số của y không được phụ thuộc vào y hoặc đạo hàm của y (Nonlinear ODE).")

    rem_expr = sp.simplify(rem3)
    is_homo = bool(rem_expr == 0)

    # Preserve leading coefficient singularity of y''
    if a_coeff != 0 and not a_coeff.is_number and (t_sym in a_coeff.free_symbols or y_sym in a_coeff.free_symbols):
        leading_coeffs_list.append(a_coeff)
        orig_restrictions_list.append(f"Điều kiện xác định ban đầu: Hệ số dẫn {a_coeff} khác 0.")

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
        interval=interval_str,
        original_domain_restrictions=tuple(orig_restrictions_list),
        original_denominators=tuple(orig_denoms_list),
        leading_coeffs=tuple(leading_coeffs_list),
        original_domain_constraints=orig_constraints,
        interval_spec=interval_spec,
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
        m_w = re.match(r"^(?:W|w|Wronskian)\s*\((.*)\)$", cleaned, flags=re.DOTALL)
        if m_w:
            cleaned = m_w.group(1).strip()
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
