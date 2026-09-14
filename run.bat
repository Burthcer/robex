@echo off
setlocal
title Robex - AI Game Macro

:: Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo [INFO] Virtual environment not found. Running setup_env.bat first...
    call setup_env.bat
    if not exist "venv\Scripts\activate.bat" (
        echo [ERROR] Setup failed or was cancelled. Cannot launch Robex.
        pause
        exit /b 1
    )
)

:: Activate virtual environment and launch application
call .\venv\Scripts\activate.bat
echo [INFO] Launching Robex...
python -m robex

if %errorlevel% neq 0 (
    echo.
    echo [INFO] Robex exited with error code %errorlevel%.
    pause
)
