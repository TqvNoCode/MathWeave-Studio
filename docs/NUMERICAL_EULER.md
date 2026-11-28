# Explicit Euler Numerical ODE Solver — Technical & Pedagogical Reference

*Bilingual Documentation (English & Tiếng Việt) — MathWeave Studio*

---

## English Reference

### 1. What is the Explicit Euler Method?
The **Explicit Euler Method** (also called the **Forward Euler Method**) is a first-order numerical integration algorithm for approximating solutions to ordinary differential equation (ODE) **Initial Value Problems (IVPs)** on a finite interval $[t_0, T]$. Rather than searching for a closed-form symbolic formula, it steps across discrete grid points $t_0, t_1, \dots, t_N = T$ using the local tangent slope evaluated at the current known state.

### 2. Separated Workflows & Critical Distinction vs. Euler–Cauchy
MathWeave Studio separates numerical ODE solving directly by ODE module order:
- **First-Order ODE Module (`Phương trình vi phân (ODE)`):** Offers **Analytical Solution** and **Numerical Solution — Explicit Euler** for $y' = f(t, y)$, $y(t_0) = y_0$. No second-order inputs or order selectors appear here.
- **Second-Order ODE Module (`Phương trình vi phân cấp 2 (Second-Order)`):** Offers **Analytical Solution** and **Numerical Solution — Explicit Euler** for $y'' = F(t, y, y')$, $y(t_0) = y_0$, $y'(t_0) = v_0$.
- **Distinction vs. Euler–Cauchy Differential Equations:**
  - **Explicit Euler (*Phương pháp Euler tiến*):** A general **numerical approximation algorithm** for first- and second-order IVPs.
  - **Euler–Cauchy ODE (*Phương trình vi phân Euler–Cauchy*):** A specific **class of linear second-order ODEs** $A t^2 y'' + B t y' + C y = g(t)$ ($A \neq 0$) with a regular singular point at $t = 0$. The analytical Euler–Cauchy solver remains independent, while the second-order Explicit Euler workflow can numerically integrate Euler–Cauchy equations on regular intervals not touching or crossing $t = 0$.

### 3. Mathematical Architecture & Formulas

#### Shared Core & Order-Specific Adapters
Both ODE modules reuse a single `Decimal` drift-free time-grid builder (`time_grid.py`) and vector Explicit Euler integration engine (`euler_engine.py`) via order-specific adapters (`FirstOrderEulerAdapter`, `SecondOrderEulerAdapter`).

#### First-Order ODE IVP
Given $y' = f(t, y)$ with initial condition $y(t_0) = y_0$, positive step magnitude $h > 0$, and direction $d = \operatorname{sign}(T - t_0) \in \{+1, -1\}$:
$$t_{n+1} = t_n + h_n, \qquad y_{n+1} = y_n + h_n f(t_n, y_n)$$
where the signed step $h_n$ satisfies $|h_n| = \min(h, |T - t_n|)$ so that if $|T - t_0|$ is not divisible by $h$, the final step is shortened automatically without overshooting $T$.

#### Second-Order ODE IVP & System Transformation
Given $y'' = F(t, y, y')$ with initial value $y(t_0) = y_0$ and initial derivative $v_0 = y'(t_0)$, transform into a first-order system using $z_1 = y$ and $z_2 = v = y'$:
$$\begin{cases} z_1' = z_2 \\ z_2' = F(t, z_1, z_2) \end{cases}$$
Both state variables are updated **simultaneously** strictly from the previous step's state $(y_n, v_n)$:
$$y_{n+1} = y_n + h_n v_n, \qquad v_{n+1} = v_n + h_n F(t_n, y_n, v_n)$$
*(Note: The solver never uses $y_{n+1}$ when computing $v_{n+1}$; that would be semi-implicit/symplectic Euler, not Explicit Euler.)* Both $y(T) \approx y_N$ and $y'(T) \approx v_N$ are reported together.

#### Euler–Cauchy Numerical Transformation
When an Euler–Cauchy equation $At^2 y'' + Bty' + Cy = g(t)$ ($A \neq 0$) is provided in second-order numerical mode, it is algebraically isolated into:
$$y'' = \frac{g(t) - Bty' - Cy}{At^2}, \qquad t \neq 0$$
Intervals touching or crossing $t = 0$ are rejected with `SINGULARITY_ERROR`.

### 4. Local One-Step Error, Global Error, and Richardson Estimates

#### Unnormalized One-Step Local Defect Convention
MathWeave Studio explicitly uses the **unnormalized one-step local defect** $\delta_{n+1}$ (rather than the normalized per-unit-step local truncation error $\tau_{n+1} = \delta_{n+1}/h_n$ used in some textbooks):
- **First-order:** $\delta_{n+1} = y(t_{n+1}) - y(t_n) - h_n f(t_n, y(t_n)) = O(h_n^2)$
- **Second-order:**
  $$\delta^y_{n+1} = y(t_{n+1}) - y(t_n) - h_n y'(t_n) = O(h_n^2), \qquad \delta^v_{n+1} = y'(t_{n+1}) - y'(t_n) - h_n F(t_n, y(t_n), y'(t_n)) = O(h_n^2)$$
Under $C^2$/$C^3$ smoothness of the exact solution, $|\delta_{n+1}| = O(h_n^2)$.

#### Actual Global Error (When Exact Analytical Solution Exists)
- **First-order:** $E^y_n = |y_{\text{exact}}(t_n) - y_n| = O(h)$
- **Second-order:** $E^y_n = |y_{\text{exact}}(t_n) - y_n| = O(h)$ and $E^v_n = |y'_{\text{exact}}(t_n) - v_n| = O(h)$
Both final-point errors and maximum grid errors over all $n = 0..N$ are reported consistently across the summary card, error-analysis panels, iteration table, and verifier.

#### Exact vs. Estimated Errors & When No Exact Solution Exists
- **Zero Fabrication:** When no closed-form analytical solution exists (e.g., $y' = \sin(ty)$ or $y'' = -\sin(y)$), exact local defects and exact global errors are **never fabricated**; theoretical convergence orders $O(h^2)$ (local defect) and $O(h)$ (global error) are displayed instead.
- **Step-Halving Richardson Estimate ($h/2$):** An independent solve on a subdivided $h/2$ grid aligned at every coarse node computes the asymptotic first-order ($p = 1$) error estimate:
  $$E_h \approx 2 \times |y_{h/2} - y_h|$$
  (and $E^v_h \approx 2 \times |v_{h/2} - v_h|$ for second-order). All step-halving outputs are explicitly labeled as **numerical estimates**, not exact errors.

#### Stability Limitations
Explicit Euler is **not A-stable** (not unconditionally stable for every step size $h$ or ODE). For stiff decay $y' = \lambda y$ ($\lambda < 0$), $|1 + h\lambda| \le 1$ is required; for oscillatory systems like $y'' = -y$, Explicit Euler does not conserve energy and amplifies amplitude unless $h$ is sufficiently small.

### 5. How to Use Both Interfaces
1. Select **Phương trình vi phân (ODE)** (First-Order) or **Phương trình vi phân cấp 2 (Second-Order)** from the catalog.
2. Choose **Giải số — Phương pháp Euler tiến (Explicit Euler)** in the `CHẾ ĐỘ GIẢI:` bar.
3. Enter the equation, independent variable, initial conditions (`t0`, `y0`, plus `v0` for 2nd-order), endpoint `T`, and positive step size `h > 0`.
4. Click **TÍNH XẤP XỈ EULER CẤP 1** or **TÍNH XẤP XỈ EULER CẤP 2**.
5. Review **Level 1** (main numerical approximation & comparison status), expand **Level 2** (local defect, global error, convergence/stability, $h/2$ Richardson estimate), inspect the Plotly graphs and paginated iteration table, and open **Level 3** (4-stage pedagogical derivation) as needed.

---

## Tài liệu Tiếng Việt

### 1. Phương pháp Euler tiến (Explicit Euler) là gì?
**Phương pháp Euler tiến (Explicit Euler / Forward Euler)** là thuật toán giải xấp xỉ số bậc một cho **bài toán giá trị ban đầu (IVP)** của phương trình vi phân thường trên đoạn hữu hạn $[t_0, T]$. Thay vì tìm biểu thức nghiệm giải tích đóng, phương pháp tính lần lượt các giá trị rời rạc $y_0, y_1, \dots, y_N$ tại các nút lưới thời gian $t_n$ dựa theo độ dốc tiếp tuyến tại điểm hiện tại.

### 2. Tách biệt hai quy trình Cấp 1 / Cấp 2 & Phân biệt với Euler–Cauchy
- **Module PTVP Cấp 1 (`Phương trình vi phân (ODE)`):** Cung cấp hai chế độ **Giải tích** và **Giải số — Phương pháp Euler tiến** cho $y' = f(t, y)$, $y(t_0) = y_0$ (không lẫn bộ chọn cấp phương trình hay trường $v_0$).
- **Module PTVP Cấp 2 (`Phương trình vi phân cấp 2 (Second-Order)`):** Cung cấp hai chế độ **Giải tích** và **Giải số — Phương pháp Euler tiến** cho $y'' = F(t, y, y')$, $y(t_0) = y_0, y'(t_0) = v_0$.
- **Phân biệt với Phương trình Euler–Cauchy ($At^2y'' + Bty' + Cy = g(t)$):** Explicit Euler là **thuật toán xấp xỉ số** tổng quát, khác với **họ phương trình vi phân giải tích Euler–Cauchy** có điểm kỳ dị chính quy tại $t = 0$. Ở chế độ số cấp 2, phương trình Euler–Cauchy được hỗ trợ trên các khoảng chính quy không chạm hoặc đi qua $t = 0$.

### 3. Công thức toán học & Biến đổi hệ cấp 1
- **PTVP cấp 1 ($y' = f(t, y), \, y(t_0) = y_0$):**
  $$t_{n+1} = t_n + h_n, \qquad y_{n+1} = y_n + h_n f(t_n, y_n), \qquad |h_n| = \min(h, |T - t_n|)$$
  Hỗ trợ tích phân thuận ($T > t_0$) và lùi ($T < t_0$) trong khi luôn hiển thị độ lớn $h > 0$.
- **PTVP cấp 2 ($y'' = F(t, y, y'), \, y(t_0) = y_0, \, y'(t_0) = v_0$):** Đặt $z_1 = y, z_2 = v = y'$:
  $$\begin{cases} z_1' = z_2 \\ z_2' = F(t, z_1, z_2) \end{cases} \implies y_{n+1} = y_n + h_n v_n, \qquad v_{n+1} = v_n + h_n F(t_n, y_n, v_n)$$
  *(Cả $y_{n+1}$ và $v_{n+1}$ đều dùng cặp giá trị cũ $(y_n, v_n)$ ở bước $n$; kết quả cuối luôn hiển thị cả $y(T)$ và $y'(T)$.)*

### 4. Sai số cục bộ, Sai số toàn cục & Ước lượng giảm nửa bước $h/2$
- **Sai số chặt cục bộ một bước chưa chuẩn hóa ($\delta_{n+1}$):**
  - Cấp 1: $\delta_{n+1} = y(t_{n+1}) - y(t_n) - h_n f(t_n, y(t_n)) = O(h_n^2)$.
  - Cấp 2: $\delta^y_{n+1} = y(t_{n+1}) - y(t_n) - h_n y'(t_n) = O(h_n^2)$ và $\delta^v_{n+1} = y'(t_{n+1}) - y'(t_n) - h_n F(t_n, y(t_n), y'(t_n)) = O(h_n^2)$.
  *(Khác với đại lượng chuẩn hóa $\tau_{n+1} = \delta_{n+1}/h_n = O(h_n)$ trong một số tài liệu.)*
- **Sai số toàn cục thực tế (khi có nghiệm giải tích):**
  - $E^y_n = |y_{\text{exact}}(t_n) - y_n| = O(h)$ và (với cấp 2) $E^v_n = |y'_{\text{exact}}(t_n) - v_n| = O(h)$, gồm cả giá trị tại điểm cuối $T$ và cực đại trên toàn lưới.
- **Khi không có nghiệm giải tích:** Hệ thống **không bịa đặt số liệu sai số thực**; chỉ hiển thị bậc hội tụ lý thuyết ($O(h^2)$ cục bộ, $O(h)$ toàn cục) và tùy chọn **ước lượng Richardson** bằng lưới giảm nửa bước $h/2$:
  $$E_h \approx 2 \times |y_{h/2} - y_h|$$
  (được gắn nhãn rõ ràng là **ước lượng số**, không phải sai số chính xác).
- **Tính ổn định & an toàn tài nguyên:** Explicit Euler **không ổn định với mọi bước nhảy $h$ hay mọi phương trình**; giới hạn mặc định **10,000 bước**, tự động phát hiện `NaN`/`Infinity`, tràn số, chia cho 0, logarit không dương, căn số âm, cực lượng giác và điểm kỳ dị $t = 0$ của Euler–Cauchy.
