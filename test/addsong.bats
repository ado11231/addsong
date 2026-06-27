#!/usr/bin/env bats
#
# Unit tests for addsong's pure helpers and config parsing. The script gates
# main() behind a source guard, so sourcing it loads the functions without
# parsing arguments, running preflight, or touching the network.

setup() {
  ADDSONG="${BATS_TEST_DIRNAME}/../addsong"
}

# Run a snippet with the script sourced, in an isolated subshell so the
# script's `set -euo pipefail` does not leak into the bats runner.
sourced() {
  run bash -c "source '$ADDSONG'; $1"
}

# --- clean_meta -----------------------------------------------------------

@test "clean_meta strips (Official Video)" {
  sourced "printf '%s' 'Never Gonna Give You Up (Official Video)' | clean_meta"
  [ "$status" -eq 0 ]
  [ "$output" = 'Never Gonna Give You Up' ]
}

@test "clean_meta strips [4K] and (Lyrics)" {
  sourced "printf '%s' 'Title [4K] (Lyrics)' | clean_meta"
  [ "$output" = 'Title' ]
}

@test "clean_meta strips (feat. X)" {
  sourced "printf '%s' 'Song (feat. Someone)' | clean_meta"
  [ "$output" = 'Song' ]
}

@test "clean_meta strips a trailing - Topic" {
  sourced "printf '%s' 'Some Artist - Topic' | clean_meta"
  [ "$output" = 'Some Artist' ]
}

@test "clean_meta collapses whitespace and trims ends" {
  sourced "printf '%s' '   Spaced     Out   ' | clean_meta"
  [ "$output" = 'Spaced Out' ]
}

@test "clean_meta leaves an already-clean title unchanged" {
  sourced "printf '%s' 'Bohemian Rhapsody' | clean_meta"
  [ "$output" = 'Bohemian Rhapsody' ]
}

# --- safe_name ------------------------------------------------------------

@test "safe_name replaces slashes, colons and backslashes" {
  # Pass the input through the environment to avoid backslash-quoting layers.
  export IN='AC/DC: Back\Black'
  run bash -c "source '$ADDSONG'; safe_name \"\$IN\""
  [ "$status" -eq 0 ]
  [ "$output" = 'AC_DC_ Back_Black' ]
}

@test "safe_name leaves a normal name unchanged" {
  sourced "safe_name 'Artist - Title'"
  [ "$output" = 'Artist - Title' ]
}

# --- config file parsing --------------------------------------------------

@test "config file supplies ADDSONG_* defaults" {
  cfg="$(mktemp)"
  printf 'ADDSONG_AUDIO_FORMAT=mp3\n' > "$cfg"
  run bash -c "ADDSONG_CONFIG='$cfg' source '$ADDSONG'; printf '%s' \"\$AUDIO_FORMAT\""
  rm -f "$cfg"
  [ "$output" = 'mp3' ]
}

@test "a real environment variable overrides the config file" {
  cfg="$(mktemp)"
  printf 'ADDSONG_AUDIO_FORMAT=mp3\n' > "$cfg"
  run bash -c "ADDSONG_CONFIG='$cfg' ADDSONG_AUDIO_FORMAT=flac source '$ADDSONG'; printf '%s' \"\$AUDIO_FORMAT\""
  rm -f "$cfg"
  [ "$output" = 'flac' ]
}

@test "config parser ignores comments and non-ADDSONG keys" {
  cfg="$(mktemp)"
  printf '# a comment\nEVIL=value\nADDSONG_AUDIO_FORMAT=ogg\n' > "$cfg"
  run bash -c "ADDSONG_CONFIG='$cfg' source '$ADDSONG'; printf '%s|%s' \"\$AUDIO_FORMAT\" \"\${EVIL:-unset}\""
  rm -f "$cfg"
  [ "$output" = 'ogg|unset' ]
}

