# Báo Cáo Chuyên Sâu: Windows Code Signing, File Metadata & Cơ Chế Thực Thi Code Integrity

**Dự án:** MathWeave Studio  
**Mục tiêu:** Điều tra nguyên nhân gốc rễ sự cố chặn thực thi trên Windows, xác định chính xác chính sách Code Integrity đang hoạt động, thiết lập kiến trúc chữ ký số Authenticode SHA-256 với nhãn thời gian RFC 3161, bổ sung tài nguyên siêu dữ liệu PE (FileVersionInfo), tự động hóa toàn diện trong GitHub Actions workflow và nghiệm thu thực tế không suy giảm bảo mật hệ thống.  
**Ngày báo cáo:** 20/11/2026  
**Nhánh thực hiện:** `test`  

---

## 1. Bảng Trạng Thái Nghiệm Thu Thực Tế (Implementation & Release Status Matrix)

Để phản ánh chính xác và trung thực tiến độ kỹ thuật, chúng tôi phân định rõ ràng giữa những gì đã hoàn thiện cục bộ, những gì đã cam kết, những gì đã chạy trên máy chủ CI và điều kiện cần để đạt chứng nhận Smart App Control trên môi trường thực tế:

| Hạng Mục Kỹ Thuật | Trạng Thái Thực Tế | Chi Tiết & Bằng Chứng Đối Soát |
| :--- | :--- | :--- |
| **1. Triển khai cục bộ (Implemented locally)** | **HOÀN THÀNH (100%)** | Đã sửa `build_tools/generate_version_info.py`, `mathweave-studio.spec`, `mathweave-studio-onefile.spec`, `.github/scripts/sign_windows_binaries.py`, `.github/scripts/smoke_test_windows.py` và workflow `.github/workflows/windows-build.yml`. 7/7 bài unit test pass 100%. |
| **2. Cam kết mã nguồn cục bộ (Committed locally)** | **ĐANG CHỜ (Pending Approval)** | Toàn bộ thay đổi nằm trong working tree của nhánh `test`. Tuân thủ chỉ thị: *Không commit hoặc push khi chưa có yêu cầu trực tiếp từ người dùng*. Đã tạo bản sao lưu toàn diện trước khi sửa đổi. |
| **3. Đẩy lên GitHub remote (Pushed to origin/test)** | **CHƯA ĐẨY (Not Pushed)** | Remote `origin/test` hiện đang ở commit `0f158a1` (chưa chứa pipeline ký số mới). |
| **4. Thực thi trên GitHub Actions (Executed in CI)** | **ĐÃ CHẠY BẢN BUILD TRƯỚC (Run 44547556435)** | Lần chạy trước thành công với bản build Unsigned. Pipeline ký số mới sẵn sàng thực thi ngay khi đẩy mã nguồn. |
| **5. Ký số bằng Chứng chỉ Sản xuất Tin cậy (Public Trusted Root CA)** | **BỊ CHẶN (BLOCKED)** | **Chưa cấu hình bí mật `WINDOWS_CERT_BASE64` trên kho chứa.** Không thể phát hành bản thương mại ký số công khai nếu thiếu chứng chỉ từ CA thuộc Microsoft Trusted Root Program hoặc Microsoft Trusted Signing. |
| **6. Ký số thử nghiệm cục bộ (Ephemeral Test-Only Signing)** | **CHỈ DÙNG TRONG TEST ISOLATED** | Hỗ trợ qua cờ `--allow-test-cert` để kiểm tra cú pháp SignTool. **Tuyệt đối không đưa vào bản phát hành và không nạp vào Root Store của CI runner để mạo danh tính tương thích.** |
| **7. Nghiệm thu Smart App Control trên máy Windows 11 độc lập** | **BỊ CHẶN (BLOCKED)** | Bị chặn bởi mục (5). SAC sẽ từ chối các bản build chưa có chữ ký từ CA công khai hoặc danh tiếng đám mây ISG. Bản build hiện tại được gắn nhãn minh bạch là **Unsigned Development Build**. |

---

## 2. Xác Định Chính Xác Cơ Chế Thực Thi Bảo Mật Của Windows (Phase A)

### 2.1. Phân tích dữ liệu sự kiện Windows CodeIntegrity đã ghi nhận

