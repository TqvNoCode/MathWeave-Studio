# Hướng dẫn cài đặt và vận hành MathWeave Studio trên Linux

Tài liệu này hướng dẫn chi tiết cách cài đặt, cấu hình môi trường và vận hành **MathWeave Studio** trên các hệ điều hành Linux. Môi trường phát triển và kiểm chuẩn chính của dự án là **Arch Linux**, đồng thời các hướng dẫn dưới đây tương thích với các bản phân phối Linux phổ biến khác như **Ubuntu/Debian** và **Fedora**.

---

## Mục lục

1. [Yêu cầu hệ thống](#1-yêu-cầu-hệ-thống)
2. [Phương thức A: Chạy từ mã nguồn (Khuyến nghị)](#2-phương-thức-a-chạy-từ-mã-nguồn-khuyến-nghị)
   - [Cách 1: Sử dụng uv (Nhanh và ổn định nhất)](#cách-1-sử-dụng-uv-nhanh-và-ổn-định-nhất)
   - [Cách 2: Sử dụng venv và pip truyền thống](#cách-2-sử-dụng-venv-và-pip-truyền-thống)
3. [Cách khởi chạy ứng dụng](#3-cách-khởi-chạy-ứng-dụng)
   - [Chế độ giao diện Web Browser (Khuyên dùng)](#chế-độ-giao-diện-web-browser-khuyên-dùng)
   - [Chế độ cửa sổ Native Desktop (Qt6 WebEngine)](#chế-độ-cửa-sổ-native-desktop-qt6-webengine)
4. [Phương thức B: Tích hợp Desktop và Bản dựng nhị phân](#4-phương-thức-b-tích-hợp-desktop-và-bản-dựng-nhị-phân)
   - [Kịch bản khởi chạy launch.sh](#kịch-bản-khởi-chạy-launchsh)
   - [Cài đặt phím tắt .desktop vào hệ thống người dùng](#cài-đặt-phím-tắt-desktop-vào-hệ-thống-người-dùng)
   - [Trạng thái bản đóng gói nhị phân (dist)](#trạng-thái-bản-đóng-gói-nhị-phân-dist)
5. [Kiểm tra và xác thực môi trường bằng bộ kiểm thử](#5-kiểm-tra-và-xác-thực-môi-trường-bằng-bộ-kiểm-thử)
6. [Xử lý sự cố thường gặp (Troubleshooting)](#6-xử-lý-sự-cố-thường-gặp-troubleshooting)

---

## 1. Yêu cầu hệ thống

- **Hệ điều hành:** Linux 64-bit (Arch Linux, Ubuntu 22.04+, Debian 12+, Fedora 38+).
- **Python:** Phiên bản `>= 3.11` (phiên bản khuyến nghị là `Python 3.14+`).
- **Trình quản lý gói:** [`uv`](https://docs.astral.sh/uv/) (khuyến nghị số 1 cho tốc độ và tính nhất quán) hoặc `python3-venv` / `pip`.
- **Trình duyệt web:** Bất kỳ trình duyệt hiện đại nào (Firefox, Chromium, Chrome, Brave) để hiển thị giao diện người dùng NiceGUI và kết xuất công thức toán KaTeX/MathML.

---

## 2. Phương thức A: Chạy từ mã nguồn (Khuyến nghị)

Chạy từ mã nguồn là phương pháp linh hoạt, luôn cập nhật các sửa đổi mới nhất và không phụ thuộc vào các thư viện đồ họa hệ thống phức tạp.

### Cách 1: Sử dụng uv (Nhanh và ổn định nhất)

`uv` là công cụ quản lý dự án Python hiện đại, tự động xử lý môi trường ảo và đồng bộ toàn bộ thư viện từ `pyproject.toml` và `uv.lock`.

1. **Di chuyển vào thư mục dự án:**

   ```bash
   cd /path/to/math_app
   ```

2. **Đồng bộ hóa môi trường phụ thuộc:**

   ```bash
   uv sync
   ```

   Lệnh này tự động tạo môi trường ảo `.venv/` (nếu chưa có) và cài đặt đầy đủ các thư viện cần thiết (`nicegui`, `sympy`, `numpy`, `plotly`, `latex2mathml`, `pywebview`, `pytest`...).

3. **Khởi chạy ứng dụng:**

   ```bash
   uv run run.py --browser
   ```

---

### Cách 2: Sử dụng venv và pip truyền thống

Nếu máy của bạn chưa cài đặt `uv`, bạn có thể sử dụng môi trường ảo tiêu chuẩn của Python:

1. **Di chuyển vào thư mục dự án:**

   ```bash
   cd /path/to/math_app
   ```

2. **Khởi tạo môi trường ảo:**

   ```bash
   python3 -m venv .venv
   ```

3. **Kích hoạt môi trường ảo:**

   ```bash
   source .venv/bin/activate
   ```

4. **Cài đặt dự án ở chế độ phát triển (editable mode):**

   ```bash
   pip install -e .
   ```

5. **Khởi chạy ứng dụng:**

   ```bash
   python run.py --browser
   ```

---

## 3. Cách khởi chạy ứng dụng

MathWeave Studio cung cấp hai phương thức hiển thị giao diện tùy thuộc vào cấu hình hệ thống đồ họa của bạn.

### Chế độ giao diện Web Browser (Khuyên dùng)

Đây là chế độ **khuyến nghị hàng đầu** vì đảm bảo độ ổn định tuyệt đối trên mọi môi trường Linux (kể cả môi trường Wayland, X11, máy chủ từ xa SSH hoặc các hệ thống tối giản không có Qt WebEngine).

```bash
# Khởi chạy qua uv
uv run run.py --browser

# Hoặc khởi chạy trực tiếp qua môi trường ảo
.venv/bin/python run.py --browser
```

Khi khởi chạy thành công, terminal sẽ thông báo:

```text
NiceGUI ready to go on http://127.0.0.1:8080
```

Mở trình duyệt web của bạn và truy cập:
👉 **[http://localhost:8080](http://localhost:8080)**

Để dừng ứng dụng an toàn, nhấn tổ hợp phím **`Ctrl + C`** trong cửa sổ terminal. Ứng dụng đã được tích hợp bộ xử lý tín hiệu ngắt an toàn để giải phóng cổng mạng ngay lập tức.

### Chế độ cửa sổ Native Desktop (Qt6 WebEngine)

Nếu bạn muốn ứng dụng mở trong một cửa sổ ứng dụng độc lập như phần mềm Desktop truyền thống:

```bash
uv run run.py
# hoặc
.venv/bin/python run.py
```

*Lưu ý về chế độ Native Desktop:*
Chế độ này sử dụng `pywebview` với backend `Qt6 WebEngine`. Để cửa sổ native khởi chạy mượt mà, hệ điều hành của bạn cần có sẵn các thư viện nền tảng Qt6 tương ứng:
- **Trên Arch Linux:** Cần cài đặt gói `qt6-base` và `qt6-webengine`. Nếu dùng X11, đảm bảo có `libxcb` và `xcb-util-cursor`.
- **Trên Ubuntu/Debian:** Cần cài đặt `libxcb-cursor0` và các gói `python3-pyqt6.qtwebengine`.

Nếu môi trường thiếu driver đồ họa hoặc thư viện Qt platform (ví dụ trong container hoặc Wayland không đủ socket), bạn chỉ cần thêm cờ `--browser` để ứng dụng tự động mở qua trình duyệt web mà không gặp bất kỳ gián đoạn nào.

---

## 4. Phương thức B: Tích hợp Desktop và Bản dựng nhị phân

### Kịch bản khởi chạy launch.sh

Trong thư mục gốc có sẵn kịch bản khởi chạy [launch.sh](file:///home/tqv/Desktop/CODE/Python/math_app/launch.sh). Kịch bản này tự động phát hiện thứ tự ưu tiên:
1. Bản dựng nhị phân độc lập đóng gói sẵn (`dist/mathweave-studio/mathweave-studio` hoặc `dist/mathstudio/mathstudio`).
2. Môi trường ảo cục bộ `.venv/bin/python`.
3. Trình quản lý `uv run run.py`.

Cấp quyền thực thi và chạy trực tiếp:

```bash
chmod +x launch.sh
./launch.sh --browser
```

### Cài đặt phím tắt .desktop vào hệ thống người dùng

Để MathWeave Studio xuất hiện trong menu ứng dụng hệ thống (Application Launcher) của GNOME, KDE Plasma, XFCE hoặc các Desktop Environment khác mà không cần quyền `sudo`:

1. **Sao chép tập tin desktop entry vào thư mục ứng dụng cá nhân:**

   ```bash
   mkdir -p ~/.local/share/applications
   cp mathweave-studio.desktop ~/.local/share/applications/
   ```

2. **Kiểm tra đường dẫn tuyệt đối:**
   Mở tập tin `~/.local/share/applications/mathweave-studio.desktop` và đảm bảo hai trường sau trỏ chính xác vào thư mục dự án trên máy của bạn:

   ```ini
   Exec=/home/tqv/Desktop/CODE/Python/math_app/launch.sh
   Icon=/home/tqv/Desktop/CODE/Python/math_app/assets/icon.png
   ```

3. **Cập nhật cơ sở dữ liệu desktop entry của người dùng:**

   ```bash
   update-desktop-database ~/.local/share/applications/
   ```

Bây giờ bạn có thể tìm thấy **MathWeave Studio** trực tiếp từ thanh tìm kiếm ứng dụng của hệ điều hành.

### Trạng thái bản đóng gói nhị phân (dist)

- Trong thư mục `dist/mathstudio/` hiện có bản dựng nhị phân độc lập thử nghiệm được tạo bởi PyInstaller.
- File cấu hình đóng gói mới nhất cho dự án đã được cập nhật tại [mathweave-studio.spec](file:///home/tqv/Desktop/CODE/Python/math_app/mathweave-studio.spec) và [mathstudio.spec](file:///home/tqv/Desktop/CODE/Python/math_app/mathstudio.spec).
- Tuy nhiên, đối với người dùng cuối và các nhà phát triển, **chế độ chạy từ mã nguồn với `uv` (Phương thức A)** vẫn là phương thức được kiểm chuẩn chặt chẽ nhất, đảm bảo tính tương thích cao và cập nhật toàn bộ các bài kiểm thử toán học mới nhất.

---

## 5. Kiểm tra và xác thực môi trường bằng bộ kiểm thử

Sau khi cài đặt xong, bạn có thể chạy toàn bộ bộ kiểm thử tự động của MathWeave Studio để đảm bảo mọi tính toán đại số và giải tích hoạt động chính xác:

```bash
# Sử dụng uv
uv run pytest

# Hoặc sử dụng môi trường ảo
.venv/bin/pytest
```

Kết quả mong đợi:
```text
======================== 190 passed in 9.9s ========================
```

Toàn bộ 190 test cases bao gồm kiểm thử ranh giới kiến trúc Clean Architecture, thuật toán giải tích từng bước, quy tắc đạo hàm và nguyên hàm, kiểm chứng định lý vectơ và ma trận đều phải vượt qua (100% pass).

---

## 6. Xử lý sự cố thường gặp (Troubleshooting)

### 1. Cổng 8080 đã bị ứng dụng khác chiếm dụng
- **Hiện tượng:** Bạn gặp thông báo xung đột cổng hoặc ứng dụng chuyển sang cổng khác.
- **Xử lý:** Ứng dụng đã tích hợp hàm [`get_available_port()`](file:///home/tqv/Desktop/CODE/Python/math_app/src/math_app/main.py#L91-L104) để tự động phát hiện nếu cổng 8080 đang bận và tự động liên kết tới một cổng trống ngẫu nhiên. Hãy quan sát dòng thông báo trên terminal để biết địa chỉ cổng chính xác (ví dụ: `http://127.0.0.1:42189`).

### 2. Lỗi Qt Platform Plugin khi chạy Native Window
- **Hiện tượng:**
  ```text
  qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found.
  ```
- **Xử lý:** Đây là lỗi đặc thù của môi trường thiếu thư viện XCB hoặc biến môi trường hiển thị. Hãy chuyển sang chạy chế độ trình duyệt bằng cách thêm cờ `--browser`:
  ```bash
  uv run run.py --browser
  ```

### 3. Lỗi quyền thực thi kịch bản (Permission denied)
- **Hiện tượng:** `bash: ./launch.sh: Permission denied`
- **Xử lý:** Cấp quyền thực thi cho kịch bản:
  ```bash
  chmod +x launch.sh run.py
  ```

### 4. Lỗi thiếu thư viện Python khi vừa clone mã nguồn
- **Xử lý:** Chạy `uv sync` để đồng bộ lại toàn bộ các gói thư viện từ file khóa `uv.lock`.
