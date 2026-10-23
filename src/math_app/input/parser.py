"""Mathematical input normalization and safe SymPy parsing via restricted AST."""

from __future__ import annotations

import ast
import re
from typing import Iterable
import sympy as sp

from math_app.domain.exceptions import InvalidInputError
from math_app.input.validator import (
    ALLOWED_COMMON_VARIABLES,
    ALLOWED_CONSTANTS,
    ALLOWED_FUNCTIONS,
    MAX_EXPONENT_VALUE,
    validate_expression_syntax,
)


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


class SafeASTToSymPy(ast.NodeVisitor):
    """Safely converts a validated AST tree into a SymPy expression."""

    def __init__(self, allowed_names: set[str] | frozenset[str], evaluate: bool = False) -> None:
        self.allowed_names = set(allowed_names)
        self.evaluate = evaluate

    def visit_Expression(self, node: ast.Expression) -> sp.Expr:
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> sp.Expr:
        if type(node.value) is bool:
            raise InvalidInputError("Giá trị boolean không được hỗ trợ trong biểu thức toán học (Booleans are not supported).")
        if isinstance(node.value, int):
            return sp.Integer(node.value)
        elif isinstance(node.value, float):
            return sp.Float(node.value)
        raise InvalidInputError(f"Giá trị hằng số '{node.value}' không được hỗ trợ (Disallowed constant value).")

    def visit_Name(self, node: ast.Name) -> sp.Expr:
        name = node.id
        if name in ("pi", "PI"):
            return sp.pi
        if name in ("e", "E"):
            return sp.E
        if name in ("oo", "inf", "infinity"):
            return sp.oo
        clean = normalize_variable_name(name)
        if clean in self.allowed_names or name in self.allowed_names:
            return sp.Symbol(clean)
        raise InvalidInputError(
            f"Ký hiệu không xác định '{name}' (Unknown identifier). Ký hiệu cho phép: {sorted(self.allowed_names)}."
        )

    def visit_UnaryOp(self, node: ast.UnaryOp) -> sp.Expr:
        operand = self.visit(node.operand)
        if isinstance(node.op, ast.UAdd):
            return +operand
        elif isinstance(node.op, ast.USub):
            return -operand if self.evaluate else sp.Mul(-1, operand, evaluate=False)
        raise InvalidInputError(f"Toán tử một ngôi '{type(node.op).__name__}' không được hỗ trợ (Disallowed unary operator).")

    def visit_BinOp(self, node: ast.BinOp) -> sp.Expr:
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = node.op

        if isinstance(op, ast.Add):
            if self.evaluate:
                return left + right
            left_args = left.args if isinstance(left, sp.Add) else (left,)
            right_args = right.args if isinstance(right, sp.Add) else (right,)
            return sp.Add(*left_args, *right_args, evaluate=False)
        elif isinstance(op, ast.Sub):
            if self.evaluate:
                return left - right
            left_args = left.args if isinstance(left, sp.Add) else (left,)
            neg_right = sp.Mul(-1, right, evaluate=False)
            return sp.Add(*left_args, neg_right, evaluate=False)
        elif isinstance(op, ast.Mult):
            if self.evaluate:
                return left * right
            left_args = left.args if isinstance(left, sp.Mul) else (left,)
            right_args = right.args if isinstance(right, sp.Mul) else (right,)
            return sp.Mul(*left_args, *right_args, evaluate=False)
        elif isinstance(op, ast.Div):
            if right == 0:
                raise InvalidInputError("Phép chia cho 0 không xác định (Division by zero).")
            if self.evaluate:
                return left / right
            left_args = left.args if isinstance(left, sp.Mul) else (left,)
            return sp.Mul(*left_args, sp.Pow(right, -1, evaluate=False), evaluate=False)
        elif isinstance(op, ast.Pow):
            if isinstance(node.right, ast.Constant) and isinstance(node.right.value, (int, float)):
                if abs(node.right.value) > MAX_EXPONENT_VALUE:
                    raise InvalidInputError(
                        f"Số mũ {node.right.value} vượt quá giới hạn an toàn tối đa (exceeds maximum allowed value): {MAX_EXPONENT_VALUE}."
                    )
            return (left ** right) if self.evaluate else sp.Pow(left, right, evaluate=False)
        raise InvalidInputError(f"Toán tử '{type(op).__name__}' không được hỗ trợ (Disallowed binary operator).")

    def visit_Call(self, node: ast.Call) -> sp.Expr:
        if not isinstance(node.func, ast.Name):
            raise InvalidInputError("Chỉ cho phép gọi hàm trực tiếp (Only direct function calls are permitted).")
        func_name = node.func.id
        if func_name not in ALLOWED_FUNCTIONS:
            raise InvalidInputError(
                f"Hàm không xác định '{func_name}' (Unknown identifier). Các hàm hỗ trợ: {sorted(ALLOWED_FUNCTIONS)}."
            )
        if len(node.args) != 1:
            raise InvalidInputError(f"Hàm '{func_name}' yêu cầu đúng 1 đối số (Function expects 1 argument).")
        if node.keywords:
            raise InvalidInputError("Không hỗ trợ đối số từ khóa trong biểu thức toán học (Keyword arguments are not allowed).")

        arg = self.visit(node.args[0])
        func_map = {
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
            "ln": sp.log,
            "sqrt": sp.sqrt,
        }
        f = func_map[func_name]
        return f(arg) if self.evaluate else f(arg, evaluate=False)

    def generic_visit(self, node: ast.AST) -> sp.Expr:
        raise InvalidInputError(
            f"Cấu trúc ngôn ngữ không được phép: '{type(node).__name__}' (Disallowed language construct)."
        )


