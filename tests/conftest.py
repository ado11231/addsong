"""Pytest configuration: ensure src/ is importable without an editable install.

Also hosts the shared `stubs` fixture and `run_cli` helper: fake yt-dlp +
ffmpeg on PATH, isolated watch/ledger/subs in tmp_path, driven by
STUB_META_FAIL / STUB_DL_FAIL / STUB_FF_FAIL / STUB_META knobs. Each test that
needs the CLI imports these via conftest; pytest makes the `stubs` fixture
available to any test in the tests/ tree.
"""

from __future__ import annotations

import contextlib
import io
import os
import stat
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from addsong.cli import main  # noqa: E402

_YTDLP_STUB = r'''#!/usr/bin/env bash
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
    --audio-format)  fmt="$2"; shift ;;
    -o)              out="$2"; shift ;;
    --print-to-file)  metafile="$3"; shift 2 ;;
  esac
  shift
done
if [[ "$extract" -eq 1 ]]; then
  [[ "${STUB_DL_FAIL:-0}" == 1 ]] && { echo 'ERROR: unable to download video data' >&2; exit 1; }
  printf 'audio' > "$(dirname "$out")/VID000.$fmt"
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
echo 'WARNING: addsong-stub-warning' >&2
printf '%s\n' "${STUB_META:-VID000
Test Title
Test Uploader
NA
NA
NA
NA
NA}"
'''

_FFMPEG_STUB = r'''#!/usr/bin/env bash
[[ "${STUB_FF_FAIL:-0}" == 1 ]] && { echo 'ERROR: tagging failed' >&2; exit 1; }
out="${@: -1}"
printf 'tagged' > "$out"
exit 0
'''


def _write_stub(path: str, body: str) -> None:
    with open(path, "w") as fh:
        fh.write(body)
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


class Stubs:
    """Paths + helpers for the stubbed CLI test run."""

    def __init__(self, bin_dir: str, watch: str, ledger: str, subs: str) -> None:
        self.bin_dir = bin_dir
        self.watch = watch
        self.ledger = ledger
        self.subs = subs

    def add_notifier(self, name: str) -> str:
        """Install a fake notifier that appends its argv to watch/.notify."""
        path = os.path.join(self.bin_dir, name)
        with open(path, "w") as fh:
            fh.write('#!/usr/bin/env bash\n')
            fh.write(f'printf "NOTIFIED %s\\n" "$*" >> "{self.watch}/.notify"\n')
        os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        return path


@pytest.fixture()
def stubs(tmp_path, monkeypatch):
    """Install fake yt-dlp + ffmpeg, isolate ledger/subs/watch to tmp_path."""
    bin_dir = tmp_path / "bin"
    watch = tmp_path / "watch"
    watch.mkdir()
    ledger = tmp_path / "ledger.tsv"
    subs = tmp_path / "subs.tsv"
    subs.touch()
    bin_dir.mkdir()

    _write_stub(str(bin_dir / "yt-dlp"), _YTDLP_STUB)
    _write_stub(str(bin_dir / "ffmpeg"), _FFMPEG_STUB)

    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")
    monkeypatch.setenv("ADDSONG_WATCH_DIR", str(watch))
    monkeypatch.setenv("ADDSONG_LEDGER", str(ledger))
    monkeypatch.setenv("ADDSONG_SUBSCRIPTIONS", str(subs))
    monkeypatch.setenv("ADDSONG_RETRIES", "0")
    monkeypatch.setenv("ADDSONG_RETRY_DELAY", "0")

    return Stubs(str(bin_dir), str(watch), str(ledger), str(subs))


def run_cli(*args: str) -> tuple[int, str, str]:
    """Invoke addsong.cli.main capturing stderr and stdout.

    Returns ``(rc, stderr_text, stdout_text)``. The `list` subcommand prints
    to stdout; everything else is on stderr.
    """
    err = io.StringIO()
    out = io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
        try:
            rc = main(list(args))
        except SystemExit as e:
            rc = int(e.code) if e.code is not None else 0
    return rc, err.getvalue(), out.getvalue()
