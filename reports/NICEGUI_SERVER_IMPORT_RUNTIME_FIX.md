# Báo Cáo Kỹ Thuật: Khắc Phục Lỗi Nhập Thư Viện NiceGUI Khi Phân Phối Trên Windows
## MathWeave Studio — Sửa Lỗi `ImportError: cannot import name 'Server' from 'nicegui'`

**Dự án:** MathWeave Studio
**Mã kho nguồn:** `TqvNoCode/MathWeave-Studio`
**Nhánh:** `test`
**Ngày thực hiện:** 21/11/2026
**Trạng thái kiểm thử:** 100% Passed (663/663 test cases đạt chuẩn)
**Trạng thái Git:** Sẵn sàng nghiệm thu (Không tự động commit, không push)

---

## 1. Tóm Tắt Sự Cố & Nguyên Nhân Gốc Rễ (Root Cause Analysis)

### 1.1. Hiện tượng ghi nhận
Sau khi quy trình GitHub Actions hoàn tất việc biên dịch và đóng gói bộ cài đặt Inno Setup cũng như tệp thực thi Portable, người dùng cài đặt ứng dụng trên máy tính Windows thực tế và khởi chạy từ shortcut màn hình nền hoặc Start Menu thì gặp lỗi:

```text
Unhandled exception in script 'run'

ImportError: cannot import name 'Server' from 'nicegui'

Traceback:
  File "run.py", line 26, in <module>
  File "math_app\main.py", line 351, in main

ImportError: cannot import name 'Server' from 'nicegui'
```

