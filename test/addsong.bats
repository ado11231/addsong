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
  sourced "printf '%s' 'Bohemian Rhapsody (Official Video)' | clean_meta"
  [ "$status" -eq 0 ]
  [ "$output" = 'Bohemian Rhapsody' ]
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

# --- --results argument parsing -------------------------------------------
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
  # Fake yt-dlp covering all three calls the script makes:
  #   --flat-playlist  -> canned ids (search/playlist expansion)
  #   --extract-audio  -> writes a staged audio file next to the -o template
  #   otherwise        -> prints the 8 per-track metadata lines
  # Env toggles let the failure tests force a specific step to error:
  #   STUB_META_FAIL=1  fail the metadata read
  #   STUB_DL_FAIL=1    fail the download/extract step
  #   STUB_META=...     override the canned metadata block
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
extract=0; out=""; fmt="m4a"; metafile=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --extract-audio)  extract=1 ;;
    --audio-format)   fmt="$2"; shift ;;
    -o)               out="$2"; shift ;;
    --print-to-file)  metafile="$3"; shift 2 ;;   # flag TEMPLATE FILE
  esac
  shift
done
if [[ "$extract" -eq 1 ]]; then
  [[ "${STUB_DL_FAIL:-0}" == 1 ]] && { echo 'ERROR: unable to download video data' >&2; exit 1; }
  printf 'audio' > "$(dirname "$out")/VID000.$fmt"
  # Fast path: the combined download+metadata call captures fields via
  # --print-to-file. Emulate that by appending the canned metadata block.
  [[ -n "$metafile" ]] && printf '%s\n' "${STUB_META:-VID000
Test Title
Test Uploader
NA
NA
NA
NA
NA}" >> "$metafile"
  exit 0
fi
[[ "${STUB_META_FAIL:-0}" == 1 ]] && { echo 'ERROR: Private video' >&2; exit 1; }
# A benign stderr warning: run_ytdlp captures it to the err file and only
# surfaces it under --verbose (used by the verbosity tests).
echo 'WARNING: addsong-stub-warning' >&2
printf '%s\n' "${STUB_META:-VID000
Test Title
Test Uploader
NA
NA
NA
NA
NA}"
STUB
  # Fake ffmpeg: write the (tagged) output file it is asked to produce so the
  # script's "no output / empty file" guards pass. STUB_FF_FAIL=1 forces an error.
  cat > "$STUBBIN/ffmpeg" <<'STUB'
#!/usr/bin/env bash
[[ "${STUB_FF_FAIL:-0}" == 1 ]] && { echo 'ERROR: tagging failed' >&2; exit 1; }
out="${@: -1}"
printf 'tagged' > "$out"
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

@test "--results 2 expands to 2 tracks (dry-run)" {
  setup_stubs
  run "$ADDSONG" --dry-run --results 2 "80s mix"
  [ "$status" -eq 0 ]
  # Per-track lines are indented ("  Would add ..."); the summary line is not.
  [ "$(printf '%s\n' "$output" | grep -c '^  Would add')" -eq 2 ]
  teardown_stubs
}

@test "bare non-URL arg defaults to a 1-result search" {
  setup_stubs
  run "$ADDSONG" --dry-run "queen bohemian rhapsody"
  [ "$status" -eq 0 ]
  grep -q 'Searching YouTube for: queen bohemian rhapsody' <<<"$output"
  [ "$(printf '%s\n' "$output" | grep -c '^  Would add')" -eq 1 ]
  teardown_stubs
}

@test "unquoted multi-word query is joined, not truncated to the last word" {
  setup_stubs
  run "$ADDSONG" --dry-run stronger by kanye west
  [ "$status" -eq 0 ]
  grep -q 'Searching YouTube for: stronger by kanye west' <<<"$output"
  [ "$(printf '%s\n' "$output" | grep -c '^  Would add')" -eq 1 ]
  teardown_stubs
}

@test "--results rejects 0" {
  run "$ADDSONG" --results 0 "x"
  [ "$status" -ne 0 ]
  grep -q 'positive integer' <<<"$output"
}

@test "--results rejects non-integers" {
  run "$ADDSONG" --results abc "x"
  [ "$status" -ne 0 ]
  grep -q 'positive integer' <<<"$output"
}

@test "--results is capped at 50" {
  run "$ADDSONG" --results 999 "x"
  [ "$status" -ne 0 ]
  grep -q 'capped at 50' <<<"$output"
}

