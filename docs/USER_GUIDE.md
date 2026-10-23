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

### Xử lý lỗi thường gặp

1. **Lỗi `Mismatched parentheses` (Thiếu ngoặc):** Kiểm tra xem mỗi dấu mở ngoặc `(`, `[` đã có dấu đóng ngoặc tương ứng chưa.
2. **Lỗi ma trận không đồng dạng:** Ma trận có các hàng lệch số lượng phần tử (ví dụ `[[1, 2], [3]]`). Sửa lại cho các hàng có cùng số cột.
3. **Lỗi biến số không khớp:** Biểu thức chứa biến $y$ nhưng trường biến vi phân đang chọn là $x$. Hãy chọn lại biến $y$.