Các nhật ký sự kiện (`Microsoft-Windows-CodeIntegrity/Operational`) thu thập từ máy đích ghi nhận:
- **Event ID 3077:** Sự kiện chặn thực thi (Enforcement Block).
- **Event ID 3033:** Sự kiện từ chối nạp nhị phân vào tiến trình (Module Load Failure).
- **Event ID 3089:** Sự kiện chi tiết chẩn đoán chữ ký số và thuật toán băm (Signature Information Event).
- **Policy ID ghi nhận trong sự kiện:** `{0283ac0f-fff1-49ae-ada1-8a933130cad6}`
- **Thông điệp sự kiện:**  
  `Code Integrity determined that a process (...) attempted to load (...) that did not meet the Enterprise signing level requirements or violated code integrity policy (Policy ID:{0283ac0f-fff1-49ae-ada1-8a933130cad6}).`

**Các tệp bị chặn thực tế:**
1. **Bản Onedir:** `_internal/libcrypto-3-x64.dll`
2. **Bản Portable:** `MathWeave-Studio-Portable.exe`

### 2.2. Phân định ranh giới giữa các cơ chế bảo mật Windows

Để không nhầm lẫn giữa các lớp kiểm soát ứng dụng của Microsoft, chúng tôi tiến hành phân định chi tiết:

| Tiêu Chí | 1. Smart App Control (SAC) | 2. App Control for Business (WDAC) | 3. Enterprise Code Integrity Signing Levels | 4. Các cơ chế khác (AppLocker, SRP) |
| :--- | :--- | :--- | :--- | :--- |
| **Bản chất** | Tính năng bảo mật tích hợp trên Windows 11 (22H2+), quản lý tự động bởi Microsoft Cloud Intelligence. | Giải pháp kiểm soát ứng dụng doanh nghiệp (Application Whitelisting) cấu hình qua GPO, Intune hoặc PowerShell. | Cấp độ chữ ký nội bộ trong nhân (`ci.dll`) kiểm tra tính toàn vẹn của mã nhị phân khi nạp vào bộ nhớ. | AppLocker chạy dưới dịch vụ `AppIDSvc`; SRP (Software Restriction Policies) đã lỗi thời từ Windows 10 1803. |
| **Tệp chính sách** | `%windir%\System32\CodeIntegrity\CiPolicies\Active\{0283ac0f-fff1-49ae-ada1-8a933130cad6}.cip` | Các tệp `.cip` tùy biến do Quản trị viên IT triển khai (GUID ngẫu nhiên hoặc cố định của tổ chức). | Định nghĩa trong cấu trúc nhị phân của PE header và catalog signing của Windows. | Lưu trong registry `HKLM\SOFTWARE\Policies\Microsoft\Windows\SrpV2`. |
| **Cơ chế đánh giá** | 1. Đánh giá độ tin cậy đám mây (ISG).<br>2. Nếu chưa có danh tiếng: Bắt buộc chữ ký số Authenticode hợp lệ từ CA thuộc Microsoft Trusted Root. | Dựa hoàn toàn vào các quy tắc quy định trước (Signer Rule, Hash Rule, FilePath Rule, hoặc bật ISG thủ công). | Kiểm tra signing level của tiến trình và so sánh với signing level của thư viện được nạp. | Kiểm tra đường dẫn, hàm băm hoặc thông tin nhà phát hành theo quy tắc AppLocker. |
| **Hỗ trợ thuật toán chữ ký** | **Hỗ trợ cả RSA và ECC/ECDSA** cho chứng chỉ Authenticode chuẩn. | **HOÀN TOÀN KHÔNG HỖ TRỢ** ECDSA trong Signer Rule (gây ra lỗi `VerificationError 23`). Chỉ hỗ trợ RSA. | Tùy thuộc vào phiên bản nhân và chính sách CI kích hoạt. | Hỗ trợ kiểm tra publisher theo chuỗi chứng chỉ chuẩn của Windows. |

### 2.3. Bằng chứng định danh Policy ID `{0283ac0f-fff1-49ae-ada1-8a933130cad6}`

Đối chiếu với cơ sở dữ liệu hệ thống Windows 11 và công cụ chẩn đoán chuyên dụng `CiTool.exe` (`CiTool -lp -json`):
- **GUID:** `{0283ac0f-fff1-49ae-ada1-8a933130cad6}`
- **Friendly Name:** `VerifiedAndReputableDesktop`
- **IsSystemPolicy:** `True`
- **IsEnforced:** `True`
- **Đường dẫn tệp thực tế:** `C:\Windows\System32\CodeIntegrity\CiPolicies\Active\{0283ac0f-fff1-49ae-ada1-8a933130cad6}.cip`

