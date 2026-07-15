"""Per-track and per-batch pipeline: dedup, download, finalize, summarize.

The CLI builds a `Run` once (shared config, UI, ledger/subs paths, flags) and
calls into these functions: `process_one`, `interactive_for`, `run_url_stream`,
`finish_batch`, and `note_imported`.
"""

from __future__ import annotations

import collections.abc
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass

from addsong import ledger, subscriptions
from addsong.config import Config
from addsong.constants import AUDIO_FORMATS, EXIT_ADDED, EXIT_FAILED, EXIT_SKIPPED
from addsong.meta import TrackMeta, id_from_url, parse_meta
from addsong.platform import default_watch_dir, detect_os
from addsong.review import confirm_forget, review_meta
from addsong.ui import UI

# yt-dlp field order for the --print / --print-to-file metadata block.
_META_FIELDS = (
    "%(id)s", "%(title)s", "%(uploader)s",
    "%(track)s", "%(artist)s", "%(album)s",
    "%(release_year)s", "%(track_number)s",
)


@dataclass
class Flags:
    """Per-run boolean behaviour flags, after env + argv resolution.

    CLI parsing (cli.py) builds this; the pipeline reads it. Defaults are all
    false at the top of a run.
    """

    playlist: bool = False
    assume_yes: bool = False
    review_force: bool = False
    reimport: bool = False
    dry_run: bool = False
    from_file: str = ""
    results: int = 0


@dataclass
class Run:
    """Everything one addsong invocation needs."""

    config: Config
    ui: UI
    flags: Flags
    have_tty: bool
    os_mode: str
    watch_dir: str
    audio_format: str
    audio_quality: str

    # Tallies for the end-of-run summary (mirrors N_ADDED/N_SKIPPED/N_FAILED).
    n_added: int = 0
    n_skipped: int = 0
    n_failed: int = 0


def interactive_for(run: Run, playlist: bool) -> bool:
    """Whether to review a track interactively.

    Dry-run never reviews; --yes forces off;
    --review forces on (only at a TTY); playlists default off; single track at a
    TTY defaults on.
    """
    if run.flags.dry_run:
        return False
    if run.flags.assume_yes:
        return False
    if run.flags.review_force:
        return run.have_tty
    if playlist:
        return False
    return run.have_tty


# --- per-track pipeline -----------------------------------------------------


def _staged_ytdlp_args(staging: str, audio_format: str, audio_quality: str) -> list[str]:
    """Shared yt-dlp download args (used by both fast and slow paths)."""
    return [
        "--no-playlist", "--retries", "3", "--fragment-retries", "3", "--socket-timeout", "30",
        "--extract-audio", "--audio-format", audio_format, "--audio-quality", audio_quality,
        "--embed-thumbnail", "--convert-thumbnails", "jpg",
        "-o", os.path.join(staging, "%(id)s.%(ext)s"),
    ]


