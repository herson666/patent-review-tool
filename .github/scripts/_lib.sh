#!/usr/bin/env bash
# bin/_lib.sh — shared helpers for github-multiplatform-packager
# Source this from other bin/*.sh scripts: `. "$(dirname "$0")/_lib.sh"`
set -euo pipefail

# ---- Logging ----------------------------------------------------------------
log()  { printf '[%s] [packager] %s\n' "$(date +%H:%M:%S)" "$*" >&2; }
ok()   { log "✅ $*"; }
warn() { log "⚠️  $*"; }
die()  { log "❌ $*"; exit 1; }
debug_log() { [ "${DEBUG:-}" = "1" ] && log "[debug] $*"; }

# ---- Environment helpers ----------------------------------------------------
require_env() {
  for v in "$@"; do
    if [ -z "${!v:-}" ]; then
      die "缺少环境变量: $v"
    fi
  done
}

# macOS-compatible ISO 8601 timestamp (replacement for GNU date -u +%Y-%m-%dT%H:%M:%SZ)
iso_timestamp() {
  if command -v gdate >/dev/null 2>&1; then
    gdate -u +%Y-%m-%dT%H:%M:%SZ
  else
    # Pure shell: parse `date -u` output (BSD/macOS compatible format: "Thu Jun 12 10:30:45 UTC 2026")
    date -u "+%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || python3 -c "import datetime; print(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'))"
  fi
}

# ---- Dependency check -------------------------------------------------------
check_dependencies() {
  local missing=()
  for tool in git curl jq; do
    command -v "$tool" >/dev/null 2>&1 || missing+=("$tool")
  done

  if [ ${#missing[@]} -eq 0 ]; then
    return 0
  fi

  local os pkg_mgr install_cmd
  os=$(uname -s)
  case "$os" in
    Linux)
      if   command -v apt-get >/dev/null; then pkg_mgr="apt"
      elif command -v dnf     >/dev/null; then pkg_mgr="dnf"
      elif command -v yum     >/dev/null; then pkg_mgr="yum"
      elif command -v apk     >/dev/null; then pkg_mgr="apk"
      elif command -v pacman  >/dev/null; then pkg_mgr="pacman"
      else pkg_mgr="unknown"
      fi
      case "$pkg_mgr" in
        apt)         install_cmd="sudo apt-get install -y ${missing[*]}" ;;
        dnf|yum)     install_cmd="sudo $pkg_mgr install -y ${missing[*]}" ;;
        apk)         install_cmd="sudo apk add ${missing[*]}" ;;
        pacman)      install_cmd="sudo pacman -S --noconfirm ${missing[*]}" ;;
        *)           install_cmd="# 未识别的包管理器（$os），请手动安装：${missing[*]}" ;;
      esac
      ;;
    Darwin)
      if command -v brew >/dev/null; then
        install_cmd="brew install ${missing[*]}"
      else
        install_cmd="# macOS 缺少 Homebrew，请先安装 https://brew.sh ，然后执行: brew install ${missing[*]}"
      fi
      ;;
    MINGW*|MSYS*|CYGWIN*)
      if   command -v winget >/dev/null; then install_cmd="winget install --id=Git.Git jqlang.jq cURL.cURL"
      elif command -v choco  >/dev/null; then install_cmd="choco install -y git jq curl"
      else install_cmd="# Windows Git Bash：请用 MSYS2 的 pacman： pacman -S ${missing[*]}"
      fi
      ;;
    *)
      install_cmd="# 未识别的操作系统：$os，请手动安装：${missing[*]}"
      ;;
  esac

  warn "缺少必要工具：${missing[*]}"
  log "📋 推荐安装命令（$os / ${pkg_mgr:-无}）："
  log "   $install_cmd"
  echo
  printf "是否现在执行安装? [y/N] "
  read -r ans
  case "$ans" in
    y|Y|yes|YES)
      log "执行: $install_cmd"
      eval "$install_cmd" || die "安装失败，请手动处理"
      ;;
    *)
      die "缺少必要工具，已退出"
      ;;
  esac
}

# ---- GitHub API helpers -----------------------------------------------------
gh_api() {
  # Usage: gh_api METHOD PATH [DATA]
  # Returns response body; sets GH_HTTP_CODE in env
  local method="$1" path="$2" data="${3:-}"
  local url="https://api.github.com$path"
  local args=(-sS -X "$method" -H "Authorization: token $GITHUB_TOKEN"
              -H "Accept: application/vnd.github+json"
              -H "User-Agent: github-multiplatform-packager"
              -w "\n%{http_code}")
  if [ -n "$data" ]; then
    args+=(-H "Content-Type: application/json" -d "$data")
  fi
  local response
  response=$(curl "${args[@]}" "$url")
  # shellcheck disable=SC2034 # GH_HTTP_CODE is intentionally exported for callers (see push-to-gh.sh)
  GH_HTTP_CODE=$(printf '%s' "$response" | tail -n1)
  printf '%s' "$response" | sed '$d'
}

