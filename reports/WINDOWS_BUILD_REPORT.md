# Báo Cáo Triển Khai Build Windows & Trạng Thái Đối Soát Với GitHub — MathWeave Studio

**Dự án:** MathWeave Studio<br>
**Mục tiêu:** Xây dựng quy trình tự động hóa đóng gói Windows (Standard Onedir & Standalone Portable EXE) trên GitHub Actions với đầy đủ smoke test khởi động và kiểm tra tính toàn vẹn tài nguyên.<br>
**Nhánh thực hiện:** `test`<br>
**Ngày báo cáo:** 19/11/2026<br>

---

## 1. Bảng Đối Soát Trạng Thái Triển Khai (Status Reconciliation)

Nhằm đảm bảo tính minh bạch tuyệt đối giữa mã nguồn cục bộ (Local Working Tree) và kho lưu trữ từ xa trên GitHub (`origin/test`), bảng dưới đây phân định rõ trạng thái hiện tại của từng giai đoạn:

| Giai Đoạn / Hạng Mục | Trạng Thái | Chi Tiết |
| :--- | :--- | :--- |
| **1. Triển khai cục bộ (Implemented locally)** | **ĐÃ HOÀN THÀNH (100%)** | Đã sửa spec onedir, spec onefile, `main.py`, `startup.py`, `app.py`, viết script smoke test và file workflow. |
| **2. Commit cục bộ (Committed locally)** | **CHƯA COMMIT** | Các tệp đang ở trạng thái Unstaged / Untracked trên working tree của nhánh `test` nhằm tuân thủ quy tắc an toàn Git ("không tự ý commit/push khi chưa có phê duyệt"). |
| **3. Đẩy lên GitHub (Pushed to GitHub)** | **CHƯA PUSH** | Nhánh từ xa `origin/test` vẫn ở commit `23af50451d5052df20ecad0220871e7003aa2c56`, chưa nhận các tệp mới này. |
| **4. Thực thi trên GitHub Actions** | **CHƯA CHẠY** | Workflow `.github/workflows/windows-build.yml` chỉ có thể được GitHub Actions nhận diện và chạy sau khi code được commit và push lên `origin/test`. |
| **5. Artifacts đã upload** | **CHƯA CÓ TRÊN GITHUB** | Tệp `MathWeave-Studio-Windows-Onedir.zip` và `MathWeave-Studio-Portable.exe` sẽ được sinh ra và upload khi workflow chạy thành công trên GitHub runner. |

---

## 2. Giải Thích Sự Khác Biệt Giữa Local và Remote (`origin/test`)

Khi người dùng kiểm tra trực tiếp trên nhánh `origin/test` của GitHub và thấy:
1. `.github/workflows/windows-build.yml` chưa có trên GitHub.
2. `.github/scripts/smoke_test_windows.py` chưa có trên GitHub.
3. `mathweave-studio-onefile.spec` trên GitHub vẫn có `name="MathWeaveStudio-Beta"` và `console=True`.
4. `mathweave-studio.spec` trên GitHub chưa có `import sys`.
5. `main.py` trên GitHub chưa có `--port` / `MATHWEAVE_PORT` / fallback assets.

**Nguyên nhân:** Toàn bộ các thay đổi trên đã được hiện thực đầy đủ, chính xác tại máy cục bộ (local working tree). Tuy nhiên, theo nguyên tắc an toàn nghiêm ngặt:
> *"Never reset, clean, stash, force-push, rebase, merge, or modify main. Do not commit or push unless explicitly requested."*

Agent đã dừng lại sau khi hoàn thành việc chỉnh sửa mã nguồn cục bộ và chạy test cục bộ, không tự ý tạo commit hay push lên remote GitHub. Do đó, remote `origin/test` vẫn là trạng thái của commit trước đó.

---

## 3. Chi Tiết Danh Mục Tệp Đã Triển Khai Cục Bộ

