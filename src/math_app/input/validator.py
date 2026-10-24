"""Input validator using AST inspection against strict whitelists and complexity bounds."""

from __future__ import annotations

import ast
import math

from math_app.domain.exceptions import InvalidInputError

MAX_EXPRESSION_LENGTH = 200
MAX_AST_DEPTH = 12
MAX_AST_NODES = 100
MAX_EXPONENT_VALUE = 50.0
MAX_CONSTANT_VALUE = 10_000_000.0  # 10^7
MAX_CONSTANT_LOG_POWER = 7.0  # log10(base^exp) > 7 means > 10,000,000

ALLOWED_FUNCTIONS = frozenset({
    "sin", "cos", "tan", "sec", "csc", "cot",
    "asin", "acos", "atan",
    "exp", "log", "ln", "sqrt",
})
ALLOWED_CONSTANTS = frozenset({"e", "pi", "E", "PI", "oo", "inf", "infinity"})
ALLOWED_COMMON_VARIABLES = frozenset({"x", "y", "z", "t", "u", "v", "r", "s", "w", "rho", "ρ", "theta", "phi", "θ", "φ"})


def get_ast_depth(node: ast.AST) -> int:
    """Recursively calculate the maximum depth of an AST tree."""
    if not list(ast.iter_child_nodes(node)):
        return 1
    return 1 + max(get_ast_depth(child) for child in ast.iter_child_nodes(node))


def evaluate_constant_exponent(node: ast.AST) -> float | None:
    """Safely evaluate constant arithmetic in exponent without computing dangerous powers.

    Returns float value if node is purely constant arithmetic (+, -, *, /), or None if symbolic.
    Raises InvalidInputError if division by zero or disallowed operation is detected.
    """
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)) and type(node.value) is not bool:
            return float(node.value)
        raise InvalidInputError(f"Giá trị hằng số '{node.value}' không được hỗ trợ trong số mũ (Disallowed constant in exponent).")
    elif isinstance(node, ast.UnaryOp):
        val = evaluate_constant_exponent(node.operand)
        if val is None:
            return None
        if isinstance(node.op, ast.UAdd):
            return +val
        elif isinstance(node.op, ast.USub):
            return -val
        raise InvalidInputError(f"Toán tử một ngôi '{type(node.op).__name__}' không được hỗ trợ trong số mũ.")
    elif isinstance(node, ast.BinOp):
        if isinstance(node.op, ast.Pow):
            raise InvalidInputError(
                "Số mũ không được chứa phép toán lũy thừa lồng nhau (Nested exponents/powers in exponent are not allowed)."
            )
        left_val = evaluate_constant_exponent(node.left)
        right_val = evaluate_constant_exponent(node.right)
        if left_val is None or right_val is None:
            return None
        if isinstance(node.op, ast.Add):
            return left_val + right_val
        elif isinstance(node.op, ast.Sub):
            return left_val - right_val
        elif isinstance(node.op, ast.Mult):
            return left_val * right_val
        elif isinstance(node.op, ast.Div):
            if abs(right_val) < 1e-12:
                raise InvalidInputError("Phép chia cho 0 trong số mũ không xác định (Division by zero in exponent).")
            return left_val / right_val
        raise InvalidInputError(f"Toán tử '{type(node.op).__name__}' không được hỗ trợ trong số mũ.")
    elif isinstance(node, ast.Name):
        return None
    elif isinstance(node, ast.Call):
        return None
    else:
        raise InvalidInputError(f"Cấu trúc không hợp lệ trong số mũ: '{type(node).__name__}'.")


def validate_expression_syntax(
    raw_expression: str,
    target_variable: str = "x",
    allowed_variables: set[str] | frozenset[str] | None = None,
) -> None:
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

    node_count = sum(1 for _ in ast.walk(tree))
    if node_count > MAX_AST_NODES:
        raise InvalidInputError(
            f"Số lượng toán tử/nút trong biểu thức ({node_count}) vượt quá giới hạn cho phép: {MAX_AST_NODES}."
        )

    allowed_names = {target_variable} | ALLOWED_CONSTANTS | ALLOWED_FUNCTIONS | ALLOWED_COMMON_VARIABLES
    if allowed_variables:
        allowed_names = allowed_names | set(allowed_variables)

    for node in ast.walk(tree):
        if isinstance(node, ast.Expression):
            continue
        elif isinstance(node, ast.BinOp):
            if not isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)):
                raise InvalidInputError(f"Toán tử '{type(node.op).__name__}' không được hỗ trợ (Disallowed binary operator).")
            # If power operation, restrict exponent complexity and value
            if isinstance(node.op, ast.Pow):
                # 1. Disallow nested powers inside exponent
                if any(isinstance(n, ast.Pow) for n in ast.walk(node.right)):
                    raise InvalidInputError(
                        "Số mũ không được chứa phép toán lũy thừa lồng nhau (Nested exponents/powers in exponent are not allowed)."
                    )
                # 2. Evaluate constant exponent if purely arithmetic
                exp_val = evaluate_constant_exponent(node.right)
                if exp_val is not None:
                    if abs(exp_val) > MAX_EXPONENT_VALUE:
                        raise InvalidInputError(
                            f"Số mũ {exp_val} vượt quá giới hạn an toàn tối đa (exceeds maximum allowed value): {MAX_EXPONENT_VALUE}."
                        )
                    # 3. Guard against huge constant powers (e.g. 9^9, 10^8)
                    if isinstance(node.left, ast.Constant) and isinstance(node.left.value, (int, float)) and type(node.left.value) is not bool:
                        base_val = abs(float(node.left.value))
                        if base_val > 1.0 and exp_val > 0:
                            log_size = exp_val * math.log10(base_val)
                            if log_size > MAX_CONSTANT_LOG_POWER:
                                raise InvalidInputError(
                                    f"Giá trị lũy thừa hằng số {node.left.value}^{exp_val} vượt quá giới hạn an toàn tối đa (Constant power exceeds safe limit)."
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
            if type(node.value) is bool or not isinstance(node.value, (int, float)):
                raise InvalidInputError(f"Giá trị hằng số '{node.value}' không được hỗ trợ (Disallowed constant value).")
            if abs(node.value) > MAX_CONSTANT_VALUE:
                raise InvalidInputError(
                    f"Giá trị hằng số {node.value} vượt quá giới hạn an toàn tối đa (Constant exceeds maximum allowed value): {MAX_CONSTANT_VALUE}."
                )
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
