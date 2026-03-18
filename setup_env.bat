@echo off
setlocal enabledelayedexpansion

REM Change to script directory
cd /d "%~dp0"

echo [*] Checking Python...
where python >nul 2>&1
if errorlevel 1 (
    echo [!] Python not found in PATH. Install Python 3 and try again.
    pause
    exit /b 1
)

set VENV_DIR=.venv

if not exist "%VENV_DIR%" (
    echo [*] Creating virtual environment in %VENV_DIR% ...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [!] Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [*] Virtual environment already exists: %VENV_DIR%
)

echo [*] Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo [!] Failed to activate virtual environment.
    pause
    exit /b 1
)

echo [*] Installing dependencies from requirements.txt ...
pip install --upgrade pip
pip install -r requirements.txt

if errorlevel 1 (
    echo [!] Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo [OK] Environment is ready.
echo.
echo To run the app now, press Y and Enter.
set /p RUN_NOW="Run server now? [Y/n]: "
if /I "%RUN_NOW%"=="Y" (
    echo.
    echo [*] Starting development server...
    "%VENV_DIR%\Scripts\python.exe" app.py
) else (
    echo.
    echo You can start it later with:
    echo   %VENV_DIR%\Scripts\python app.py
    pause
)

endlocal
exit /b 0