### 3.1. Các tệp đã sửa đổi (Modified in Local Working Tree)
- **`mathweave-studio.spec`** (Standard Windows Onedir):
  - Bổ sung `import sys` tường minh tại đầu file spec.
  - Thu thập tài nguyên gói nội bộ `math_app`: `datas += collect_data_files("math_app")` (đảm bảo đầy đủ phông chữ `DejaVuMathTeXGyre.ttf`, KaTeX CSS/JS và templates).
  - Thu thập toàn diện backend pywebview và WebView2:
    ```python
    try:
        pkg_datas, pkg_binaries, pkg_hidden = collect_all("webview")
        datas += pkg_datas
        binaries += pkg_binaries
        hiddenimports += pkg_hidden
    except Exception:
        datas += collect_data_files("webview")
        binaries += collect_dynamic_libs("webview")
        hiddenimports += collect_submodules("webview")
    ```
  - Thu thập đầy đủ .NET interop DLLs (`pythonnet`, `clr_loader`, `Python.Runtime.dll`).
  - Bổ sung hidden imports cho ASGI server NiceGUI (`engineio.async_drivers.asgi`, `socketio.async_drivers.asgi`).
  - Cấu hình `name="mathweave-studio"`, `console=False`.

- **`mathweave-studio-onefile.spec`** (Portable Windows Standalone):
  - Đổi tên tệp thực thi đích từ `name="MathWeaveStudio-Beta"` thành:
    ```python
    name="MathWeave-Studio-Portable"
    ```
    (Trên Windows, PyInstaller tự động tạo tệp `MathWeave-Studio-Portable.exe`, khớp hoàn toàn với workflow và smoke test).
  - Đổi `console=True` thành:
    ```python
    console=False
    ```
    (Giúp ứng dụng Portable chạy trực tiếp cửa sổ GUI sạch sẽ, không bật kèm màn hình dòng lệnh console đen phía sau).
  - Bổ sung `import sys`, `datas += collect_data_files("math_app")`, `collect_all("webview")`, hidden imports ASGI.

- **`src/math_app/presentation/startup.py`**:
  - Bổ sung `DEFAULT_APP_PORT = 8080`.
  - Bổ sung hàm pure function `resolve_configured_port(argv, environ, default_port)` xử lý thứ tự ưu tiên: CLI `--port <PORT>` > Biến môi trường `MATHWEAVE_PORT` > Mặc định (8080).
  - Bổ sung hàm `resolve_assets_path()` tự động phân giải đường dẫn tài nguyên: ưu tiên `sys._MEIPASS / "assets"`, kế tiếp kiểm tra thư mục liền kề tệp thực thi (`exe_dir / "assets"` hoặc `exe_dir / "_internal" / "assets"` khi frozen), và fallback về thư mục phát triển.

- **`src/math_app/main.py`**:
  - Cập nhật `get_resource_path()` hỗ trợ phân giải tài nguyên khi frozen (`_MEIPASS` và `exe_dir / "_internal"`).
  - Sử dụng `resolve_configured_port()` để khởi tạo cổng mạng cho NiceGUI một cách linh hoạt, phục vụ trực tiếp cho smoke test tự động không bị tranh chấp port.

- **`src/math_app/presentation/app.py`**:
  - Sử dụng `resolve_assets_path()` để mount static files `/assets` an toàn trong mọi môi trường (dev, onedir, onefile).

- **`tests/unit/presentation/test_startup_mode.py`**:
  - Bổ sung 3 test cases chuyên biệt:
    1. `test_get_resource_path_development_and_frozen`: Xác thực hàm phân giải tài nguyên cho dev mode, MEIPASS mode, và adjacent executable mode.
    2. `test_resolve_assets_path_modes`: Xác thực phát hiện thư mục assets trong mọi chế độ.
    3. `test_resolve_configured_port_precedence_and_validation`: Xác thực thứ tự ưu tiên cấu hình port (mặc định, env var, invalid env var, CLI `--port`, invalid CLI arg).
  - Toàn bộ 17 unit tests trong module này đều passed 100%.

