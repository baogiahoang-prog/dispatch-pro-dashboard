@echo off
REM ============================================================
REM  BUILD DISPATCH PRO DASHBOARD THANH FILE .EXE
REM  Script nay GOI THANG Python 3.12, khong dua vao PATH chung
REM ============================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "PY="

REM --- Cach 1: dung py launcher de chon dung ban 3.12 ---
py -3.12 -c "print(1)" >nul 2>&1
if not errorlevel 1 (
    set "PY=py -3.12"
    goto found_python
)

REM --- Cach 2: do tim trong cac thu muc cai dat chuan thuong gap ---
for %%P in (
    "%LocalAppData%\Programs\Python\Python312\python.exe"
    "C:\Python312\python.exe"
    "C:\Program Files\Python312\python.exe"
    "C:\Program Files (x86)\Python312\python.exe"
) do (
    if exist %%P (
        set "PY=%%~P"
        goto found_python
    )
)

echo  ============================================================
echo   KHONG TIM THAY PYTHON 3.12 CHUAN TREN MAY.
echo   Hay cai Python 3.12 tu: https://www.python.org/downloads/
echo   Khi cai, nho TICK chon:
echo      [x] Add python.exe to PATH
echo      [x] pip
echo   Sau do mo lai cmd MOI va chay lai file nay.
echo  ============================================================
pause
exit /b 1

:found_python
echo Dang dung Python:
%PY% --version
echo.

echo [1/5] Dang kiem tra pip...
%PY% -m pip --version >nul 2>&1
if not errorlevel 1 goto have_pip

echo   -> Chua co pip, dang thu cai qua ensurepip...
%PY% -m ensurepip --upgrade >nul 2>&1
%PY% -m pip --version >nul 2>&1
if not errorlevel 1 goto have_pip

echo  KHONG THE CAI PIP CHO PYTHON NAY. Vui long cai lai Python 3.12 chuan.
pause
exit /b 1

:have_pip
echo   -> OK, da co pip.
echo.

echo [2/5] Dang nang cap pip...
%PY% -m pip install --upgrade pip
if errorlevel 1 goto loi_pip_upgrade
goto cai_requirements

:loi_pip_upgrade
echo  LOI: nang cap pip bi loi. Xem thong bao loi o tren.
pause
exit /b 1

:cai_requirements
echo.
echo [3/5] Dang cai thu vien trong requirements.txt...
%PY% -m pip install -r requirements.txt
if errorlevel 1 goto loi_requirements
goto cai_pyinstaller

:loi_requirements
echo  ============================================================
echo   LOI: CAI THU VIEN TRONG requirements.txt BI LOI.
echo   Xem dong loi mau do o phia tren de biet thu vien nao bi loi.
echo   Thuong gap: python-calamine can cong cu build Rust de cai.
echo   Neu loi, co the mo file requirements.txt, xoa dong chua chu
echo   python-calamine, luu lai, roi chay lai file nay - day la thu
echo   vien toi uu, khong bat buoc phai co.
echo  ============================================================
pause
exit /b 1

:cai_pyinstaller
echo.
echo [4/5] Dang cai pyinstaller...
%PY% -m pip install pyinstaller
if errorlevel 1 goto loi_pyinstaller
goto kiem_tra_import

:loi_pyinstaller
echo  LOI: cai pyinstaller bi loi. Xem thong bao loi o tren.
pause
exit /b 1

:kiem_tra_import
echo   -> OK, da cai xong toan bo thu vien.
echo.
echo [4.5/5] Dang kiem tra cac thu vien quan trong da co chua...
%PY% -c "import gspread, oauth2client, pandas, streamlit" 2>&1
if errorlevel 1 goto loi_import
goto build_now

:loi_import
echo  ============================================================
echo   LOI: mot trong cac thu vien quan trong CHUA duoc cai dung.
echo   Xem loi cu the o phia tren.
echo   Thu chay thu cong: %PY% -m pip install gspread oauth2client
echo  ============================================================
pause
exit /b 1

:build_now
echo   -> OK, da xac nhan day du thu vien.
echo.

echo [5/5] Dang build file .exe (co the mat vai phut)...
%PY% -m PyInstaller --onefile --noconsole --name DispatchProDashboard ^
    --collect-all streamlit ^
    --collect-all altair ^
    --collect-all pandas ^
    --collect-all pyarrow ^
    --collect-all gspread ^
    --collect-all oauth2client ^
    --hidden-import gspread ^
    --hidden-import oauth2client.service_account ^
    run_dispatch_pro.py
if errorlevel 1 goto loi_build
goto copy_files

:loi_build
echo  Build .exe bi loi, xem thong bao loi o tren.
pause
exit /b 1

:copy_files
echo.
echo Dang copy cac file can thiet vao thu muc dist...
copy /Y "dispatch_pro_app.py" "dist\dispatch_pro_app.py" >nul

if exist "credentials.json" copy /Y "credentials.json" "dist\credentials.json" >nul
if exist "app_config.json" copy /Y "app_config.json" "dist\app_config.json" >nul

echo.
echo  ============================================================
echo   HOAN TAT! File .exe nam trong thu muc dist\DispatchProDashboard.exe
echo.
echo   QUAN TRONG: trong thu muc dist phai co DU 3 file nay:
echo      - DispatchProDashboard.exe
echo      - dispatch_pro_app.py   (da tu copy)
echo      - credentials.json      (anh copy thu cong neu chua co)
echo      - app_config.json       (anh copy thu cong neu chua co)
echo  ============================================================
pause
endlocal
