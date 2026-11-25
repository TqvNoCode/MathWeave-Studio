"""Shared pedagogical text and mathematical expression renderer with MathML and KaTeX support."""

from __future__ import annotations

import html
import re
import latex2mathml.converter

from math_app.rendering.latex.formatter import normalize_latex

MATH_DELIMITER_REGEX = re.compile(
    r"(\$\$.*?\$\$|\\\[.*?\\\]|\$.*?\$|\\\(.*?\\\))",
    re.DOTALL,
)


def is_pure_latex_math(s: str) -> bool:
    """Check if a string represents a pure LaTeX mathematical expression rather than mixed prose."""
    cleaned = s.strip()
    if not cleaned:
        return False
    if cleaned.startswith("$") and cleaned.endswith("$"):
        cleaned = cleaned[1:-1].strip()
    # If contains Vietnamese diacritics, it is natural language text
    if re.search(r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđĐ]", cleaned, re.IGNORECASE):
        return False
    # If contains natural words of 3+ letters not preceded by a backslash
    words = re.findall(r"(?<!\\)\b[a-zA-Z]{3,}\b", cleaned)
    allowed_math_identifiers = {
        "sin", "cos", "tan", "cot", "exp", "log", "ln", "det", "lim", "inf",
        "max", "min", "sec", "csc", "arcsin", "arccos", "arctan", "sinh", "cosh", "tanh"
    }
    unrecognized = [w for w in words if w.lower() not in allowed_math_identifiers]
    return len(unrecognized) == 0


def convert_latex_to_mathml(latex_str: str, block: bool = False, is_icon: bool = False) -> str:
    """Convert LaTeX string to styled MathML HTML snippet with KaTeX data attributes."""
    cleaned = latex_str.strip()
    if not cleaned:
        return ""

    normalized = normalize_latex(cleaned)
    escaped_tex = html.escape(normalized)
    display_mode = "block" if block else "inline"

    if is_icon:
        cls = "math-icon math-container math-tex select-none pointer-events-none"
    else:
        cls = "math-block math-tex my-1" if block else "math-inline math-tex"

    tag = "div" if block else "span"

    try:
        mathml = latex2mathml.converter.convert(normalized, display="block" if block else "inline")
        # Ensure rendered MathML does not contain injected script tags or event handlers
        if re.search(r"<(?:script|iframe|object|embed|style)", mathml, re.IGNORECASE) or re.search(r"\bon\w+\s*=", mathml, re.IGNORECASE):
            raise ValueError("Unsafe HTML tags or event handlers detected in MathML output.")
        return f'<{tag} class="{cls}" data-tex="{escaped_tex}" data-display="{display_mode}">{mathml}</{tag}>'
    except Exception:
        # Fallback to styled mathematical font span with explicit HTML escaping and data-tex for KaTeX
        safe_fallback = html.escape(normalized)
        fallback_cls = (
            f"{cls} math-fallback font-serif text-blue-900 tracking-wide select-none"
            if is_icon
            else f"{cls} math-fallback font-serif text-blue-900 tracking-wide"
        )
        return f'<{tag} class="{fallback_cls}" data-tex="{escaped_tex}" data-display="{display_mode}">{safe_fallback}</{tag}>'


def _apply_to_text_chunks(text: str, func) -> str:
    """Apply a string transformation only to non-mathematical text segments, preserving existing $...$."""
    tokens = MATH_DELIMITER_REGEX.split(text)
    out: list[str] = []
    for token in tokens:
        if not token:
            continue
        if MATH_DELIMITER_REGEX.match(token):
            out.append(token)
        else:
            out.append(func(token))
    return "".join(out)