@test "--results and a URL are mutually exclusive" {
  run "$ADDSONG" --dry-run --results 3 "https://youtu.be/xyz"
  [ "$status" -ne 0 ]
  grep -q 'mutually exclusive' <<<"$output"
}

@test "--from and --results are mutually exclusive" {
  tmp="$(mktemp)"; printf 'https://youtu.be/a\n' > "$tmp"
  run "$ADDSONG" --from "$tmp" --results 2 "x"
  [ "$status" -ne 0 ]
  grep -q 'exclusive' <<<"$output"
  rm -f "$tmp"
}

@test "--playlist and --results are mutually exclusive" {
  run "$ADDSONG" --playlist --results 2 "https://youtube.com/playlist?list=x"
  [ "$status" -ne 0 ]
  grep -q 'exclusive' <<<"$output"
}

# --- process_one() pipeline ----------------------------------------------
#
# Exercise the full per-track pipeline against the fake yt-dlp/ffmpeg from
# setup_stubs, asserting all three return codes. process_one is called
# directly (sourced) so we observe its raw 0/2/1 rather than main()'s mapped
# exit status. WATCH_DIR is normally filled in by main(), so we set it here.

# Source the script and run process_one with the stubs on PATH, capturing its
# real return code. $1 = extra shell to run before the call (env toggles etc).
run_process_one() {
  # PATH (with the stubs) is already exported by setup_stubs and inherited here.
  # No retries/backoff so the failure case doesn't sleep.
  run bash -c "
    export ADDSONG_RETRIES=0 ADDSONG_RETRY_DELAY=0
    $1
    source '$ADDSONG'
    WATCH_DIR='$WATCH'
    process_one 'https://www.youtube.com/watch?v=z' 0 && r=0 || r=\$?
    echo \"RC=\$r\""
}

@test "process_one: added -> returns 0, file in watch dir, ledger row written" {
  setup_stubs
  run_process_one ""
  grep -q 'RC=0' <<<"$output"
  grep -q '^  Added' <<<"$output"
  [ -s "$WATCH/Test Uploader - Test Title.m4a" ]
  grep -q '^VID000	' "$ADDSONG_LEDGER"
  teardown_stubs
}

@test "process_one: skipped -> duplicate in ledger returns 2, no file imported" {
  setup_stubs
  printf 'VID000\tTest Uploader\tTest Title\t2024-01-01T00:00:00\n' > "$ADDSONG_LEDGER"
  run_process_one ""
  grep -q 'RC=2' <<<"$output"
  grep -q 'already imported' <<<"$output"
  [ -z "$(ls -A "$WATCH")" ]
  teardown_stubs
}

@test "process_one: failed -> download error returns 1, nothing imported" {
  setup_stubs
  run_process_one "export STUB_DL_FAIL=1"
  grep -q 'RC=1' <<<"$output"
  grep -q 'download failed' <<<"$output"
  [ -z "$(ls -A "$WATCH")" ]
  [ ! -s "$ADDSONG_LEDGER" ]
  teardown_stubs
}

@test "slow path: metadata read error is reported (dry-run)" {
  setup_stubs
  export STUB_META_FAIL=1
  run "$ADDSONG" --dry-run --results 1 "x"
  [ "$status" -ne 0 ]
  grep -q 'could not read info' <<<"$output"
  teardown_stubs
}

@test "known id in URL is skipped with no download (zero-network dedup)" {
  setup_stubs
  # An 11-char id parseable straight from the URL, already in the ledger.
  printf 'dQw4w9WgXcQ\tArtist\tTitle\t2024-01-01T00:00:00\n' > "$ADDSONG_LEDGER"
  run bash -c "
    export ADDSONG_RETRIES=0 ADDSONG_RETRY_DELAY=0
    source '$ADDSONG'
    WATCH_DIR='$WATCH'
    process_one 'https://www.youtube.com/watch?v=dQw4w9WgXcQ' 0 && r=0 || r=\$?
    echo \"RC=\$r\""
  grep -q 'RC=2' <<<"$output"
  grep -q 'already imported' <<<"$output"
  [ -z "$(ls -A "$WATCH")" ]
  teardown_stubs
}

# --- --format / --quality flags ------------------------------------------

@test "--format rejects an unsupported value" {
  run "$ADDSONG" --format ogg "x"
  [ "$status" -ne 0 ]
  grep -q 'must be one of' <<<"$output"
}