def parse_safe_expression(
    raw_input: str,
    target_variable: str = "x",
    allowed_variables: set[str] | frozenset[str] | Iterable[str] | None = None,
    evaluate: bool = False,
) -> sp.Expr:
    """Safely validate and parse a mathematical string into a SymPy expression via AST.

    Bypasses sympy.sympify and eval entirely to guarantee runtime safety.
    """
    cleaned = raw_input.strip()
    if not cleaned:
        raise InvalidInputError("Biểu thức không được để trống (cannot be empty).")

    clean_var = normalize_variable_name(target_variable) if target_variable else "x"
    normalized = normalize_expression_string(cleaned, clean_var)

    extra_vars = set(allowed_variables) if allowed_variables else set()
    validate_expression_syntax(normalized, clean_var, allowed_variables=extra_vars)

    allowed_names = {clean_var} | ALLOWED_CONSTANTS | ALLOWED_FUNCTIONS | ALLOWED_COMMON_VARIABLES | extra_vars

    try:
        tree = ast.parse(normalized, mode="eval")
        visitor = SafeASTToSymPy(allowed_names, evaluate=evaluate)
        return visitor.visit(tree)
    except InvalidInputError:
        raise
    except Exception as exc:
        raise InvalidInputError(f"Không thể phân tích biểu thức toán học (Failed to parse mathematical expression): {exc}") from exc


def parse_mathematical_input(
    raw_input: str,
    target_variable: str = "x",
    allowed_variables: set[str] | frozenset[str] | Iterable[str] | None = None,
) -> tuple[sp.Expr, sp.Symbol]:
    """Safely validate and parse user input string into a SymPy expression.

    Returns:
        tuple[sp.Expr, sp.Symbol]: Parsed expression and target variable symbol.

    Raises:
        InvalidInputError: If expression fails validation or cannot be safely parsed.
    """
    clean_var = normalize_variable_name(target_variable) if target_variable else "x"
    var_symbol = sp.Symbol(clean_var)
    expr = parse_safe_expression(
        raw_input,
        target_variable=clean_var,
        allowed_variables=allowed_variables,
        evaluate=False,
    )
    return expr, var_symbol


def _split_matrix_row_elements(row_str: str) -> list[str]:
    """Split row string into element strings respecting parentheses."""
    cleaned = row_str.strip()
    if not cleaned:
        return []

    p_depth = 0
    has_comma = False
    for c in cleaned:
        if c == "(":
            p_depth += 1
        elif c == ")":
            p_depth -= 1
        elif c == "," and p_depth == 0:
            has_comma = True

    if p_depth != 0:
        raise InvalidInputError("Dấu ngoặc đơn không khớp trong phần tử hàng ma trận (Unmatched parentheses in row).")

    parts: list[str] = []
    if has_comma:
        curr: list[str] = []
        p_depth = 0
        for c in cleaned:
            if c == "(":
                p_depth += 1
                curr.append(c)
            elif c == ")":
                p_depth -= 1
                curr.append(c)
            elif c == "," and p_depth == 0:
                parts.append("".join(curr).strip())
                curr = []
            else:
                curr.append(c)
        if curr:
            parts.append("".join(curr).strip())
    else:
        parts = [p.strip() for p in re.split(r"[\s\t]+", cleaned) if p.strip()]

    return [p for p in parts if p]


