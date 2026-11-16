"""Unit tests for shared mathematical and text rendering architecture."""

from math_app.rendering.text_math_renderer import (
    delimit_unwrapped_math_in_text,
    render_math_in_text_html,
)


def test_radical_preservation_sqrt33():
    """Verify that sqrt(33) renders as a valid radical MathML element."""
    raw = r"Giá trị nghiệm chứa căn thức: $\sqrt{33}$."
    rendered = render_math_in_text_html(raw)
    assert "<msqrt>" in rendered
    assert "<mn>33</mn>" in rendered
    assert "Giá trị nghiệm chứa căn thức:" in rendered


def test_exponential_expression_rendering():
    """Verify exp(t/2) and e^{t/2} render as valid exponentials."""
    raw = r"Nghiệm tổng quát chứa hàm mũ: $e^{t/2}$."
    rendered = render_math_in_text_html(raw)
    assert "<msup>" in rendered
    assert "Nghiệm tổng quát chứa hàm mũ:" in rendered


def test_subscripts_and_linear_combination():
    """Verify C1*y1 + C2*y2 renders with subscripts and multiplication."""
    raw = r"Tổ hợp tuyến tính: $C_1 y_1(t) + C_2 y_2(t)$."
    rendered = render_math_in_text_html(raw)
    assert "<msub>" in rendered
    assert "<mi>C</mi>" in rendered
    assert "Tổ hợp tuyến tính:" in rendered


def test_superscript_exponent_rendering():
    """Verify x**2 and x^2 render with superscripts."""
    raw = r"Xét đa thức bậc hai: $x^2 + 2x + 1$."
    rendered = render_math_in_text_html(raw)
    assert "<msup>" in rendered
    assert "<mo>&#x0002B;</mo>" in rendered or "+" in rendered


def test_integrals_and_derivatives():
    """Verify integrals, derivatives, fractions and Greek letters."""
    raw = (
        r"Đạo hàm: $\frac{d}{dt}[\mu(t)y] = \mu(t)y' + \mu'(t)y$ "
        r"và tích phân $\int (t+2)e^{t/2}\,dt = 2te^{t/2} + C$."
    )
    rendered = render_math_in_text_html(raw)
    assert "<mfrac>" in rendered
    assert "<mo>&#x0222B;</mo>" in rendered or "int" in rendered.lower()


def test_vietnamese_text_preservation():
    """Verify that complex Vietnamese diacritics and grammar are fully preserved."""
    raw = "Vì biệt thức $\\Delta = 33 > 0$, phương trình đặc trưng có hai nghiệm thực phân biệt."
    rendered = render_math_in_text_html(raw)
    assert "Vì biệt thức" in rendered
    assert "phương trình đặc trưng có hai nghiệm thực phân biệt." in rendered
    assert "<math" in rendered


def test_xss_payload_safety_escaping():
    """Verify that dangerous HTML script, iframe, and event handler payloads are sanitized."""
    xss_samples = [
        "<script>alert('XSS')</script>",
        '<img src=x onerror="alert(1)">',
        "<iframe src='javascript:alert(1)'></iframe>",
        "<a href='javascript:evil()'>click</a>",
    ]
    for xss in xss_samples:
        payload = f"Văn bản chứa mã độc {xss} và công thức $x^2 + 1 = 0$."
        rendered = render_math_in_text_html(payload)
        # Ensure unsafe tags are escaped or eliminated
        assert "<script" not in rendered
        assert "<iframe" not in rendered
        assert "<img" not in rendered
        assert "<a " not in rendered
        assert "&lt;" in rendered


def test_delimit_unwrapped_math():
    """Verify detection and delimiting of raw unwrapped math tokens."""
    raw = "Hàm số sqrt(33) và đa thức x**2 cùng với C1*y1 + C2*y2."
    delimited = delimit_unwrapped_math_in_text(raw)
    assert "$sqrt(33)$" in delimited or r"\sqrt{33}" in delimited
    assert "$x**2$" in delimited or "$x^2$" in delimited
    assert "$C1*y1 + C2*y2$" in delimited


def test_delimit_and_render_row_operations():
    """Verify linear algebra row operations are delimited and rendered."""
    raw = r"R_{1} \leftrightarrow R_{2}"
    rendered = render_math_in_text_html(raw)
    assert "<math" in rendered
    assert "data-tex" in rendered
    assert "R_{1}" in rendered


def test_delimit_and_render_delta_expressions():
    """Verify discriminant Delta expressions are properly delimited and rendered."""
    raw = "Xác định hai nghiệm thực phân biệt (Delta > 0) và kiểm tra Delta = 33"
    delimited = delimit_unwrapped_math_in_text(raw)
    assert r"$(\Delta > 0)$" in delimited
    assert r"$\Delta = 33$" in delimited
    rendered = render_math_in_text_html(raw)
    assert "<math" in rendered
    assert "data-tex" in rendered


def test_delimit_and_render_radical_fractions():
    """Verify coefficients like C1 = 2*sqrt(33)/33 and r1 = (-1 + sqrt(33))/4 are properly formatted."""
    raw = "Hằng số C1 = 2*sqrt(33)/33 và r1 = (-1 + sqrt(33))/4"
    delimited = delimit_unwrapped_math_in_text(raw)
    assert r"\sqrt{33}" in delimited
    assert r"\frac" in delimited
    rendered = render_math_in_text_html(raw)
    assert "<math" in rendered
    assert "<msqrt>" in rendered
    assert "<mfrac>" in rendered


def test_delimit_and_render_cauchy_conditions():
    """Verify Cauchy conditions y(0) = 0 and y'(0) = 1 are delimited."""
    raw = "Thay vào y(0) = 0 và y'(0) = 1 thu được hệ phương trình"
    delimited = delimit_unwrapped_math_in_text(raw)
    assert "$y(0) = 0$" in delimited
    assert "$y'(0) = 1$" in delimited
    rendered = render_math_in_text_html(raw)
    assert "<math" in rendered
    assert "&#x0003D;" in rendered or "<mo>=</mo>" in rendered or "=" in rendered
