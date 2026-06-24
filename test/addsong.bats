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
