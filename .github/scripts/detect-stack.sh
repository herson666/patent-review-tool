#!/usr/bin/env bash
# bin/detect-stack.sh — output stack detection JSON to stdout
# Exit code: 0 = detected, 1 = unknown (caller decides next step)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/_lib.sh"
check_dependencies

# Run all detectors, write findings to a temp JSON
RESULT=$(mktemp)
trap 'rm -f "$RESULT"' EXIT

jq -n '{}' > "$RESULT"
update() {
  # update 'key' 'value'
  local tmp
  tmp=$(mktemp)
  jq --arg k "$1" --arg v "$2" '. + {($k): $v}' "$RESULT" > "$tmp" && mv "$tmp" "$RESULT"
}

# --- 1. flutter ---
if [ -f pubspec.yaml ] && grep -q '^flutter:' pubspec.yaml 2>/dev/null; then
  update stack "flutter"
  update build_tool "flutter-cli"
  update entry_point "lib/main.dart"
  update config_files "$(jq -c '.' < <(printf '%s' "[\"pubspec.yaml\"]"))"
  if grep -q 'version:' pubspec.yaml 2>/dev/null; then
    v=$(grep '^version:' pubspec.yaml | head -1 | sed -E 's/^version:[[:space:]]*([0-9]+\.[0-9]+\.[0-9]+).*/\1/')
    [ -n "$v" ] && update version "$v"
  fi
fi

# --- 2. tauri ---
if [ -z "$(jq -r '.stack // empty' "$RESULT")" ] && [ -f src-tauri/tauri.conf.json ]; then
  update stack "tauri"
  update build_tool "tauri-cli"
  update entry_point "src-tauri/"
  update config_files "$(jq -c '.' < <(printf '%s' "[\"src-tauri/tauri.conf.json\"]"))"
fi

# --- 3. rust ---
if [ -z "$(jq -r '.stack // empty' "$RESULT")" ] && [ -f Cargo.toml ]; then
  update stack "rust"
  update build_tool "cargo-bundle"
  # Try to find [[bin]] name
  bin_name=$(grep -A1 '\[\[bin\]\]' Cargo.toml 2>/dev/null | grep '^name' | head -1 | sed -E 's/^name[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/')
  if [ -n "$bin_name" ]; then
    update entry_point "$bin_name"
  else
    # Try [package].name
    pkg_name=$(grep -A2 '^\[package\]' Cargo.toml | grep '^name' | head -1 | sed -E 's/^name[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/')
    [ -n "$pkg_name" ] && update entry_point "$pkg_name"
  fi
  v=$(grep '^version' Cargo.toml | head -1 | sed -E 's/version[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/')
  [ -n "$v" ] && update version "$v"
fi

# --- 4. go ---
if [ -z "$(jq -r '.stack // empty' "$RESULT")" ] && [ -f go.mod ]; then
  update stack "go"
  update build_tool "go-build"
  update entry_point "main.go"
  # Extract module name (first line) for version derivation if needed
fi

# --- 5. java ---
if [ -z "$(jq -r '.stack // empty' "$RESULT")" ] && { [ -f pom.xml ] || ls build.gradle* >/dev/null 2>&1; }; then
  update stack "java"
  update build_tool "jpackage"
  if [ -f pom.xml ]; then
    update entry_point "pom.xml"
  else
    update entry_point "build.gradle"
  fi
fi

# --- 6. dotnet ---
if [ -z "$(jq -r '.stack // empty' "$RESULT")" ] && { ls *.csproj >/dev/null 2>&1 || ls *.sln >/dev/null 2>&1; }; then
  update stack "dotnet"
  update build_tool "dotnet-publish"
  update entry_point "$(ls *.csproj 2>/dev/null | head -1 || ls *.sln 2>/dev/null | head -1)"
fi