# ---- JSON helpers -----------------------------------------------------------
# Use jq for everything; this is a thin wrapper for consistent error messages
jq_get() {
  # Usage: jq_get '.field' file.json
  local filter="$1" file="$2"
  jq -r "$filter" "$file" 2>/dev/null || die "jq 解析失败: $file"
}

# ---- Git helpers ------------------------------------------------------------
git_user_email() {
  git config user.email 2>/dev/null || echo "noreply@github.com"
}
git_user_name() {
  git config user.name 2>/dev/null || echo "github-multiplatform-packager"
}

# ---- Cross-platform helper --------------------------------------------------
open_url() {
  # Cross-platform: open a URL in the default browser
  local url="$1"
  case "$(uname -s)" in
    Darwin) open "$url" ;;
    MINGW*|MSYS*|CYGWIN*) start "$url" ;;
    Linux) command -v xdg-open >/dev/null && xdg-open "$url" ;;
  esac
}

# ---- Trae IDE credential extraction ----------------------------------------
# Trae IDE does not expose its internal GitHub token to shell scripts.
# These functions probe documented/semi-documented locations where the token
# may already exist, in priority order:
#   1. ~/.trae/mcp.json or ./.trae/mcp.json  (Trae's MCP server config)
#   2. ~/.git-credentials                    (git credential.helper=store)
#   3. OS keychain (macOS Keychain / Windows Credential Manager / libsecret)
#   4. TRAE_* / VSCode-specific env vars

# Returns 0 + token on stdout if found in any .trae/mcp.json
extract_trae_mcp_token() {
  local mcp_file token
  for mcp_file in "$HOME/.trae/mcp.json" "./.trae/mcp.json"; do
    [ -f "$mcp_file" ] || continue
    # Look for a server entry whose name matches github (case-insensitive)
    # and extract its env.GITHUB_TOKEN (or env.GH_TOKEN)
    token=$(jq -r '
      (.mcpServers // {}) as $servers |
      $servers | to_entries[] |
      select(.key | test("github"; "i")) |
      .value.env.GITHUB_TOKEN // .value.env.GH_TOKEN // .value.env.GH_TOKEN // empty
    ' "$mcp_file" 2>/dev/null | head -1)
    if [ -n "$token" ] && [ "$token" != "null" ]; then
      printf '%s' "$token"
      return 0
    fi
  done
  return 1
}

# Returns 0 + token on stdout if found in ~/.git-credentials
extract_git_credentials_token() {
  local creds="${HOME}/.git-credentials"
  [ -f "$creds" ] || return 1
  # Match the github.com line, parse https://USER:TOKEN@github.com
  local line
  line=$(grep -E 'github\.com' "$creds" 2>/dev/null | head -1) || return 1
  [ -n "$line" ] || return 1
  local parsed
  parsed=$(printf '%s' "$line" | sed -nE 's|^[[:space:]]*https?://[^:]+:([^@]+)@github\.com.*$|\1|p')
  [ -n "$parsed" ] || return 1
  printf '%s' "$parsed"
}

# Returns 0 + token on stdout if found in OS keychain
extract_keychain_token() {
  case "$(uname -s)" in
    Darwin)
      # macOS Keychain — Trae may store under service=github.com
      security find-generic-password -s "github.com" -w 2>/dev/null && return 0
      # Some tools use "GitHub" with capital H
      security find-generic-password -s "GitHub" -w 2>/dev/null && return 0
      return 1
      ;;
    MINGW*|MSYS*|CYGWIN*)
      # Windows Credential Manager via PowerShell
      # shellcheck disable=SC2016  # Expressions are intentionally literal in PowerShell heredoc
      powershell.exe -NoProfile -Command '
        $sig = @"
          [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Auto)]
          public struct CREDENTIAL {
            public uint Flags; public uint Type; public IntPtr TargetName;
            public IntPtr Comment; public System.Runtime.InteropServices.ComTypes.FILETIME LastWritten;
            public uint CredentialBlobSize; public IntPtr CredentialBlob;
            public uint Persist; public uint AttributeCount; public IntPtr Attributes;
            public IntPtr TargetAlias; public IntPtr UserName;
          }
