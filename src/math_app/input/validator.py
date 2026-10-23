"""Input validator using AST inspection against strict whitelists and complexity bounds."""

from __future__ import annotations

import ast

from math_app.domain.exceptions import InvalidInputError

MAX_EXPRESSION_LENGTH = 200
MAX_AST_DEPTH = 12
MAX_EXPONENT_VALUE = 50.0

ALLOWED_FUNCTIONS = frozenset({
    "sin", "cos", "tan", "sec", "csc", "cot",
    "asin", "acos", "atan",
    "exp", "log", "ln", "sqrt",
})
ALLOWED_CONSTANTS = frozenset({"e", "pi", "E", "PI"})
ALLOWED_COMMON_VARIABLES = frozenset({"x", "y", "z", "t", "u", "v", "r", "rho", "ρ", "theta", "phi", "θ", "φ"})


def get_ast_depth(node: ast.AST) -> int:
    """Recursively calculate the maximum depth of an AST tree."""
    if not list(ast.iter_child_nodes(node)):
        return 1
    return 1 + max(get_ast_depth(child) for child in ast.iter_child_nodes(node))


def validate_expression_syntax(raw_expression: str, target_variable: str = "x") -> None:
    """Validate mathematical expression against grammar, whitelist, and complexity limits.

    Raises:
        InvalidInputError: If expression is empty, malformed, too deep, or contains
                           disallowed tokens/nodes.
    """
    cleaned = raw_expression.strip()
    if not cleaned:
        raise InvalidInputError("Biểu thức không được để trống (cannot be empty).")

    if len(cleaned) > MAX_EXPRESSION_LENGTH:
        raise InvalidInputError(
            f"Biểu thức vượt quá độ dài tối đa cho phép (maximum allowable length): {MAX_EXPRESSION_LENGTH} ký tự."
        )

    # Basic bracket balance check before AST
    bracket_pairs = {"(": ")", "[": "]", "{": "}"}
    stack: list[str] = []
    for char in cleaned:
        if char in bracket_pairs:
            stack.append(bracket_pairs[char])
        elif char in bracket_pairs.values():
            if not stack or stack.pop() != char:
                raise InvalidInputError("Dấu ngoặc trong biểu thức không khớp hoặc chưa đóng đúng (brackets).")
    if stack:
        raise InvalidInputError("Dấu ngoặc trong biểu thức không khớp hoặc chưa đóng đúng (brackets).")

    try:
        tree = ast.parse(cleaned, mode="eval")
    except SyntaxError as exc:
        raise InvalidInputError(f"Lỗi cú pháp trong biểu thức (Syntax error): {exc.msg}") from exc

    depth = get_ast_depth(tree)
    if depth > MAX_AST_DEPTH:
        raise InvalidInputError(
            f"Độ phức tạp của biểu thức vượt quá giới hạn cho phép (maximum allowable depth): {MAX_AST_DEPTH} cấp."
        )

    allowed_names = {target_variable} | ALLOWED_CONSTANTS | ALLOWED_FUNCTIONS | ALLOWED_COMMON_VARIABLES

    for node in ast.walk(tree):
        if isinstance(node, ast.Expression):
            continue
        elif isinstance(node, ast.BinOp):
            if not isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)):
                raise InvalidInputError(f"Toán tử '{type(node.op).__name__}' không được hỗ trợ (Disallowed binary operator).")
            # If power operation, ensure constant exponent does not exceed limit
            if isinstance(node.op, ast.Pow) and isinstance(node.right, ast.Constant):
                if isinstance(node.right.value, (int, float)) and abs(node.right.value) > MAX_EXPONENT_VALUE:
                    raise InvalidInputError(
                        f"Số mũ {node.right.value} vượt quá giới hạn an toàn tối đa (exceeds maximum allowed value): {MAX_EXPONENT_VALUE}."
                    )
        elif isinstance(node, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)):
            continue
        elif isinstance(node, ast.UnaryOp):
            if not isinstance(node.op, (ast.UAdd, ast.USub)):
                raise InvalidInputError(f"Toán tử một ngôi '{type(node.op).__name__}' không được hỗ trợ (Disallowed unary operator).")
        elif isinstance(node, (ast.UAdd, ast.USub)):
            continue
        elif isinstance(node, ast.Load):
            continue
        elif isinstance(node, ast.Constant):
            if not isinstance(node.value, (int, float)):
                raise InvalidInputError(f"Giá trị hằng số '{node.value}' không được hỗ trợ (Disallowed constant value).")
        elif isinstance(node, ast.Name):
            if node.id not in allowed_names:
                raise InvalidInputError(
                    f"Ký hiệu không xác định '{node.id}' (Unknown identifier). Biến cho phép: '{target_variable}' "
                    f"và các hàm: {sorted(ALLOWED_FUNCTIONS)}."
                )
        elif isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise InvalidInputError("Chỉ cho phép gọi hàm trực tiếp (Only direct function calls are permitted).")
            if node.func.id not in ALLOWED_FUNCTIONS:
                raise InvalidInputError(
                    f"Hàm không xác định '{node.func.id}' (Unknown identifier). Các hàm hỗ trợ: {sorted(ALLOWED_FUNCTIONS)}."
                )
            if len(node.args) != 1:
                raise InvalidInputError(f"Hàm '{node.func.id}' yêu cầu đúng 1 đối số (Function expects 1 argument).")
            if node.keywords:
                raise InvalidInputError("Không hỗ trợ đối số từ khóa trong biểu thức toán học (Keyword arguments are not allowed).")
        else:
            raise InvalidInputError(f"Cấu trúc ngôn ngữ không được phép: '{type(node).__name__}' (Disallowed language construct).")
