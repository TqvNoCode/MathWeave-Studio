# Báo Cáo Triển Khai Build Windows & Nghiệm Thu GitHub Actions — MathWeave Studio

**Dự án:** MathWeave Studio<br>
**Mục tiêu:** Xây dựng quy trình tự động hóa đóng gói Windows (Standard Onedir & Standalone Portable EXE) trên GitHub Actions với đầy đủ smoke test khởi động và kiểm tra tính toàn vẹn tài nguyên.<br>
**Nhánh thực hiện:** `test`<br>
**Commit SHA:** `8473bb4f4c7474c098f7ae0f916fee643b208656`<br>
**Ngày báo cáo:** 19/11/2026<br>

---

## 1. Bảng Đối Soát Trạng Thái Nghiệm Thu Thực Tế (Final Verification Status)

| Giai Đoạn / Hạng Mục | Trạng Thái | Chi Tiết |
| :--- | :--- | :--- |
| **1. Triển khai cục bộ (Implemented locally)** | **HOÀN THÀNH (100%)** | Đã sửa spec onedir, spec onefile, `main.py`, `startup.py`, `app.py`, viết script smoke test và file workflow. |
| **2. Commit cục bộ (Committed locally)** | **HOÀN THÀNH (100%)** | Đã tạo commit `8473bb4` trên nhánh `test`. |
| **3. Đẩy lên GitHub (Pushed to GitHub)** | **HOÀN THÀNH (100%)** | Đã push thành công lên `origin/test` tại GitHub. |
| **4. Thực thi trên GitHub Actions** | **HOÀN THÀNH (100% SUCCESS)** | Run ID `44547556435` đã hoàn tất tất cả 16 bước trên Windows runner với kết quả xanh (`success`). |
| **5. Artifacts đã upload** | **HOÀN THÀNH (100%)** | Cả 2 artifacts đã được xác thực, đóng gói và upload lên GitHub Actions lưu trữ 14 ngày. |

---

## 2. Thông Tin GitHub Actions Run & Artifacts Thực Tế