@test "--quality rejects a value above 10" {
  run "$ADDSONG" --quality 11 "x"
  [ "$status" -ne 0 ]
  grep -q '0-10' <<<"$output"
}

@test "--quality rejects a non-integer" {
  run "$ADDSONG" --quality high "x"
  [ "$status" -ne 0 ]
  grep -q '0-10' <<<"$output"
}

@test "--format mp3 produces an .mp3 in the watch dir" {
  setup_stubs
  run "$ADDSONG" -y --no-progress --format mp3 "https://www.youtube.com/watch?v=z"
  [ "$status" -eq 0 ]
  [ -s "$WATCH/Test Uploader - Test Title.mp3" ]
  teardown_stubs
}

# --- --notify ------------------------------------------------------------

@test "--notify invokes a notifier for an added track" {
  setup_stubs
  # Stub every notifier so this passes regardless of the runner's OS_MODE
  # (notify-send on Linux/Windows/WSL; terminal-notifier/osascript on macOS).
  for n in notify-send terminal-notifier osascript; do
    cat > "$STUBBIN/$n" <<STUB
#!/usr/bin/env bash
printf 'NOTIFIED %s\n' "\$*" >> "$WATCH/.notify"
STUB
    chmod +x "$STUBBIN/$n"
  done
  run "$ADDSONG" -y --no-progress --notify "https://www.youtube.com/watch?v=z"
  [ "$status" -eq 0 ]
  [ -f "$WATCH/.notify" ]
  grep -q 'Test Uploader - Test Title' "$WATCH/.notify"
  teardown_stubs
}

@test "without --notify no notifier is invoked" {
  setup_stubs
  cat > "$STUBBIN/notify-send" <<STUB
#!/usr/bin/env bash
printf 'NOTIFIED\n' >> "$WATCH/.notify"
STUB
  chmod +x "$STUBBIN/notify-send"
  run "$ADDSONG" -y --no-progress "https://www.youtube.com/watch?v=z"
  [ "$status" -eq 0 ]
  [ ! -f "$WATCH/.notify" ]
  teardown_stubs
}

# --- --quiet / --verbose / non-TTY spinner -------------------------------

@test "--quiet suppresses status lines" {
  setup_stubs
  run "$ADDSONG" --quiet -y --no-progress --dry-run "https://www.youtube.com/watch?v=z"
  [ "$status" -eq 0 ]
  ! grep -q 'Would add' <<<"$output"
  teardown_stubs
}

@test "--quiet still prints errors" {
  setup_stubs
  export STUB_DL_FAIL=1
  run "$ADDSONG" --quiet -y --no-progress "https://www.youtube.com/watch?v=z"
  [ "$status" -ne 0 ]
  grep -q 'download failed' <<<"$output"
  teardown_stubs
}

@test "--verbose surfaces yt-dlp stderr" {
  setup_stubs
  run "$ADDSONG" --verbose -y --dry-run "https://www.youtube.com/watch?v=z"
  [ "$status" -eq 0 ]
  grep -q 'addsong-stub-warning' <<<"$output"
  teardown_stubs
}

@test "without --verbose yt-dlp stderr stays hidden" {
  setup_stubs
  run "$ADDSONG" -y --dry-run "https://www.youtube.com/watch?v=z"
  [ "$status" -eq 0 ]
  ! grep -q 'addsong-stub-warning' <<<"$output"
  teardown_stubs
}

@test "with_spinner runs synchronously and propagates exit when there's no TTY" {
  # have_tty=0 forces the no-TTY branch: the command runs synchronously (its
  # output is not swallowed), its exit status is returned, and no spinner frame
  # or label is written (the spinner only ever paints to /dev/tty).
  run bash -c "source '$ADDSONG'; have_tty=0; with_spinner 'SpinLabel' bash -c 'echo HELLO; exit 7' && r=0 || r=\$?; echo \"rc=\$r\""
  grep -q 'HELLO' <<<"$output"
  grep -q 'rc=7' <<<"$output"
  ! grep -q 'SpinLabel' <<<"$output"
  ! grep -q '⠋' <<<"$output"
}

# --- run_ytdlp() retry / backoff / hard-error classification -------------
#
# run_ytdlp retries transient failures (linear backoff) and bails at once on a
# permanent failure matching YTDLP_HARD_ERRORS. A counter file records how many
# times the fake yt-dlp was invoked. Retries/backoff are set tiny so it's fast.

