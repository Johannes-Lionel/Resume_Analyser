@echo off
title Setup AI Resume Sorter on New PC
cd /d "%~dp0"

echo ========================================================
echo        Setting up AI Resume Sorter on this PC
echo ========================================================
echo.

REM 1. Verify Python is installed
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not added to PATH!
    echo Please install Python 3.10 or newer from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo [OK] Python found.

REM 2. Create virtual environment if it doesn't exist
if not exist ".venv" (
    echo [INFO] Creating virtual environment (.venv)...
    python -m venv .venv
)

REM 3. Install required packages
echo [INFO] Installing required libraries (Streamlit, Ollama, PDF/Word readers)...
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================
    echo  SUCCESS! All setup is complete!
    echo  You can now double-click "Launch_App.bat" to start.
    echo ========================================================
) else (
    echo.
    echo [ERROR] Package installation failed. Please check your internet connection.
)

echo.
pause
