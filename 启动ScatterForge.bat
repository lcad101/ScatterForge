@echo off
cd /d "%~dp0"
title ScatterForge Launcher

rem =====================================================
rem  ScatterForge - Excel Scatter Chart Generator
rem  Double-click this file to launch the application.
rem  First run installs dependencies automatically.
rem =====================================================

rem ---- 1. Locate Python ----
set "PY=python"
python --version >nul 2>nul
if errorlevel 1 set "PY=py -3"
%PY% --version >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found.
    echo Please install Python 3.10+ and check "Add python.exe to PATH".
    echo.
    pause
    exit /b 1
)

rem ---- 2. First run: install dependencies ----
if not exist "libs\PySide6" (
    echo First run: installing dependencies, please wait...
    %PY% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Dependency installation failed. Check your network and retry.
        echo.
        pause
        exit /b 1
    )
    echo Dependencies installed.
)

rem ---- 3. Launch the application ----
echo Starting ScatterForge...
%PY% main.py
if errorlevel 1 (
    echo.
    echo [ERROR] Program exited with code %errorlevel%
    pause
)
