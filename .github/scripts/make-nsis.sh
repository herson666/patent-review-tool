#!/usr/bin/env bash
# .github/scripts/make-nsis.sh — wrap PyInstaller output in NSIS installer
set -euo pipefail
cd "$GITHUB_WORKSPACE"

# Install NSIS (Windows runner)
if ! command -v makensis >/dev/null; then
  echo "Installing NSIS..."
  choco install nsis -y --no-progress 2>/dev/null || \
    echo "::warning::NSIS not installed; using makensis if available"
fi

# Use spec-file-based approach; assume App/app.exe or App/App.exe exists in dist
if [ ! -d "dist/App" ] && [ ! -d "dist/App/_internal" ]; then
  echo "::error::Expected dist/App/ from PyInstaller"
  exit 1
fi

# Generate NSIS script on-the-fly
cat > /tmp/installer.nsi <<'NSIS_EOF'
Unicode True
SetCompressor /SOLID lzma
!define APP_NAME "App"
!define APP_VERSION "0.0.0"
!define APP_EXE "App.exe"

Name "${APP_NAME} v${APP_VERSION}"
OutFile "dist/App-setup.exe"
InstallDir "$PROGRAMFILES64\${APP_NAME}"
RequestExecutionLevel admin

!include "MUI2.nsh"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_LANGUAGE "English"

Section "Main"
  SectionIn RO
  SetOutPath "$INSTDIR"
  File /r "dist\App\*"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  CreateShortcut "$SMPROGRAMS\App.lnk" "$INSTDIR\${APP_EXE}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\App" \
    "UninstallString" '"$INSTDIR\Uninstall.exe"'
SectionEnd

Section "Uninstall"
  RMDir /r "$INSTDIR"
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\App"
SectionEnd
NSIS_EOF

VERSION="${VERSION:-0.0.0}"
sed -i "s|\${APP_VERSION}|$VERSION|g" /tmp/installer.nsi

# Copy dist contents to a flat location for NSIS
mkdir -p nsis-build
cp -r dist/App/* nsis-build/ 2>/dev/null || cp -r dist/App nsis-build/
# Adjust File path in NSIS
sed -i "s|dist\\\\App\\\\|nsis-build\\\\|g" /tmp/installer.nsi 2>/dev/null || true
sed -i 's|dist\\App\\|nsis-build\\|g' /tmp/installer.nsi 2>/dev/null || true
mv /tmp/installer.nsi ./installer.nsi

makensis installer.nsi || die "NSIS build failed"
rm -rf nsis-build installer.nsi
echo "NSIS installer built: dist/App-setup.exe"