"@
        Add-Type -MemberDefinition @"
          [DllImport("Advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
          public static extern bool CredRead(string target, uint type, uint flags, out IntPtr credential);
          [DllImport("Advapi32.dll", SetLastError=true)]
          public static extern void CredFree(IntPtr buffer);
"@ -Name WinCred -Namespace Utils -UsingNamespace System.Runtime.InteropServices
        $ptr = [IntPtr]::Zero
        if ([Utils.WinCred]::CredRead("github.com", 1, 0, [ref]$ptr)) {
          $cred = [System.Runtime.InteropServices.Marshal]::PtrToStructure($ptr, [type][Utils.WinCred+CREDENTIAL])
          $bytes = New-Object byte[] $cred.CredentialBlobSize
          [System.Runtime.InteropServices.Marshal]::Copy($cred.CredentialBlob, $bytes, 0, $cred.CredentialBlobSize)
          [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bytes)
          [Utils.WinCred]::CredFree($ptr) | Out-Null
        }
      ' 2>/dev/null
      ;;
    Linux)
      # Linux libsecret via secret-tool (if installed)
      if command -v secret-tool >/dev/null 2>&1; then
        secret-tool lookup service github.com 2>/dev/null && return 0
        secret-tool lookup application trae 2>/dev/null && return 0
      fi
      return 1
      ;;
  esac
  return 1
}

# Returns 0 + token on stdout if TRAE/VSCode env var is set
extract_trae_env_token() {
  local var
  for var in TRAE_GITHUB_TOKEN TRAE_GH_TOKEN GITHUB_TOKEN_VSCODE VSCODE_GITHUB_TOKEN; do
    if [ -n "${!var:-}" ]; then
      printf '%s' "${!var}"
      debug_log "Found $var env var"
      return 0
    fi
  done
  return 1
}

# Run all 4 probes in priority order.
# On success: token is on stdout, source name is on stderr.
# On failure: returns 1 with no output.
discover_github_token() {
  local token
  if token=$(extract_trae_env_token); then
    echo "TRAE_* env var" >&2
    printf '%s' "$token"
    return 0
  fi
  if token=$(extract_trae_mcp_token); then
    echo ".trae/mcp.json" >&2
    printf '%s' "$token"
    return 0
  fi
  if token=$(extract_git_credentials_token); then
    printf 'git-credentials file\n' >&2
    printf '%s' "$token"
    return 0
  fi
  if token=$(extract_keychain_token); then
    echo "OS keychain" >&2
    printf '%s' "$token"
    return 0
  fi
  return 1
}

# ---- GitHub CLI auth (preferred over GITHUB_TOKEN env var) -----------------
ensure_gh_cli() {
  # Fast path: GITHUB_TOKEN env var already set
  if [ -n "${GITHUB_TOKEN:-}" ]; then
    debug_log "Using existing GITHUB_TOKEN env var"
    return 0
  fi

  # Probe Trae IDE credential sources (in priority order) before falling
  # back to interactive gh auth login. Each probe is best-effort.
  local discovered_token=""
  local discovered_source=""

  # discover_github_token writes source to stderr, token to stdout
  discovered_source=$(discover_github_token 2>&1 >/dev/null) || true
  if [ -n "$discovered_source" ]; then
    discovered_token=$(discover_github_token 2>/dev/null)
    warn "使用 Trae IDE 凭据: $discovered_source（无需额外配置）"
  fi

  if [ -n "$discovered_token" ]; then
    GITHUB_TOKEN="$discovered_token"
    export GITHUB_TOKEN
    # Fetch username from GitHub API (works without gh CLI)
    if command -v curl >/dev/null 2>&1; then
      GITHUB_USER=$(curl -sS -H "Authorization: token $GITHUB_TOKEN" \
        -H "User-Agent: github-multiplatform-packager" \
        https://api.github.com/user 2>/dev/null | jq -r .login 2>/dev/null) || GITHUB_USER=""
    fi
    if [ -n "$GITHUB_USER" ] && [ "$GITHUB_USER" != "null" ]; then
      export GITHUB_USER
      ok "GitHub 鉴权完成 (via $discovered_source): $GITHUB_USER"
      return 0
    fi
    warn "token 解析成功但获取用户名失败，将继续走 gh CLI 流程"
  fi

  # Detect if gh is installed
  if ! command -v gh >/dev/null 2>&1; then
    warn "gh CLI 未安装，正在自动下载..."
    install_gh_cli || die "gh CLI 安装失败，请手动安装 https://cli.github.com 或设置 GITHUB_TOKEN 环境变量"
  fi

  # Check if already authenticated
  if gh auth status >/dev/null 2>&1; then
    debug_log "gh CLI 已登录"
  else
    warn "gh CLI 未登录，请选择登录方式："
    echo "  [1] 浏览器 OAuth 流程（推荐，会自动打开浏览器）"
    echo "  [2] 粘贴已有 GitHub Personal Access Token"
    printf "选择 [1/2]: "
    read -r choice
    case "$choice" in
      1|"" ) gh auth login -h github.com -p https -s 'repo,workflow' --web ;;
      2)
        printf "粘贴 token: "
        read -r token
        [ -n "$token" ] || die "未输入 token"
        printf '%s\n' "$token" | gh auth login --with-token
        # Ensure scopes are sufficient (PAT may have been created with limited scopes)
        warn "请确认 token 包含 'repo' 和 'workflow' scopes（GitHub Settings → Developer settings → PAT）"
        ;;
      *) die "未选择登录方式，已退出" ;;
    esac
  fi

  # Export GITHUB_TOKEN and GITHUB_USER for downstream use
  GITHUB_TOKEN=$(gh auth token 2>/dev/null) || die "无法从 gh CLI 获取 token"
  export GITHUB_TOKEN
  GITHUB_USER=$(gh api user -q .login 2>/dev/null) || die "无法从 GitHub API 获取用户名"
  export GITHUB_USER
  ok "GitHub 鉴权完成: $GITHUB_USER"
}

