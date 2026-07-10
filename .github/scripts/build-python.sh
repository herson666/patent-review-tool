#!/usr/bin/env bash
# .github/scripts/build-python.sh — Python app builder
# Supports: desktop-gui, cli subtypes
# Platforms: windows, macos, linux
set -euo pipefail
PLATFORM="${PLATFORM:?}"; VERSION="${VERSION:?}"

# Determine subtype
SUBTYPE="library"
if [ -f pyproject.toml ] || [ -f requirements.txt ]; then
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

    # Prefer spec file for predictable data + hidden imports
    if [ -f "App.spec" ]; then
      echo "==> Using App.spec"
      pyinstaller --noconfirm --clean App.spec
    else
      ENTRY="main.py"
      case "$SUBTYPE" in
        desktop-gui)
          # Add data dirs only if they exist
          ADD_DATA_ARGS=""
          [ -d "assets" ]   && ADD_DATA_ARGS="$ADD_DATA_ARGS --add-data assets;assets"
          [ -d "rules_kb" ] && ADD_DATA_ARGS="$ADD_DATA_ARGS --add-data rules_kb;rules_kb"
          pyinstaller --noconfirm --clean --name "App" --windowed --onedir $ADD_DATA_ARGS "$ENTRY"
          ;;
        cli)
          pyinstaller --noconfirm --clean --name "App" --onefile "$ENTRY"
          ;;
        *)
          echo "::warning::Python subtype '$SUBTYPE' not packaged on windows"
          exit 0
          ;;
      esac
    fi

    bash .github/scripts/make-nsis.sh
    mv dist/*.exe "dist/App-${VERSION}-windows-x64.exe" 2>/dev/null || true
    ;;

  macos)
    pip install --upgrade pip
    pip install -r requirements.txt 2>/dev/null || pip install .
    pip install pyinstaller
    if [ -f "App.spec" ]; then
      pyinstaller --noconfirm --clean App.spec
    else
      ENTRY="main.py"
      pyinstaller --noconfirm --clean --name "App" --windowed --onedir "$ENTRY"
    fi
    if [ -f ".github/scripts/make-dmg.sh" ]; then
      bash .github/scripts/make-dmg.sh
      mv dist/*.dmg "dist/App-${VERSION}-macos-universal.dmg" 2>/dev/null || true
    fi
    ;;

  linux)
    pip install --upgrade pip
    pip install -r requirements.txt 2>/dev/null || pip install .
    pip install pyinstaller
    if [ -f "App.spec" ]; then
      pyinstaller --noconfirm --clean App.spec
    else
      ENTRY="main.py"
      pyinstaller --noconfirm --clean --name "App" --windowed --onedir "$ENTRY"
    fi
    [ -f ".github/scripts/make-appimage.sh" ] && bash .github/scripts/make-appimage.sh
    [ -f ".github/scripts/make-deb.sh" ]      && bash .github/scripts/make-deb.sh
    ;;

  android|ios)
    echo "::notice::Python stack does not support platform '$PLATFORM' (use flutter for mobile)"
    exit 0
    ;;
esac
