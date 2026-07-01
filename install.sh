#!/usr/bin/env bash
# One command installer for addsong on Linux, WSL, Git Bash, and macOS as fallback.
# Installs yt-dlp and ffmpeg then puts addsong on your PATH.
#
# Usage
#   curl -fsSL https://ado11231.github.io/addsong/install.sh | bash
#
# macOS users should prefer brew install ado11231/tap/addsong
#
# Honors NO_COLOR (https://no-color.org/). Override the download ref with
# ADDSONG_REF (defaults to main) and the install dir with ADDSONG_BIN_DIR.
set -euo pipefail

REPO="ado11231/addsong"
REF="${ADDSONG_REF:-main}"
# Default install pulls from GitHub Pages. Pinning ADDSONG_REF to a tag or branch
# uses the raw URL so you can install a specific version.
if [[ "$REF" == "main" ]]; then
  RAW_URL="https://ado11231.github.io/addsong/addsong"
else
  RAW_URL="https://raw.githubusercontent.com/$REPO/$REF/addsong"
fi

# Messaging TTY and NO_COLOR aware like addsong
C_INFO=""; C_OK=""; C_WARN=""; C_ERR=""; C_RESET=""
if [[ -t 2 && -z "${NO_COLOR:-}" ]]; then
  C_INFO=$'\033[1m'; C_OK=$'\033[32m'; C_WARN=$'\033[33m'
  C_ERR=$'\033[1;31m'; C_RESET=$'\033[0m'
fi
info() { printf '%s%s%s\n' "$C_INFO" "$*" "$C_RESET" >&2; }
ok()   { printf '  %s%s%s\n' "$C_OK"   "$*" "$C_RESET" >&2; }
warn() { printf '  %s%s%s\n' "$C_WARN" "$*" "$C_RESET" >&2; }
die()  { printf '%sinstall:%s %s\n' "$C_ERR" "$C_RESET" "$*" >&2; exit 1; }

# Platform detection mirrors addsong detect_os
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

# Dependencies
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

# Install the script
# Prefer ~/.local/bin on PATH by default on modern distros, else ~/bin.
if [[ -n "${ADDSONG_BIN_DIR:-}" ]]; then
  BIN_DIR="$ADDSONG_BIN_DIR"
elif [[ ":$PATH:" == *":$HOME/.local/bin:"* ]]; then
  BIN_DIR="$HOME/.local/bin"
elif [[ ":$PATH:" == *":$HOME/bin:"* ]]; then
  BIN_DIR="$HOME/bin"
else
  BIN_DIR="$HOME/.local/bin"
fi
mkdir -p "$BIN_DIR" || die "cannot create $BIN_DIR"

info "Installing addsong -> $BIN_DIR/addsong"
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
curl -fsSL "$RAW_URL" -o "$tmp" || die "download failed: $RAW_URL"
grep -q '^VERSION=' "$tmp" || die "downloaded file does not look like addsong; aborting."
install -m 0755 "$tmp" "$BIN_DIR/addsong"

# PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
  rc="$HOME/.bashrc"
  [[ "${SHELL:-}" == *zsh* ]] && rc="$HOME/.zshrc"
  line="export PATH=\"$BIN_DIR:\$PATH\""
  marker="# added by addsong installer"
  if ! grep -qF "$marker" "$rc" 2>/dev/null; then
    printf '\n%s\n%s\n' "$marker" "$line" >> "$rc"
    warn "Added $BIN_DIR to PATH in $rc"
  fi
  warn "Open a new terminal (or run: source \"$rc\") so 'addsong' is found."
fi

# Verify
ok "Installed: $("$BIN_DIR/addsong" --version 2>/dev/null || echo addsong)"
info "Done. Try:  addsong \"songname\""
