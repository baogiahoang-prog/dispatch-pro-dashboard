@echo off
REM ============================================================
REM  CHAY TRUC TIEP DISPATCH PRO DASHBOARD BANG PYTHON (khong build .exe)
REM ============================================================
setlocal

echo Dang dung Python:
where python
python --version
echo.

echo [1/3] Dang kiem tra pip...
python -m pip --version >nul 2>&1
if not errorlevel 1 goto have_pip

echo   -> Chua co pip, dang thu tu cai qua ensurepip...
python -m ensurepip --upgrade >nul 2>&1
python -m pip --version >nul 2>&1
if not errorlevel 1 goto have_pip

echo.
echo  ============================================================
echo   KHONG THE CAI PIP CHO PYTHON NAY:
where python
echo  Day co ve la ban Python rut gon / dong goi rieng (embeddable),
echo  khong co pip va khong tu cai duoc qua ensurepip.
echo.
echo  CACH XU LY: cai ban Python 3.12 CHUAN tu trang chu:
echo     https://www.python.org/downloads/
echo  Khi cai, nho TICK chon:
echo     [x] Add python.exe to PATH
echo     [x] pip (mac dinh da tick san trong ban chuan)
echo  Sau do mo lai cmd MOI (de PATH duoc cap nhat) va chay lai file nay.
echo  ============================================================
pause
exit /b 1

:have_pip
echo   -> OK, da co pip.

echo [2/3] Dang cai thu vien can thiet...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo  Cai thu vien bi loi, xem thong bao loi o tren.
    pause
    exit /b 1
)

echo [3/3] Dang khoi dong Dispatch Pro Dashboard...
echo   (Trinh duyet se tu mo sau vai giay. Dung tat cua so nay khi dung dung app.)
python run_dispatch_pro.py

pause
endlocal
