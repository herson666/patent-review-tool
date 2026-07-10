#!/usr/bin/env bash
# .github/scripts/build-python.sh — Python app builder
# Supports: desktop-gui, cli subtypes
# Platforms: windows, macos, linux
set -euo pipefail
PLATFORM="${PLATFORM:?}"; VERSION="${VERSION:?}"

# Determine subtype
SUBTYPE="library"
if [ -f pyproject.toml ]; then
  if grep -qiE 'PySide6|PyQt5|PyQt6|wxPython|tkinter' pyproject.toml requirements.txt 2>/dev/null; then
    SUBTYPE="desktop-gui"
  elif grep -qiE 'click|typer|argparse' pyproject.toml requirements.txt 2>/dev/null; then
    SUBTYPE="cli"
  elif grep -qiE 'fastapi|django|flask|starlette' pyproject.toml requirements.txt 2>/dev/null; then
    SUBTYPE="web"
  fi
fi

case "$PLATFORM" in
  windows)
    pip install --upgrade pip
    pip install -r requirements.txt 2>/dev/null || pip install . 2>/dev/null
    pip install pyinstaller
    # Detect entry point
    ENTRY="main.py"
    if [ -f pyproject.toml ]; then
      ep=$(grep -A5 '\[project.scripts\]' pyproject.toml | grep '=' | head -1 | sed -E 's/.*=[[:space:]]*"([^"]+)".*/\1/' | cut -d: -f1)
      [ -n "$ep" ] && [ -f "$ep" ] && ENTRY="$ep"
    fi
    case "$SUBTYPE" in
      desktop-gui)
        pyinstaller --noconfirm --clean --name "App" --windowed --onedir \
          --add-data "assets;assets" "$ENTRY"
        # Qt plugin fix (PySide6 / PyQt5)
        python -c "
import os, site
_SITE = next((p for p in site.getsitepackages()
              if os.path.isdir(os.path.join(p, 'PySide6')) or
                 os.path.isdir(os.path.join(p, 'PyQt5'))), None)
if _SITE:
    for pkg in ('PySide6', 'PyQt5'):
        plug = os.path.join(_SITE, pkg, 'plugins')
        if os.path.isdir(plug):
            print(f'Qt plugin found: {plug}')
"
        bash .github/scripts/make-nsis.sh
        mv dist/*.exe "dist/App-${VERSION}-windows-x64.exe" 2>/dev/null || true
        ;;
      cli)
        pyinstaller --noconfirm --clean --name "App" --onefile "$ENTRY"
        mv dist/App.exe "dist/App-${VERSION}-windows-x64.exe" 2>/dev/null || true
        ;;
      *)
        echo "::warning::Python subtype '$SUBTYPE' not packaged on windows"
        exit 0
        ;;
    esac
    ;;
  macos)
    pip install --upgrade pip
    pip install -r requirements.txt 2>/dev/null || pip install .
    pip install pyinstaller
    ENTRY="main.py"
    pyinstaller --noconfirm --clean --name "App" --windowed --onedir \
      --add-data "assets:assets" "$ENTRY"
    bash .github/scripts/make-dmg.sh
    mv dist/*.dmg "dist/App-${VERSION}-macos-universal.dmg" 2>/dev/null || true
    ;;
  linux)
    pip install --upgrade pip
    pip install -r requirements.txt 2>/dev/null || pip install .
    pip install pyinstaller
    ENTRY="main.py"
    pyinstaller --noconfirm --clean --name "App" --windowed --onedir \
      --add-data "assets:assets" "$ENTRY"
    bash .github/scripts/make-appimage.sh
    bash .github/scripts/make-deb.sh
    ;;
  android|ios)
    echo "::notice::Python stack does not support platform '$PLATFORM' (use flutter for mobile)"
    exit 0
    ;;
esac
