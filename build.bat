@echo off
:: ─────────────────────────────────────────────────────────
:: File Cleaner — Windows build script
:: ─────────────────────────────────────────────────────────
echo ========================================
echo   File Cleaner - Build Script (Windows)
echo ========================================

:: 1. Create venv
if not exist ".venv" (
    echo [1/4] Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

:: 2. Install dependencies
echo [2/4] Installing dependencies...
pip install --upgrade pip
pip install pyinstaller

:: 3. Build
echo [3/4] Running PyInstaller...
pyinstaller file_cleaner.spec --clean --noconfirm

:: 4. Result
echo [4/4] Done!
echo.
echo   OK  Executable: dist\FileCleaner.exe
echo.
echo   To create an installer (requires NSIS):
echo     makensis installer.nsi
echo.
pause