### 3.2. Các tệp mới tạo (Untracked Files in Local Working Tree)
- **`.github/workflows/windows-build.yml`**:
  - Workflow GitHub Actions chuyên biệt cho build Windows, không chạm vào `ci.yml`.
  - Chạy trên `windows-latest`, dùng `uv` cài Python 3.14, đồng bộ `uv sync --frozen --dev`.
  - Build bản Onedir (`mathweave-studio.spec`) -> nén thành `dist/MathWeave-Studio-Windows-Onedir.zip`.
  - Build bản Portable (`mathweave-studio-onefile.spec`) -> `dist/MathWeave-Studio-Portable.exe`.
  - Bước xác thực tính toàn vẹn: Kiểm tra file tồn tại, dung lượng tối thiểu (>1MB cho zip, >15MB cho exe).
  - Bước chạy smoke test: Thực thi `.github/scripts/smoke_test_windows.py`.
  - Bước upload: Sử dụng `actions/upload-artifact@v4` lưu trữ 14 ngày cho cả 2 bản (`MathWeave-Studio-Windows-Onedir` và `MathWeave-Studio-Windows-Portable`).

- **`.github/scripts/smoke_test_windows.py`**:
  - Kiểm tra môi trường Windows WebView2 (`_is_chromium()`).
  - Xác thực cấu trúc thư mục Onedir và các file tài nguyên bắt buộc:
    - `DejaVuMathTeXGyre.ttf`
    - `katex.js`
    - `katex.css`
    - `icon.ico`
  - Khởi chạy Onedir executable ở chế độ `--browser --port 8091`, thăm dò HTTP 200 tại `/`, kiểm tra nội dung HTML, kiểm tra tải static assets KaTeX và DejaVu font, sau đó kết thúc tiến trình an toàn.
  - Lặp lại quy trình smoke test cho Portable executable trên port 8092.

---

## 4. Kết Quả Kiểm Thử Cục Bộ (Local Verification)

```bash
# 1. Kiểm tra cú pháp và quy chuẩn mã nguồn
uv run ruff check .
# Kết quả: All checks passed! (0 lỗi)

# 2. Kiểm tra bộ unit tests presentation & startup mode
uv run pytest tests/unit/presentation/test_startup_mode.py
# Kết quả: 17 passed in 1.54s

# 3. Kiểm tra kịch bản smoke test với tham số trợ giúp
uv run python .github/scripts/smoke_test_windows.py --help
# Kết quả: Mã thoát 0, hiển thị usage hướng dẫn đầy đủ
```

---

## 5. Quy Trình Để Triển Khai Lên GitHub & Xác Nhận Build

Để quy trình trên GitHub Actions thực sự diễn ra và có kết quả kiểm chứng:
1. **Bước 1 (Phê duyệt từ người dùng):** Người dùng xác nhận cho phép commit các tệp đã sửa đổi và tạo mới trên nhánh `test`.
2. **Bước 2 (Commit & Push):**
   - Stage các tệp:
     - `mathweave-studio.spec`
     - `mathweave-studio-onefile.spec`
     - `src/math_app/main.py`
     - `src/math_app/presentation/app.py`
     - `src/math_app/presentation/startup.py`
     - `tests/unit/presentation/test_startup_mode.py`
     - `.github/workflows/windows-build.yml`
     - `.github/scripts/smoke_test_windows.py`
     - `reports/WINDOWS_BUILD_REPORT.md`
   - Tạo commit với thông điệp rõ ràng, ví dụ: `feat(ci): add windows onedir and portable build pipeline with smoke tests`.
   - Push lên remote: `git push origin test`.
3. **Bước 3 (Thực thi GitHub Actions):**
   - Workflow `Windows Build` sẽ tự động kích hoạt trên GitHub Actions tại nhánh `test`.
   - Người dùng hoặc agent có thể theo dõi tiến độ qua URL:
     `https://github.com/TqvNoCode/MathWeave-Studio/actions/workflows/windows-build.yml`
4. **Bước 4 (Nghiệm thu Artifacts):**
   - Chỉ khi workflow trên GitHub Actions hoàn thành màu xanh (Success), 2 artifacts `MathWeave-Studio-Windows-Onedir` và `MathWeave-Studio-Windows-Portable` mới chính thức có sẵn để tải về.

---

*Báo cáo được cập nhật và lưu trữ chính thức tại `reports/WINDOWS_BUILD_REPORT.md`.*