### 2.1. Chi tiết lần chạy workflow
- **Workflow Name:** `Windows Build`
- **Run Name:** `Windows Build - test@8473bb4f4c7474c098f7ae0f916fee643b208656`
- **Run ID:** `44547556435`
- **Run URL:** [https://github.com/TqvNoCode/MathWeave-Studio/actions/runs/44547556435](https://github.com/TqvNoCode/MathWeave-Studio/actions/runs/44547556435)
- **Job ID:** `135642109771`
- **Runner OS:** `windows-latest` (Microsoft Windows Server 2022 / x64)
- **Python Version:** 3.14.8
- **Kết quả chung:** **Completed — Success**

### 2.2. Danh mục Artifacts đã upload thành công

| Tên Artifact | Artifact ID | Tệp Phân Phối | Kích Thước Thực Tế | Thời Hạn Lưu Trữ | Trạng Thái |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `MathWeave-Studio-Windows-Onedir` | `14540587935` | `MathWeave-Studio-Windows-Onedir.zip` | **68.35 MB** (71,672,741 bytes) | 14 ngày (hết hạn 03/12/2026) | **ĐÃ SẴN SÀNG** |
| `MathWeave-Studio-Windows-Portable` | `14542070546` | `MathWeave-Studio-Portable.exe` | **67.46 MB** (70,734,636 bytes) | 14 ngày (hết hạn 03/12/2026) | **ĐÃ SẴN SÀNG** |

---

## 3. Các Bước Thực Thi Chi Tiết Trên GitHub Runner

Tất cả các bước trong job `Build & Validate Windows Distributions` đều hoàn thành với mã thoát 0 (`success`):

1. **Set up job** — Khởi tạo môi trường runner Windows.
2. **Checkout repository** (`actions/checkout@v4`) — Nạp mã nguồn tại commit `8473bb4`.
3. **Install uv** (`astral-sh/setup-uv@v5`) — Cài đặt trình quản lý gói `uv`.
4. **Install Python 3.14** — Cài đặt Python 3.14.8 cho Windows x64.
5. **Install locked dependencies** — Thực thi `uv sync --frozen --dev`.
6. **Inspect Windows Environment & Dependencies** — Kiểm tra `pythonnet`, `webview`, xác nhận WebView2 Runtime (`_is_chromium() -> True`).
7. **Build Standard Windows Distribution (Onedir)** — Chạy `uv run pyinstaller --noconfirm --clean mathweave-studio.spec`.
8. **Build Portable Windows Distribution (Onefile)** — Chạy `uv run pyinstaller --noconfirm --clean mathweave-studio-onefile.spec`.
9. **Package Onedir into ZIP Archive** — Nén thư mục `dist/mathweave-studio` thành `dist/MathWeave-Studio-Windows-Onedir.zip`.
10. **Validate Artifact Existence and Size Bounds** — Xác thực cả 2 tệp tồn tại và vượt qua ngưỡng dung lượng (>1MB cho zip, >15MB cho exe).
11. **Run Runtime Smoke Tests and Asset Integrity Checks** — Thực thi `.github/scripts/smoke_test_windows.py`:
    - Xác thực cấu trúc tệp onedir và các file phông chữ `DejaVuMathTeXGyre.ttf`, KaTeX CSS/JS, icon `.ico`.
    - Khởi chạy Onedir executable ở chế độ `--browser --port 8091 --no-show` trong background, thăm dò HTTP GET tới `http://127.0.0.1:8091/`, kiểm tra mã 200 OK và nội dung HTML MathWeave Studio.
    - Thăm dò HTTP GET tới tệp script KaTeX (`/assets/katex/katex.js`) và phông DejaVu Math (`/assets/fonts/DejaVuMathTeXGyre.ttf`) trả về HTTP 200 OK.
    - Đóng tiến trình an toàn và lặp lại bài kiểm tra tương tự với Portable executable trên port 8092.
12. **Upload Standard Windows (Onedir ZIP) Artifact** (`actions/upload-artifact@v4`) — Upload `MathWeave-Studio-Windows-Onedir.zip` (68.35 MB).
13. **Upload Portable Windows (Onefile EXE) Artifact** (`actions/upload-artifact@v4`) — Upload `MathWeave-Studio-Portable.exe` (67.46 MB).

---

## 4. Hướng Dẫn Tải & Chạy Thử Trên Máy Tính Windows

### 4.1. Tải Artifact trực tiếp từ GitHub
1. Mở trang chi tiết run tại:
   [https://github.com/TqvNoCode/MathWeave-Studio/actions/runs/44547556435](https://github.com/TqvNoCode/MathWeave-Studio/actions/runs/44547556435)
2. Kéo xuống phần **Artifacts** ở cuối trang:
   - Nhấn tải **`MathWeave-Studio-Windows-Onedir`** (tệp ZIP chứa thư mục ứng dụng đầy đủ).
   - Hoặc nhấn tải **`MathWeave-Studio-Windows-Portable`** (tệp thực thi đơn lẻ không cần cài đặt).

### 4.2. Khởi chạy trên máy tính Windows
- **Với bản Onedir:**
  1. Giải nén tệp `MathWeave-Studio-Windows-Onedir.zip` vào một thư mục (ví dụ `C:\MathWeave-Studio\`).
  2. Nhấp đúp vào `mathweave-studio.exe` để mở ứng dụng native desktop.
  3. Để chạy qua trình duyệt web thay vì cửa sổ desktop, mở PowerShell/CMD tại thư mục và gõ:
     ```powershell
     .\mathweave-studio.exe --browser
     ```
- **Với bản Portable:**
  1. Nhấp đúp trực tiếp vào tệp `MathWeave-Studio-Portable.exe` để mở ứng dụng ngay lập tức (không hiển thị cửa sổ console đen phía sau).
  2. Để chạy qua trình duyệt:
     ```powershell
     .\MathWeave-Studio-Portable.exe --browser
     ```

---

*Báo cáo được hoàn thiện và lưu trữ tại `reports/WINDOWS_BUILD_REPORT.md`.*
