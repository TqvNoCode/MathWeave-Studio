# MathWeave Studio v0.1.1 — Initial Windows Distribution Release

## English

MathWeave Studio v0.1.1 marks the first official production release featuring native Windows desktop distributions, robust lifecycle management, and independent mathematical verification.

### Core Features
- **Step-by-Step Pedagogical Derivation:** Transparent rule breakdown for limits, differentiation (chain, product, quotient, trigonometric rules), and integrals with expandable substeps.
- **Symbolic Computation & Dual-Layer Verification:** Exact algebra powered by SymPy cross-checked against reference symbolic invariants and multi-point numerical probing.
- **Calculus & Differential Equations (ODEs):** First-order linear and separable ODEs, exact differential equations with integrating factors, second-order constant-coefficient ODEs with discriminant analysis, Cauchy IVPs, reduction of order, and Wronskian determinant auditing.
- **Linear Algebra:** Matrix determinants, inverses, rank, Gaussian elimination (REF/RREF), matrix operations, and linear system solving.
- **Interactive Visualization:** Interactive 2D plotting with automatic singularity/asymptote detection, standardized 3D surface visualization, and academic variation tables (*bảng biến thiên*).

### Windows Improvements & Stability Hardening
- **Native Desktop Startup:** Seamless native desktop application execution powered by Microsoft Edge WebView2.
- **Portable Standalone Executable:** Single-file distribution (`MathWeave-Studio-Portable.exe`) requiring zero installation or environment setup.
- **Windows Setup Installer:** Standard installer wizard (`MathWeave-Studio-Setup.exe`) with Start Menu and Desktop shortcuts and full clean uninstallation support.
- **Fixed NiceGUI Runtime Import Failure:** Resolved runtime `ImportError: cannot import name 'Server' from 'nicegui'` by migrating to public NiceGUI APIs and safe shutdown lifecycles.
- **Idempotent Graceful Shutdown:** Eliminated hanging background processes on window closure through coordinated SIGINT/SIGTERM handlers and thread disposal.
- **Hardened CI & Smoke Tests:** Automated Windows runner acceptance testing validating real native execution, binary metadata, and SHA-256 integrity.

### Downloads
- 📦 **Windows Portable Executable:** [`MathWeave-Studio-Portable.exe`](https://github.com/TqvNoCode/MathWeave-Studio/releases/download/v0.1.1/MathWeave-Studio-Portable.exe)
- 💾 **Windows Installer:** [`MathWeave-Studio-Setup.exe`](https://github.com/TqvNoCode/MathWeave-Studio/releases/download/v0.1.1/MathWeave-Studio-Setup.exe)
- 🔒 **SHA-256 Checksums:** [`SHA256SUMS.txt`](https://github.com/TqvNoCode/MathWeave-Studio/releases/download/v0.1.1/SHA256SUMS.txt)

### System Requirements
- **Operating System:** Windows 10 / 11 (64-bit x64).
- **Runtime Component:** Microsoft Edge WebView2 Evergreen Runtime (pre-installed on Windows 11 and modern Windows 10).
- **No Python Installation Required:** All Python runtimes, dependencies, and math libraries are fully self-contained.

### Known Limitations
- Native desktop mode requires a graphical display session. For headless or remote environments, execute with the `--browser` flag.

---

## Tiếng Việt

Phiên bản MathWeave Studio v0.1.1 đánh dấu bản phát hành chính thức đầu tiên hỗ trợ đầy đủ các gói phân phối desktop native trên Windows, hoàn thiện quản lý vòng đời ứng dụng và bộ máy kiểm chuẩn toán học độc lập.

### Tính Năng Cốt Lõi
- **Phân rã từng bước sư phạm:** Hiển thị minh bạch quy tắc giải tích (đạo hàm hàm hợp, tích, thương, lượng giác, tích phân) kèm các bước con chi tiết.
- **Tính toán biểu tượng & Kiểm chuẩn 2 tầng:** Đại số chính xác tuyệt đối với SymPy, đối soát chéo độc lập bằng bất biến đại số và lấy mẫu số học đa điểm.
- **Giải tích & Phương trình vi phân (ODE):** Phương trình vi phân tuyến tính cấp 1, tách biến, vi phân toàn phần, thừa số tích phân, phương trình vi phân cấp 2 hệ số hằng, bài toán Cauchy, hạ bậc nghiệm và định thức Wronskian.
- **Đại số tuyến tính:** Định thức, ma trận nghịch đảo, khử Gauss/Gauss-Jordan, các phép toán ma trận và giải hệ phương trình tuyến tính.
- **Trực quan hóa tương tác:** Đồ thị hàm số 2D phát hiện điểm kỳ dị và tiệm cận đứng, đồ thị 3D không gian chuẩn hệ trục RGB và bảng biến thiên toán học chuẩn mực.

### Cải Tiến Trên Windows & Tối Ưu Độ Ổn Định
- **Giao diện Desktop Native:** Khởi chạy cửa sổ ứng dụng desktop mượt mà thông qua Microsoft Edge WebView2.
- **Bản Portable độc lập:** Tệp thực thi đơn lẻ (`MathWeave-Studio-Portable.exe`) chạy ngay không cần cài đặt.
- **Bộ cài đặt Windows Setup:** Trình cài đặt tiêu chuẩn (`MathWeave-Studio-Setup.exe`) tạo shortcut Start Menu và Desktop, hỗ trợ gỡ cài đặt sạch sẽ.
- **Khắc phục lỗi Import Server của NiceGUI:** Loại bỏ hoàn toàn lỗi `ImportError: cannot import name 'Server' from 'nicegui'`, chuẩn hóa phương thức đóng ứng dụng `app.shutdown()`.
- **Đóng ứng dụng mượt mà (Graceful Shutdown):** Xử lý triệt để hiện tượng tiến trình chạy ngầm sau khi đóng cửa sổ.
- **Tăng cường kiểm thử CI:** Tự động hóa kiểm thử nghiệm thu trên môi trường Windows GitHub Actions, xác thực metadata PE và tính toàn vẹn SHA-256.

### Tải Về
- 📦 **Bản Portable Windows:** [`MathWeave-Studio-Portable.exe`](https://github.com/TqvNoCode/MathWeave-Studio/releases/download/v0.1.1/MathWeave-Studio-Portable.exe)
- 💾 **Bộ Cài Đặt Windows:** [`MathWeave-Studio-Setup.exe`](https://github.com/TqvNoCode/MathWeave-Studio/releases/download/v0.1.1/MathWeave-Studio-Setup.exe)
- 🔒 **Mã Kiểm Tra SHA-256:** [`SHA256SUMS.txt`](https://github.com/TqvNoCode/MathWeave-Studio/releases/download/v0.1.1/SHA256SUMS.txt)

### Yêu Cầu Hệ Thống
- **Hệ điều hành:** Windows 10 / 11 (64-bit x64).
- **Thành phần phụ thuộc:** Microsoft Edge WebView2 Runtime (đã tích hợp sẵn trên Windows 11 và Windows 10 cập nhật).
- **Không cần cài đặt Python:** Toàn bộ runtime, thư viện toán học và phụ thuộc đã được đóng gói độc lập.
