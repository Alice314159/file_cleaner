#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# File Cleaner — macOS / Linux build script
# ─────────────────────────────────────────────────────────
set -e

echo "========================================"
echo "  File Cleaner — Build Script (macOS)"
echo "========================================"

# 1. Create venv (optional but clean)
if [ ! -d ".venv" ]; then
    echo "[1/4] Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

# 2. Install dependencies
echo "[2/4] Installing dependencies..."
pip install --upgrade pip
pip install pyinstaller

# 3. Build
echo "[3/4] Running PyInstaller..."
pyinstaller file_cleaner.spec --clean --noconfirm

# 4. Result
echo "[4/4] Done!"
echo ""
if [ "$(uname)" = "Darwin" ]; then
    echo "  ✅  App bundle:  dist/FileCleaner.app"
    echo "  → Drag FileCleaner.app to /Applications to install"
    echo ""
    echo "  To create a DMG:"
    echo "    hdiutil create -volname FileCleaner -srcfolder dist/FileCleaner.app \\"
    echo "      -ov -format UDZO dist/FileCleaner.dmg"
else
    echo "  ✅  Executable:  dist/FileCleaner"
fi
echo ""
