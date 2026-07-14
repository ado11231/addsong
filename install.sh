#!/usr/bin/env bash
# One command installer for addsong on Linux, WSL, Git Bash, and macOS.
#
# Installs yt-dlp and ffmpeg (if missing), then installs the addsong Python
# package via pipx (preferred) or pip --user, which puts the `addsong`
# console-script on your PATH.
#
# Usage
#   curl -fsSL https://ado11231.github.io/addsong/install.sh | bash
#
# macOS users can also use: brew install ado11231/tap/addsong
#
# Honors NO_COLOR (https://no-color.org/). Override the download ref with
# ADDSONG_REF (defaults to main) and the install dir with ADDSONG_BIN_DIR.
set -euo pipefail

REPO="ado11231/apple-music-pipeline"
REF="${ADDSONG_REF:-main}"

# Messaging TTY and NO_COLOR aware like addsong.
C_INFO=""; C_OK=""; C_WARN=""; C_ERR=""; C_RESET=""
if [[ -t 2 && -z "${NO_COLOR:-}" ]]; then
  C_INFO=$'\033[1m'; C_OK=$'\033[32m'; C_WARN=$'\033[33m'
  C_ERR=$'\033[1;31m'; C_RESET=$'\033[0m'
fi
info() { printf '%s%s%s\n' "$C_INFO" "$*" "$C_RESET" >&2; }
ok()   { printf '  %s%s%s\n' "$C_OK"   "$*" "$C_RESET" >&2; }
warn() { printf '  %s%s%s\n' "$C_WARN" "$*" "$C_RESET" >&2; }
die()  { printf '%sinstall:%s %s\n' "$C_ERR" "$C_RESET" "$*" >&2; exit 1; }

# Platform detection mirrors addsong.detect_os.
detect_os() {
  case "${OSTYPE:-}" in
    darwin*)        echo mac ;;
    msys*|cygwin*)  echo win ;;
    linux*)
      if [[ -r /proc/sys/kernel/osrelease ]] \
         && grep -qi microsoft /proc/sys/kernel/osrelease 2>/dev/null; then
        echo wsl
      else
        echo linux
      fi ;;
    *)              echo other ;;
  esac
}

# Run a command with sudo when not root and sudo exists.
as_root() {
  if [[ "$(id -u)" -eq 0 ]]; then "$@"
  elif command -v sudo >/dev/null 2>&1; then sudo "$@"
  else die "need root to install packages, but 'sudo' is not available. Re-run as root or install $* manually."
  fi
}

# Detect a package manager and install the named packages.
install_pkgs() {
  local pkgs=("$@") pm=""
  for c in pacman apt-get dnf yum zypper brew choco; do
    command -v "$c" >/dev/null 2>&1 && { pm="$c"; break; }
  done
  [[ -n "$pm" ]] || die "no supported package manager found. Please install: ${pkgs[*]}"
  info "Installing ${pkgs[*]} with $pm ..."
  case "$pm" in
    pacman)  as_root pacman -S --needed --noconfirm "${pkgs[@]}" ;;
    apt-get) as_root apt-get update && as_root apt-get install -y "${pkgs[@]}" ;;
    dnf)     as_root dnf install -y "${pkgs[@]}" ;;
    yum)     as_root yum install -y "${pkgs[@]}" ;;
    zypper)  as_root zypper install -y "${pkgs[@]}" ;;
    brew)    brew install "${pkgs[@]}" ;;        # never run brew as root
    choco)   choco install -y "${pkgs[@]}" ;;
  esac
}

# Preflight
command -v curl >/dev/null 2>&1 || die "curl is required to run this installer."
OS="$(detect_os)"
info "addsong installer  (platform: $OS)"

# Python is required.
if ! command -v python3 >/dev/null 2>&1; then
  warn "python3 missing -- installing ..."
  install_pkgs python3
fi

# Dependencies (the Python package's external binaries).
info "Checking dependencies ..."
missing=()
for dep in yt-dlp ffmpeg; do
  if command -v "$dep" >/dev/null 2>&1; then
    ok "$dep found"
  else
    warn "$dep missing"
    missing+=("$dep")
  fi
done
[[ ${#missing[@]} -gt 0 ]] && install_pkgs "${missing[@]}"

# Install addsong from the source archive.
ARCHIVE_URL="https://github.com/$REPO/archive/refs/heads/$REF.tar.gz"
info "Downloading addsong source ($REF) ..."
TMPDIR_INSTALL="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_INSTALL"' EXIT
curl -fsSL "$ARCHIVE_URL" -o "$TMPDIR_INSTALL/addsong.tar.gz" \
  || die "download failed: $ARCHIVE_URL"
mkdir -p "$TMPDIR_INSTALL/src"
tar -xzf "$TMPDIR_INSTALL/addsong.tar.gz" -C "$TMPDIR_INSTALL/src" --strip-components=1 \
  || die "extract failed"
SRC_DIR="$TMPDIR_INSTALL/src"

# Prefer pipx for an isolated, PATH-friendly install; fall back to pip --user.
info "Installing addsong ..."
if command -v pipx >/dev/null 2>&1; then
  pipx install "$SRC_DIR" || die "pipx install failed"
else
  python3 -m pip install --user --upgrade "$SRC_DIR" \
    || die "pip install failed (try: pipx install addsong)"
fi

# Verify
ok "Installed: $(addsong --version 2>/dev/null || echo addsong)"
info "Done. Try:  addsong \"songname\""