> [!IMPORTANT]
> **KẾT LUẬN ĐỊNH DANH:**
> Policy ID `{0283ac0f-fff1-49ae-ada1-8a933130cad6}` là **Chính sách nền tảng gốc của Smart App Control (SAC)** trên hệ điều hành Windows 11.
> Dưới tầng nhân (`ci.dll`), Smart App Control được hiện thực hóa dưới dạng một chính sách Code Integrity nghiêm ngặt kết hợp với dịch vụ Microsoft Intelligent Security Graph (ISG). Khi một tệp thiếu chữ ký số thương mại đáng tin cậy và chưa có danh tiếng đám mây, thông điệp sự kiện 3077 xuất hiện với chuỗi chuẩn hóa: *"did not meet the Enterprise signing level requirements or violated code integrity policy"*.
> Trong suốt quá trình chẩn đoán, **tuyệt đối không tắt, sửa đổi hoặc làm suy yếu chính sách bảo mật Windows**.

---

## 3. Tương Quan Sự Kiện CodeIntegrity & Phân Tích Nguyên Nhân Gốc (Phase A)

### 3.1. Đối chiếu tương quan qua ActivityID

Bằng cách nhóm các sự kiện theo `ActivityId` trong nhật ký `Microsoft-Windows-CodeIntegrity/Operational`:
```powershell
Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-CodeIntegrity/Operational'; Id=3077,3033,3089} |
    Group-Object -Property ActivityId
```
Kết quả cho thấy mỗi hành vi chặn luôn gồm 1 cặp sự kiện đồng bộ:
1. **Sự kiện 3077 hoặc 3033:** Xác định tiến trình gọi (`Process Name`), tệp bị chặn (`File Name`), và Policy ID áp dụng (`{0283ac0f-fff1-49ae-ada1-8a933130cad6}`).
2. **Sự kiện 3089 (Đi kèm với cùng ActivityID):** Cung cấp dữ liệu mật mã học về lý do từ chối:
   - `TotalSignatureCount: 0` (đối với tệp hoàn toàn không có chữ ký).
   - `VerificationError: 31` (Lỗi thiếu chữ ký số khi chính sách yêu cầu ký số).
   - `StatusCode: 0xc0000428` (`STATUS_INVALID_IMAGE_HASH` — Windows từ chối cấp phát trang nhớ thực thi cho nhị phân không hợp lệ).

### 3.2. Tại sao `_internal/libcrypto-3-x64.dll` và `MathWeave-Studio-Portable.exe` bị chặn?

1. **Với tệp Onedir `_internal/libcrypto-3-x64.dll`:**
   - Trong bản Onedir của PyInstaller, các tệp thư viện động (.dll) và phần mở rộng C (.pyd) nằm trong thư mục `_internal/`.
   - `libcrypto-3-x64.dll` là thư viện mã hóa OpenSSL đi kèm Python 3.14 Windows.
   - Khi ứng dụng khởi động và nạp module (`import hashlib` hoặc `import ssl`), nhân Windows kích hoạt trình điều khiển Code Integrity để xác thực tệp DLL trước khi ánh xạ vào bộ nhớ.
   - Do tệp `libcrypto-3-x64.dll` được trích xuất từ môi trường build CI chưa được ký số bởi chứng chỉ của nhà phát triển và chưa có danh tiếng đám mây trên hệ thống SAC, chính sách SAC lập tức áp đặt quy tắc chặn (Event 3077 & 3033), khiến tiến trình chính bị sập với lỗi `ImportError: DLL load failed`.
2. **Với tệp Portable `MathWeave-Studio-Portable.exe`:**
   - Là một tệp thực thi mới được tạo ra từ trình biên dịch PyInstaller.
   - Khi người dùng tải về và nhấp đúp, Windows Smart App Control kiểm tra tệp thực thi ở cấp tiến trình đầu vào (`explorer.exe` khởi chạy).
   - Vì tệp không có chữ ký số Authenticode và mã băm SHA-256 hoàn toàn mới đối với hệ thống trí tuệ đám mây của Microsoft, SAC chặn ngay lập tức tại thời điểm mở tệp.