# Write a fake yt-dlp whose body is $2 into dir $1, with a call counter at $1/n.
make_ytdlp() {
  printf '0' > "$1/n"
  cat > "$1/yt-dlp" <<STUB
#!/usr/bin/env bash
n=\$(( \$(cat "$1/n") + 1 )); printf '%s' "\$n" > "$1/n"
$2
STUB
  chmod +x "$1/yt-dlp"
}

# Source the script (low retries/no backoff) and run run_ytdlp with the stub.
run_run_ytdlp() {
  run bash -c "
    export PATH=\"$1:\$PATH\" ADDSONG_RETRIES=2 ADDSONG_RETRY_DELAY=0
    source '$ADDSONG'
    run_ytdlp '$1/out' '$1/err' --print x -- url && echo RYRC=0 || echo RYRC=\$?"
}

@test "run_ytdlp: succeeds on the first try (no retry)" {
  bin="$(mktemp -d)"
  make_ytdlp "$bin" 'exit 0'
  run_run_ytdlp "$bin"
  grep -q 'RYRC=0' <<<"$output"
  [ "$(cat "$bin/n")" -eq 1 ]
  rm -rf "$bin"
}

@test "run_ytdlp: transient failure then success (retries)" {
  bin="$(mktemp -d)"
  make_ytdlp "$bin" '[[ "$n" -eq 1 ]] && { echo "ERROR: unable to download (timed out)" >&2; exit 1; }; exit 0'
  run_run_ytdlp "$bin"
  grep -q 'RYRC=0' <<<"$output"
  [ "$(cat "$bin/n")" -eq 2 ]   # one failed attempt + one success
  rm -rf "$bin"
}

