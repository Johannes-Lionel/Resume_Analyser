@echo off
title AI Resume Sorter Launcher
cd /d "%~dp0"

echo ========================================================
echo         Starting AI Resume Sorter & Ranker
echo ========================================================
echo.

REM 1. Check if Ollama is running, start it if not
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I /N "ollama.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [OK] Ollama is currently running.
) else (
    echo [INFO] Starting Ollama in the background...
    start /B "" ollama serve >nul 2>&1
    timeout /t 3 /nobreak >nul
)

REM 2. Determine Python executable
if exist ".venv\Scripts\python.exe" (
    set "PY_CMD=.venv\Scripts\python.exe"
) else (
    set "PY_CMD=python"
)

echo [INFO] Launching Streamlit web interface...
echo [INFO] Your browser will open automatically at http://localhost:8501
echo.

%PY_CMD% -m streamlit run app.py --server.headless false

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] The application stopped with an error code: %ERRORLEVEL%
    pause
)
