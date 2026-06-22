# Dispatch Pro Dashboard

Ứng dụng dashboard quản lý điều phối (Dispatch), xây dựng bằng [Streamlit](https://streamlit.io/), đọc/ghi dữ liệu qua Google Sheets API.

## Cấu trúc thư mục

```
dispatch_pro_app.py      # App chính (Streamlit)
run_dispatch_pro.py      # Launcher: chạy app như ứng dụng desktop, tự mở browser
requirements.txt         # Danh sách thư viện Python cần thiết
run_app.bat              # Chạy app trực tiếp bằng Python (không cần build .exe)
build_exe.bat            # Build app thành file .exe độc lập (dùng PyInstaller)
HUONG_DAN_CHAY_APP.md    # Hướng dẫn chi tiết (tiếng Việt)
```

> ⚠️ **`credentials.json`** (Google Service Account key) và **`app_config.json`** (cấu hình riêng) **không** được đưa vào repo này — xem mục Cấu hình bên dưới.

## Yêu cầu

- Python 3.12 (bản chuẩn từ [python.org](https://www.python.org/downloads/), không dùng bản rút gọn/embeddable)
- Một Google Service Account có quyền truy cập Google Sheet bạn muốn kết nối

## Cấu hình

1. Tạo Service Account trên [Google Cloud Console](https://console.cloud.google.com/), bật Google Sheets API, tải file key JSON.
2. Đổi tên file key đó thành `credentials.json`, đặt vào cùng thư mục với `dispatch_pro_app.py`.
3. Chia sẻ (Share) Google Sheet với email của Service Account đó.
4. (Tuỳ chọn) Tạo `app_config.json` nếu cần lưu cấu hình cột/cấu trúc riêng — xem `HUONG_DAN_CHAY_APP.md`.

## Cách chạy (không build .exe)

```cmd
git clone <repo-url>
cd <repo-folder>
run_app.bat
```

Script sẽ tự kiểm tra pip, cài thư viện trong `requirements.txt`, rồi mở app tại `http://localhost:8501`.

## Build thành file .exe

```cmd
build_exe.bat
```

File `.exe` xuất ra tại `dist\DispatchProDashboard.exe`. Cần copy `credentials.json` và `app_config.json` vào cùng thư mục `dist` trước khi chạy.

## Giấy phép

(Thêm license bạn muốn dùng, ví dụ MIT)
