"""
Launcher: chạy file này (hoặc file .exe build ra từ nó) để khởi động Dispatch Pro Dashboard
như một ứng dụng desktop bình thường — tự mở trình duyệt, không cần gõ lệnh streamlit run.
"""
import os
import sys
import threading
import time
import webbrowser

PORT = 8501

# FIX: khi đóng gói bằng PyInstaller, Streamlit tự nhận lầm là đang ở development mode,
# khiến nó từ chối nhận --server.port (lỗi "server.port does not work when
# global.developmentMode is true"). Phải set biến môi trường này TRƯỚC khi import streamlit.
os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"


def _resource_dir():
    # Khi chạy từ .exe (PyInstaller), file gốc nằm cùng thư mục với .exe.
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def open_browser():
    time.sleep(2.5)
    webbrowser.open(f"http://localhost:{PORT}")


def main():
    base_dir = _resource_dir()
    app_path = os.path.join(base_dir, "dispatch_pro_app.py")
    os.chdir(base_dir)  # để app đọc đúng credentials.json / app_config.json cùng thư mục

    threading.Thread(target=open_browser, daemon=True).start()

    from streamlit.web import cli as stcli
    sys.argv = [
        "streamlit", "run", app_path,
        "--server.port", str(PORT),
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--global.developmentMode", "false",
    ]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
