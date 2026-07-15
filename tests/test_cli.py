"""CLI tests.

These run the full addsong CLI (addsong.cli.main) under the shared `stubs`
fixture (fake yt-dlp + ffmpeg on PATH, isolated watch/ledger/subs).
"""

from __future__ import annotations

import os

from tests.conftest import run_cli

# --- results argument parsing -------------------------------------------


def test_results_2_expands_to_2_tracks_dry_run(stubs) -> None:
    rc, err, _out = run_cli("--dry-run", "--results", "2", "80s mix")
    assert rc == 0
    assert err.count("  Would add") == 2


def test_bare_non_url_defaults_to_1_result_search(stubs) -> None:
    rc, err, _out = run_cli("--dry-run", "queen bohemian rhapsody")
    assert rc == 0
    assert "Searching YouTube for: queen bohemian rhapsody" in err
    assert err.count("  Would add") == 1


def test_unquoted_multi_word_query_is_joined(stubs) -> None:
    # argparse joins the positional, so this is a single baked query.
    rc, err, _out = run_cli("--dry-run", "stronger", "by", "kanye", "west")
    assert rc == 0
    assert "Searching YouTube for: stronger by kanye west" in err
    assert err.count("  Would add") == 1


def test_results_rejects_0(stubs) -> None:
    rc, err, _out = run_cli("--results", "0", "x")
    assert rc != 0
    assert "positive integer" in err


def test_results_rejects_non_integers(stubs) -> None:
    rc, err, _out = run_cli("--results", "abc", "x")
    assert rc != 0
    assert "positive integer" in err


def test_results_capped_at_50(stubs) -> None:
    rc, err, _out = run_cli("--results", "999", "x")
    assert rc != 0
    assert "capped at 50" in err


def test_results_and_url_mutually_exclusive(stubs) -> None:
    rc, err, _out = run_cli("--dry-run", "--results", "3", "https://youtu.be/xyz")
    assert rc != 0
    assert "mutually exclusive" in err


def test_from_and_results_mutually_exclusive(stubs, tmp_path) -> None:
    f = tmp_path / "urls.txt"
    f.write_text("https://youtu.be/a\n")
    rc, err, _out = run_cli("--from", str(f), "--results", "2", "x")
    assert rc != 0
    assert "exclusive" in err


def test_playlist_and_results_mutually_exclusive(stubs) -> None:
    rc, err, _out = run_cli(
        "--playlist", "--results", "2", "https://youtube.com/playlist?list=x"
    )
    assert rc != 0
    assert "exclusive" in err


# --- process_one pipeline outcomes --------------------------------------


def test_process_one_added_writes_file_and_ledger(stubs) -> None:
    rc, err, _out = run_cli("-y", "--no-progress", "https://www.youtube.com/watch?v=z")
    assert rc == 0
    assert "Added" in err
    assert os.path.isfile(os.path.join(stubs.watch, "Test Uploader - Test Title.m4a"))
    with open(stubs.ledger) as fh:
        rows = fh.read()
    assert rows.startswith("VID000\t")


def test_process_one_skipped_duplicate_no_file(stubs) -> None:
    with open(stubs.ledger, "w") as fh:
        fh.write("VID000\tTest Uploader\tTest Title\t2024-01-01T00:00:00\n")
    rc, err, _out = run_cli("-y", "--no-progress", "https://www.youtube.com/watch?v=z")
    assert rc == 0  # skipped returns 2, top-level exits 0
    assert "already imported" in err
    assert not any(os.listdir(stubs.watch))


def test_process_one_failed_download_returns_1(stubs, monkeypatch) -> None:
    monkeypatch.setenv("STUB_DL_FAIL", "1")
    rc, err, _out = run_cli("-y", "--no-progress", "https://www.youtube.com/watch?v=z")
    assert rc != 0
    assert "download failed" in err
    assert not any(os.listdir(stubs.watch))
    assert not os.path.isfile(stubs.ledger) or os.path.getsize(stubs.ledger) == 0


def test_slow_path_metadata_read_error_reported(stubs, monkeypatch) -> None:
    monkeypatch.setenv("STUB_META_FAIL", "1")
    rc, err, _out = run_cli("--dry-run", "--results", "1", "x")
    assert rc != 0
    assert "could not read info" in err