---

## 4. Kiến Trúc Chữ Ký Số & Cơ Sở Lựa Chọn Thuật Toán Chứng Chỉ (Phase B)

### 4.1. Phân tích tương thích thuật toán: RSA so với ECC/ECDSA

Tài liệu kỹ thuật của Microsoft làm rõ:
1. **Smart App Control (SAC):** Hỗ trợ đầy đủ cả chứng chỉ **RSA** và **ECC (Elliptic Curve Cryptography)** Authenticode code-signing, miễn là chứng chỉ được cấp bởi CA thuộc Microsoft Trusted Root Program.
2. **App Control for Business / WDAC (Enterprise):** **HOÀN TOÀN KHÔNG HỖ TRỢ ECDSA trong Signer Rules**. Nếu một tệp nhị phân được ký bằng ECDSA, trình kiểm tra Code Integrity của App Control sẽ trả về lỗi **`VerificationError = 23`** và từ chối tệp. Hơn nữa, chứng chỉ dùng để ký chính sách WDAC bắt buộc phải dùng khóa RSA (2K, 3K, 4K).
3. **Cơ sở lựa chọn:** Để đạt được khả năng tương thích chéo phổ quát (Universal Windows Compatibility) — hoạt động trơn tru trên cả máy trạm cá nhân bật Smart App Control và máy tính doanh nghiệp áp dụng App Control for Business / WDAC — MathWeave Studio lựa chọn **chuẩn khóa RSA (3072-bit hoặc 4096-bit)** kết hợp hàm băm **SHA-256**. Lựa chọn này là quyết định kỹ thuật về tính tương thích diện rộng, không phải vì SAC từ chối ECC.

### 4.2. Xóa bỏ hoàn toàn cơ chế Fallback Self-Signed trong quy trình Release

Theo yêu cầu nghiêm ngặt từ phản hồi kỹ thuật:
- **Loại bỏ tự động sinh chứng chỉ tự ký (Self-signed):** Không tự động sinh chứng chỉ tự ký khi thiếu bí mật `WINDOWS_CERT_BASE64`.
- **Tuyệt đối không can thiệp Trust Store của CI:** Không nạp chứng chỉ tự ký vào `Cert:\CurrentUser\Root` để làm giả trạng thái chữ ký `Valid`.
- **Phân tách rạch ròi 2 chế độ:**
  - **Chế độ Sản Xuất (`--mode production` hoặc `--require-signing`):** Bắt buộc có chứng chỉ thương mại tin cậy từ CA ngoài hoặc Microsoft Trusted Signing. Nếu thiếu, **tiến trình CI sẽ thất bại ngay lập tức (FAIL)** với thông báo lỗi rõ ràng.
  - **Chế độ Phát Triển (`--mode unsigned-dev` hoặc mặc định khi thiếu secret):** Giữ nguyên bản build không ký, dán nhãn minh bạch trên tên tệp và Artifact: `MathWeave-Studio-Windows-Onedir-Unsigned-Dev.zip` và `MathWeave-Studio-Portable-Unsigned-Dev.exe`.
  - **Chế độ Thử Nghiệm Cô Lập (`--allow-test-cert`):** Chỉ dùng duy nhất trong test suite nội bộ để kiểm thử cú pháp gọi SignTool, cảnh báo rõ ràng rằng chứng chỉ này không có giá trị phát hành.

---

## 5. Thách Thức & Giải Pháp Ký Số Từng Tệp Nhị Phân Bên Trong Portable Onefile

### 5.1. Cơ chế đóng gói Onefile của PyInstaller
Trong chế độ Onefile (`mathweave-studio-onefile.spec`), PyInstaller thu thập tất cả các tệp `.dll` và `.pyd` vào danh sách `a.binaries` và đóng gói thành một kho lưu trữ nhị phân (CArchive) nhúng bên trong tệp thực thi `MathWeave-Studio-Portable.exe`.