@test "config parser strips surrounding quotes from values" {
  cfg="$(mktemp)"
  printf 'ADDSONG_AUDIO_FORMAT="wav"\n' > "$cfg"
  run bash -c "ADDSONG_CONFIG='$cfg' source '$ADDSONG'; printf '%s' \"\$AUDIO_FORMAT\""
  rm -f "$cfg"
  [ "$output" = 'wav' ]
}

# --- --search argument parsing -------------------------------------------
#
# main() is gated by the source guard, so to exercise arg parsing we run the
# script directly in a subshell with stubs on PATH (no yt-dlp/ffmpeg network).
# A fake yt-dlp answers the flat-playlist search-expansion call with canned IDs
# and the per-track metadata call with canned fields; --dry-run keeps it from
# touching the watch folder or ledger.

setup_stubs() {
  STUBBIN="$(mktemp -d)"
  WATCH="$(mktemp -d)"
  mkdir -p "$STUBBIN"
  cat > "$STUBBIN/yt-dlp" <<'STUB'
#!/usr/bin/env bash
for a in "$@"; do
  if [[ "$a" == "--flat-playlist" ]]; then
    last="${@: -1}"
    case "$last" in
      ytsearch2:*) printf 'AAA111\nBBB222\n' ;;
      ytsearch1:*) printf 'CCC333\n' ;;
      *)           printf 'PPP000\n' ;;
    esac
    exit 0
  fi
done
printf 'VID000\nTest Title\nTest Uploader\nNA\nNA\nNA\nNA\nNA\n'
STUB
  cat > "$STUBBIN/ffmpeg" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
  chmod +x "$STUBBIN/yt-dlp" "$STUBBIN/ffmpeg"
  export PATH="$STUBBIN:$PATH"
  export ADDSONG_WATCH_DIR="$WATCH"
  local ledger
  ledger="$(mktemp)"
  export ADDSONG_LEDGER="$ledger"
}

teardown_stubs() {
  rm -rf "$STUBBIN" "$WATCH"
  rm -f "$ADDSONG_LEDGER"
}

@test "--search 2 expands to 2 tracks (dry-run)" {
  setup_stubs
  run "$ADDSONG" --dry-run --search 2 "80s mix"
  [ "$status" -eq 0 ]
  # Per-track lines are indented ("  Would add ..."); the summary line is not.
  [ "$(printf '%s\n' "$output" | grep -c '^  Would add')" -eq 2 ]
  teardown_stubs
}

@test "bare non-URL arg defaults to a 1-result search" {
  setup_stubs
  run "$ADDSONG" --dry-run "rick astley never gonna give you up"
  [ "$status" -eq 0 ]
  grep -q 'Searching YouTube for: rick astley never gonna give you up' <<<"$output"
  [ "$(printf '%s\n' "$output" | grep -c '^  Would add')" -eq 1 ]
  teardown_stubs
}

@test "--search rejects 0" {
  run "$ADDSONG" --search 0 "x"
  [ "$status" -ne 0 ]
  grep -q 'positive integer' <<<"$output"
}

@test "--search rejects non-integers" {
  run "$ADDSONG" --search abc "x"
  [ "$status" -ne 0 ]
  grep -q 'positive integer' <<<"$output"
}

@test "--search is capped at 50" {
  run "$ADDSONG" --search 999 "x"
  [ "$status" -ne 0 ]
  grep -q 'capped at 50' <<<"$output"
}

@test "--search and a URL are mutually exclusive" {
  run "$ADDSONG" --dry-run --search 3 "https://youtu.be/xyz"
  [ "$status" -ne 0 ]
  grep -q 'mutually exclusive' <<<"$output"
}

@test "--from and --search are mutually exclusive" {
  tmp="$(mktemp)"; printf 'https://youtu.be/a\n' > "$tmp"
  run "$ADDSONG" --from "$tmp" --search 2 "x"
  [ "$status" -ne 0 ]
  grep -q 'exclusive' <<<"$output"
  rm -f "$tmp"
}