def test_known_id_in_url_skipped_with_no_download(stubs) -> None:
    with open(stubs.ledger, "w") as fh:
        fh.write("dQw4w9WgXcQ\tArtist\tTitle\t2024-01-01T00:00:00\n")
    # process_one via CLI; id parsed from URL hits zero-network dedup.
    rc, err, _out = run_cli("-y", "--no-progress", "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert rc == 0
    assert "already imported" in err
    assert not any(os.listdir(stubs.watch))


# --- format and quality flags -------------------------------------------


def test_format_rejects_unsupported_value(stubs) -> None:
    rc, err, _out = run_cli("--format", "ogg", "x")
    assert rc != 0
    assert "must be one of" in err


def test_quality_rejects_above_10(stubs) -> None:
    rc, err, _out = run_cli("--quality", "11", "x")
    assert rc != 0
    assert "0-10" in err


def test_quality_rejects_non_integer(stubs) -> None:
    rc, err, _out = run_cli("--quality", "high", "x")
    assert rc != 0
    assert "0-10" in err


def test_format_mp3_produces_mp3_in_watch_dir(stubs) -> None:
    rc, err, _out = run_cli(
        "-y", "--no-progress", "--format", "mp3", "https://www.youtube.com/watch?v=z"
    )
    assert rc == 0
    assert os.path.isfile(os.path.join(stubs.watch, "Test Uploader - Test Title.mp3"))


# --- notify ---------------------------------------------------------------


def test_notify_invokes_a_notifier_for_an_added_track(stubs, monkeypatch) -> None:
    for n in ("notify-send", "terminal-notifier", "osascript"):
        stubs.add_notifier(n)
    monkeypatch.setenv("OS_MODE", "linux")
    rc, err, _out = run_cli(
        "-y", "--no-progress", "--notify", "https://www.youtube.com/watch?v=z"
    )
    assert rc == 0
    notify_file = os.path.join(stubs.watch, ".notify")
    assert os.path.isfile(notify_file)
    with open(notify_file) as fh:
        txt = fh.read()
    assert "Test Uploader - Test Title" in txt


def test_without_notify_no_notifier_invoked(stubs, monkeypatch) -> None:
    stubs.add_notifier("notify-send")
    monkeypatch.setenv("OS_MODE", "linux")
    rc, err, _out = run_cli("-y", "--no-progress", "https://www.youtube.com/watch?v=z")
    assert rc == 0
    assert not os.path.isfile(os.path.join(stubs.watch, ".notify"))


# --- quiet / verbose / spinner -------------------------------------------


def test_quiet_suppresses_status_lines(stubs) -> None:
    rc, err, _out = run_cli(
        "--quiet", "-y", "--no-progress", "--dry-run",
        "https://www.youtube.com/watch?v=z",
    )
    assert rc == 0
    assert "Would add" not in err


def test_quiet_still_prints_errors(stubs, monkeypatch) -> None:
    monkeypatch.setenv("STUB_DL_FAIL", "1")
    rc, err, _out = run_cli("--quiet", "-y", "--no-progress", "https://www.youtube.com/watch?v=z")
    assert rc != 0
    assert "download failed" in err


def test_verbose_surfaces_ytdlp_stderr(stubs) -> None:
    rc, err, _out = run_cli("--verbose", "-y", "--dry-run", "https://www.youtube.com/watch?v=z")
    assert rc == 0
    assert "addsong-stub-warning" in err


def test_without_verbose_ytdlp_stderr_hidden(stubs) -> None:
    rc, err, _out = run_cli("-y", "--dry-run", "https://www.youtube.com/watch?v=z")
    assert rc == 0
    assert "addsong-stub-warning" not in err


# --- subscriptions --------------------------------------------------------


def test_subscribe_appends_a_url(stubs) -> None:
    rc, err, _out = run_cli("subscribe", "https://www.youtube.com/playlist?list=PLabc")
    assert rc == 0
    with open(stubs.subs) as fh:
        lines = [ln for ln in fh.read().splitlines() if ln]
    assert lines == ["https://www.youtube.com/playlist?list=PLabc"]


def test_subscribe_rejects_a_non_url(stubs) -> None:
    rc, err, _out = run_cli("subscribe", "not a url")
    assert rc != 0
    assert "needs a URL" in err


def test_subscribe_is_idempotent_exact_line_dedup(stubs) -> None:
    run_cli("subscribe", "https://youtu.be/PLabc")
    run_cli("subscribe", "https://youtu.be/PLabc")
    with open(stubs.subs) as fh:
        lines = [ln for ln in fh.read().splitlines() if ln]
    assert lines.count("https://youtu.be/PLabc") == 1


def test_unsubscribe_removes_a_url(stubs) -> None:
    run_cli("subscribe", "https://youtu.be/PLabc")
    run_cli("subscribe", "https://youtu.be/PLxyz")
    rc, err, _out = run_cli("unsubscribe", "https://youtu.be/PLabc")
    assert rc == 0
    with open(stubs.subs) as fh:
        lines = [ln for ln in fh.read().splitlines() if ln]
    assert "https://youtu.be/PLabc" not in lines
    assert "https://youtu.be/PLxyz" in lines


def test_unsubscribe_idempotent_when_not_subscribed(stubs) -> None:
    rc, err, _out = run_cli("unsubscribe", "https://youtu.be/never")
    assert rc == 0


def test_list_skips_blanks_and_comments(stubs) -> None:
    with open(stubs.subs, "w") as fh:
        fh.write("# my subscriptions\n\nhttps://youtu.be/AA\n# trailing note\nhttps://youtu.be/BB\n")
    # list prints to stdout; the parity assertion is over stdout.
    rc, _err, out = run_cli("list")
    assert rc == 0
    assert out.count("https://") == 2


def test_list_with_no_subscriptions_prints_hint(stubs) -> None:
    rc, _err, out = run_cli("list")
    assert rc == 0
    assert "No subscriptions yet" in out


def test_sync_no_subscriptions_exits_early_no_preflight(stubs) -> None:
    rc, err, _out = run_cli("sync")
    assert rc != 0
    assert "no subscriptions yet" in err
    assert "not found on PATH" not in err


def test_sync_expands_each_subscribed_playlist_dry_run(stubs) -> None:
    with open(stubs.subs, "w") as fh:
        fh.write("https://youtu.be/PLabc\nhttps://youtu.be/PLxyz\n")
    rc, err, _out = run_cli("sync", "--dry-run")
    assert rc == 0
    assert err.count("Syncing:") == 2
    assert err.count("  Would add") == 2
    assert "Would add 2" in err


def test_sync_skips_comments_and_blank_lines(stubs) -> None:
    with open(stubs.subs, "w") as fh:
        fh.write("# annotate\n\nhttps://youtu.be/PLabc\n# trailing\n")
    rc, err, _out = run_cli("sync", "--dry-run")
    assert rc == 0
    assert err.count("Syncing:") == 1


# --- forget ---------------------------------------------------------------


def test_forget_y_wipes_populated_ledger(stubs) -> None:
    with open(stubs.ledger, "w") as fh:
        fh.write("VID1\tArtist\tTitle\t2024-01-01T00:00:00\n")
        fh.write("VID2\tArtist2\tTitle2\t2024-01-02T00:00:00\n")
    rc, err, _out = run_cli("forget", "-y")
    assert rc == 0
    assert "Forgot" in err
    assert not os.path.isfile(stubs.ledger) or os.path.getsize(stubs.ledger) == 0


def test_forget_reports_already_empty_ledger(stubs) -> None:
    rc, err, _out = run_cli("forget")
    assert rc == 0
    assert "already empty" in err


def test_forget_refuses_without_confirmation_when_no_terminal(stubs) -> None:
    # Detach from TTY the way `setsid` does so /dev/tty open fails.
    import addsong.review as review

    original = review._open_tty_rw
    review._open_tty_rw = lambda: None  # type: ignore[assignment]
    try:
        with open(stubs.ledger, "w") as fh:
            fh.write("VID1\tArtist\tTitle\t2024-01-01T00:00:00\n")
        rc, err, _out = run_cli("forget")
        assert rc != 0
        assert "refusing to forget" in err
        assert os.path.getsize(stubs.ledger) > 0  # ledger untouched
    finally:
        review._open_tty_rw = original  # type: ignore[assignment]
