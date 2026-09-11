@echo off
chcp 65001 >nul
title Build ImpedanceFitting.exe
cd /d "%~dp0"

echo ============================================
echo   ImpedanceFitting.exe 빌드
echo   (scipy/plotly/streamlit 포함, 수 분 소요)
echo ============================================
echo.

REM PyInstaller 준비
python -m pip install pyinstaller --quiet

REM 단일 파일(onefile) exe 빌드
python -m PyInstaller run_exe.py --noconfirm --clean --onefile ^
  --name ImpedanceFitting ^
  --collect-all streamlit ^
  --collect-all plotly ^
  --copy-metadata streamlit ^
  --add-data "app.py;." ^
  --add-data "impedance_fit.py;."

echo.
echo ============================================
echo   완료 → dist\ImpedanceFitting.exe
echo ============================================
pause
