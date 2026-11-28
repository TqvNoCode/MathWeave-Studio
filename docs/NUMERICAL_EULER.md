# Explicit Euler Numerical ODE Solver — Technical & Pedagogical Reference

*Bilingual Documentation (English & Tiếng Việt) — MathWeave Studio*

---

## English Reference

### 1. What is the Explicit Euler Method?
The **Explicit Euler Method** (also called the **Forward Euler Method**) is a first-order numerical integration algorithm for approximating solutions to ordinary differential equation (ODE) **Initial Value Problems (IVPs)** on a finite interval $[t_0, T]$. Rather than searching for a closed-form symbolic formula, it steps across discrete grid points $t_0, t_1, \dots, t_N = T$ using the local tangent slope evaluated at the current known state.

### 2. Critical Distinction: Explicit Euler vs. Euler–Cauchy
- **Explicit Euler Method (*Phương pháp Euler tiến*):** A **numerical approximation algorithm** applicable to general linear and nonlinear IVPs ($y' = f(t, y)$ or $y'' = F(t, y, y')$).
- **Euler–Cauchy Differential Equation (*Phương trình vi phân Euler–Cauchy*):** A **specific class of second-order linear ODEs** of the form $A t^2 y'' + B t y' + C y = g(t)$ ($A \neq 0$) with a regular singular point at $t = 0$.

MathWeave Studio keeps both capabilities strictly separate: the analytical Euler–Cauchy solver remains unchanged, while the Explicit Euler numerical engine can also numerically approximate an Euler–Cauchy IVP on any regular subinterval not touching or crossing $t = 0$.

### 3. Mathematical Formulas

#### First-Order ODE IVP
Given $y' = f(t, y)$ with initial condition $y(t_0) = y_0$, step size $h > 0$, and direction $d = \operatorname{sign}(T - t_0) \in \{+1, -1\}$:
$$t_{n+1} = t_n + h_n, \qquad y_{n+1} = y_n + h_n f(t_n, y_n)$$
where the signed step $h_n$ satisfies $|h_n| = \min(h, |T - t_n|)$ so that if $|T - t_0|$ is not divisible by $h$, the final step is shortened automatically without overshooting $T$.

