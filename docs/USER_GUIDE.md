# MathWeave Studio — Hướng dẫn sử dụng (User Guide)

Tài liệu này cung cấp hướng dẫn thực hành gọn gàng, rõ ràng để bạn nhanh chóng làm chủ quy trình giải toán, đọc hiểu lời giải sư phạm và tương tác với các công cụ đồ họa trong **MathWeave Studio**.

---

## Mục lục

1. [Quy trình giải toán chuẩn](#1-quy-trình-giải-toán-chuẩn)
2. [Các ví dụ giải toán đại diện](#2-các-ví-dụ-giải-toán-đại-diện)
   - [Đạo hàm và Bảng biến thiên](#ví-dụ-1-đạo-hàm-và-bảng-biến-thiên)
   - [Nguyên hàm và Hằng số tích phân C](#ví-dụ-2-nguyên-hàm-và-hằng-số-tích-phân-c)
   - [Giới hạn hàm số](#ví-dụ-3-giới-hạn-hàm-số-limit)
   - [Đại số tuyến tính & Hệ phương trình ma trận](#ví-dụ-4-đại-số-tuyến-tính--hệ-phương-trình-ma-trận)
   - [Phương trình vi phân & Bài toán Cauchy](#ví-dụ-5-phương-trình-vi-phân-ode--bài-toán-cauchy)
3. [Đọc hiểu kết quả và kiểm chứng độc lập](#3-đọc-hiểu-kết-quả-và-kiểm-chứng-độc-lập)
   - [Cây bước giải sư phạm và Bước con](#cây-bước-giải-sư-phạm-và-bước-con-substeps)
   - [Huy hiệu kiểm chứng độc lập (Verification Badge)](#huy-hiệu-kiểm-chứng-độc-lập-verification-badge)
   - [Miền xác định (Domain Restrictions)](#miền-xác-định-domain-restrictions)
4. [Công cụ trực quan hóa (Graphs & Variation Tables)](#4-công-cụ-trực-quan-hóa-graphs--variation-tables)
5. [Trạng thái tính năng: Ổn định vs. Thử nghiệm](#5-trạng-thái-tính-năng-ổn-định-vs-thử-nghiệm)
6. [Cú pháp và Xử lý lỗi nhập liệu thường gặp](#6-cú-pháp-và-xử-lý-lỗi-nhập-liệu-thường-gặp)

---

## 1. Quy trình giải toán chuẩn

Quy trình sử dụng chung cho mọi bài toán trong MathWeave Studio gồm 5 bước chính:

```
[1. Chọn dạng toán] ──> [2. Nhập dữ liệu & Tham số] ──> [3. Bấm Giải / Enter] ──> [4. Đọc lời giải] ──> [5. Trực quan hóa]
```

1. **Chọn dạng toán:** Tại màn hình chính, nhấn vào thẻ bài toán cần giải (ví dụ: *Đạo hàm*, *Nguyên hàm*, *Định thức ma trận*...).
2. **Nhập dữ liệu:** Nhập biểu thức toán học hoặc ma trận vào ô nhập liệu chính. Chọn hoặc thay đổi biến số (mặc định là `x`).
3. **Thực thi:** Bấm nút **GIẢI PHƯƠNG TRÌNH** (hoặc **GIẢI PHÉP TOÁN MA TRẬN**), hoặc nhấn phím **Enter**.
4. **Đọc kết quả và lời giải:**
   - Xem lại đề bài chuẩn hóa và đáp số rút gọn cuối cùng.
   - Đọc chuỗi biến đổi toán học từng bước có ghi chú quy tắc (Quy tắc lũy thừa, tổng, hiệu, tích, thương, đạo hàm hàm hợp...).
   - Bấm mở rộng *"Xem giải thích chi tiết các phép biến đổi"* để theo dõi các bước con (*Substeps*).
5. **Kiểm tra đồ thị & Bảng biến thiên:** Cuộn xuống dưới để xem đồ thị 2D, đồ thị mặt cong 3D hoặc bảng biến thiên tương ứng.

---

## 2. Các ví dụ giải toán đại diện

### Ví dụ 1: Đạo hàm và Bảng biến thiên

- **Dạng toán:** *Đạo hàm (Derivative)*
- **Dữ liệu nhập:** `2*x^3 + 6*x - 8`
- **Biến vi phân:** `x` | **Cấp đạo hàm:** `1`
- **Kết quả hiển thị:**
  $$f'(x) = 6x^2 + 6$$
- **Diễn giải sư phạm:**
  1. *Quy tắc đạo hàm của tổng và hiệu:* Tách vi phân từng số hạng $\frac{d}{dx}(2x^3) + \frac{d}{dx}(6x) - \frac{d}{dx}(8)$.
  2. *Quy tắc lũy thừa & nhân hằng số:* $\frac{d}{dx}(2x^3) = 2 \cdot (3x^2) = 6x^2$; $\frac{d}{dx}(6x) = 6$; $\frac{d}{dx}(8) = 0$.
  3. Kết hợp kết quả và rút gọn.
- **Trực quan hóa:** Nhấn **BẢNG BIẾN THIÊN** để xem bảng khảo sát hàm số với $\mathcal{D} = \mathbb{R}$, dấu đạo hàm luôn dương ($+$) và mũi tên đồng biến $(\nearrow)$ từ $-\infty$ đến $+\infty$.

### Ví dụ 2: Nguyên hàm và Hằng số tích phân C

- **Dạng toán:** *Tích phân bất định / Nguyên hàm (Indefinite Integral)*
- **Dữ liệu nhập:** `x^2` (hoặc `3*x^2 + 2*x`)
- **Kết quả hiển thị:**
  $$\int x^2 \, dx = \frac{x^3}{3} + C$$
- **Diễn giải sư phạm:**
  1. *Quy tắc lũy thừa:* Áp dụng công thức $\int x^n \, dx = \frac{x^{n+1}}{n+1}$ với $n = 2 \implies \frac{x^3}{3}$.
  2. *Bổ sung hằng số tích phân:* Cộng hằng số tích phân $C$ vào họ nguyên hàm.

### Ví dụ 3: Giới hạn hàm số (Limit)

- **Dạng toán:** *Giới hạn hàm số (Limit)*
- **Dữ liệu nhập:** `sin(x)/x`
- **Điểm tiến tới ($a$):** `0` | **Hướng tiến tới:** `+- (Hai phía)`
- **Kết quả hiển thị:**
  $$\lim_{x \to 0} \frac{\sin(x)}{x} = 1$$
- **Diễn giải:** Ứng dụng nhận diện dạng vô định $\left[\frac{0}{0}\right]$ và giải thích phép khử tương đương.

### Ví dụ 4: Đại số tuyến tính & Hệ phương trình ma trận

Tất cả ma trận đều sử dụng cú pháp danh sách lồng nhau chuẩn: `[[hàng 1], [hàng 2], ..., [hàng m]]`.

- **Tính định thức ma trận 2x2:**
  - Nhập: `[[1, 2], [3, 4]]`
  - Kết quả: $\det(A) = (1)(4) - (2)(3) = -2$.
- **Giải hệ phương trình tuyến tính ($Ax = b$):**
  - Nhập: `[[1, 2], [3, 4]] = [5, 11]`
  - Kết quả: Nghiệm duy nhất $x = 1, y = 2$ với các bước khử Gauss–Jordan trên ma trận mở rộng $[A | b]$.

### Ví dụ 5: Phương trình vi phân (ODE) & Bài toán Cauchy

MathWeave Studio hỗ trợ phương trình vi phân cấp 1: tuyến tính (hệ số hằng & biến số), phương trình tách biến, vi phân toàn phần và phương trình có thừa số tích phân $\mu(x)$ hoặc $\mu(y)$.

- **Phương trình tuyến tính hệ số biến (Nhân tử tích phân):**
  - Nhập: `y' + (1/2)*y = t + 2`
  - Biến độc lập: `t`
  - Kết quả: $y(t) = 2t + C e^{-t/2}$
  - Các bước giải sư phạm:
    1. Nhận dạng dạng chuẩn: $p(t) = 1/2$, $g(t) = t + 2$.
    2. Tìm thừa số tích phân: $\mu(t) = e^{\int \frac{1}{2}dt} = e^{t/2}$.
    3. Nhân hai vế với $\mu(t)$ và biến đổi vế trái thành $\frac{d}{dt}[e^{t/2}y] = (t+2)e^{t/2}$.
    4. Tích phân hai vế: $e^{t/2}y = 2t e^{t/2} + C$.
    5. Chia cho $\mu(t)$ và rút ra nghiệm tổng quát $y(t) = 2t + C e^{-t/2}$.

- **Bài toán giá trị ban đầu Cauchy (IVP):**
  - Nhập: `y' = 2*y + 3, y(0) = 1`
  - Kết quả: $y(t) = \frac{5}{2}e^{2t} - \frac{3}{2}$
  - Diễn giải: Xác định nghiệm cân bằng $y_{eq} = -3/2$, suy ra nghiệm tổng quát $y(t) = C e^{2t} - 3/2$, thay $t=0, y=1$ giải ra $C = 5/2$.
  - Kiểm định: Đạo hàm $y'(t) = 5e^{2t}$ thế vào biểu thức dư $R(t) = y' - 2y - 3 \equiv 0$ và nghiệm đúng $y(0) = 1$.

- **Phương trình vi phân toàn phần (Exact ODE):**
  - Nhập: `(2*x*y + 3)*dx + (x^2 + 4*y)*dy = 0` (hoặc `(2*x*y + 3) + (x^2 + 4*y)*y' = 0`)
  - Biến độc lập: `x`
  - Kết quả: $x^2 y + 3x + 2y^2 = C$
  - Diễn giải: Kiểm tra điều kiện vi phân toàn phần $\frac{\partial M}{\partial y} = 2x = \frac{\partial N}{\partial x}$, tích phân $\Psi(x, y) = \int M dx = x^2 y + 3x$, tìm $h(y) = 2y^2$ và kết luận hàm thế $F(x, y) = C$.

- **Phương trình có thừa số tích phân (Integrating Factor):**
  - Nhập: `(3*x*y + y^2)*dx + (x^2 + x*y)*dy = 0`
  - Biến độc lập: `x`
  - Kết quả: $x^3 y + \frac{1}{2}x^2 y^2 = C$
  - Diễn giải: Đạo hàm riêng $\frac{\partial M}{\partial y} = 3x + 2y \ne \frac{\partial N}{\partial x} = 2x + y$. Tính tỉ số $\frac{M_y - N_x}{N} = \frac{1}{x} = f(x)$, suy ra thừa số tích phân $\mu(x) = e^{\int \frac{1}{x}dx} = x$. Nhân hai vế với $\mu(x)$ đưa về phương trình vi phân toàn phần và xác định hàm thế $F(x, y) = C$.

- **Phương trình vi phân cấp 2 hệ số hằng ($a y'' + b y' + c y = 0$):**
  - Nhập: `y'' + 5*y' + 6*y = 0`
  - Biến độc lập: `t`
  - Kết quả: $y(t) = C_1 e^{-2t} + C_2 e^{-3t}$
  - Các bước giải sư phạm:
    1. Thiết lập phương trình đặc trưng: $r^2 + 5r + 6 = 0$.
    2. Tính biệt thức Delta: $\Delta = 5^2 - 4(1)(6) = 1 > 0$.
    3. Xác định hai nghiệm thực phân biệt: $r_1 = -2, r_2 = -3$.
    4. Xây dựng hệ nghiệm cơ bản $y_1 = e^{-2t}, y_2 = e^{-3t}$ và nghiệm tổng quát $y(t) = C_1 e^{-2t} + C_2 e^{-3t}$.
    5. Kiểm chứng độc lập bằng biểu thức dư $R(t) \equiv 0$.

- **Bài toán Cauchy cấp 2 (Second-Order IVP):**
  - Nhập: `y'' + 5*y' + 6*y = 0, y(0) = 2, y'(0) = 3`
  - Biến độc lập: `t`
  - Kết quả: $y(t) = 9e^{-2t} - 7e^{-3t}$
  - Diễn giải: Lập hệ phương trình tuyến tính cho $C_1, C_2$:
    $$\begin{cases} C_1 + C_2 = 2 \\ -2C_1 - 3C_2 = 3 \end{cases} \implies C_1 = 9, \; C_2 = -7$$
    Thay vào nghiệm tổng quát thu được nghiệm riêng $y(t) = 9e^{-2t} - 7e^{-3t}$.
    Kiểm chứng thành công: $y(0) = 9 - 7 = 2$, $y'(0) = -18 + 21 = 3$, và biểu thức dư đồng nhất bằng 0.

- **Hạ bậc phương trình cấp 2 (Reduction of Order):**
  - Nhập: `2*t^2*y'' + 3*t*y' - y = 0, y1 = 1/t`
  - Biến độc lập: `t`
  - Kết quả: $y(t) = \frac{C_1}{t} + C_2 \sqrt{t}$
  - Diễn giải:
    1. Chuẩn hóa: $y'' + \frac{3}{2t}y' - \frac{1}{2t^2}y = 0 \implies p(t) = \frac{3}{2t}$.
    2. Kiểm chứng nghiệm đã biết $y_1(t) = 1/t$: Biểu thức dư $R_1(t) \equiv 0$.
    3. Đặt $y_2(t) = v(t)y_1(t)$, đưa về phương trình cấp một cho $u = v'$: $u' + \left(\frac{3}{2t} + \frac{2(-1/t^2)}{1/t}\right)u = 0 \implies u' - \frac{1}{2t}u = 0$.
    4. Giải ra $u(t) = \sqrt{t}$ (với $t > 0$) hoặc $u(t) = \sqrt{-t}$ (với $t < 0$), nguyên hàm $v(t) = \frac{2}{3}|t|^{3/2}$.
    5. Nghiệm cơ bản thứ hai: $y_2(t) \propto \sqrt{t}$ trên $t > 0$ (hoặc $\sqrt{-t}$ trên $t < 0$).
    6. Kiểm chứng độc lập qua định thức Wronskian $W(y_1, y_2) = \frac{3}{2} t^{-3/2} \ne 0$ trên $(0, +\infty)$ và điểm kỳ dị tại $t = 0$.

- **Định thức Wronskian (Wronskian Determinant) & Lưu ý Định lý Peano:**
  - Nhập: `cos(t), sin(t)`
  - Kết quả: $W(y_1, y_2)(t) = 1 \ne 0$
  - Diễn giải: Đạo hàm $y_1' = -\sin(t)$, $y_2' = \cos(t)$. Ma trận Wronski:
    $$W = \cos(t)\cos(t) - (-\sin(t))\sin(t) = \cos^2(t) + \sin^2(t) = 1 \ne 0$$
    Kết luận: Hai hàm số độc lập tuyến tính trên toàn trục số.
  - **Lưu ý quan trọng về $W \equiv 0$:** Đối với hai hàm số bất kỳ không kèm phương trình vi phân tuyến tính cấp 2 đã được kiểm chứng, $W \equiv 0$ là **chưa thể kết luận** (inconclusive, hiển thị huy hiệu hổ phách) do phản ví dụ kinh điển của Peano ($y_1 = t^2, y_2 = t|t|$ có $W \equiv 0$ trên $\mathbb{R}$ nhưng độc lập tuyến tính). Tính phụ thuộc tuyến tính chỉ được xác nhận khi hai hàm số là nghiệm của cùng một phương trình vi phân tuyến tính thuần nhất trên khoảng liên tục theo Định lý Abel.

- **Bảo toàn Căn thức & Hệ Cauchy cấp 2 (Square Root Preservation):**
  - Nhập: `2*y'' + y' - 4*y = 0, y(0) = 0, y'(0) = 1`
  - Biến độc lập: `t`
  - Kết quả: $y(t) = \frac{2\sqrt{33}}{33} \left(e^{\frac{\sqrt{33}t}{2}} - 1\right) e^{-\frac{(1+\sqrt{33})t}{4}}$
  - Biệt thức $\Delta = 33$, căn bậc hai $\sqrt{\Delta} = \sqrt{33}$, hai nghiệm thực phân biệt $r_{1,2} = \frac{-1 \pm \sqrt{33}}{4}$.
  - Hệ điều kiện ban đầu Cauchy:
    $$\begin{cases} C_1 + C_2 = 0 \\ \frac{-1+\sqrt{33}}{4}C_1 + \frac{-1-\sqrt{33}}{4}C_2 = 1 \end{cases} \implies C_1 = \frac{2\sqrt{33}}{33}, \; C_2 = -\frac{2\sqrt{33}}{33}$$
  - Toàn bộ căn thức $\sqrt{33}$ được bảo toàn nguyên vẹn xuyên suốt các bước giải và hiển thị dưới dạng MathML chuẩn.

---

## 3. Đọc hiểu kết quả và kiểm chứng độc lập

### Cây bước giải sư phạm và Bước con (Substeps)
- **Tiêu đề bước:** Nêu rõ mục tiêu toán học và quy tắc sơ cấp được vận dụng.
- **So sánh Trước / Sau:** Hiển thị biểu thức trước biến đổi bên trái và sau biến đổi bên phải.
- **Mục con chi tiết:** Khi vi phân một đa thức nhiều số hạng, mỗi số hạng được tách thành một bước con độc lập để người học không bị nhảy cóc bước tính.

### Huy hiệu kiểm chứng độc lập (Verification Badge)
MathWeave Studio kiểm tra độc lập mọi lời giải bằng hai cơ chế:
- **Verified (Kiểm chứng thành công):** Thuật toán đối chiếu kết quả từng bước với bộ máy đại số ký hiệu của SymPy hoặc các bất biến toán học.
- **Numerical Probe (Dò số học):** Lấy mẫu số học tại hàng loạt điểm ngẫu nhiên trên miền xác định để xác thực sai số nằm dưới ngưỡng $10^{-9}$.

### Miền xác định (Domain Restrictions)
Ứng dụng tự động phát hiện các ràng buộc xác định:
- Mẫu số khác 0: Ví dụ $\mathcal{D} = \mathbb{R} \setminus \{-1\}$ đối với hàm $\frac{x}{x+1}$.
- Biểu thức trong căn bậc hai không âm: $\sqrt{f(x)} \implies f(x) \ge 0$.
- Hàm lượng giác $\tan(x), \sec(x)$: Điều kiện $\cos(x) \ne 0 \iff x \ne \frac{\pi}{2} + k\pi$.

---

## 4. Công cụ trực quan hóa (Graphs & Variation Tables)

- **Đồ thị 2D Plotly:** Hỗ trợ hàm một biến $y = f(x)$. Tự động nhận diện tiệm cận đứng để ngắt nét vẽ chính xác (không nối dây sai lệch qua hai nhánh tiệm cận). Hỗ trợ phóng to (*Zoom*), di chuyển (*Pan*) và rê chuột đọc tọa độ.
- **Đồ thị 3D không gian:** Dành cho mặt cong $z = f(x, y)$ và đường cong tham số. Hệ trục tọa độ chuẩn màu RGB:
  - **Trục X:** Màu đỏ (*Red*), nét liền xuyên gốc tọa độ.
  - **Trục Y:** Màu xanh lá (*Green*), nét đứt.
  - **Trục Z:** Màu xanh dương (*Blue*), nét chấm gạch.
- **Bảng biến thiên:** Tự động giải phương trình đạo hàm $f'(x) = 0$, xác định điểm cực trị, điểm gián đoạn (vạch kép `||`), dấu đạo hàm ($+ / -$) và mũi tên biến thiên ($\nearrow / \searrow$).

---

## 5. Trạng thái tính năng: Ổn định vs. Thử nghiệm

| Phân hệ / Tính năng | Trạng thái | Ghi chú kỹ thuật |
| :--- | :--- | :--- |
| **Đạo hàm (Cấp 1 & Cấp cao $n \le 10$)** | **Ổn định (Tested)** | 100% test cases đạt, đầy đủ bước giải sư phạm. |
| **Đạo hàm riêng** | **Ổn định (Tested)** | Hỗ trợ hàm nhiều biến theo biến chỉ định. |
| **Nguyên hàm (Tích phân bất định)** | **Ổn định (Tested)** | Phân rã quy tắc lũy thừa, lượng giác, hằng số $+ C$. |
| **Tích phân xác định cơ bản** | **Ổn định (Tested)** | Cận hữu hạn $[a, b]$, định lý Newton–Leibniz. |
| **Giới hạn hàm số (Limits)** | **Ổn định (Tested)** | Giới hạn tại điểm hữu hạn và vô cực ($\pm\infty$). |
| **Phương trình vi phân (Tuyến tính cấp 1, Tách biến, Vi phân toàn phần)** | **Ổn định (Tested)** | 100% test cases đạt; hỗ trợ hệ số hằng/biến, nghiệm cân bằng, hàm thế và bài toán Cauchy. |
| **Ma trận (Det, Nghịch đảo, REF, RREF, Hệ $Ax=b$)** | **Ổn định (Tested)** | Khử Gauss và Gauss–Jordan từng bước. |
| **Tích phân mặt tham số & Đa biến phức tạp** | **Giới hạn / Thử nghiệm** | Tối ưu cho miền chữ nhật; miền cong tùy ý đang phát triển. |
| **Tích phân không sơ cấp** | **Dự phòng ký hiệu** | Trả về nghiệm rút gọn chính xác từ SymPy, không chia nhỏ bước sơ cấp. |

---

## 6. Cú pháp và Xử lý lỗi nhập liệu thường gặp

| Ký hiệu | Cú pháp nhập | Ví dụ |
| :--- | :--- | :--- |
| Lũy thừa | `x^n` hoặc `x**n` | `x^3 + 2*x` |
| Nhân | `*` hoặc dấu cách | `2*x`, `x*sin(x)` |
| Chia | `/` | `(x + 1)/(x - 1)` |
| Căn bậc hai | `sqrt(x)` | `sqrt(x^2 + 1)` |
| Lượng giác | `sin(x)`, `cos(x)`, `tan(x)` | `cos(2*x)` |
| Hàm mũ | `exp(x)` | `exp(-x^2)` |
| Logarit | `ln(x)` hoặc `log(x)` | `ln(x + 1)` |
| Vô cực | `oo` hoặc `inf` | `x -> oo` |
| Ma trận | `[[hàng 1], [hàng 2]]` | `[[1, 2], [3, 4]]` |
| Đạo hàm phương trình vi phân | `y'`, `dy/dt`, `dy/dx` | `y' + 1/2*y = t + 2` |
| Dạng vi phân toàn phần | `M*dx + N*dy = 0` | `(2*x*y + 3)*dx + (x^2 + 4*y)*dy = 0` |
| Điều kiện ban đầu Cauchy | `y(t0) = y0` | `y' = 2*y + 3, y(0) = 1` |

### Xử lý lỗi thường gặp

1. **Lỗi `Mismatched parentheses` (Thiếu ngoặc):** Kiểm tra xem mỗi dấu mở ngoặc `(`, `[` đã có dấu đóng ngoặc tương ứng chưa.
2. **Lỗi ma trận không đồng dạng:** Ma trận có các hàng lệch số lượng phần tử (ví dụ `[[1, 2], [3]]`). Sửa lại cho các hàng có cùng số cột.
3. **Lỗi biến số không khớp:** Biểu thức chứa biến $y$ nhưng trường biến vi phân đang chọn là $x$. Hãy chọn lại biến $y$.