install_gh_via_rpm() {
  # Helper for dnf|yum: try prebuilt rpm from cli/cli releases, fallback to native package
  local pkg_mgr="$1"
  local rpm_url
  rpm_url="https://github.com/cli/cli/releases/download/v2.62.0/gh-2.62.0-1.${pkg_mgr}.$(uname -m).rpm"
  case "$pkg_mgr" in
    dnf)
      sudo dnf install -y "$rpm_url" 2>/dev/null || sudo dnf install -y gh
      ;;
    yum)
      sudo yum install -y "$rpm_url" 2>/dev/null || sudo yum install -y gh
      ;;
  esac
}

install_gh_cli() {
  local os pkg_mgr
  os=$(uname -s)
  case "$os" in
    Linux)
      if command -v apt-get >/dev/null; then
        pkg_mgr="apt"
      elif command -v dnf >/dev/null; then
        pkg_mgr="dnf"
      elif command -v yum >/dev/null; then
        pkg_mgr="yum"
      fi

      case "$pkg_mgr" in
        apt)
          log "通过 apt 仓库安装 gh..."
          (curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.asc | sudo gpg --dearmor -o /usr/share/keyrings/githubcli-archive-keyring.gpg) 2>/dev/null && \
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null && \
            sudo apt-get update -qq && \
            sudo apt-get install -y gh
          ;;
        dnf|yum)
          log "通过 $pkg_mgr 仓库安装 gh..."
          install_gh_via_rpm "$pkg_mgr"
          ;;
        *)
          log "未识别的包管理器，下载 binary..."
          local gh_version
          gh_version=$(curl -sS https://api.github.com/repos/cli/cli/releases/latest | jq -r .tag_name)
          local gh_archive="gh_${gh_version#v}_linux_amd64.tar.gz"
          curl -sSL "https://github.com/cli/cli/releases/download/${gh_version}/${gh_archive}" -o "/tmp/${gh_archive}"
          tar -xzf "/tmp/${gh_archive}" -C /tmp/
          sudo mv "/tmp/gh_${gh_version#v}_linux_amd64/bin/gh" /usr/local/bin/
          rm -rf "/tmp/gh_${gh_version#v}_linux_amd64" "/tmp/${gh_archive}"
          ;;
      esac
      ;;
    Darwin)
      if command -v brew >/dev/null; then
        log "通过 brew 安装 gh..."
        brew install gh
      else
        log "未安装 brew，下载 macOS binary..."
        local gh_version
        gh_version=$(curl -sS https://api.github.com/repos/cli/cli/releases/latest | jq -r .tag_name)
        curl -sSL "https://github.com/cli/cli/releases/download/${gh_version}/gh_${gh_version#v}_macOS_universal.tar.gz" -o /tmp/gh-macos.tar.gz
        tar -xzf /tmp/gh-macos.tar.gz -C /tmp/
        sudo mv "/tmp/gh_${gh_version#v}_macOS_universal/bin/gh" /usr/local/bin/
        rm -rf "/tmp/gh_${gh_version#v}_macOS_universal" /tmp/gh-macos.tar.gz
      fi
      ;;
    MINGW*|MSYS*|CYGWIN*)
      if command -v winget >/dev/null; then
        log "通过 winget 安装 gh..."
        winget install --id GitHub.cli
      elif command -v choco >/dev/null; then
        log "通过 choco 安装 gh..."
        choco install -y gh
      else
        log "Windows 需手动安装 gh: https://cli.github.com"
        return 1
      fi
      ;;
    *)
      warn "未识别的操作系统: $os"
      return 1
      ;;
  esac
  command -v gh >/dev/null 2>&1
}