#### Second-Order ODE IVP
Given $y'' = F(t, y, y')$ with initial displacement $y(t_0) = y_0$ and initial derivative $v_0 = y'(t_0)$, convert to a first-order system ($z_1 = y, z_2 = y'$):
$$\begin{cases} z_1' = z_2 \\ z_2' = F(t, z_1, z_2) \end{cases}$$
Both variables are updated **simultaneously** from the previous state $(y_n, v_n)$:
$$y_{n+1} = y_n + h_n v_n, \qquad v_{n+1} = v_n + h_n F(t_n, y_n, v_n)$$
*(Note: The solver never uses $y_{n+1}$ when computing $v_{n+1}$; that would be semi-implicit/symplectic Euler, not Explicit Euler.)*

#### Euler–Cauchy Numerical Transformation
When an Euler–Cauchy equation $At^2 y'' + Bty' + Cy = g(t)$ ($A \neq 0$) is provided in numerical mode, it is algebraically isolated into:
$$y'' = \frac{g(t) - Bty' - Cy}{At^2}, \qquad t \neq 0$$
Integration intervals containing, starting at, or ending at $t = 0$ are rejected with a singularity error.

### 4. Initial-Value Requirements & Step Size Interpretation
- **First-order:** Requires `t0`, `y0 = y(t0)`, `T != t0`, and `h > 0`.
- **Second-order:** Requires `t0`, `y0 = y(t0)` (initial displacement), `v0 = y'(t0)` (initial derivative/velocity), `T != t0`, and `h > 0`.
- **Forward & Backward Integration:** Supported for both $T > t_0$ ($+h$) and $T < t_0$ ($-h$).
- **Grid Drift & Resource Guard:** Time grid points $t_n$ are computed in exact `Decimal` arithmetic to avoid cumulative floating-point drift. Calculations exceeding **10,000 steps** are rejected cleanly without silent truncation.

### 5. Accuracy, Error Behavior & Numerical Stability
- **Local Truncation Error:** $O(h^2)$ per step (under $C^2$ smoothness of $y$).
- **Global Error:** $O(h)$ across the interval $[t_0, T]$ under appropriate smoothness (e.g., Lipschitz continuity) and stability assumptions. Reducing $h$ generally improves accuracy, though error is **not guaranteed to decrease monotonically** for every step change or problem due to round-off and stability boundaries.
- **Stability:** Explicit Euler is **not A-stable** (not universally stable). For stiff equations such as $y' = \lambda y$ ($\lambda < 0$), $|1 + h\lambda| \le 1$ is required; for oscillatory equations like $y'' = -y$, Explicit Euler does not conserve energy and gradually amplifies amplitude unless $h$ is small.

### 6. Supported Input Formats & Representative Examples
- **Allowed syntax:** `+`, `-`, `*`, `/`, `^` or `**`, `sin`, `cos`, `tan`, `sec`, `csc`, `cot`, `asin`, `acos`, `atan`, `exp`, `log`, `ln`, `sqrt`, `abs`, constants `pi`, `e`, and scalar numeric expressions such as `pi/2` or `sqrt(2)` in `t0`, `y0`, `v0`, `T`, `h`.
- **Examples:**
  - Exponential growth: `y' = y`, $t_0 = 0, y_0 = 1, T = 1, h = 0.1 \implies y_{10} = 1.1^{10} = 2.5937424601$.
  - Exponential decay: `y' = -2*y`, $t_0 = 0, y_0 = 1, T = 1, h = 0.1$.
  - Non-homogeneous 1st-order: `y' = t + y`, $t_0 = 0, y_0 = 1, T = 0.5, h = 0.1$.
  - Harmonic oscillator: `y'' = -y`, $t_0 = 0, y_0 = 0, v_0 = 1, T = 3.14, h = 0.1$.
  - Euler–Cauchy on $t > 0$: `t^2*y'' - t*y' + y = t^2`, $t_0 = 1, y_0 = 0, v_0 = 0, T = 2, h = 0.1$.

### 7. Interpreting the Iteration Table, Graph & Analytical Comparison
- **Iteration Table:** Displays `n`, `t_n`, `y_n`, `f(t_n, y_n)` (1st-order) or `n`, `t_n`, `y_n`, `v_n = y'_n`, `F(t_n, y_n, v_n)` (2nd-order). Values are formatted to 6 decimal places for readability while full IEEE 754 `float64` precision is preserved internally. Large tables support **expand & paginate** (25 rows/page).
- **Numerical Graph:** Plotted directly from solver output rows `(t_n, y_n)` (plus an optional `v_n = y'_n` derivative plot for 2nd-order ODEs).
- **Optional Analytical Comparison:** When existing analytical solvers can independently verify a closed-form solution $y(t)$ for the same IVP, the UI displays $E_n = |y(t_n) - y_n|$ and overlays the dashed exact curve. When no closed-form solution exists, comparison is omitted honestly.

---

## Tài liệu Tiếng Việt

### 1. Phương pháp Euler tiến (Explicit Euler) là gì?
**Phương pháp Euler tiến (Explicit Euler / Forward Euler)** là thuật toán giải xấp xỉ số bậc một cho **bài toán giá trị ban đầu (IVP)** của phương trình vi phân thường trên đoạn hữu hạn $[t_0, T]$. Thay vì tìm biểu thức nghiệm giải tích đóng, phương pháp tính lần lượt các giá trị rời rạc $y_0, y_1, \dots, y_N$ tại các nút lưới thời gian $t_n$ dựa theo độ dốc tiếp tuyến tại điểm hiện tại.

### 2. Phân biệt Explicit Euler và Phương trình Euler–Cauchy
- **Phương pháp Euler tiến (Explicit Euler):** Thuật toán **xấp xỉ số** giải PTVP cấp 1 hoặc cấp 2 kèm điều kiện ban đầu trên lưới rời rạc.
- **Phương trình Euler–Cauchy ($At^2y'' + Bty' + Cy = g(t)$):** Một **họ phương trình vi phân tuyến tính cấp 2 biến hệ số** có điểm kỳ dị chính quy tại $t = 0$.

Ứng dụng tách biệt hoàn toàn hai khái niệm này: bộ giải giải tích Euler–Cauchy được giữ nguyên vẹn, đồng thời chế độ Euler tiến có thể xấp xỉ số phương trình Euler–Cauchy trên bất kỳ khoảng chính quy nào không chạm hoặc đi qua $t = 0$.

### 3. Công thức toán học
- **PTVP cấp 1 ($y' = f(t, y), \, y(t_0) = y_0$):**
  $$t_{n+1} = t_n + h_n, \qquad y_{n+1} = y_n + h_n f(t_n, y_n), \qquad |h_n| = \min(h, |T - t_n|)$$
- **PTVP cấp 2 ($y'' = F(t, y, y'), \, y(t_0) = y_0, \, y'(t_0) = v_0$):** Đặt $z_1 = y, z_2 = v = y'$:
  $$y_{n+1} = y_n + h_n v_n, \qquad v_{n+1} = v_n + h_n F(t_n, y_n, v_n)$$
  *(Cả $y_{n+1}$ và $v_{n+1}$ đều dùng cặp giá trị cũ $(y_n, v_n)$ ở bước $n$.)*
- **Chuyển đổi Euler–Cauchy ($At^2y'' + Bty' + Cy = g(t), A \neq 0$):**
  $$y'' = \frac{g(t) - Bty' - Cy}{At^2} \qquad (t \neq 0)$$

### 4. Độ chính xác, tính ổn định & giới hạn đã biết
- **Sai số chặt cục bộ:** $O(h^2)$; **Sai số toàn cục:** $O(h)$ dưới các điều kiện đủ trơn và ổn định (không đảm bảo đơn điệu giảm trên mọi lưới/phương trình).
- **Tính ổn định:** Không ổn định tuyệt đối; với PTVP cứng hoặc hệ dao động $y'' = -y$, cần chọn $h$ đủ nhỏ.
- **An toàn tài nguyên & miền xác định:** Giới hạn mặc định **10,000 bước lặp** (không tự ý cắt xén phép tính); tự động phát hiện `NaN`, `Infinity`, tràn số, chia cho 0, logarit không dương, căn số âm, cực lượng giác và điểm kỳ dị $t = 0$ của Euler–Cauchy.
- **Định dạng hiển thị:** Bảng lặp hiển thị 6 chữ số thập phân (và phân trang 25 hàng/trang khi mở rộng) trong khi tính toán nội bộ giữ nguyên độ chính xác `float64`.