def delimit_unwrapped_math_in_text(text: str) -> str:
    """Detect and safely wrap unwrapped mathematical expressions inside $...$ in natural language text.

    Preserves existing $...$, $$...$$, \\(...\\), and \\[...]\\ blocks unchanged.
    Converts raw tokens such as sqrt(x), quadratic Delta, linear algebra row operations,
    programmer exponents, and Cauchy initial conditions into canonical LaTeX math blocks.
    """
    if not text:
        return ""

    current = text

    # 1. Row operations in linear algebra e.g. R_{1} \leftrightarrow R_{2} or R_1 \leftarrow ...
    def step_row_ops(chunk: str) -> str:
        return re.sub(
            r"(?<!\$)(R_\{?\d+\}?\s*\\(?:leftrightarrow|leftarrow)\s*[^$,\n;]+)(?!\$)",
            r"$\1$",
            chunk,
        )

    current = _apply_to_text_chunks(current, step_row_ops)

    # 2. Delta expressions: (Delta > 0), (Delta < 0), (Delta = 0), Delta = b^2 - 4ac, Delta > 0, Delta
    def step_delta(chunk: str) -> str:
        def repl_delta(m: re.Match[str]) -> str:
            full = m.group(0)
            m_paren = re.match(r"^\(\s*(?:Delta|\\Delta)\s*([<>=!]+)\s*([^)]+)\)$", full)
            if m_paren:
                return f"$(\\Delta {m_paren.group(1)} {m_paren.group(2)})$"
            m_comp = re.match(r"^(?:Delta|\\Delta)\s*([<>=!]+)\s*([0-9a-zA-Z\.\-]+)$", full)
            if m_comp:
                return f"$\\Delta {m_comp.group(1)} {m_comp.group(2)}$"
            return r"$\Delta$"

        return re.sub(
            r"\(\s*(?:Delta|\\Delta)\s*[<>=!]+\s*[^)]+\)|"
            r"(?<!\$)\bDelta\s*[<>=!]+\s*[0-9a-zA-Z\.\-]+(?!\$)|"
            r"(?<!\$)\bDelta\b(?!\$)",
            repl_delta,
            chunk,
        )

    current = _apply_to_text_chunks(current, step_delta)

    # 3. exp(...) with radicals e.g. exp(sqrt(33)*t/2) or exp(r*t)
    def step_exp(chunk: str) -> str:
        def repl_exp(m: re.Match[str]) -> str:
            arg = m.group(1).strip()
            arg_ltx = re.sub(r"sqrt\(([^)]+)\)", r"\\sqrt{\1}", arg)
            m_frac = re.match(r"^(\\sqrt\{[^}]+\})\s*\*\s*([a-zA-Z])\s*/\s*(\d+)$", arg_ltx)
            if m_frac:
                arg_ltx = f"\\frac{{{m_frac.group(1)} {m_frac.group(2)}}}{{{m_frac.group(3)}}}"
            elif "*" in arg_ltx:
                arg_ltx = arg_ltx.replace("*", " ")
            return f"$e^{{{arg_ltx}}}$"

        return re.sub(r"\bexp\(((?:[^()]+|\([^()]*\))+)\)", repl_exp, chunk)

    current = _apply_to_text_chunks(current, step_exp)

    # 4. Equation with parenthesized fraction containing sqrt: r1 = (-1 + sqrt(33))/4
    def step_eq_paren_sqrt(chunk: str) -> str:
        def repl_eq_paren_sqrt(m: re.Match[str]) -> str:
            var = m.group(1)
            num = m.group(2).strip()
            den = m.group(3).strip()
            var_ltx = re.sub(r"([a-zA-Z])(\d+)", r"\1_{\2}", var)
            num_ltx = re.sub(r"sqrt\(([^)]+)\)", r"\\sqrt{\1}", num)
            return f"${var_ltx} = \\frac{{{num_ltx}}}{{{den}}}$"

        return re.sub(
            r"(?<!\$)\b([a-zA-Z]\d?)\s*=\s*\(\s*([+-]?\s*\d+\s*[+-]\s*sqrt\([^)]+\))\s*\)\s*/\s*(\d+)(?!\$)",
            repl_eq_paren_sqrt,
            chunk,
        )

    current = _apply_to_text_chunks(current, step_eq_paren_sqrt)

    # 5. Equation with radical: C1 = 2*sqrt(33)/33 or C2 = -2*sqrt(33)/33
    def step_eq_sqrt(chunk: str) -> str:
        def repl_eq_sqrt(m: re.Match[str]) -> str:
            var = m.group(1)
            val = m.group(2).strip()
            var_ltx = re.sub(r"([a-zA-Z])(\d+)", r"\1_{\2}", var)
            m2 = re.match(r"^([+-]?)\s*(\d*)\s*\*?\s*sqrt\(([^)]+)\)(?:\s*([*\/])\s*([a-zA-Z0-9]+))?$", val)
            if m2:
                sign, coeff, rad, op, extra = m2.groups()
                coeff_str = coeff if coeff else ""
                if op == "/":
                    num = f"{coeff_str}\\sqrt{{{rad}}}" if coeff_str else f"\\sqrt{{{rad}}}"
                    val_ltx = f"-\\frac{{{num}}}{{{extra}}}" if sign == "-" else f"\\frac{{{num}}}{{{extra}}}"
                elif op == "*":
                    num = f"{coeff_str}\\sqrt{{{rad}}}\\,{extra}" if coeff_str else f"\\sqrt{{{rad}}}\\,{extra}"
                    val_ltx = f"-{num}" if sign == "-" else num
                else:
                    num = f"{coeff_str}\\sqrt{{{rad}}}" if coeff_str else f"\\sqrt{{{rad}}}"
                    val_ltx = f"-{num}" if sign == "-" else num
            else:
                val_ltx = re.sub(r"sqrt\(([^)]+)\)", r"\\sqrt{\1}", val)
            return f"${var_ltx} = {val_ltx}$"

        return re.sub(
            r"(?<!\$)\b([a-zA-Z]\d?)\s*=\s*([+-]?\s*\d*\s*\*?\s*sqrt\([^)]+\)(?:\s*[\*\/]\s*[a-zA-Z0-9]+)?)(?!\$)",
            repl_eq_sqrt,
            chunk,
        )

    current = _apply_to_text_chunks(current, step_eq_sqrt)

    # 6. Standalone parenthesized fraction with sqrt: (-1 + sqrt(33))/4
    def step_paren_sqrt_frac(chunk: str) -> str:
        def repl_paren_sqrt_frac(m: re.Match[str]) -> str:
            num = m.group(1).strip()
            den = m.group(2).strip()
            num_ltx = re.sub(r"sqrt\(([^)]+)\)", r"\\sqrt{\1}", num)
            return f"$\\frac{{{num_ltx}}}{{{den}}}$"

        return re.sub(
            r"(?<!\$)\(\s*([+-]?\s*\d+\s*[+-]\s*sqrt\([^)]+\))\s*\)\s*/\s*(\d+)(?!\$)",
            repl_paren_sqrt_frac,
            chunk,
        )

    current = _apply_to_text_chunks(current, step_paren_sqrt_frac)

    # 7. Standalone radical expression: [+-]2*sqrt(33)/33 or sqrt(33)/2 or 2*sqrt(33) or sqrt(33)
    def step_sqrt_expr(chunk: str) -> str:
        def repl_sqrt_expr(m: re.Match[str]) -> str:
            matched = m.group(0)
            prefix_space = " " if matched.startswith(" ") else ""
            full = matched.strip()
            m2 = re.match(r"^([+-]?)\s*(\d*)\s*\*?\s*sqrt\(([^)]+)\)(?:\s*([*\/])\s*([a-zA-Z0-9]+))?$", full)
            if not m2:
                inner_ltx = re.sub(r"sqrt\(([^)]+)\)", r"\\sqrt{\1}", full)
                return f"{prefix_space}${inner_ltx}$"
            sign, coeff, rad, op, extra = m2.groups()
            coeff_str = coeff if coeff else ""
            if op == "/":
                num = f"{coeff_str}\\sqrt{{{rad}}}" if coeff_str else f"\\sqrt{{{rad}}}"
                if sign == "-":
                    return f"{prefix_space}$-\\frac{{{num}}}{{{extra}}}$"
                elif sign == "+":
                    return f"{prefix_space}$\\frac{{{num}}}{{{extra}}}$"
                return f"{prefix_space}$\\frac{{{num}}}{{{extra}}}$"
            elif op == "*":
                num = f"{coeff_str}\\sqrt{{{rad}}}\\,{extra}" if coeff_str else f"\\sqrt{{{rad}}}\\,{extra}"
                prefix = "-" if sign == "-" else ""
                return f"{prefix_space}${prefix}{num}$"
            else:
                num = f"{coeff_str}\\sqrt{{{rad}}}" if coeff_str else f"\\sqrt{{{rad}}}"
                prefix = "-" if sign == "-" else ""
                return f"{prefix_space}${prefix}{num}$"

        return re.sub(
            r"(?<![a-zA-Z0-9_\\])(?:[+-]?\s*\d*\s*\*?\s*sqrt\([^)]+\)(?:\s*[\*\/]\s*[a-zA-Z0-9]+)?)(?![a-zA-Z0-9_])",
            repl_sqrt_expr,
            chunk,
        )

    current = _apply_to_text_chunks(current, step_sqrt_expr)

    # 8. Linear combination C1*y1 + C2*y2
    def step_linear_comb(chunk: str) -> str:
        return re.sub(r"(?<!\$)\b(C1\*y1\s*[\+\-]\s*C2\*y2)\b(?!\$)", r"$\1$", chunk)

    current = _apply_to_text_chunks(current, step_linear_comb)

    # 9. Wronskian W(y1, y2)
    def step_wronskian(chunk: str) -> str:
        return re.sub(r"(?<!\$)\b(W\s*\(\s*y_?1\s*,\s*y_?2\s*\))(?!\$)", r"$\1$", chunk)

    current = _apply_to_text_chunks(current, step_wronskian)

    # 10. Cauchy initial conditions y(0) = 0 and y'(0) = 1
    def step_cauchy(chunk: str) -> str:
        c1 = re.sub(r"(?<!\$)\by\s*\(\s*(\d+)\s*\)\s*=\s*([0-9a-zA-Z\.\-]+)(?!\$)", r"$y(\1) = \2$", chunk)
        return re.sub(r"(?<!\$)\by'\s*\(\s*(\d+)\s*\)\s*=\s*([0-9a-zA-Z\.\-]+)(?!\$)", r"$y'(\1) = \2$", c1)

    current = _apply_to_text_chunks(current, step_cauchy)

    # 11. Programmer exponents x**2
    def step_exponents(chunk: str) -> str:
        return re.sub(r"(?<!\$)\b([a-zA-Z])\*\*(\d+)(?!\$)", r"$\1^\2$", chunk)

    current = _apply_to_text_chunks(current, step_exponents)

    # 12. Standard ODE general solution expressions: y(t) = y_c(t) + y_p(t)
    def step_ode_eq(chunk: str) -> str:
        return re.sub(
            r"(?<![a-zA-Z0-9_\$\\])(y\([a-zA-Z]\)\s*=\s*y_c\([a-zA-Z]\)\s*\+\s*y_p\([a-zA-Z]\))(?![a-zA-Z0-9_\$\\])",
            r"$\1$",
            chunk,
        )

    current = _apply_to_text_chunks(current, step_ode_eq)

    # 13. ODE residuals: R(t) = 0, R(t) \equiv 0, R(x) = 0
    def step_ode_res(chunk: str) -> str:
        return re.sub(
            r"(?<![a-zA-Z0-9_\$\\])(R\([a-zA-Z]\)\s*(?:\\equiv|=|==)\s*0)(?![a-zA-Z0-9_\$\\])",
            r"$\1$",
            chunk,
        )

    current = _apply_to_text_chunks(current, step_ode_res)

    # 14. Integrating factor mu(t) or \mu(t)
    def step_ode_mu(chunk: str) -> str:
        return re.sub(
            r"(?<![a-zA-Z0-9_\$\\])(\\mu\([a-zA-Z]\)|\bmu\([a-zA-Z]\))(?![a-zA-Z0-9_\$\\])",
            lambda m: f"${m.group(1).replace('mu(', r'\mu(')}$",
            chunk,
        )

    current = _apply_to_text_chunks(current, step_ode_mu)

    # 15. ODE solution functions: y_c(t), y_p(t), y_1(t), y_2(t), y(t)
    def step_ode_funcs(chunk: str) -> str:
        return re.sub(
            r"(?<![a-zA-Z0-9_\$\\])(y_[cp12]\([a-zA-Z]\)|y\([a-zA-Z]\))(?![a-zA-Z0-9_\$\\])",
            r"$\1$",
            chunk,
        )

    current = _apply_to_text_chunks(current, step_ode_funcs)

    # 16. ODE constants, trial coefficients, and fundamental solutions: C_1, C_2 or A_0, B_0 or y_1, y_2
    def step_ode_consts(chunk: str) -> str:
        def _repl_pairs(m: re.Match[str]) -> str:
            txt = m.group(1)
            txt = re.sub(r"\b([CABy])([012cp])\b", r"\1_\2", txt)
            return f"${txt}$"

        c = re.sub(
            r"(?<![a-zA-Z0-9_\$\\])([CABy]_?[012cp]\s*,\s*[CABy]_?[012cp])(?![a-zA-Z0-9_\$\\])",
            _repl_pairs,
            chunk,
        )

        def _repl_single(m: re.Match[str]) -> str:
            txt = m.group(1)
            txt = re.sub(r"^([CABy])([012cp])$", r"\1_\2", txt)
            return f"${txt}$"

        c = re.sub(
            r"(?<![a-zA-Z0-9_\$\\])(C_[12]|C[12]|A_[01]|A[01]|B_[01]|B[01]|y_1|y_2|y1|y2|y_c|y_p|yc|yp)(?![a-zA-Z0-9_\$\\])",
            _repl_single,
            c,
        )
        return c

    current = _apply_to_text_chunks(current, step_ode_consts)

    # 17. Unwrapped equivalence and implication expressions
    def step_ode_equiv_implies(chunk: str) -> str:
        # e.g. R(t) \equiv 0, y_p(t) \equiv 0, A \equiv B
        c = re.sub(
            r"(?<![a-zA-Z0-9_\$\\])([a-zA-Z0-9_\(\)]+\s*\\equiv\s*[a-zA-Z0-9_\(\)]+)(?![a-zA-Z0-9_\$\\])",
            r"$\1$",
            chunk,
        )
        # Standalone \equiv or \implies
        return re.sub(
            r"(?<![a-zA-Z0-9_\$\\])(\\equiv|\\implies)(?![a-zA-Z0-9_\$\\])",
            r"$\1$",
            c,
        )

    current = _apply_to_text_chunks(current, step_ode_equiv_implies)

    # 18. Unwrapped LaTeX math expressions (e.g. \cos{\left(x \right)}, -\tan{\left(x \right)}, \partial, \mu \cdot y', etc.)
    def step_unwrapped_latex(chunk: str) -> str:
        pattern = re.compile(
            r"(?<![a-zA-Z0-9\$\\])("
            r"(?:[+-]\s*)?"
            r"\\[a-zA-Z]+"
            r"(?:"
                r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}|"
                r"\[[^\[\]]*\]|"
                r"\([^()]*\)|"
                r"\^[a-zA-Z0-9{}]|_\{?[a-zA-Z0-9]+\}?|"
                r"\s*(?:[\+\-\*\/=<>~]|\\cdot|\\implies|\\equiv|\\neq|\\le|\\ge)\s*|"
                r"\s*\\[a-zA-Z]+|"
                r"\s+[0-9a-zA-Z]+(?:\\?'|')*|"
                r"\b[0-9a-zA-Z]+(?:\\?'|')*"
            r")*"
            r")(?![a-zA-Z0-9\$\\])"
        )

        def repl_unwrapped(m: re.Match[str]) -> str:
            val = m.group(1).rstrip()
            trailing_punct = ""
            while val and val[-1] in ",.;:!?":
                trailing_punct = val[-1] + trailing_punct
                val = val[:-1].rstrip()
            if not val:
                return trailing_punct
            return f"${val}${trailing_punct}"

        subbed = pattern.sub(repl_unwrapped, chunk)
        return re.sub(r"\$(\s*)(.*?)\s*\$", r"\1$\2$", subbed)

    current = _apply_to_text_chunks(current, step_unwrapped_latex)

    return current


