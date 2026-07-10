#!/usr/bin/env bash
# .github/scripts/make-nsis.sh — wrap PyInstaller output in NSIS installer
set -euo pipefail
cd "$GITHUB_WORKSPACE"

echo "==> PyInstaller dist/ contents:"
ls -la dist/ || true

# PyInstaller --onedir --windowed output:
#   dist/App/App.exe
#   dist/App/_internal/... (Python runtime + data)
EXPECT_APP="dist/App/App.exe"
if [ ! -f "$EXPECT_APP" ]; then
  echo "::error::Expected $EXPECT_APP from PyInstaller (got:)"
  find dist -maxdepth 3 -type f 2>/dev/null || true
  exit 1
fi

# Install NSIS if missing (windows-latest runners have choco pre-installed)
if ! command -v makensis >/dev/null 2>&1; then
  echo "==> Installing NSIS via Chocolatey..."
  choco install nsis -y --no-progress 2>&1 | tail -10
fi

if ! command -v makensis >/dev/null 2>&1; then
  echo "::error::makensis not found after install. NSIS install failed."
  exit 1
fi

VERSION="${VERSION:-0.0.0}"
APP_NAME="PatentReviewTool"
APP_EXE="App.exe"

# Generate NSIS script
cat > installer.nsi <<NSIS_EOF
Unicode True
SetCompressor /SOLID lzma
!define APP_NAME "${APP_NAME}"
!define APP_VERSION "${VERSION}"
!define APP_EXE "${APP_EXE}"

Name "\${APP_NAME} v\${APP_VERSION}"
OutFile "dist\${APP_NAME}-setup.exe"
InstallDir "\$PROGRAMFILES64\\\${APP_NAME}"
RequestExecutionLevel admin

!include "MUI2.nsh"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_LANGUAGE "SimpChinese"

Section "Main"
  SectionIn RO
  SetOutPath "\$INSTDIR"
  File /r "dist\\App\\*"
  WriteUninstaller "\$INSTDIR\\Uninstall.exe"
  CreateDirectory "\$SMPROGRAMS\\\${APP_NAME}"
  CreateShortcut "\$SMPROGRAMS\\\${APP_NAME}\\\${APP_NAME}.lnk" "\$INSTDIR\\\${APP_EXE}"
  CreateShortcut "\$DESKTOP\\\${APP_NAME}.lnk" "\$INSTDIR\\\${APP_EXE}"
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\\${APP_NAME}" \\
    "DisplayName" "\${APP_NAME}"
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\\${APP_NAME}" \\
    "DisplayVersion" "\${APP_VERSION}"
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\\${APP_NAME}" \\
    "UninstallString" '"\$INSTDIR\\Uninstall.exe"'
SectionEnd

Section "Uninstall"
  RMDir /r "\$INSTDIR"
  RMDir /r "\$SMPROGRAMS\\\${APP_NAME}"
  Delete "\$DESKTOP\\\${APP_NAME}.lnk"
  DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\\${APP_NAME}"
SectionEnd
NSIS_EOF

echo "==> Running makensis..."
makensis /V2 installer.nsi

rm -f installer.nsi
echo "==> NSIS installer built: dist/${APP_NAME}-setup.exe"
ls -la dist/