### 1.2. Vị trí mã nguồn lỗi chính xác
Tại [src/math_app/main.py](file:///home/tqv/Desktop/CODE/Python/math_app/src/math_app/main.py), dòng 350–352:
```python
if use_native:
    from nicegui import app, Server  # <-- Lỗi cú pháp import
```

### 1.3. Tại sao lỗi xảy ra trong tệp đóng gói (Frozen Executable)?
1. **Kiến trúc module của NiceGUI 3.18.0:**
   - Trong NiceGUI phiên bản `3.18.0` (được khóa trong `uv.lock`), lớp `Server` (kế thừa từ `uvicorn.Server`) nằm trong submodule `nicegui.server`.
   - Tệp khởi tạo module gốc `nicegui/__init__.py` chỉ nạp module con `server` (`from . import server`), tuyệt đối **không** re-export lớp `Server` lên không gian tên cấp cao nhất (`__all__` hoặc `nicegui.Server`).
   - Lệnh `from nicegui import Server` ném ngoại lệ `ImportError` ở mọi môi trường Python (cả mã nguồn dev lẫn gói PyInstaller).
2. **Khởi động thực tế khác biệt với kịch bản kiểm thử CI:**
   - Khi người dùng khởi chạy ứng dụng Windows từ shortcut (hoặc double-click vào `mathweave-studio.exe` / `MathWeave-Studio-Portable.exe`), không có tham số dòng lệnh nào được truyền vào.
   - Hàm `resolve_startup_mode()` trên Windows phân giải thành `StartupMode.NATIVE`, dẫn đến `use_native = True`.
   - Khối `if use_native:` được thực thi ngay trong hàm `main()`, trước khi `ui.run()` được gọi. Câu lệnh `from nicegui import app, Server` lập tức kích hoạt lỗi và làm dừng toàn bộ ứng dụng.
3. **Tại sao GitHub Actions Windows CI vượt qua thành công?**
   - Kịch bản kiểm thử tự động [.github/scripts/smoke_test_windows.py](file:///home/tqv/Desktop/CODE/Python/math_app/.github/scripts/smoke_test_windows.py) đã khởi chạy tệp thực thi với cờ `--browser --port <port> --no-show`.
   - Cờ `--browser` khiến `resolve_startup_mode()` trả về `StartupMode.BROWSER`, đặt `use_native = False`.
   - Do đó, khối `if use_native:` (dòng 350–369) bị **bỏ qua hoàn toàn** trong mọi bài test của CI, che giấu lỗi nghiêm trọng này.

---

## 2. Lựa Chọn Giải Pháp API & Đánh Giá Tính Tương Thích (Selected API & Compatibility)

### 2.1. Phân tích API công khai của NiceGUI
Chúng tôi đã kiểm tra mã nguồn thực tế của lớp `App` trong `nicegui/app/app.py`:
```python
def shutdown(self) -> None:
    """Shut down NiceGUI.

    This will programmatically stop the server.
    """
    if self.native.main_window:
        self.native.main_window.destroy()
    if self.config.reload or Server.instance.config.should_reload:
        os.kill(os.getppid(), getattr(signal, 'CTRL_C_EVENT' if platform.system() == 'Windows' else 'SIGINT'))
    else:
        Server.instance.should_exit = True
```
**Nhận định kỹ thuật:**
- Phương thức `app.shutdown()` là **API công khai chính thức (Official Supported API)** của NiceGUI để tắt ứng dụng có trật tự.
- Bên trong phương thức này, NiceGUI đã tự động kiểm tra và tiêu hủy cửa sổ native `self.native.main_window.destroy()` cũng như gán `Server.instance.should_exit = True`.
- Do đó, việc tự viết mã can thiệp trực tiếp vào `Server.instance` là không cần thiết và mang tính phụ thuộc vào triển khai nội bộ (internal implementation dependency).

### 2.2. Chiến lược xử lý chuẩn hóa
1. **Loại bỏ nhập trực tiếp:** Xóa hoàn toàn câu lệnh `from nicegui import app, Server` ở đầu khối `if use_native:`.
2. **Ưu tiên API công khai:** Tại bộ điều phối đóng cửa sổ native (`_on_native_window_closed`) và tác vụ tắt nền (`_execute_graceful_shutdown`), gọi `app.shutdown()` làm phương thức chính.
3. **Duy trì lớp phòng thủ thứ cấp an toàn:** Nhằm đảm bảo tương thích tối đa với các trường hợp ngoại lệ hiếm gặp, bước can thiệp trực tiếp `from nicegui.server import Server` được bọc độc lập trong khối `try...except Exception: pass`, đảm bảo không bao giờ gây unhandled exception.

---

## 3. Chi Tiết Các Tệp Đã Thay Đổi (Files Modified)

### 3.1. `src/math_app/main.py`
- Xóa bỏ dòng nhập lỗi `from nicegui import app, Server`.
- Chuẩn hóa thứ tự điều phối tắt: Gọi `app.shutdown()` trước, sau đó fallback sang `Server.instance.should_exit = True` (nếu cần) có bọc ngoại lệ an toàn.

```diff
--- a/src/math_app/main.py
+++ b/src/math_app/main.py
@@ -226,6 +226,10 @@ def _setup_test_shutdown_endpoint(host: str) -> bool:
             import asyncio

             await asyncio.sleep(0.05)
+            try:
+                app.shutdown()
+            except Exception:
+                pass
             try:
                 from nicegui.server import Server

@@ -233,10 +237,6 @@ def _setup_test_shutdown_endpoint(host: str) -> bool:
                     Server.instance.should_exit = True
             except Exception:
                 pass
-            try:
-                app.shutdown()
-            except Exception:
-                pass

         background_tasks.add_task(_execute_graceful_shutdown)

@@ -348,17 +348,17 @@ def main() -> None:
     _setup_test_shutdown_endpoint(DEFAULT_HOST)

     if use_native:
-        from nicegui import app, Server
-
         def _on_native_window_closed(*_args: Any, **_kwargs: Any) -> None:
             """Proactive graceful shutdown coordinator when desktop window closes."""
             try:
-                if hasattr(Server, "instance") and Server.instance is not None:
-                    Server.instance.should_exit = True
+                app.shutdown()
             except Exception:
                 pass
             try:
-                app.shutdown()
+                from nicegui.server import Server
+
+                if hasattr(Server, "instance") and Server.instance is not None:
+                    Server.instance.should_exit = True
             except Exception:
                 pass
```

### 3.2. `.github/scripts/smoke_test_windows.py`
- Bổ sung bước xác thực sớm việc nạp thành công các API cốt lõi của NiceGUI (`app`, `ui`) trong hàm `check_native_backend_environment()`.

### 3.3. `tests/unit/presentation/test_nicegui_api_and_shutdown_compatibility.py` (Mới)
- Bổ sung 6 ca kiểm thử hồi quy tự động nhằm ngăn chặn tái diễn lỗi import và bảo đảm vòng đời tắt ứng dụng.

### 3.4. Cập nhật báo cáo kỹ thuật liên quan
- `reports/WINDOWS_SHUTDOWN_DIAGNOSTICS.md` (bổ sung mục 4.4).
- `reports/WINDOWS_DISTRIBUTION_REPORT.md` (bổ sung mục 7.4).

---

## 4. Kết Quả Kiểm Thử Chất Lượng (Quality Assurance & Test Results)

### 4.1. Bộ kiểm thử hồi quy NiceGUI API & Shutdown
Chạy lệnh: `uv run pytest tests/unit/presentation/test_nicegui_api_and_shutdown_compatibility.py`
```text
============================== test session starts ==============================
collected 6 items

tests/unit/presentation/test_nicegui_api_and_shutdown_compatibility.py ...... [100%]

=============================== 6 passed in 0.36s ===============================
```
- ✅ `test_nicegui_exports_supported_public_apis`: Xác nhận `app.shutdown` tồn tại và hợp lệ.
- ✅ `test_nicegui_does_not_export_server_at_top_level`: Xác nhận `from nicegui import Server` bị chặn đúng theo thiết kế của NiceGUI.
- ✅ `test_nicegui_server_submodule_contains_server_class`: Xác nhận `from nicegui.server import Server` hoạt động chuẩn.
- ✅ `test_no_invalid_nicegui_server_imports_in_source_tree`: Quét toàn bộ thư mục `src/`, xác nhận không còn bất kỳ câu lệnh nhập lỗi nào.
- ✅ `test_on_native_window_closed_handler_executes_safely`: Xác nhận hàm đóng cửa sổ desktop gọi `app.shutdown()` an toàn.
- ✅ `test_execute_graceful_shutdown_task_executes_safely`: Xác nhận tác vụ tắt nền chạy trơn tru qua `asyncio`.

### 4.2. Bộ kiểm thử siêu dữ liệu PE & Chữ ký số
Chạy lệnh: `uv run pytest tests/unit/test_windows_metadata_and_signing.py`
```text
============================== test session starts ==============================
collected 16 items

tests/unit/test_windows_metadata_and_signing.py ................ [100%]

======================== 16 passed, 1 warning in 0.89s =========================
```

### 4.3. Toàn bộ Test Suite của dự án
Chạy lệnh: `uv run pytest`
```text
============================== test session starts ==============================
collected 663 items

================== 663 passed, 2 warnings in 70.91s (0:01:10) ==================
```
- **Tổng số ca kiểm thử:** 663 tests.
- **Kết quả:** 663 Passed, 0 Failed, 0 Error (100% tỷ lệ vượt qua).

### 4.4. Kiểm tra mã nguồn & Định dạng
Chạy lệnh: `uv run ruff check .`
```text
All checks passed!
```
Chạy lệnh: `git diff --check` (Không có lỗi trailing whitespace hay định dạng).

---

## 5. Khả Năng Tương Thích Của Bộ Đóng Gói (Packaging Compatibility)

- **PyInstaller Analysis Hook:** Cả hai tệp spec ([mathweave-studio.spec](file:///home/tqv/Desktop/CODE/Python/math_app/mathweave-studio.spec#L26) và [mathweave-studio-onefile.spec](file:///home/tqv/Desktop/CODE/Python/math_app/mathweave-studio-onefile.spec#L27)) đều sử dụng `collect_submodules("nicegui")`.
- **Xác thực tự động:** Kiểm tra `collect_submodules("nicegui")` thu thập đầy đủ 266 submodules của NiceGUI, bao gồm cả `nicegui.server` và `nicegui.app`.
- Tệp thực thi sau khi sửa lỗi đảm bảo có đầy đủ các module cần thiết trong môi trường đông kết (`frozen`), loại bỏ hoàn toàn nguy cơ thiếu phụ thuộc khi chạy offline.

---

## 6. Giới Hạn Còn Lại & Khuyến Nghị (Remaining Risks & Recommendations)

1. **Khuyến nghị kiểm thử môi trường Windows Runner:**
   - Khi chạy workflow GitHub Actions trên `windows-latest`, cần đảm bảo bước smoke test không chỉ kiểm tra với `--browser` mà còn bao quát cả việc kiểm tra khả năng nạp module ở chế độ mặc định.
2. **Khuyến nghị GO / NO-GO:**
   - **Đánh giá:** **GO**.
   - Mã nguồn đã khắc phục đúng nguyên nhân gốc rễ, tuân thủ nguyên tắc Clean Architecture, 100% test suite đạt chuẩn và không tạo ra bất kỳ thay đổi kiến trúc không cần thiết nào.