def process_one(run: Run, url: str, interactive: bool) -> int:
    """Process one track URL. Returns 0 added, 2 skipped, 1 failed.

    The per-track pipeline: zero-network dedup via id_from_url,
    fast path (combined download+metadata) for non-interactive non-dry-run runs,
    slow path otherwise (metadata first for review or would-add line).
    """
    # Zero-network dedup for watch URLs with a parseable id already in the ledger.
    url_id = id_from_url(url)
    if url_id and not run.flags.reimport and ledger.has(run.config.ledger, url_id):
        run.ui.status("Skipped", f"already imported ({url_id})")
        return EXIT_SKIPPED

    fast = (not interactive) and (not run.flags.dry_run)
    staging = tempfile.mkdtemp(prefix="addsong.")
    dlargs = _staged_ytdlp_args(staging, run.audio_format, run.audio_quality)

    if not fast:
        # Slow path: metadata first (for review or would-add line).
        metaf = os.path.join(staging, "meta")
        open(metaf, "a", encoding="utf-8").close()  # noqa: SIM115
        err = os.path.join(staging, "err")
        args = [
            "--no-playlist", "--retries", "3", "--socket-timeout", "30",
            *[f"--print={f}" for f in _META_FIELDS],
            "--", url,
        ]
        rc = run.ui.with_spinner(
            "Reading info",
            lambda: _ytdlp_to_file(run, args, metaf, err),
        )
        if rc != 0:
            reason = _last_error_line(err) or "private, removed, region-locked, or age-gated?"
            run.ui.err(f"could not read info for: {url} ({reason})")
            _rmtree(staging)
            return EXIT_FAILED
        with open(metaf, encoding="utf-8", errors="replace") as fh:
            meta_text = fh.read()
        tm = parse_meta(meta_text)
        if tm is None:
            run.ui.err(f"no video id for: {url}")
            _rmtree(staging)
            return EXIT_FAILED

        # Dedup after metadata when the URL had no parseable id upfront.
        if not run.flags.reimport and ledger.has(run.config.ledger, tm.id):
            run.ui.status("Skipped", f"{tm.artist} - {tm.title} (already imported)")
            _rmtree(staging)
            return EXIT_SKIPPED

        if interactive:
            edited = review_meta(tm.artist, tm.title, prog="addsong")
            if edited is None:
                run.ui.status("Skipped", f"{tm.artist} - {tm.title}")
                _rmtree(staging)
                return EXIT_SKIPPED
            tm.artist, tm.title = edited

        if run.flags.dry_run:
            run.ui.status("Would add", f"{tm.artist} - {tm.title}")
            if tm.album or tm.year or tm.track_no:
                dash = "\u2014"
                run.ui.say(
                    f"           album={tm.album or dash}"
                    f"  year={tm.year or dash}"
                    f"  track={tm.track_no or dash}"
                )
            _rmtree(staging)
            return EXIT_ADDED

        # Download.
        dl_rc = run.ui.download_track(
            staging, f"Downloading: {tm.artist} - {tm.title}", [*dlargs, "--", url],
            retries=run.config.retries, retry_delay=run.config.retry_delay,
        )
    else:
        # Fast path: combine download + metadata capture in one yt-dlp call.
        metaf = os.path.join(staging, "meta.tsv")
        open(metaf, "a", encoding="utf-8").close()  # noqa: SIM115
        for field in _META_FIELDS:
            dlargs += ["--print-to-file", field, metaf]
        dlargs += ["--no-simulate", "--", url]
        dl_rc = run.ui.download_track(
            staging, "Downloading", dlargs,
            retries=run.config.retries, retry_delay=run.config.retry_delay,
        )
        if dl_rc == 0:
            with open(metaf, encoding="utf-8", errors="replace") as fh:
                meta_text = fh.read()
            tm = parse_meta(meta_text)
            if tm is None:
                run.ui.err(f"could not read info for: {url}")
                _rmtree(staging)
                return EXIT_FAILED
            if not url_id and not run.flags.reimport and ledger.has(run.config.ledger, tm.id):
                run.ui.status("Skipped", f"{tm.artist} - {tm.title} (already imported)")
                _rmtree(staging)
                return EXIT_SKIPPED

    if dl_rc != 0:
        run.ui.err(
            f"download failed: {url} ({_last_error_line(os.path.join(staging, 'dl.err'))})"
        )
        _rmtree(staging)
        return EXIT_FAILED

    # At this point tm is guaranteed non-None — both the slow and fast paths
    # above return early on a None parse_meta, but mypy can't track narrowing
    # across the if/else, so narrow explicitly.
    assert tm is not None
    rc = _finalize(run, staging, tm)
    _rmtree(staging)
    return rc


def _finalize(run: Run, staging: str, tm: TrackMeta) -> int:
    from addsong.ffmpeg import finalize_track

    return finalize_track(
        staging, tm.id, tm.artist, tm.title, tm.album, tm.year, tm.track_no,
        watch_dir=run.watch_dir,
        audio_format=_fmt_to_extension(run.audio_format),
        verbose=run.ui.verbose,
        on_status=run.ui.status,
        on_notify=run.ui.fire_notify,
        on_add=lambda i, a, t: ledger.add(run.config.ledger, i, a, t),
        on_err=run.ui.err,
    )


def _fmt_to_extension(fmt: str) -> str:
    """Resolve an --format value to the on-disk extension it produces.

    Corrects the vorbis/alac/best extension mismatch: vorbis->.ogg,
    alac->.m4a, best-> resolved from yt-dlp's output via a glob. For 'best' the
    caller is finalize_track which locates the file by glob; we keep 'best' as
    the marker and let the glob path handle it.
    """
    return {"vorbis": "ogg", "alac": "m4a"}.get(fmt, fmt)