@test "--playlist and --search are mutually exclusive" {
  run "$ADDSONG" --playlist --search 2 "https://youtube.com/playlist?list=x"
  [ "$status" -ne 0 ]
  grep -q 'exclusive' <<<"$output"
}

# --- detect_os -----------------------------------------------------------
#
# detect_os() reads $OSTYPE (and, on Linux, the kernel release for the WSL
# signature). We override OSTYPE in the sourced subprocess. The WSL branch
# can't be unit-tested (we can't fake /proc/sys/kernel/osrelease), so it is
# exercised only manually / documented.

@test "detect_os: darwin* -> mac" {
  run bash -c "OSTYPE=darwin23; source '$ADDSONG' 2>/dev/null; detect_os"
  [ "$status" -eq 0 ]
  [ "$output" = "mac" ]
}

@test "detect_os: msys -> win" {
  run bash -c "OSTYPE=msys; source '$ADDSONG' 2>/dev/null; detect_os"
  [ "$status" -eq 0 ]
  [ "$output" = "win" ]
}

@test "detect_os: cygwin -> win" {
  run bash -c "OSTYPE=cygwin1.7; source '$ADDSONG' 2>/dev/null; detect_os"
  [ "$status" -eq 0 ]
  [ "$output" = "win" ]
}

@test "detect_os: unknown OSTYPE -> other" {
  run bash -c "OSTYPE=hpux; source '$ADDSONG' 2>/dev/null; detect_os"
  [ "$status" -eq 0 ]
  [ "$output" = "other" ]
}

# --- default_watch_dir ---------------------------------------------------

@test "default_watch_dir: mac uses the standard Apple Music path" {
  run bash -c "OSTYPE=darwin23; HOME=/tmp/fakehome; source '$ADDSONG' 2>/dev/null; default_watch_dir"
  [ "$status" -eq 0 ]
  [ "$output" = "/tmp/fakehome/Music/Music/Media.localized/Automatically Add to Music.localized" ]
}

@test "default_watch_dir: win prefers Apple Music preview folder if present" {
  base="$(mktemp -d)"
  mkdir -p "$base/Music/Apple Music/Media/Automatically Add to Apple Music"
  run bash -c "OSTYPE=msys; USERPROFILE='$base'; source '$ADDSONG' 2>/dev/null; default_watch_dir"
  [ "$status" -eq 0 ]
  [ "$output" = "$base/Music/Apple Music/Media/Automatically Add to Apple Music" ]
  rm -rf "$base"
}

@test "default_watch_dir: win falls back to legacy iTunes folder" {
  base="$(mktemp -d)"
  mkdir -p "$base/Music/iTunes/iTunes Media/Automatically Add to iTunes"
  run bash -c "OSTYPE=msys; USERPROFILE='$base'; source '$ADDSONG' 2>/dev/null; default_watch_dir"
  [ "$status" -eq 0 ]
  [ "$output" = "$base/Music/iTunes/iTunes Media/Automatically Add to iTunes" ]
  rm -rf "$base"
}

@test "default_watch_dir: win returns preview path when nothing exists yet" {
  base="$(mktemp -d)"
  run bash -c "OSTYPE=msys; USERPROFILE='$base'; source '$ADDSONG' 2>/dev/null; default_watch_dir"
  [ "$status" -eq 0 ]
  [ "$output" = "$base/Music/Apple Music/Media/Automatically Add to Apple Music" ]
  rm -rf "$base"
}

@test "default_watch_dir: linux returns an output-only fallback folder" {
  run bash -c "OSTYPE=linux-gnu; HOME=/tmp/fakehome; source '$ADDSONG' 2>/dev/null; default_watch_dir"
  [ "$status" -eq 0 ]
  [ "$output" = "/tmp/fakehome/Music/addsong" ]
}
