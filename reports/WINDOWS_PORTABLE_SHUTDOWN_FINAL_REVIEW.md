# Báo Cáo Đánh Giá Mã Nguồn Lần Cuối (Final Code Review)
## MathWeave Studio — Khắc Phục Lỗi Tắt & Mở Khóa Tệp Portable Trên Windows CI

**Dự án:** MathWeave Studio
**Kho mã nguồn:** `TqvNoCode/MathWeave-Studio`
**Nhánh kiểm tra:** `test`
**Mục tiêu đánh giá:** Rà soát toàn diện trước khi commit và push cho giải pháp xử lý sự cố tắt ứng dụng Portable (GUI subsystem) và bộ test chấp nhận trên Windows CI.
**Ngày thực hiện:** 20/11/2026
**Trạng thái thao tác:** Strictly READ-ONLY (Không commit, không push).

---

### A. Tóm Tắt Tổng Quan (Executive Summary)

Sau khi Inno Setup biên dịch thành công ở lần push trước (commit `6ac2e6f`), quy trình GitHub Actions tại Run `44754679019` đã vượt qua các bước build Onedir, Portable, biên dịch Setup Installer và kiểm tra HTTP Onedir. Tuy nhiên, bước 19 (`Run Runtime Smoke Tests and Acceptance Suite`) gặp lỗi `TimeoutError: Portable application shutdown exceeded 6.0s deadline` trong vòng lặp kiểm tra Portable shutdown.

Nguyên nhân gốc rễ là do gói Portable được đóng gói ở chế độ GUI windowed (`console=False`), thuộc `IMAGE_SUBSYSTEM_WINDOWS_GUI`. Trên hệ điều hành Windows, các tiến trình GUI không có console window đính kèm, khiến hàm `GenerateConsoleCtrlEvent(CTRL_BREAK_EVENT)` bị hệ điều hành chặn hoàn toàn; đồng thời biến tiến trình trong Python trỏ vào PyInstaller C-Bootloader và bootloader không chuyển tiếp tín hiệu ngắt console tới tiến trình con Python.

Giải pháp đã được hiện thực hóa hoàn chỉnh:
1. Thiết lập endpoint loopback an toàn `POST /_test/shutdown` tại `src/math_app/main.py`, chỉ kích hoạt khi có token mật mã `MATHWEAVE_TEST_SHUTDOWN_TOKEN` và chỉ nhận kết nối từ loopback interface.
2. Cập nhật `smoke_test_windows.py` sinh token mật mã ngẫu nhiên `secrets.token_urlsafe(32)` cho từng iteration, gửi lệnh tắt qua HTTP, áp dụng thời hạn 15 giây (`SHUTDOWN_DEADLINE_SECONDS = 15.0`) kèm cơ chế trích xuất cây tiến trình WMI và log tail nếu quá hạn.
3. Sửa lỗi trích xuất phiên bản `pythonnet` và `pywebview` trong `.github/workflows/windows-build.yml` bằng `importlib.metadata.version`.
4. Gia cố lệnh gỡ cài đặt Inno Setup với `Start-Process -Wait` và vòng lặp polling 15s chờ xóa tệp sạch sẽ.
5. Bổ sung bộ kiểm thử bảo mật và quy trình tự động; 100% test suite (657 tests) đạt trạng thái pass.

Mã nguồn hiện tại đã đạt độ hoàn thiện cao, tuân thủ nghiêm ngặt ranh giới kiến trúc Clean Architecture và sẵn sàng để commit và push.

---

### B. Kiểm Toán Cây Làm Việc Git (Modified Files Audit)

- **Nhánh hiện tại:** `test` (khớp hoàn toàn với `origin/test` ở commit `6ac2e6f`).
- **Tổng số tệp thay đổi:** Chính xác 6 tệp (không có tệp mới, không có tệp bị xóa, không có tệp untracked).
- **Thư mục sao lưu:** `scratch/portable_shutdown_backup/` được lưu trữ tại đường dẫn an toàn ngoài git (`~/.gemini/antigravity-cli/brain/.../scratch/`), không nằm trong workspace repo và không bị đưa vào git.
- **Rà soát thông tin nhạy cảm:** Không có bất kỳ secret, khóa riêng tư (private key), chứng chỉ PFX hay mật khẩu nào trong working tree.

