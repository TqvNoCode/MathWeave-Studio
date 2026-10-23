"""Mathematical input normalization and safe SymPy parsing."""

from __future__ import annotations

import re
import sympy as sp

from math_app.domain.exceptions import InvalidInputError
from math_app.input.validator import validate_expression_syntax


def normalize_variable_name(raw: str) -> str:
    """Normalize user variable input string, stripping differential prefix and mapping Greek aliases."""
    cleaned = raw.strip()
    if not cleaned:
        return "x"

    # Strip differential notation prefix e.g. 'dx', 'dy', 'dt', 'dtheta', 'dθ'
    if (cleaned.startswith("d") or cleaned.startswith("d\\")) and len(cleaned) > 1:
        prefix_len = 2 if cleaned.startswith("d\\") else 1
        candidate = cleaned[prefix_len:].strip()
        if candidate:
            cleaned = candidate

    # Strip leading backslash if present (e.g. \theta -> theta)
    if cleaned.startswith("\\"):
        cleaned = cleaned[1:]

    # Map Greek unicode to ASCII name for consistent LaTeX rendering
    greek_map = {
        "θ": "theta",
        "φ": "phi",
        "ρ": "rho",
    }
    return greek_map.get(cleaned, cleaned)


def normalize_expression_string(raw: str, target_variable: str = "x") -> str:
    """Normalize user expression by expanding common mathematical shortcuts."""
    cleaned = raw.strip()
    if not cleaned:
        return ""

    # Normalize Greek letters & LaTeX notation
    normalized = cleaned.replace("\\theta", "theta").replace("\\phi", "phi").replace("\\rho", "rho")
    normalized = normalized.replace("θ", "theta").replace("φ", "phi").replace("ρ", "rho")

    # 1. Replace power symbol ^ with Python **
    normalized = normalized.replace("^", "**")

    # 2. Normalize ln -> log
    normalized = re.sub(r"\bln\b", "log", normalized)

    # 3. Handle implicit multiplication
    # 3a. Number followed by variable or function: e.g., '2x' -> '2*x', '3sin' -> '3*sin'
    normalized = re.sub(r"(\d+)\s*([a-zA-Z])", r"\1*\2", normalized)

    # 3b. Number followed by opening paren: e.g., '2(' -> '2*('
    normalized = re.sub(r"(\d+)\s*\(", r"\1*(", normalized)

    # 3c. Closing paren followed by opening paren: e.g., ')(' -> ')*('
    normalized = re.sub(r"\)\s*\(", r")*(", normalized)

    # 3d. Closing paren followed by variable/function: e.g., ')x' -> ')*x', ')sin' -> ')*sin'
    normalized = re.sub(r"\)\s*([a-zA-Z])", r")*\1", normalized)

    # 3e. Variable followed by function name: e.g., 'x sin' -> 'x*sin'
    functions = r"(?:sin|cos|tan|sec|csc|cot|asin|acos|atan|exp|log|sqrt)"
    normalized = re.sub(rf"(\b{re.escape(target_variable)}\b)\s*({functions})", r"\1*\2", normalized)

    # 3f. Variable followed by opening paren: e.g., 'x(x + 1)' -> 'x*(x + 1)'
    normalized = re.sub(rf"(\b{re.escape(target_variable)}\b)\s*\(", r"\1*(", normalized)

    return normalized


