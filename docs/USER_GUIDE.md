# Hướng dẫn sử dụng MathWeave Studio

Chào mừng bạn đến với **MathWeave Studio** — Ứng dụng hỗ trợ tính toán, học tập và nghiên cứu toán học chuyên sâu. Ứng dụng được thiết kế không chỉ để đưa ra kết quả cuối cùng, mà còn trình bày lời giải chi tiết theo từng bước sư phạm, kiểm chứng toán học độc lập và trực quan hóa hình học bằng đồ thị tương tác.

---

## Mục lục

1. [Quy trình giải toán tổng quát](#1-quy-trình-giải-toán-tổng-quát)
2. [Hướng dẫn chi tiết theo phân hệ toán học](#2-hướng-dẫn-chi-tiết-theo-phân-hệ-toán-học)
   - [A. Giải tích hàm một biến và đạo hàm](#a-giải-tích-hàm-một-biến-và-đạo-hàm)
   - [B. Tích phân và Giải tích đa biến](#b-tích-phân-và-giải-tích-đa-biến)
   - [C. Các định lý Giải tích vectơ](#c-các-định-lý-giải-tích-vectơ)
   - [D. Đại số tuyến tính và Ma trận](#d-đại-số-tuyến-tính-và-ma-trận)
3. [Cách đọc và hiểu kết quả toán học](#3-cách-đọc-và-hiểu-kết-quả-toán-học)
   - [Lời giải chi tiết từng bước (Step-by-Step Tree)](#lời-giải-chi-tiết-từng-bước-step-by-step-tree)
   - [Huy hiệu kiểm chứng độc lập (Verification Badge)](#huy-hiệu-kiểm-chứng-độc-lập-verification-badge)
   - [Miền xác định và điều kiện bài toán](#miền-xác-định-và-điều-kiện-bài-toán)
4. [Sử dụng các công cụ trực quan hóa](#4-sử-dụng-các-công-cụ-trực-quan-hóa)
   - [Đồ thị 2D tương tác](#đồ-thị-2d-tương-tác)
   - [Đồ thị không gian 3D chuẩn màu RGB](#đồ-thị-không-gian-3d-chuẩn-màu-rgb)
   - [Bảng biến thiên tự động](#bảng-biến-thiên-tự-động)
5. [Cú pháp nhập liệu và xử lý lỗi thường gặp](#5-cú-pháp-nhập-liệu-và-xử-lý-lỗi-thường-gặp)

---

## 1. Quy trình giải toán tổng quát

Quy trình sử dụng MathWeave Studio gồm các bước trực quan:

```
[Danh mục phép toán] ──> [Nhập dữ liệu & Tham số] ──> [Bấm Giải hoặc Enter] ──> [Đọc lời giải & Trực quan hóa]
```

1. **Khởi động ứng dụng:** Mở ứng dụng và truy cập màn hình chính (`http://localhost:8080`).
2. **Chọn dạng toán:** Tại màn hình danh mục (*Operation Catalog*), bấm vào thẻ phép toán bạn cần giải (ví dụ: *Đạo hàm*, *Nguyên hàm*, *Định thức ma trận*...).
3. **Nhập dữ liệu bài toán:** Nhập biểu thức toán học hoặc dữ liệu ma trận vào ô nhập liệu chính.
4. **Cấu hình tham số (nếu có):**
   - Chọn biến số cần tính (mặc định là `x`, hoặc chọn nhanh qua các chip biến tọa độ Descartes, cực, cầu).
   - Thiết lập cấp đạo hàm (nếu tính đạo hàm cấp cao).
   - Thiết lập cận tích phân hoặc phương trình mặt cong (nếu giải toán tích phân).
5. **Gửi bài toán:** Bấm nút **GIẢI PHƯƠNG TRÌNH** (hoặc **GIẢI PHÉP TOÁN MA TRẬN**), hoặc nhấn phím **Enter** ngay trong ô nhập liệu.
6. **Xem đề bài và kết quả:** Đọc lại đề bài dưới dạng chuẩn LaTeX KaTeX và kết quả rút gọn cuối cùng tại phần đầu lời giải.
7. **Đọc chuỗi biến đổi từng bước:** Theo dõi các bước suy luận từ bài toán gốc đến kết quả, xem tên quy tắc sư phạm được áp dụng (như *Quy tắc lũy thừa*, *Quy tắc nhân*, *Quy tắc đạo hàm hàm hợp*...).
8. **Mở rộng các bước con:** Nhấn vào thanh *"Xem giải thích chi tiết các phép biến đổi"* để theo dõi chi tiết đạo hàm/nguyên hàm của từng số hạng nhỏ.
9. **Kiểm tra huy hiệu kiểm chứng và miền xác định:** Đọc thông tin kiểm chứng độc lập và các điều kiện ràng buộc toán học của bài toán.
10. **Tương tác với đồ thị:** Khám phá đồ thị hàm số 2D, đồ thị mặt cong 3D hoặc bảng biến thiên tương ứng.

---

## 2. Hướng dẫn chi tiết theo phân hệ toán học

### A. Giải tích hàm một biến và đạo hàm

#### 1. Đạo hàm một biến (`DERIVATIVE`)
- **Mô tả:** Tính đạo hàm bậc 1 hoặc đạo hàm cấp cao $f^{(n)}(x)$ của hàm số với lời giải chi tiết phân rã theo từng quy tắc toán học.
- **Trường nhập liệu:**
  - *Biểu thức toán học:* Ví dụ `2*x^3 + 6*x - 8`, `x^2 * sin(x)`, `x / (x + 1)`, `cos(x) - tan(x)`.
  - *Biến vi phân:* `x` (hoặc `t`, `u`...).
  - *Cấp đạo hàm ($n$):* Từ 1 đến 10 (mặc định $n=1$).
- **Kết quả minh họa ($f(x) = x^2$):**
  $$f'(x) = 2x$$
  Áp dụng *Quy tắc lũy thừa (Power Rule)*: $\frac{d}{dx}(x^n) = n x^{n-1}$.
- **Hỗ trợ đi kèm:** Bảng biến thiên tự động và đồ thị 2D Plotly.

#### 2. Đạo hàm riêng (`PARTIAL_DERIVATIVE`)
- **Mô tả:** Tính đạo hàm của hàm nhiều biến theo biến số được chỉ định, coi các biến còn lại là hằng số.
- **Trường nhập liệu:**
  - *Biểu thức:* Ví dụ `x^2*y + sin(x*y) + y^3`.
  - *Biến vi phân:* `x` để tính $\frac{\partial f}{\partial x}$, hoặc `y` để tính $\frac{\partial f}{\partial y}$.
- **Kết quả:** Trình bày chi tiết cách xem các biến độc lập khác là hằng số trong quá trình vi phân.

#### 3. Tích phân bất định (Nguyên hàm) (`INDEFINITE_INTEGRAL`)
- **Mô tả:** Tìm họ nguyên hàm $F(x) + C$, giải thích quy tắc lấy nguyên hàm từng số hạng và bổ sung hằng số tích phân $C$.
- **Trường nhập liệu:**
  - *Biểu thức dưới dấu tích phân:* Ví dụ `2*x^3 + 6*x - 8`, `x^2`, `sin(x)`, `exp(x)`.
  - *Biến lấy tích phân:* Mặc định là `x`.
- **Kết quả minh họa ($\int x^2 dx$):**
  $$\int x^2 \, dx = \frac{x^3}{3} + C$$
  Lời giải nêu rõ công thức nguyên hàm của hàm lũy thừa và bước bổ sung hằng số $C$.

#### 4. Tích phân xác định (`DEFINITE_INTEGRAL`)
- **Mô tả:** Tính giá trị số học và ký hiệu chính xác của tích phân trên đoạn $[a, b]$ dựa trên định lý Newton–Leibniz.
- **Trường nhập liệu:**
  - *Hàm số dưới dấu tích phân:* Ví dụ `x^2`.
  - *Cận dưới ($a$):* Ví dụ `0`.
  - *Cận trên ($b$):* Ví dụ `1` hoặc biểu thức `pi`.
- **Kết quả:** Hiển thị bước tìm nguyên hàm $F(x)$, thế cận $\left. F(x) \right|_a^b = F(b) - F(a)$ và diện tích hình phẳng trực quan trên đồ thị.

#### 5. Giới hạn hàm số (`LIMIT`)
- **Mô tả:** Tính giới hạn của hàm số khi biến tiến tới điểm chỉ định, hỗ trợ giới hạn một phía và hai phía.
- **Trường nhập liệu:**
  - *Biểu thức:* Ví dụ `sin(x)/x`, `(x^2 - 1)/(x - 1)`.
  - *Điểm tiến tới ($a$):* Nhập số thực hoặc vô cực (`0`, `1`, `oo`, `-oo`).
  - *Hướng tiến tới:* `+- (Hai phía)`, `+ (Bên phải)`, `- (Bên trái)`.
- **Kết quả:** Hiển thị giá trị giới hạn và các phép biến đổi khử dạng vô định (như phân tích nhân tử hoặc quy tắc L'Hôpital).

---

### B. Tích phân và Giải tích đa biến

Tại giao diện **Tích phân xác định**, MathWeave Studio cung cấp thanh chọn dạng tích phân giúp bạn dễ dàng chuyển đổi linh hoạt:
- **Một biến:** Tích phân cơ bản $\int_a^b f(x) \, dx$.
- **Tích phân đường (`LINE_INTEGRAL`):**
  - *Kiểu tích phân:* Tích phân vô hướng $\int_C f \, ds$ hoặc tích phân đường trường vectơ $\int_C \mathbf{F} \cdot d\mathbf{r}$.
  - *Tham số hóa:* Nhập phương trình cung $C$: $x(t), y(t), z(t)$ và khoảng biến thiên $[t_{\min}, t_{\max}]$.
  - *Định hướng:* Chọn hướng thuận ($+t$) hoặc hướng nghịch ($-t$).
- **Tích phân mặt (`SURFACE_INTEGRAL`):**
  - Hỗ trợ mặt hiển $z = g(x, y)$ và mặt tham số $\mathbf{r}(u, v)$.
  - Tính thông lượng vectơ $\iint_S \mathbf{F} \cdot \mathbf{n} \, dS$ với tùy chọn định hướng pháp tuyến hướng lên (*Upward*) hoặc hướng xuống (*Downward*).
- **Tích phân khối (`TRIPLE_INTEGRAL`):**
  - Tích phân bội ba $\iiint_V f(x, y, z) \, dV$.
  - Hỗ trợ chuyển đổi linh hoạt giữa 3 hệ tọa độ:
    - *Tọa độ Descartes:* $dV = dz \, dy \, dx$.
    - *Tọa độ trụ:* $dV = r \, dz \, dr \, d\theta$.
    - *Tọa độ cầu:* $dV = \rho^2 \sin(\phi) \, d\rho \, d\phi \, d\theta$.
- **Độ dài cung (`ARC_LENGTH`):** Tính độ dài đường cong $L = \int_a^b \sqrt{1 + [f'(x)]^2} \, dx$.
- **Diện tích mặt cong (`SURFACE_AREA`):** Tính diện tích mặt $z = f(x, y)$ trên miền chữ nhật $D$.
- **Mặt & Khối tròn xoay (`SURFACE_OF_REVOLUTION`):** Tính diện tích mặt tròn xoay $S_{\text{rev}}$ và thể tích khối tròn xoay $V_{\text{rev}}$ khi quay quanh trục $Ox$ hoặc $Oy$.

---

### C. Các định lý Giải tích vectơ

MathWeave Studio hỗ trợ kiểm chứng trực tiếp hai vế của các định lý tích phân vectơ kinh điển:

1. **Định lý Green (`GREENS_THEOREM`):**
   - Đối chiếu tích phân đường biên kín $\oint_{\partial D} (P dx + Q dy)$ với tích phân kép $\iint_D \left(\frac{\partial Q}{\partial x} - \frac{\partial P}{\partial y}\right) dA$.
   - Hỗ trợ cả hai dạng: Dạng lưu thông (*Circulation*) và Dạng thông lượng (*Flux*).
2. **Định lý Stokes (`STOKES_THEOREM`):**
   - Đối chiếu lưu thông của trường vectơ $\mathbf{F}$ trên biên $\partial S$ với thông lượng của $\text{curl}(\mathbf{F})$ qua mặt cong $S$.
3. **Định lý Divergence / Định lý Gauss–Ostrogradsky (`DIVERGENCE_THEOREM`):**
   - Đối chiếu thông lượng qua mặt kín $\oiint_{\partial V} \mathbf{F} \cdot \mathbf{n} \, dS$ với tích phân bội ba của độ tản $\iiint_V \text{div}(\mathbf{F}) \, dV$.

---

### D. Đại số tuyến tính và Ma trận

Tất cả các phép toán ma trận trong MathWeave Studio sử dụng cú pháp danh sách lồng nhau tiêu chuẩn:
`[[hàng 1], [hàng 2], ..., [hàng m]]`

#### 1. Định thức ma trận (`MATRIX_DETERMINANT`)
- **Đầu vào:** Ma trận vuông, ví dụ `[[1, 2], [3, 4]]` hoặc `[[1, 2, 3], [0, 1, 4], [5, 6, 0]]`.
- **Lời giải:**
  - Với ma trận $2 \times 2$: Áp dụng trực tiếp công thức $\det = ad - bc$.
  - Với ma trận $3 \times 3$ trở lên: Hiển thị các bước khai triển Laplace theo dòng hoặc theo cột.

#### 2. Ma trận nghịch đảo (`MATRIX_INVERSE`)
- **Đầu vào:** Ma trận vuông $A$.
- **Lời giải:** Kiểm tra điều kiện khả nghịch $\det(A) \ne 0$. Nếu $\det(A) = 0$, ứng dụng giải thích rõ ma trận suy biến và không tồn tại ma trận nghịch đảo. Nếu khả nghịch, tính ma trận phụ hợp $\text{adj}(A)$ và đưa ra $A^{-1} = \frac{1}{\det(A)} \text{adj}(A)$.

#### 3. Dạng bậc thang (REF) và Bậc thang rút gọn (RREF)
- **Dạng bậc thang (REF):** Sử dụng thuật toán khử Gauss với các phép biến đổi hàng sơ cấp ($R_i \leftrightarrow R_j$, $k R_i \to R_i$, $R_i + c R_j \to R_i$).
- **Dạng bậc thang rút gọn (RREF):** Sử dụng thuật toán khử Gauss–Jordan để đưa các phần tử trụ về 1 và triệt tiêu tất cả các phần tử khác trên cột trụ về 0.

#### 4. Phép toán hai ma trận: Cộng, Trừ, Nhân
- **Cộng/Trừ ma trận:** Nhập trực tiếp biểu thức giữa hai ma trận cùng kích thước:
  ```text
  [[1, 2], [3, 4]] + [[5, 6], [7, 8]]
  [[5, 6], [7, 8]] - [[1, 2], [3, 4]]
  ```
- **Nhân hai ma trận:** Nhập bằng toán tử `*`:
  ```text
  [[1, 2], [3, 4]] * [[5, 6], [7, 8]]
  [[1, 2, 3], [4, 5, 6]] * [[1, 2], [3, 4], [5, 6]]
  ```
  Ứng dụng tự động kiểm tra tính tương thích kích thước (số cột ma trận thứ nhất phải bằng số hàng ma trận thứ hai) trước khi nhân.

#### 5. Giải hệ phương trình tuyến tính ($Ax = b$)
- **Cú pháp nhập liệu:** Nhập ma trận hệ số $A$ và vectơ vế phải $b$ phân tách bởi dấu bằng `=`:
  ```text
  [[1, 2], [3, 4]] = [5, 11]
  [[1, 1, 1], [0, 2, 5], [2, 5, -1]] = [6, -4, 27]
  ```
- **Lời giải:** Thiết lập ma trận mở rộng $[A | b]$, thực hiện thuật toán khử Gauss–Jordan từng bước và biện luận nghiệm (nghiệm duy nhất, vô số nghiệm phụ thuộc tham số tự do, hoặc vô nghiệm).

---

## 3. Cách đọc và hiểu kết quả toán học

### Lời giải chi tiết từng bước (Step-by-Step Tree)

Mỗi bước biến đổi được trình bày theo cấu trúc chuẩn:
- **Tiêu đề bước:** Nêu rõ mục tiêu toán học và quy tắc áp dụng (ví dụ: *Quy tắc đạo hàm của tổng và hiệu*, *Quy tắc tích phân của lũy thừa*...).
- **Công thức biến đổi:** So sánh trạng thái trước và sau khi áp dụng quy tắc.
- **Các bước con mở rộng (Substeps):** Đối với các đa thức hoặc biểu thức phức tạp, ứng dụng phân rã từng số hạng thành một bước con độc lập để bạn dễ dàng theo dõi chi tiết.

### Huy hiệu kiểm chứng độc lập (Verification Badge)

Bên cạnh kết quả giải, MathWeave Studio luôn hiển thị một huy hiệu trạng thái kiểm chuẩn:
- **Kiểm chứng thành công (Verified):** Kết quả được chứng minh là tương đương hoàn toàn bằng công cụ giải tích độc lập của SymPy hoặc các bất biến toán học.
- **Dò số học (Numerical Probe):** Kết quả được lấy mẫu và đối chiếu tại hàng loạt điểm ngẫu nhiên trong miền xác định, đảm bảo sai số $< 10^{-9}$.

### Miền xác định và điều kiện bài toán

Ứng dụng tự động phát hiện và cảnh báo các ràng buộc toán học quan trọng:
- Điều kiện mẫu số khác 0: Ví dụ $\mathcal{D} = \mathbb{R} \setminus \{-1\}$.
- Điều kiện dưới dấu căn bậc hai: Biểu thức dưới căn phải không âm.
- Điều kiện hàm lượng giác $\tan(x)$, $\sec(x)$: Điều kiện $\cos(x) \ne 0 \iff x \ne \frac{\pi}{2} + k\pi$.

---

## 4. Sử dụng các công cụ trực quan hóa

### Đồ thị 2D tương tác
- Tích hợp thư viện Plotly sắc nét.
- Cho phép phóng to (*Zoom*), thu nhỏ, di chuyển đồ thị (*Pan*) và rê chuột để đọc chính xác giá trị $(x, y)$.
- **Thuật toán xử lý điểm kỳ dị:** Đồ thị nhận diện các tiệm cận đứng và điểm gián đoạn của hàm phân thức hữu tỉ, tự động chèn giá trị `NaN` để tránh vẽ nối dây sai lệch qua hai nhánh tiệm cận.

### Đồ thị không gian 3D chuẩn màu RGB
- Hiển thị mặt cong $z = f(x, y)$ và các đường cong không gian 3D.
- **Hệ trục tọa độ RGB tiêu chuẩn:**
  - **Trục X:** Màu đỏ (*Red*), nét liền xuyên qua gốc tọa độ.
  - **Trục Y:** Màu xanh lá (*Green*), nét đứt.
  - **Trục Z:** Màu xanh dương (*Blue*), nét chấm gạch.
- Tỉ lệ khung hình đẳng cự (*Isometric cubic aspect ratio*) giúp giữ nguyên vẹn hình dáng học thuật của các mặt bậc hai (mặt cầu, paraboloid, nón...).

### Bảng biến thiên tự động
- Dành riêng cho các bài toán khảo sát đạo hàm đa thức và phân thức.
- Tự động xác định miền xác định $\mathcal{D}$, tính các điểm tới hạn ($f'(x) = 0$), các điểm gián đoạn (tiệm cận đứng biểu diễn bằng vạch kép `||`).
- Xác định chính xác dấu của đạo hàm ($+$ hoặc $-$) và các mũi tên chiều biến thiên đồng biến ($\nearrow$) và nghịch biến ($\searrow$) kèm giới hạn ở vô cực.

---

## 5. Cú pháp nhập liệu và xử lý lỗi thường gặp

### Bảng ký hiệu toán học được hỗ trợ

| Ký hiệu toán học | Cách nhập vào ứng dụng | Ví dụ |
| :--- | :--- | :--- |
| Lũy thừa $x^n$ | `x^n` hoặc `x**n` | `x^3`, `x^2 + 1` |
| Phép nhân | `*` hoặc viết liền có dấu cách | `2*x`, `x*sin(x)` |
| Phép chia | `/` | `x / (x + 1)` |
| Căn bậc hai $\sqrt{x}$ | `sqrt(x)` | `sqrt(x^2 + 1)` |
| Hàm lượng giác | `sin(x)`, `cos(x)`, `tan(x)` | `cos(2*x)` |
| Hàm mũ tự nhiên $e^x$ | `exp(x)` | `exp(-x^2)` |
| Logarit tự nhiên $\ln(x)$ | `ln(x)` hoặc `log(x)` | `log(x + 1)` |
| Hằng số $\pi$ | `pi` | `sin(pi * x)` |
| Vô cực $\infty$ | `oo` hoặc `inf` | Giới hạn khi $x \to \infty$: nhập `oo` |

### Các lỗi nhập liệu thường gặp

1. **Thiếu dấu đóng ngoặc:**
   - *Lỗi:* `sin(x^2 + 1`
   - *Cách sửa:* Đảm bảo các cặp ngoặc `( )`, `[ ]` luôn đóng mở đầy đủ: `sin(x^2 + 1)`.
2. **Kích thước ma trận không hợp lệ:**
   - *Lỗi:* Các hàng trong ma trận có độ dài không đồng đều, ví dụ `[[1, 2], [3]]`.
   - *Cách sửa:* Đảm bảo mỗi hàng có cùng số lượng phần tử: `[[1, 2], [3, 4]]`.
3. **Biến số trong biểu thức không khớp với biến chỉ định:**
   - *Lỗi:* Nhập biểu thức $y^2 + 2y$ nhưng để biến vi phân là `x`.
   - *Cách sửa:* Đổi trường *"Biến vi phân"* thành `y`.
4. **Chia cho 0 trong ma trận nghịch đảo:**
   - *Thông báo:* Định thức $\det(A) = 0$.
   - *Ý nghĩa:* Ma trận bị suy biến (các hàng phụ thuộc tuyến tính), hệ thống sẽ thông báo rõ ràng rằng không tồn tại ma trận nghịch đảo.