def parse_matrix_input(
    raw_input: str,
    allowed_variables: set[str] | frozenset[str] | Iterable[str] | None = None,
) -> sp.Matrix:
    """Parse a user matrix input string into a SymPy Matrix safely via AST.

    Every entry is validated against strict mathematical grammar and converted
    without passing raw user strings to sympy.sympify().

    Supports formats:
    - Nested brackets: [[1, 2], [3, 4]]
    - Vector brackets: [1, 2]
    - Semicolon rows: 1, 2; 3, 4
    - Newline rows: 1 2 \\n 3 4

    Raises:
        InvalidInputError: If input is empty, has ragged rows, or cannot be safely parsed.
    """
    cleaned = raw_input.strip()
    if not cleaned:
        raise InvalidInputError("Dữ liệu ma trận không được để trống (Matrix input cannot be empty).")

    # Check bracket balance and max depth
    max_depth = 0
    curr_depth = 0
    for c in cleaned:
        if c == "[":
            curr_depth += 1
            max_depth = max(max_depth, curr_depth)
        elif c == "]":
            curr_depth -= 1
            if curr_depth < 0:
                raise InvalidInputError("Dấu ngoặc đóng không khớp trong ma trận (Unmatched closing bracket).")
    if curr_depth != 0:
        raise InvalidInputError("Dấu ngoặc trong ma trận chưa đóng đúng (Unmatched opening bracket).")
    if max_depth > 2:
        raise InvalidInputError("Ma trận chỉ hỗ trợ tối đa 2 chiều (Matrix nesting exceeds 2 levels).")

    raw_row_strings: list[str] = []

    if max_depth == 2:
        curr_row: list[str] = []
        curr_depth = 0
        for c in cleaned:
            if c == "[":
                curr_depth += 1
                if curr_depth == 2:
                    curr_row = []
            elif c == "]":
                if curr_depth == 2:
                    row_content = "".join(curr_row).strip()
                    if not row_content:
                        raise InvalidInputError("Hàng ma trận không được rỗng (Matrix row cannot be empty).")
                    raw_row_strings.append(row_content)
                curr_depth -= 1
            else:
                if curr_depth == 2:
                    curr_row.append(c)
                elif curr_depth == 1:
                    if c not in " \t\r\n,;":
                        raise InvalidInputError(f"Ký tự không hợp lệ bên ngoài hàng ma trận: '{c}' (Unexpected token outside row).")

    elif max_depth == 1:
        if not (cleaned.startswith("[") and cleaned.endswith("]")):
            raise InvalidInputError("Định dạng ma trận có dấu ngoặc không hợp lệ (Malformed bracket format).")
        inner = cleaned[1:-1].strip()
        if not inner:
            raise InvalidInputError("Hàng ma trận không được rỗng (Matrix row cannot be empty).")
        if ";" in inner or "\n" in inner:
            raw_row_strings = [r.strip() for r in re.split(r"[;\n]+", inner) if r.strip()]
        else:
            raw_row_strings = [inner]

    else:
        # max_depth == 0: semicolon or newline delimited
        raw_row_strings = [r.strip() for r in re.split(r"[;\n]+", cleaned) if r.strip()]

    if not raw_row_strings:
        raise InvalidInputError("Không tìm thấy hàng nào trong dữ liệu ma trận (No matrix rows detected).")

    rows: list[list[sp.Expr]] = []
    matrix_allowed_vars = (
        (ALLOWED_COMMON_VARIABLES | set(allowed_variables))
        if allowed_variables
        else ALLOWED_COMMON_VARIABLES
    )

    for row_str in raw_row_strings:
        elem_parts = _split_matrix_row_elements(row_str)
        if not elem_parts:
            raise InvalidInputError("Hàng ma trận không được rỗng (Matrix row cannot be empty).")

        row_elements: list[sp.Expr] = []
        for part in elem_parts:
            try:
                expr = parse_safe_expression(
                    part,
                    target_variable="x",
                    allowed_variables=matrix_allowed_vars,
                    evaluate=True,
                )
                row_elements.append(expr)
            except Exception as exc:
                raise InvalidInputError(f"Phần tử ma trận không hợp lệ '{part}': {exc}") from exc
        rows.append(row_elements)

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
