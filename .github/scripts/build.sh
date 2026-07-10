#!/usr/bin/env bash
# .github/scripts/build.sh — dispatches to stack-specific build script
# Required env: STACK, PLATFORM, VERSION
set -euo pipefail
: "${STACK:?STACK env required}"
: "${PLATFORM:?PLATFORM env required}"
: "${VERSION:?VERSION env required}"

cd "$GITHUB_WORKSPACE"
mkdir -p dist

# The actual build scripts are copied by the skill into .github/scripts/build-<stack>.sh
SCRIPT=".github/scripts/build-${STACK}.sh"
if [ ! -f "$SCRIPT" ]; then
  echo "::warning::No build script for stack '$STACK' (looking for $SCRIPT)"
  echo "::warning::This stack is not yet supported in v1. Skipping."
  exit 0
fi

bash "$SCRIPT"