@test "run_ytdlp: hard error is not retried" {
  bin="$(mktemp -d)"
  make_ytdlp "$bin" 'echo "ERROR: Private video. Sign in if you have access." >&2; exit 1'
  run_run_ytdlp "$bin"
  grep -q 'RYRC=1' <<<"$output"
  [ "$(cat "$bin/n")" -eq 1 ]   # bailed immediately, no retry
  rm -rf "$bin"
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

# --- Subscriptions -------------------------------------------------------
#
# subscribe/unsubscribe/list operate on a small TSV of subscribed playlist
# URLs (# comments allowed, blank lines skipped). sync iterates each
# subscribed URL like --playlist would, and the importer ledger dedups
# already-imported tracks -- the subscription file holds only URLs.

subs_setup() {
  WATCH="$(mktemp -d)"
  LED="$(mktemp)"
  SUBS="$(mktemp)"
  : > "$SUBS"
  export ADDSONG_WATCH_DIR="$WATCH"
  export ADDSONG_LEDGER="$LED"
  export ADDSONG_SUBSCRIPTIONS="$SUBS"
}

subs_teardown() {
  rm -rf "$WATCH" "$SUBS"
  rm -f "$LED"
}

@test "subscribe appends a URL" {
  subs_setup
  run "$ADDSONG" subscribe "https://www.youtube.com/playlist?list=PLabc"
  [ "$status" -eq 0 ]
  grep -qxF 'https://www.youtube.com/playlist?list=PLabc' "$SUBS"
  subs_teardown
}

@test "subscribe rejects a non-URL" {
  subs_setup
  run "$ADDSONG" subscribe "not a url"
  [ "$status" -ne 0 ]
  grep -q 'needs a URL' <<<"$output"
  subs_teardown
}

@test "subscribe is idempotent (exact-line dedup)" {
  subs_setup
  "$ADDSONG" subscribe "https://youtu.be/PLabc" >/dev/null 2>&1
  "$ADDSONG" subscribe "https://youtu.be/PLabc" >/dev/null 2>&1
  [ "$(grep -cxF 'https://youtu.be/PLabc' "$SUBS")" -eq 1 ]
  subs_teardown
}

@test "unsubscribe removes a URL" {
  subs_setup
  "$ADDSONG" subscribe "https://youtu.be/PLabc" >/dev/null 2>&1
  "$ADDSONG" subscribe "https://youtu.be/PLxyz" >/dev/null 2>&1
  run "$ADDSONG" unsubscribe "https://youtu.be/PLabc"
  [ "$status" -eq 0 ]
  [ "$(grep -cxF 'https://youtu.be/PLabc' "$SUBS")" -eq 0 ]
  [ "$(grep -cxF 'https://youtu.be/PLxyz' "$SUBS")" -eq 1 ]
  subs_teardown
}

@test "unsubscribe is idempotent when the URL isn't subscribed" {
  subs_setup
  run "$ADDSONG" unsubscribe "https://youtu.be/never"
  [ "$status" -eq 0 ]
  subs_teardown
}

@test "list skips blanks and # comments" {
  subs_setup
  printf '# my subscriptions\n\nhttps://youtu.be/AA\n# trailing note\nhttps://youtu.be/BB\n' > "$SUBS"
  run "$ADDSONG" list
  [ "$status" -eq 0 ]
  [ "$(printf '%s\n' "$output" | grep -c '^https://')" -eq 2 ]
  subs_teardown
}

@test "list with no subscriptions prints a friendly hint" {
  subs_setup
  : > "$SUBS"   # exists but empty
  run "$ADDSONG" list
  [ "$status" -eq 0 ]
  grep -q 'No subscriptions yet' <<<"$output"
  subs_teardown
}

@test "sync with no subscriptions exits early (no preflight)" {
  subs_setup
  : > "$SUBS"
  run "$ADDSONG" sync
  [ "$status" -ne 0 ]
  grep -q 'no subscriptions yet' <<<"$output"
  # The empty-subscriptions short-circuit must not require yt-dlp/ffmpeg:
  # grep finding no match exits 1, which is what we expect here.
  run grep -q 'not found on PATH' <<<"$output"
  [ "$status" -eq 1 ]
  subs_teardown
}

@test "sync expands each subscribed playlist (dry-run with stubs)" {
  setup_stubs
  subs_setup
  printf 'https://youtu.be/PLabc\nhttps://youtu.be/PLxyz\n' > "$SUBS"
  run "$ADDSONG" sync --dry-run
  [ "$status" -eq 0 ]
  # One "Syncing:" header per subscribed URL, one "Would add" per stub track.
  [ "$(printf '%s\n' "$output" | grep -c '^Syncing:')" -eq 2 ]
  [ "$(printf '%s\n' "$output" | grep -c '^  Would add')" -eq 2 ]
  # The summary counts the imported (would-add) tracks across both playlists.
  grep -q 'Would add 2' <<<"$output"
  subs_teardown
  teardown_stubs
}

@test "sync skips # comments and blank lines in the subscription file" {
  setup_stubs
  subs_setup
  printf '# annotate\n\nhttps://youtu.be/PLabc\n# trailing\n' > "$SUBS"
  run "$ADDSONG" sync --dry-run
  [ "$status" -eq 0 ]
  [ "$(printf '%s\n' "$output" | grep -c '^Syncing:')" -eq 1 ]
  subs_teardown
  teardown_stubs
}

# --- forget --------------------------------------------------------
#
# forget forgets every imported track by removing the dedup ledger.
# It's destructive, so it confirms at a terminal and refuses without one
# unless -y is given. These tests need no yt-dlp/ffmpeg (it exits before
# preflight), only a populated ADDSONG_LEDGER.

@test "forget -y wipes a populated ledger" {
  led="$(mktemp)"
  printf 'VID1\tArtist\tTitle\t2024-01-01T00:00:00\n' > "$led"
  printf 'VID2\tArtist2\tTitle2\t2024-01-02T00:00:00\n' >> "$led"
  run env ADDSONG_LEDGER="$led" "$ADDSONG" forget -y
  [ "$status" -eq 0 ]
  grep -q 'Forgot' <<<"$output"
  [ ! -s "$led" ]   # removed (or empty)
  rm -f "$led"
}

@test "forget reports an already-empty ledger" {
  led="$(mktemp)"   # exists but empty
  run env ADDSONG_LEDGER="$led" "$ADDSONG" forget
  [ "$status" -eq 0 ]
  grep -q 'already empty' <<<"$output"
  rm -f "$led"
}

@test "forget refuses without confirmation when there's no terminal" {
  command -v setsid >/dev/null 2>&1 || skip "setsid not available"
  led="$(mktemp)"
  printf 'VID1\tArtist\tTitle\t2024-01-01T00:00:00\n' > "$led"
  # setsid detaches from the controlling terminal, so opening /dev/tty fails
  # and the unconfirmed clear must bail out rather than prompt or wipe.
  run setsid env ADDSONG_LEDGER="$led" "$ADDSONG" forget </dev/null
  [ "$status" -ne 0 ]
  grep -q 'refusing to forget' <<<"$output"
  [ -s "$led" ]     # left untouched
  rm -f "$led"
}
