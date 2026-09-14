@echo off
setlocal
title Robex - Build Standalone Executable (.exe)

echo ======================================================
echo             ROBEX - Standalone .exe Compiler
echo ======================================================
echo.

if not exist "venv\Scripts\activate.bat" (
    echo [INFO] Virtual environment not found. Setting up first...
    call setup_env.bat
)

call .\venv\Scripts\activate.bat

echo [INFO] Compiling Robex with PyInstaller...
pyinstaller robex.spec --noconfirm --clean

if %errorlevel% equ 0 (
    echo.
    echo ======================================================
    echo  [SUCCESS] Compilation finished!
    echo  Your standalone application is located at:
    echo  dist\Robex.exe (or dist\Robex\Robex.exe)
    echo ======================================================
) else (
    echo.
    echo [ERROR] PyInstaller compilation failed.
)

echo.
pause