def render_math_in_text_html(text: str) -> str:
    """Render explanatory prose containing inline or block mathematical expressions into safe HTML with MathML.

    - Plaintext segments are strictly HTML-escaped.
    - Mathematical segments ($...$, $$...$$, \\(...\\), \\[...]\\) are converted to MathML with KaTeX attributes.
    - Eliminates orphan punctuation marks appearing on their own lines.
    - Preserves inline and trailing punctuation marks adjacent to mathematical formulas.
    - Markdown bold (**...**) and italic (*...*) cleanly wrap around text and math without leaking asterisks.
    - Mathematical expressions containing * or _ are strictly protected from markdown parsing.
    - Newlines in prose are preserved with <br/>.
    - Complete output is verified against unsafe HTML payloads (XSS).
    """
    if not text:
        return ""

    # Delimit any unwrapped math
    clean_text = delimit_unwrapped_math_in_text(text)

    # Sanitize orphan punctuation marks on independent lines before processing
    clean_text = re.sub(r"\$\$\s*\.+", "$$", clean_text)
    clean_text = re.sub(r"(?m)^\s*[\.,;:]\s*$", "", clean_text)
    clean_text = re.sub(r"\n\s*[\.,;:]\s*(?=\n|$)", "\n", clean_text)

    # Protect math tokens by extracting them into placeholders
    math_placeholders: list[str] = []

    def repl_math(m: re.Match[str]) -> str:
        token = m.group(0)
        if token.startswith("$$") and token.endswith("$$"):
            code = token[2:-2]
            rendered = convert_latex_to_mathml(code, block=True)
        elif token.startswith(r"\[") and token.endswith(r"\]"):
            code = token[2:-2]
            rendered = convert_latex_to_mathml(code, block=True)
        elif token.startswith("$") and token.endswith("$"):
            code = token[1:-1]
            rendered = convert_latex_to_mathml(code, block=False)
        elif token.startswith(r"\(") and token.endswith(r"\)"):
            code = token[2:-2]
            rendered = convert_latex_to_mathml(code, block=False)
        else:
            return token

        idx = len(math_placeholders)
        math_placeholders.append(rendered)
        return f"\x00MATH_{idx}\x00"

    prose_with_placeholders = MATH_DELIMITER_REGEX.sub(repl_math, clean_text)

    # Plain text: safely escape HTML entities
    escaped_prose = html.escape(prose_with_placeholders)

    # Render markdown bold (**text**) and italic (*text*) into safe HTML elements
    # Since math was replaced with \x00MATH_idx\x00, asterisks in math expressions are completely protected!
    # And bold/italic formatting across math formulas works seamlessly without leaking asterisks.
    escaped_prose = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped_prose)
    escaped_prose = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", escaped_prose)

    # Preserve line breaks
    escaped_prose = escaped_prose.replace("\n", "<br/>")

    # Clean up orphan dots strictly isolated by line breaks
    escaped_prose = re.sub(r"<br/>\s*[\.,;:]\s*<br/>", "<br/>", escaped_prose)

    # Restore pre-rendered MathML/KaTeX snippets
    def restore_math(m: re.Match[str]) -> str:
        idx = int(m.group(1))
        if 0 <= idx < len(math_placeholders):
            return math_placeholders[idx]
        return m.group(0)

    full_html = re.sub(r"\x00MATH_(\d+)\x00", restore_math, escaped_prose)

    # Secondary XSS safeguard: strip or reject dangerous HTML elements
    if re.search(r"<(?:script|iframe|object|embed|style)", full_html, re.IGNORECASE) or re.search(r"\bon\w+\s*=", full_html, re.IGNORECASE):
        # Fall back to entirely escaped text if an injection attempt is detected
        return html.escape(text).replace("\n", "<br/>")

    return full_html