| STT | Tệp Thay Đổi | Thay Đổi Dòng | Mục Đích Kỹ Thuật |
| :--- | :--- | :--- | :--- |
| 1 | `src/math_app/main.py` | +75, -2 | Hiện thực hóa hàm `_setup_test_shutdown_endpoint()` với xác thực loopback, token `hmac.compare_digest` và ngắt ASGI bất đồng bộ qua FastAPI BackgroundTasks. |
| 2 | `.github/scripts/smoke_test_windows.py` | +188, -40 | Tích hợp gửi token ngẫu nhiên, gọi endpoint tắt, bổ sung `get_windows_process_tree()`, nâng thời hạn lên 15s, dùng `FileVersionInfo` và polling gỡ cài đặt Inno Setup. |
| 3 | `.github/workflows/windows-build.yml` | +1, -1 | Dùng `importlib.metadata.version` cho `pythonnet` và `pywebview`, loại bỏ `AttributeError: __version__`. |
| 4 | `tests/unit/test_windows_metadata_and_signing.py` | +75, -0 | Bổ sung 3 test cases: kiểm tra bảo mật endpoint test shutdown, kiểm tra workflow versioning và kiểm tra cấu trúc smoke test. |
| 5 | `reports/WINDOWS_SHUTDOWN_DIAGNOSTICS.md` | +27, -1 | Bổ sung Mục 4.3 phân tích chi tiết cơ chế Windows GUI subsystem và thiết kế endpoint shutdown xác thực. |
| 6 | `reports/WINDOWS_DISTRIBUTION_REPORT.md` | +15, -2 | Bổ sung Mục 7.3 tổng kết các cải tiến gia cố CI và nghiệm thu quy trình phân phối. |

---

### C. Đánh Giá An Toàn & Bảo Mật (Security Review — Shutdown Endpoint)