def _ytdlp_to_file(run: Run, args: list[str], metaf: str, err: str) -> int:
    from addsong.ytdlp import run_ytdlp

    return run_ytdlp(
        args,
        retries=run.config.retries,
        retry_delay=run.config.retry_delay,
        verbose=run.ui.verbose,
        stderr_path=err,
        stdout_path=metaf,
        on_retry=run.ui.on_retry,
    )


def _last_error_line(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in reversed(fh.readlines()):
                if "error" in line.lower():
                    return line.strip()
    except OSError:
        pass
    return ""


def _rmtree(path: str) -> None:
    import shutil

    shutil.rmtree(path, ignore_errors=True)


# --- batch + subscriptions -------------------------------------------------


def _strip(line: str) -> str:
    return line.strip()


def _is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")


def run_url_stream(
    run: Run, lines: collections.abc.Iterable[str], interactive: bool
) -> None:
    """Process a stream of URLs one per line, updating run tallies.

    Skips blank lines and `#` comments.
    """
    for raw in lines:
        line = _strip(raw)
        if not line or line.startswith("#"):
            continue
        rc = process_one(run, line, interactive)
        if rc == EXIT_ADDED:
            run.n_added += 1
        elif rc == EXIT_SKIPPED:
            run.n_skipped += 1
        else:
            run.n_failed += 1


def expand_ids_to_urls(ids_text: str) -> list[str]:
    """Turn a newline-separated id list into watch URLs."""
    return [
        f"https://www.youtube.com/watch?v={i}"
        for i in (_strip(ln) for ln in ids_text.splitlines())
        if i
    ]


def _flat_playlist_ids(url: str) -> list[str] | None:
    """Run yt-dlp --flat-playlist to return a list of ids, or None on failure."""
    try:
        proc = subprocess.run(
            ["yt-dlp", "--flat-playlist", "--print", "%(id)s", "--", url],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False, text=True,
        )
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    return [ln for ln in (_strip(x) for x in proc.stdout.splitlines()) if ln]


def builtin_search(run: Run, query: str, n: int) -> None:
    """Run a ytsearchN: via yt-dlp --flat-playlist and import the results."""
    run.ui.banner(f"Searching YouTube for: {query}")
    ids = _flat_playlist_ids(f"ytsearch{n}:{query}")
    if not ids:
        run.ui.err(f"search failed: {query}")
        raise SystemExit(EXIT_FAILED)
    rev = interactive_for(run, playlist=True)
    run_url_stream(run, expand_ids_to_urls("\n".join(ids)), rev)
    finish_batch(run)


def builtin_playlist(run: Run, url: str) -> None:
    """Import every track from a playlist URL."""
    run.ui.banner("Reading playlist...")
    ids = _flat_playlist_ids(url)
    if not ids:
        run.ui.err(f"could not read playlist: {url}")
        raise SystemExit(EXIT_FAILED)
    rev = interactive_for(run, playlist=True)
    run_url_stream(run, expand_ids_to_urls("\n".join(ids)), rev)
    finish_batch(run)


def builtin_from_file(run: Run, path: str) -> None:
    """Import URLs one per line from a file (or '-' for stdin)."""
    rev = interactive_for(run, playlist=True)
    if path == "-":
        import sys

        run_url_stream(run, sys.stdin, rev)
    else:
        if not os.path.isfile(path):
            run.ui.err(f"no such file: {path}")
            raise SystemExit(EXIT_FAILED)
        with open(path, encoding="utf-8") as fh:
            run_url_stream(run, fh.readlines(), rev)
    finish_batch(run)


def builtin_sync(run: Run) -> None:
    """Import new tracks from every subscribed playlist (ledger dedupes)."""
    if not subscriptions.has_subscriptions(run.config.subscriptions):
        run.ui.err("no subscriptions yet -- see 'addsong list'")
        raise SystemExit(EXIT_FAILED)
    rev = interactive_for(run, playlist=True)
    for url in subscriptions.read_urls(run.config.subscriptions):
        run.ui.say("")
        run.ui.banner(f"Syncing: {url}")
        ids = _flat_playlist_ids(url)
        if ids is None:
            run.ui.err(f"could not read playlist: {url}")
            run.n_failed += 1
            continue
        if not ids:
            run.ui.err(f"no tracks found in playlist: {url}")
            run.n_failed += 1
            continue
        run_url_stream(run, expand_ids_to_urls("\n".join(ids)), rev)
    finish_batch(run)


# --- forget + summary -------------------------------------------------------


def builtin_forget(run: Run, yes: bool) -> None:
    """Wipe the import ledger; prompt at a TTY unless --yes; refuse without a TTY."""
    if not os.path.isfile(run.config.ledger) or os.path.getsize(run.config.ledger) == 0:
        run.ui.say("Nothing imported yet (history is already empty).")
        return
    n = ledger.count(run.config.ledger)
    if not yes:
        try:
            ok = confirm_forget(n)
        except RuntimeError as e:
            run.ui.err(str(e))
            raise SystemExit(EXIT_FAILED) from e
        if not ok:
            run.ui.say("Cancelled. Nothing forgotten.")
            return
    ledger.clear(run.config.ledger)
    run.ui.status("Forgot", f"{n} imported track(s)")


def finish_batch(run: Run) -> None:
    """Print the end-of-run summary and raise SystemExit(1) if anything failed."""
    verb = "Would add" if run.flags.dry_run else "Added"
    run.ui.finish_batch(verb, run.n_added, run.n_skipped, run.n_failed)
    note_imported(run, run.n_added)
    raise SystemExit(EXIT_FAILED if run.n_failed > 0 else EXIT_ADDED)


def note_imported(run: Run, n: int) -> None:
    """Apple Music hint after a batch that actually added tracks (mac/win/wsl)."""
    if run.flags.dry_run or n <= 0:
        return
    if run.os_mode in {"mac", "win", "wsl"}:
        run.ui.say("")
        run.ui.say("Apple Music will import shortly. Make sure the Music app is open.")


# --- preflight --------------------------------------------------------------


def preflight(run: Run) -> None:
    """Verify yt-dlp + ffmpeg are on PATH and the watch folder is usable."""
    import shutil

    for tool in ("yt-dlp", "ffmpeg"):
        if shutil.which(tool) is None:
            run.ui.err(
                f"'{tool}' not found on PATH.\n"
                "Install yt-dlp and ffmpeg (e.g. brew install yt-dlp ffmpeg on macOS,\n"
                "choco install yt-dlp ffmpeg on Windows, or use your distro's package "
                "manager).\nSee the Setup section in the README."
            )
            raise SystemExit(EXIT_FAILED)

    if not os.path.isdir(run.watch_dir):
        mode = run.os_mode
        if mode == "mac":
            run.ui.err(
                "Apple Music watch folder not found:\n"
                f"    {run.watch_dir}\n"
                "Open Music > Settings > Files to find your 'Music Media folder "
                "location', then set ADDSONG_WATCH_DIR to the 'Automatically Add "
                "to Music' folder inside it.\nSee the Setup section in the README."
            )
            raise SystemExit(EXIT_FAILED)
        if mode in {"win", "wsl"}:
            run.ui.err(
                "Apple Music watch folder not found:\n"
                f"    {run.watch_dir}\n"
                "Open the Apple Music preview app (or iTunes) at least once so it "
                "creates the folder, then re-run. Or set ADDSONG_WATCH_DIR to your "
                "library's 'Automatically Add to ...' folder. See the Setup section "
                "in the README."
            )
            raise SystemExit(EXIT_FAILED)
        # Linux / other: create the output folder and continue.
        try:
            os.makedirs(run.watch_dir, exist_ok=True)
        except OSError as e:
            run.ui.err(f"cannot create output folder: {run.watch_dir}")
            raise SystemExit(EXIT_FAILED) from e
        run.ui.say("note: output folder is:")
        run.ui.say(f"      {run.watch_dir}")
        run.ui.say("      import files into your library of choice manually.")


# Keep these imported for callers that build a Run by hand.
__all__ = [
    "Run", "Flags", "interactive_for", "process_one", "run_url_stream",
    "builtin_search", "builtin_playlist", "builtin_from_file", "builtin_sync",
    "builtin_forget", "finish_batch", "preflight",
    "AUDIO_FORMATS", "default_watch_dir", "detect_os", "re",
]
