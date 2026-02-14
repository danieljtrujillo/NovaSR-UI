@echo off
:: ============================================================
::  NovaSR – One-Click Setup
::  Installs the package, registers the right-click menu,
::  and launches the GUI.
:: ============================================================
title NovaSR Setup
echo.
echo  ================================================
echo   NovaSR  -  Audio Super-Resolution Installer
echo  ================================================
echo.

:: ── Locate Python ──
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python not found on PATH.
    echo  Please install Python 3.9+ from https://python.org
    pause
    exit /b 1
)

:: ── Install the package (editable) ──
echo  [1/3] Installing NovaSR and dependencies...
pip install -e "%~dp0." --quiet
if %errorlevel% neq 0 (
    echo  [ERROR] pip install failed. Check the output above.
    pause
    exit /b 1
)

:: ── Register right-click context menu ──
echo  [2/3] Registering right-click context menu...
python "%~dp0install_context_menu.py" --install

:: ── Launch GUI ──
echo  [3/3] Launching NovaSR GUI...
echo.
start "" python "%~dp0novasr_gui.py"

echo.
echo  ================================================
echo   Setup complete!
echo   - Right-click any audio file to upscale.
echo   - Or launch novasr_gui.py anytime.
echo  ================================================
echo.
pause