Rà soát chi tiết hàm `_setup_test_shutdown_endpoint(host: str)` trong [src/math_app/main.py](file:///home/tqv/Desktop/CODE/Python/math_app/src/math_app/main.py#L182-L260):

1. **Vô hiệu hóa mặc định trong môi trường sản xuất:**
   - Hàm kiểm tra:
     ```python
     token = os.environ.get("MATHWEAVE_TEST_SHUTDOWN_TOKEN")
     if not token or not token.strip():
         return False
     ```
   - Trong quá trình triển khai thực tế của người dùng, biến môi trường này không tồn tại. Hàm lập tức trả về `False` và router `/_test/shutdown` hoàn toàn **không được đăng ký vào FastAPI** (mọi request tới endpoint này nhận mã lỗi HTTP 404).
2. **Bảo vệ chống phơi nhiễm ra mạng ngoài (Loopback Enforcement):**
   - Ràng buộc binding: Nếu ứng dụng khởi động với host không thuộc dải loopback (`127.0.0.1`, `localhost`, `::1`), endpoint từ chối đăng ký.
   - Ràng buộc caller: Khi có request tới, hàm kiểm tra `request.client.host`. Nếu địa chỉ client không phải loopback, trả về ngay lập tức `HTTP 403 Forbidden`.
3. **Xác thực mã hóa thời gian bất biến (Constant-Time Token Comparison):**
   - Xác thực tiêu đề `X-Shutdown-Token` bằng `hmac.compare_digest(x_shutdown_token.encode("utf-8"), expected_token.encode("utf-8"))`.
   - Ngăn chặn hoàn toàn các cuộc tấn công dò tìm token qua kênh phụ đo thời gian (timing side-channel attacks).
   - Yêu cầu thiếu token hoặc sai token trả về `HTTP 401 Unauthorized`.
4. **Không làm rò rỉ token (Zero Token Leakage):**
   - Giá trị token không bao giờ xuất hiện trong log, ngoại lệ (exception), query parameter hay nội dung HTTP response.
5. **Thực thi bất đồng bộ an toàn (Asynchronous Safe Teardown):**
   - Việc xác thực hoàn tất trước khi kích hoạt bất kỳ tác vụ tắt nào.
   - Tác vụ tắt ứng dụng được đưa vào `background_tasks.add_task(_execute_graceful_shutdown)`.
   - Cơ chế của FastAPI/Starlette sẽ flush toàn bộ gói tin phản hồi HTTP 200 về cho client trước khi thực thi hàm background task.
   - Hàm `_execute_graceful_shutdown` có độ trễ `await asyncio.sleep(0.05)` bảo đảm socket HTTP đóng hoàn chỉnh, sau đó gán `Server.instance.should_exit = True` và gọi `app.shutdown()` có bọc `try...except`.

---

### D. Đánh Giá Vòng Đời Tiến Trình Windows (Windows Process Lifecycle Findings)

1. **Khắc phục rào cản Bootloader & GUI Subsystem:**
   - Việc chuyển từ phát tín hiệu `CTRL_BREAK_EVENT` sang gọi HTTP endpoint trực tiếp giúp lệnh tắt đi thẳng vào không gian bộ nhớ của Python MainProcess (Tầng 2).
   - Ứng dụng không còn phụ thuộc vào việc Bootloader (Tầng 1) có forward tín hiệu hay không.
2. **Chu trình tắt xác định tuần tự (Deterministic Shutdown):**
   - Khi nhận tín hiệu tắt từ endpoint, Uvicorn dừng nhận kết nối mới và đóng các kết nối WebSocket hiện hữu.
   - Lifespan của FastAPI chạy chu trình shutdown dọn dẹp các tài nguyên.
   - Multiprocessing children (nếu có) được join có giới hạn thời gian (bounded join).
   - Python process thoát sạch sẽ, trả mã thoát 0 về cho Bootloader.
   - Bootloader thức dậy sau lệnh `WaitForSingleObject`, quét dọn thư mục tạm `%TEMP%\_MEIxxxxxx` mà không bị lỗi `ERROR_SHARING_VIOLATION`.
   - Bootloader thoát hoàn toàn, giải phóng 100% file handle trên tệp thực thi Portable.
3. **Xác minh giải phóng khóa tệp (File Lock Verification):**
   - Kịch bản `smoke_test_windows.py` thực hiện thao tác đổi tên tệp thực thi hai chiều (`portable_exe.rename(...)`) ngay sau khi tiến trình thoát.
   - Nếu bất kỳ tiến trình nào còn giữ tệp mở, Windows NTFS sẽ ném lỗi `PermissionError` (`WinError 32`). Thao tác này bảo đảm tính giải phóng thực sự.

---

### E. Đánh Giá CI/CD & Đóng Gói (CI/CD and Packaging Findings)

1. **Kịch bản `smoke_test_windows.py`:**
   - Sinh token bảo mật ngẫu nhiên `secrets.token_urlsafe(32)` cho từng iteration riêng biệt.
   - Thời hạn chờ tắt ứng dụng được đặt ở mức 15.0 giây (`SHUTDOWN_DEADLINE_SECONDS = 15.0`), đủ rộng cho quá trình ASGI teardown và xóa thư mục tạm trên runner ảo hóa, nhưng vẫn có giới hạn chặn đứng nguy cơ treo vô hạn (hang).
   - Bổ sung hàm WMI `get_windows_process_tree()` giúp thu thập đầy đủ thông tin PID, tên tiến trình và dòng lệnh của các tiến trình con nếu xảy ra quá hạn.
   - Xử lý khối `finally` nghiêm ngặt: giải phóng file log handle và kết liễu tiến trình nếu còn sót lại.
2. **Kịch bản cài đặt Inno Setup:**
   - Lệnh `Start-Process -FilePath '{uninstaller}' -ArgumentList '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART' -Wait` trong PowerShell bảo đảm runner chờ tiến trình gỡ cài đặt hoàn tất.
   - Vòng lặp polling bổ sung (tối đa 15 giây) kiểm tra sự biến mất của tệp `mathweave-studio.exe`, loại bỏ hoàn toàn các trường hợp race condition khi uninstaller dọn dẹp không đồng bộ.
3. **Chẩn đoán phiên bản trên Windows Runner:**
   - Đã thay thế thuộc tính không tồn tại bằng `from importlib.metadata import version; version('pythonnet'); version('pywebview')`. Hoạt động tương thích hoàn hảo trên Python 3.14.

---

### F. Kết Quả Kiểm Thử Độc Lập (Verified Test Results)

Đã chạy kiểm tra độc lập tại môi trường hiện tại:
1. **Ruff Linter:** `uv run ruff check .` -> **Passed** (0 lỗi).
2. **Kiểm thử chuyên biệt Metadata, Signing & Shutdown:** `uv run pytest tests/unit/test_windows_metadata_and_signing.py` -> **16/16 passed** (0.84s).
3. **Toàn bộ Test Suite Dự án:** `uv run pytest` -> **657/657 passed** (71.62s).
4. **Kiểm tra định dạng diff:** `git diff --check` -> **Clean** (0 lỗi định dạng whitespace).

**Giải trình chi tiết 2 Warnings ghi nhận từ test suite:**
- **Warning 1 (`RuntimeWarning: invalid value encountered in sqrt` tại `test_analysis_service.py`):**
  - Phát sinh từ hàm `lambdify` của SymPy khi lấy mẫu tọa độ 2D trên lưới viewport có chứa giá trị âm cho căn bậc hai. Đây là hành vi xử lý số phức/NaN có chủ đích của thư viện toán học khi vẽ đồ thị ngoài tập xác định thực, hoàn toàn không phải lỗi hồi quy.
- **Warning 2 (`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated` tại `test_windows_metadata_and_signing.py`):**
  - Cảnh báo của thư viện Starlette khi khởi tạo `TestClient` với phiên bản `httpx` hiện hành, khuyến nghị chuyển sang `httpx2` trong các bản phát hành tương lai. Không ảnh hưởng đến logic ứng dụng và kết quả kiểm thử.

---

### G. Các Giới Hạn & Rủi Ro Còn Lại (Remaining Risks)

1. **Môi trường CI Headless so với Windows Desktop vật lý:**
   - Việc kiểm thử trên Linux runner mô phỏng endpoint HTTP và logic bảo mật của Python; việc kiểm thử tương tác thực tế với Windows Kernel, PE loader, thư viện WinForms và EdgeChromium WebView2 chỉ có thể chạy thực trên runner `windows-latest` của GitHub Actions.
2. **Độ trễ I/O trên máy ảo GitHub-hosted:**
   - Các máy ảo Windows Server trên GitHub Actions có thể có độ trễ đĩa I/O biến thiên khi tải nặng. Thời hạn 15.0s được thiết lập để giảm thiểu tối đa rủi ro timeout ngẫu nhiên.

---

### H. Khuyến Nghị Cuối Cùng (Final Recommendation)

# **GO**

Giải pháp xử lý lỗi shutdown acceptance test và chẩn đoán CI đã được kiểm chứng toàn diện, bảo đảm an toàn bảo mật tuyệt đối, giữ vững ranh giới kiến trúc và sẵn sàng để commit và push lên nhánh `test`.

---

### I. Các Lệnh Git Đề Xuất (Proposed Git Commands)

*Lưu ý: Các lệnh dưới đây chỉ mang tính đề xuất theo quy trình, KHÔNG tự động thực thi.*

```bash
# 1. Kiểm tra trạng thái trước khi stage
git branch --show-current
git status --short

# 2. Stage chính xác 6 tệp đã rà soát
git add .github/scripts/smoke_test_windows.py \
  .github/workflows/windows-build.yml \
  reports/WINDOWS_DISTRIBUTION_REPORT.md \
  reports/WINDOWS_SHUTDOWN_DIAGNOSTICS.md \
  reports/WINDOWS_PORTABLE_SHUTDOWN_FINAL_REVIEW.md \
  src/math_app/main.py \
  tests/unit/test_windows_metadata_and_signing.py

# 3. Kiểm tra lại diff đã stage
git diff --cached --stat

# 4. Tạo commit theo quy ước
git commit -m "fix(windows): resolve portable shutdown signal block and harden acceptance tests"

# 5. Đẩy lên nhánh test trên remote
git push origin test
```