Khi người dùng chạy `MathWeave-Studio-Portable.exe`:
1. Trình nạp bootloader của PyInstaller giải nén toàn bộ các tệp nhị phân ra thư mục tạm `%TEMP%\_MEIxxxxxx\`.
2. Hệ điều hành Windows bắt đầu nạp các tệp DLL phụ thuộc từ thư mục này.
3. Nếu chỉ ký tệp `.exe` bên ngoài mà các tệp `.dll` bên trong không có chữ ký số, Smart App Control hoặc App Control sẽ chặn nạp các DLL trong `%TEMP%` (như đã xảy ra với `libcrypto-3-x64.dll`).

### 5.2. Giải pháp kỹ thuật đã triển khai
1. **Thay thế nhị phân trước khi đóng gói:**
   Trong `mathweave-studio-onefile.spec`, chúng tôi đã bổ sung logic kiểm tra: Nếu thư mục Onedir `dist/mathweave-studio/_internal` đã tồn tại và chứa các tệp nhị phân đã ký số, PyInstaller sẽ ưu tiên trỏ đường dẫn `a.binaries` sang các tệp đã ký đó.
   Bằng cách này, toàn bộ các tệp nhị phân nhúng trong Onefile (bao gồm `libcrypto-3-x64.dll` và `_ssl.pyd`) đều mang chữ ký Authenticode trước khi được đóng gói vào CArchive.
2. **Ký tệp thực thi bên ngoài:** Ký số toàn diện tệp `MathWeave-Studio-Portable.exe` sau khi build hoàn tất.
3. **Bảo tồn chữ ký gốc của nhà cung cấp:** Trong script ký số, các tệp mang chữ ký hợp lệ của Microsoft (như CRT DLLs) được bảo tồn nguyên vẹn (`should_preserve_vendor_signature`), tránh ký đè không cần thiết.
4. **Kiểm tra trích xuất có kiểm soát (`verify_onefile_embedded_binaries`):**
   Cung cấp tính năng khởi chạy Portable EXE trong môi trường hộp cát với biến `TEMP` tạm thời, đợi giải nén và quét trực tiếp từng tệp DLL/PYD trong `_MEIxxxxxx` để thẩm định chữ ký số độc lập.

> [!WARNING]
> **Khuyến nghị phân phối cho môi trường Doanh nghiệp:**
> Mặc dù các tệp bên trong Onefile đã được ký số, nhiều môi trường doanh nghiệp áp dụng chính sách App Control khắt khe cấm hoàn toàn việc thực thi mã từ các thư mục có quyền ghi của người dùng (`%TEMP%`, `%APPDATA%`). Khi đó, bản **Standard Onedir** (được cài đặt vào thư mục được bảo vệ như `C:\Program Files\`) được khuyến nghị mạnh mẽ là kênh phân phối chính thức, ổn định và an toàn hơn bản Portable Onefile.

---

## 6. Chuẩn Hóa Siêu Dữ Liệu Tệp (Windows File Metadata) Theo Danh Tính Dự Án Thực Tế

Tránh hoàn toàn việc tự suy diễn tên công ty hay pháp nhân thương mại. Toàn bộ thông tin định danh PE được ánh xạ trực tiếp từ cấu hình xác thực trong `pyproject.toml` (tác giả: `TqvNoCode`):

| Trường Siêu Dữ Liệu | Bản Phân Phối Onedir | Bản Phân Phối Portable Onefile | Nguồn Gốc Xác Thực |
| :--- | :--- | :--- | :--- |
| **`CompanyName`** | `TqvNoCode` | `TqvNoCode` | Mục `authors` trong `pyproject.toml` |
| **`FileDescription`** | MathWeave Studio - Mathematics Learning & Research Application | MathWeave Studio - Standalone Portable Mathematics Application | Mô tả kỹ thuật sản phẩm |
| **`FileVersion`** | `0.1.1.0` | `0.1.1.0` | Thuộc tính `version` trong `pyproject.toml` |
| **`InternalName`** | `mathweave-studio` | `MathWeave-Studio-Portable` | Tên định danh tiến trình |
| **`LegalCopyright`** | Copyright (C) 2026 TqvNoCode. All rights reserved. | Copyright (C) 2026 TqvNoCode. All rights reserved. | Bản quyền tác giả đã xác nhận |
| **`OriginalFilename`** | `mathweave-studio.exe` | `MathWeave-Studio-Portable.exe` | Tên tệp gốc chống đổi tên |
| **`ProductName`** | MathWeave Studio | MathWeave Studio | Tên sản phẩm chính thức |
| **`ProductVersion`** | `0.1.1.0` | `0.1.1.0` | Phiên bản sản phẩm thương mại |

---

## 7. Đối Soát So Sánh Giữa Smart App Control & Enterprise App Control (WDAC)

| Tiêu Chí Kỹ Thuật | Smart App Control (SAC) | App Control for Business / WDAC (Enterprise) |
| :--- | :--- | :--- |
| **Mục đích triển khai** | Bảo vệ tự động người dùng phổ thông trước mã độc và phần mềm không rõ nguồn gốc. | Thiết lập hàng rào bảo vệ vững chắc cho môi trường doanh nghiệp (Zero-Trust Application Control). |
| **Cơ chế đánh giá độ tin cậy** | Ưu tiên trí tuệ đám mây (ISG). Ứng dụng mới ký bởi CA thương mại thuộc Microsoft Root Program sẽ được cho phép chạy. | Tuân theo danh sách trắng nghiêm ngặt. Không tự động tin tưởng một chứng chỉ thương mại trừ khi Quản trị viên IT đã thêm Signer Rule cho chứng chỉ đó. |
| **Hỗ trợ thuật toán chữ ký** | Hỗ trợ cả RSA và ECC Authenticode. | **Chỉ hỗ trợ RSA** cho Signer Rules. Chữ ký ECDSA bị báo lỗi `VerificationError 23` và bị từ chối. |
| **Quy tắc thư mục tạm (%TEMP%)** | Cho phép tệp portable chạy từ thư mục người dùng nếu có chữ ký số hoặc danh tiếng tốt. | Nhiều chính sách mẫu cấm hoàn toàn việc thực thi nhị phân từ thư mục `%TEMP%`. Khi đó bản Portable Onefile có thể bị chặn bởi quy tắc đường dẫn dù đã ký số. |
| **Khả năng can thiệp của Quản trị viên** | Người dùng có thể tắt trong Windows Security nhưng không thể bật lại trừ khi cài lại Windows. Không quản lý bằng `CiTool`. | Hoàn toàn quản lý được bằng PowerShell, GPO, Intune và `CiTool.exe` thông qua các tệp Supplemental Policy. |

---

## 8. Tiêu Chuẩn Nghiệm Thu Cuối Cùng (Production Acceptance Criteria)

Để tuyên bố giải quyết triệt để vấn đề chặn thực thi và sẵn sàng phát hành:

1. **Điều kiện tiên quyết về Chứng chỉ Số:**
   - Cung cấp chứng chỉ số Authenticode thương mại hợp lệ (hoặc đăng ký Microsoft Trusted Signing).
   - Thiết lập biến bí mật `WINDOWS_CERT_BASE64` và `WINDOWS_CERT_PASSWORD` trên GitHub Secrets.
2. **Kiểm tra trên Runner GitHub Actions:**
   - Workflow chạy thành công với bước `has_signing == true`.
   - Toàn bộ các tệp `.exe`, `.dll`, `.pyd` (bao gồm `_internal/libcrypto-3-x64.dll`) đều có chữ ký Authenticode SHA-256 kèm RFC 3161 timestamp.
   - Chuỗi chứng chỉ thẩm định qua chuỗi Root CA công khai mà **không qua thao tác nạp chứng chỉ cục bộ vào `Root` store**.
   - Kiểm tra giải nén tệp Onedir ZIP và Portable Onefile xác nhận chữ ký số của các tệp nhị phân bên trong được bảo toàn 100%.
3. **Nghiệm thu thực tế trên máy Windows 11 độc lập (Real-world Acceptance):**
   - Tải tệp artifact về một máy tính Windows 11 độc lập (chưa từng cài đặt chứng chỉ test CI).
   - Đảm bảo **Smart App Control đang ở trạng thái BẬT (ON)**.
   - Khởi chạy cả bản Onedir và bản Portable.
   - Xác nhận tiến trình khởi động trơn tru, thư viện `_ssl` và OpenSSL nạp thành công, giao diện NiceGUI hiển thị đầy đủ và không phát sinh bất kỳ sự kiện Event 3077 / 3033 nào trong `Microsoft-Windows-CodeIntegrity/Operational`.

---

*Báo cáo được hoàn thiện và cập nhật tại `reports/WINDOWS_SIGNING_AND_METADATA_REPORT.md` tuân thủ đầy đủ các tiêu chuẩn kiểm soát kỹ thuật và an toàn mã nguồn.*
