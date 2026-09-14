@echo off
setlocal enabledelayedexpansion
title Robex - Setup Environment

echo ======================================================
echo           ROBEX - Automated Environment Setup
echo ======================================================
echo.

:: Detect Python
set PYTHON_CMD=
py -3.12 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py -3.12
) else (
    python --version >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_CMD=python
    ) else (
        echo [ERROR] Python was not detected on your system.
        echo Please install Python 3.10, 3.11, or 3.12 from https://www.python.org/
        echo Make sure to check "Add Python to PATH" during installation.
        pause
        exit /b 1
    )
)

echo [OK] Using Python: %PYTHON_CMD%

:: Create Virtual Environment
if not exist "venv" (
    echo [INFO] Creating virtual environment (venv)...
    %PYTHON_CMD% -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
) else (
    echo [OK] Virtual environment already exists.
)

:: Activate and install dependencies
echo.
echo [INFO] Installing/Updating dependencies...
call .\venv\Scripts\activate.bat

python -m pip install --upgrade pip
pip install -r requirements-dev.txt

if %errorlevel% equ 0 (
    echo.
    echo ======================================================
    echo  [SUCCESS] Environment setup complete!
    echo  You can now run "run.bat" to start Robex,
    echo  or run "build_exe.bat" to compile Robex into an .exe.
    echo ======================================================
) else (
    echo.
    echo [ERROR] Encountered an error while installing dependencies.
)

echo.
pause
