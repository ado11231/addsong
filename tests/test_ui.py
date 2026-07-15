"""Tests for the UI layer (spinner synchronous-no-TTY contract, quiet, notify).

`with_spinner` is the only directly-tested UI behaviour; the rich progress bar
is exercised only to the extent that the no-tty and quiet paths fall back to
synchronous execution (no animation, exit code propagated).
"""

from __future__ import annotations

import os
import stat

import pytest

from addsong.ui import UI


def test_with_spinner_runs_synchronously_no_tty_and_propagates_rc(
    capsys: pytest.CaptureFixture[str],
) -> None:
    ui = UI(prog="addsong", have_tty=False, quiet=False, verbose=False)
    rc = ui.with_spinner("SpinLabel", lambda: (_print_hello(), 7)[1])
    out, _ = capsys.readouterr()
    assert rc == 7
    assert "HELLO" in out
    assert "SpinLabel" not in out
    assert "\u280b" not in out  # no braille spinner frame


def _print_hello() -> None:
    print("HELLO")


def test_say_suppressed_under_quiet(capsys: pytest.CaptureFixture[str]) -> None:
    ui = UI(prog="addsong", have_tty=False, quiet=True)
    ui.say("should be hidden")
    ui.banner("also hidden")
    ui.status("Added", "x")
    out, _ = capsys.readouterr()
    assert out == ""


def test_err_always_shows_even_under_quiet(capsys: pytest.CaptureFixture[str]) -> None:
    ui = UI(prog="addsong", have_tty=False, quiet=True)
    ui.err("boom")
    _, err = capsys.readouterr()
    assert "boom" in err
    assert "addsong" in err


def test_status_formats_added_line(capsys: pytest.CaptureFixture[str]) -> None:
    ui = UI(prog="addsong", have_tty=False, quiet=False)
    ui.status("Added", "Artist - Title")
    _, err = capsys.readouterr()
    assert "Added" in err
    assert "Artist - Title" in err


def test_notify_no_op_when_disabled(tmp_path: str, monkeypatch: pytest.MonkeyPatch) -> None:
    bin_dir = os.path.join(tmp_path, "bin")
    os.makedirs(bin_dir)
    for n in ("notify-send", "terminal-notifier", "osascript"):
        s = os.path.join(bin_dir, n)
        with open(s, "w") as fh:
            fh.write("#!/usr/bin/env bash\nexit 99\n")
        os.chmod(s, os.stat(s).st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")
    ui = UI(prog="addsong", have_tty=False, notify=False, os_mode="linux")
    ui.fire_notify("t", "b")  # must not invoke anything


def test_download_track_no_tty_runs_synchronously(
    tmp_path: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Stub yt-dlp that exits 0 without writing anything.
    bin_dir = os.path.join(tmp_path, "bin")
    os.makedirs(bin_dir)
    s = os.path.join(bin_dir, "yt-dlp")
    with open(s, "w") as fh:
        fh.write("#!/usr/bin/env bash\nexit 0\n")
    os.chmod(s, os.stat(s).st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")

    staging = os.path.join(tmp_path, "stage")
    os.makedirs(staging)
    ui = UI(prog="addsong", have_tty=False, progress=True)
    rc = ui.download_track(
        staging, "Downloading", ["--", "url"],
        retries=0, retry_delay=0, on_retry=ui.on_retry,
    )
    assert rc == 0


def test_on_retry_message(capsys: pytest.CaptureFixture[str]) -> None:
    ui = UI(prog="addsong", have_tty=False)
    ui.on_retry(1, 2, 3)
    _, err = capsys.readouterr()
    assert "retrying (1/2)" in err
    assert "3s" in err


def test_finish_batch_prints_headline_then_counts_on_separate_lines(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # No TTY -> plain text, no color/icons, but headline and counts split across lines.
    ui = UI(prog="addsong", have_tty=False, quiet=False)
    ui.finish_batch("Added", 2, 0, 0)
    _, err = capsys.readouterr()
    lines = [ln for ln in err.splitlines() if ln]
    assert lines[0] == "Done."
    assert "Added 2" in lines[1]
    assert "skipped 0" in lines[1]
    assert "failed 0" in lines[1]


def test_finish_batch_all_failed_headline_is_failed(capsys: pytest.CaptureFixture[str]) -> None:
    ui = UI(prog="addsong", have_tty=False, quiet=False)
    ui.finish_batch("Added", 0, 0, 1)
    _, err = capsys.readouterr()
    lines = [ln for ln in err.splitlines() if ln]
    assert lines[0] == "Failed."
    assert "failed 1" in lines[1]