def parse_mathematical_input(raw_input: str, target_variable: str = "x") -> tuple[sp.Expr, sp.Symbol]:
    """Safely validate and parse user input string into a SymPy expression.

    Returns:
        tuple[sp.Expr, sp.Symbol]: Parsed expression and target variable symbol.

    Raises:
        InvalidInputError: If expression fails validation or cannot be safely parsed.
    """
    clean_var = normalize_variable_name(target_variable)
    normalized = normalize_expression_string(raw_input, clean_var)
    validate_expression_syntax(normalized, clean_var)

    var_symbol = sp.Symbol(clean_var, real=True)
    local_dict = {
        clean_var: var_symbol,
        "x": var_symbol if clean_var == "x" else sp.Symbol("x", real=True),
        "y": var_symbol if clean_var == "y" else sp.Symbol("y", real=True),
        "z": var_symbol if clean_var == "z" else sp.Symbol("z", real=True),
        "t": var_symbol if clean_var == "t" else sp.Symbol("t", real=True),
        "u": var_symbol if clean_var == "u" else sp.Symbol("u", real=True),
        "v": var_symbol if clean_var == "v" else sp.Symbol("v", real=True),
        "r": var_symbol if clean_var == "r" else sp.Symbol("r", real=True),
        "rho": var_symbol if clean_var == "rho" else sp.Symbol("rho", real=True),
        "theta": var_symbol if clean_var == "theta" else sp.Symbol("theta", real=True),
        "phi": var_symbol if clean_var == "phi" else sp.Symbol("phi", real=True),
        "sin": sp.sin,
        "cos": sp.cos,
        "tan": sp.tan,
        "sec": sp.sec,
        "csc": sp.csc,
        "cot": sp.cot,
        "asin": sp.asin,
        "acos": sp.acos,
        "atan": sp.atan,
        "exp": sp.exp,
        "log": sp.log,
        "sqrt": sp.sqrt,
        "pi": sp.pi,
        "E": sp.E,
        "e": sp.E,
    }

    try:
        expr = sp.sympify(normalized, locals=local_dict, evaluate=False)
        return expr, var_symbol
    except Exception as exc:
        raise InvalidInputError(f"Không thể phân tích biểu thức toán học (Failed to parse mathematical expression): {exc}") from exc


def parse_matrix_input(raw_input: str) -> sp.Matrix:
    """Parse a user matrix input string into a SymPy Matrix.

    Supports formats:
    - Nested brackets: [[1, 2], [3, 4]]
    - Semicolon rows: 1, 2; 3, 4
    - Newline rows: 1 2 \\n 3 4

    Raises:
        InvalidInputError: If input is empty, has ragged rows, or cannot be parsed.
    """
    cleaned = raw_input.strip()
    if not cleaned:
        raise InvalidInputError("Dữ liệu ma trận không được để trống (Matrix input cannot be empty).")

    rows: list[list[sp.Expr]] = []

    # Format 1: Bracketed rows [[1, 2], [3, 4]]
    if cleaned.startswith("[") and cleaned.endswith("]"):
        inner_rows = re.findall(r"\[([^\[\]]+)\]", cleaned)
        if inner_rows:
            for r in inner_rows:
                parts = [p.strip() for p in re.split(r"[, \t]+", r.strip()) if p.strip()]
                row_elements: list[sp.Expr] = []
                for p in parts:
                    try:
                        row_elements.append(sp.sympify(p))
                    except Exception as exc:
                        raise InvalidInputError(f"Phần tử ma trận không hợp lệ '{p}': {exc}") from exc
                rows.append(row_elements)

    # Format 2: Semicolon or newline delimited
    if not rows:
        raw_rows = [r.strip() for r in re.split(r"[;\n]+", cleaned) if r.strip()]
        for r in raw_rows:
            parts = [p.strip() for p in re.split(r"[, \t]+", r.strip("[] \t")) if p.strip()]
            row_elements = []
            for p in parts:
                try:
                    row_elements.append(sp.sympify(p))
                except Exception as exc:
                    raise InvalidInputError(f"Phần tử ma trận không hợp lệ '{p}': {exc}") from exc
            if row_elements:
                rows.append(row_elements)

    if not rows:
        raise InvalidInputError("Không tìm thấy hàng nào trong dữ liệu ma trận (No matrix rows detected).")

    col_count = len(rows[0])
    if col_count == 0:
        raise InvalidInputError("Hàng ma trận không được rỗng (Matrix row cannot be empty).")

    for idx, r in enumerate(rows):
        if len(r) != col_count:
            raise InvalidInputError(
                f"Kích thước ma trận không đồng nhất: Hàng 1 có {col_count} cột nhưng hàng {idx + 1} có {len(r)} cột "
                "(Mismatched matrix row dimensions)."
            )

    return sp.Matrix(rows)