# --- 7. package.json (with Node sub-branches) ---
if [ -z "$(jq -r '.stack // empty' "$RESULT")" ] && [ -f package.json ]; then
  has_dep() { jq -e --arg d "$1" '[(.dependencies // {}), (.devDependencies // {})] | map(has($d)) | any' package.json >/dev/null 2>&1; }
  if has_dep electron-builder || has_dep electron; then
    update stack "electron"
    update build_tool "electron-builder"
  elif has_dep @neutralinojs/neu; then
    update stack "neutralino"
    update build_tool "neutralinojs-cli"
  elif has_dep pkg || has_dep nexe || has_dep "@vercel/ncc"; then
    update stack "node-cli"
    update build_tool "pkg"
  else
    update stack "node"
    update build_tool "ncc"
  fi
  # entry point
  main=$(jq -r '.main // empty' package.json 2>/dev/null)
  if [ -n "$main" ]; then
    update entry_point "$main"
  else
    update entry_point "index.js"
  fi
  # version
  v=$(jq -r '.version // empty' package.json 2>/dev/null)
  [ -n "$v" ] && update version "$v"
fi

# --- 8. python ---
if [ -z "$(jq -r '.stack // empty' "$RESULT")" ] && { [ -f pyproject.toml ] || [ -f setup.py ] || [ -f requirements.txt ]; }; then
  update stack "python"
  # Determine subtype from dependencies
  subtype="library"
  gui_framework=""
  py_deps=""
  if [ -f pyproject.toml ]; then
    py_deps=$(grep -E '^[[:space:]]*[\"a-zA-Z]' pyproject.toml | tr -d ' ' || true)
  fi
  if [ -f requirements.txt ]; then
    py_deps="$py_deps $(cat requirements.txt | tr -d ' ' || true)"
  fi
  case "$py_deps" in
    *PySide6*|*PyQt5*|*PyQt6*|*wxpython*|*wxPython*|*tkinter*) subtype="desktop-gui"; gui_framework=$(echo "$py_deps" | grep -oiE 'PySide6|PyQt5|PyQt6|wxPython|tkinter' | head -1) ;;
    *click*|*typer*|*argparse*) subtype="cli" ;;
    *fastapi*|*django*|*flask*|*starlette*) subtype="web" ;;
  esac
  update subtype "$subtype"
  [ -n "$gui_framework" ] && update gui_framework "$gui_framework"
  update build_tool "pyinstaller"
  update entry_point "main.py"
  # version
  if [ -f pyproject.toml ]; then
    v=$(grep -E '^version[[:space:]]*=' pyproject.toml | head -1 | sed -E 's/version[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/')
    [ -n "$v" ] && update version "$v"
  fi
fi

# --- 9. ios-native (no pubspec.yaml to avoid flutter collision) ---
if [ -z "$(jq -r '.stack // empty' "$RESULT")" ] && { ls *.xcodeproj >/dev/null 2>&1 || ls *.xcworkspace >/dev/null 2>&1 || [ -f Podfile ]; }; then
  update stack "ios-native"
  update build_tool "xcodebuild"
  update entry_point "$(ls *.xcodeproj 2>/dev/null | head -1 || ls *.xcworkspace 2>/dev/null | head -1)"
fi

# --- 10. android-native (no pubspec.yaml) ---
if [ -z "$(jq -r '.stack // empty' "$RESULT")" ] && [ -d android ] && { [ -f android/AndroidManifest.xml ] || [ -f android/app/src/main/AndroidManifest.xml ]; }; then
  update stack "android-native"
  update build_tool "gradle"
  update entry_point "android/app"
fi

# --- Try git describe for version if still missing ---
if [ -z "$(jq -r '.version // empty' "$RESULT")" ] && git describe --tags --abbrev=0 >/dev/null 2>&1; then
  tag=$(git describe --tags --abbrev=0 | sed 's/^v//')
  update version "$tag"
fi

# --- Output ---
if [ -z "$(jq -r '.stack // empty' "$RESULT")" ]; then
  echo '{"stack":"unknown"}'
  exit 1
fi

# Ensure config_files is at least an empty array
tmp=$(mktemp)
jq '. + {config_files: (.config_files // [])}' "$RESULT" > "$tmp" && mv "$tmp" "$RESULT"

cat "$RESULT"
