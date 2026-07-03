@echo off
title Impedance Fitting
cd /d "%~dp0"

set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"

if not exist "%PYEXE%" (
    echo [!] Python not found at:
    echo     %PYEXE%
    echo     Edit PYEXE in this .bat if Python is installed elsewhere.
    echo.
    pause
    exit /b 1
)

echo ============================================
echo   Starting Impedance Fitting app...
echo   Your browser will open automatically.
echo   To quit: press Ctrl+C here, or close window
echo ============================================
echo.

"%PYEXE%" -m streamlit run app.py

echo.
echo App stopped.
pause
