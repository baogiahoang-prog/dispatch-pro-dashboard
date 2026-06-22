# Hướng dẫn chạy Dispatch Pro Dashboard trực tiếp bằng Python (không cần .exe)

## Các file cần có (đặt cùng 1 thư mục trên máy Windows)
- `dispatch_pro_app.py` — app chính
- `run_dispatch_pro.py` — launcher, tự mở trình duyệt khi chạy
- `requirements.txt`
- `run_app.bat` — chạy file này để cài thư viện + khởi động app
- `credentials.json` — file key Google Service Account của anh
- `app_config.json` — cấu hình COT cũ, nếu có thì copy vào để giữ lại

## Cách dùng
1. Copy toàn bộ các file trên vào 1 thư mục, ví dụ `D:\DispatchPro\`
2. Double-click file **`run_app.bat`**
3. Script sẽ tự kiểm tra pip, cài thư viện cần thiết, rồi mở app trên trình duyệt.

## Nếu báo lỗi "No module named pip"
Máy đang dùng 1 bản Python rút gọn / đóng gói riêng (như "Turtle Python") — bản này
không có sẵn `pip` và cũng không tự cài được qua `ensurepip`. Cách xử lý:

1. Cài Python 3.12 bản **chuẩn** từ trang chủ: https://www.python.org/downloads/
2. Khi cài, **tick chọn**:
   - ✅ Add python.exe to PATH
   - ✅ pip (mặc định bản chuẩn đã có sẵn pip)
3. Mở **cmd mới** (để PATH được cập nhật) rồi chạy lại `run_app.bat`.

Lưu ý: nếu máy có nhiều bản Python cùng lúc, gõ `where python` trong cmd để xem
bản nào đang được dùng đầu tiên trong PATH — cần đảm bảo đó là bản Python 3.12
chuẩn vừa cài, không phải bản rút gọn cũ.

## Mỗi lần muốn chạy lại app
Chỉ cần double-click `run_app.bat` lần nữa — lần sau các thư viện đã cài rồi nên
sẽ khởi động nhanh hơn lần đầu.
