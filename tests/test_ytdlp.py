"""Parity tests for run_ytdlp retry/hard-error classification.

Ports the bats make_ytdlp pattern: a fake yt-dlp on PATH with a counter file
that records how many times it ran, controlled to fail transiently or with a
hard error. Retries/delay are set tiny for speed.
"""

from __future__ import annotations

import os
import stat

import pytest

from addsong.ytdlp import run_ytdlp


def _make_ytdlp(bin_dir: str, body: str) -> str:
    """Install a fake yt-dlp in bin_dir with the given bash body. Returns counter path."""
    counter = os.path.join(bin_dir, "n")
    with open(counter, "w") as fh:
        fh.write("0")
    script = os.path.join(bin_dir, "yt-dlp")
    with open(script, "w") as fh:
        fh.write("#!/usr/bin/env bash\n")
        fh.write(f'n=$(( $(cat "{counter}") + 1 )); printf \'%s\' "$n" > "{counter}"\n')
        fh.write(body)
    os.chmod(script, os.stat(script).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return counter


@pytest.fixture()
def stub_path(monkeypatch: pytest.MonkeyPatch, tmp_path: str) -> str:
    """Put a fresh stubbin dir at the front of PATH and yield its path."""
    bin_dir = os.path.join(tmp_path, "bin")
    os.makedirs(bin_dir, exist_ok=True)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")
    return bin_dir


def test_run_ytdlp_succeeds_first_try_no_retry(stub_path: str, tmp_path: str) -> None:
    counter = _make_ytdlp(stub_path, "exit 0")
    err_path = str(tmp_path / "err")
    rc = run_ytdlp(
        ["--print", "x", "--", "url"],
        retries=2, retry_delay=0, verbose=False, stderr_path=err_path,
        stdout_path=str(tmp_path / "out"),
    )
    assert rc == 0
    with open(counter) as fh:
        assert int(fh.read()) == 1  # one attempt, no retry


def test_run_ytdlp_transient_then_success_retries(stub_path: str, tmp_path: str) -> None:
    counter = _make_ytdlp(
        stub_path,
        'if [[ "$n" -eq 1 ]]; then echo "ERROR: unable to download (timed out)" >&2; exit 1; fi\nexit 0',
    )
    rc = run_ytdlp(
        ["--print", "x", "--", "url"],
        retries=2, retry_delay=0, verbose=False, stderr_path=str(tmp_path / "err"),
        stdout_path=str(tmp_path / "out"),
    )
    assert rc == 0
    with open(counter) as fh:
        assert int(fh.read()) == 2  # one failed attempt plus one success


def test_run_ytdlp_hard_error_not_retried(stub_path: str, tmp_path: str) -> None:
    counter = _make_ytdlp(
        stub_path,
        'echo "ERROR: Private video. Sign in if you have access." >&2\nexit 1',
    )
    rc = run_ytdlp(
        ["--print", "x", "--", "url"],
        retries=2, retry_delay=0, verbose=False, stderr_path=str(tmp_path / "err"),
        stdout_path=str(tmp_path / "out"),
    )
    assert rc == 1
    with open(counter) as fh:
        assert int(fh.read()) == 1  # single attempt, no retry


def test_run_ytdlp_streams_stdout_to_progress_callback(stub_path: str, tmp_path: str) -> None:
    _make_ytdlp(stub_path, 'printf "line1\\nline2\\n" >&1\nexit 0')
    received: list[str] = []
    rc = run_ytdlp(
        ["url"], retries=0, retry_delay=0, verbose=False,
        stderr_path=str(tmp_path / "err"), on_progress=received.append,
    )
    assert rc == 0
    assert received == ["line1", "line2"]
