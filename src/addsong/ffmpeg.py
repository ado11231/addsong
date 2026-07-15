"""ffmpeg tagging + watch-folder move.

Re-tags the downloaded audio with `ffmpeg -c copy` (preserving embedded
artwork), moves it into the watch folder with collision-safe naming, and emits
the Added status + desktop notification via callbacks. Ledger writes are
delegated to an ``on_add`` callback so this module stays decoupled from the
on-disk ledger format.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable

from addsong.meta import safe_name

FFMPEG_BIN = "ffmpeg"

StatusFn = Callable[[str, str], None]
NotifyFn = Callable[[str, str], None]
AddFn = Callable[[str, str, str], None]
ErrFn = Callable[[str], None]


def _last_error_line(err_path: str) -> str:
    """Return the last line of ff.err containing 'error' (case-insensitive), or ''."""
    try:
        with open(err_path, encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError:
        return ""
    for line in reversed(lines):
        if "error" in line.lower():
            return line.strip()
    return ""


def finalize_track(
    staging: str,
    track_id: str,
    artist: str,
    title: str,
    album: str,
    year: str,
    track_no: str,
    *,
    watch_dir: str,
    audio_format: str,
    verbose: bool,
    on_status: StatusFn,
    on_notify: NotifyFn,
    on_add: AddFn,
    on_err: ErrFn,
) -> int:
    """Tag the staged file and move it into the watch folder.

    Returns 0 on success, 1 on failure. Failures are reported via ``on_err``
    (matching the historical `err()` convention). On success,
    calls ``on_add(id, artist, title)`` (ledger), ``on_status("Added",
    "artist - title")``, and ``on_notify(title, body)`` — in that order.
    """
    staged = os.path.join(staging, f"{track_id}.{audio_format}")
    if not os.path.isfile(staged) or os.path.getsize(staged) == 0:
        on_err(f"no .{audio_format} produced for: {artist} - {title}")
        return 1

    final = os.path.join(staging, f"out.{audio_format}")
    tag_args: list[str] = [
        "-metadata", f"title={title}",
        "-metadata", f"artist={artist}",
        "-metadata", f"album_artist={artist}",
    ]
    if album:
        tag_args += ["-metadata", f"album={album}"]
    if year:
        tag_args += ["-metadata", f"date={year}"]
    if track_no:
        tag_args += ["-metadata", f"track={track_no}"]

    ff_err = os.path.join(staging, "ff.err")
    try:
        with open(ff_err, "wb") as err:
            rc = subprocess.run(
                [
                    FFMPEG_BIN, "-y", "-loglevel", "error",
                    "-i", staged, "-map", "0", "-c", "copy",
                    *tag_args,
                    final,
                ],
                stdout=subprocess.DEVNULL,
                stderr=err,
                check=False,
            ).returncode
    except FileNotFoundError:
        on_err(f"ffmpeg not found: {artist} - {title}")
        return 1
    if verbose and os.path.getsize(ff_err) > 0:
        try:
            with open(ff_err, encoding="utf-8", errors="replace") as fh:
                sys.stderr.write(fh.read())
        except OSError:
            pass

    if rc != 0:
        reason = _last_error_line(ff_err)
        on_err(f"tagging failed: {artist} - {title} ({reason})")
        return 1
    if not os.path.isfile(final) or os.path.getsize(final) == 0:
        on_err(f"tagging produced an empty file: {artist} - {title}")
        return 1

    # Move into the watch folder with collision-safe naming.
    base = f"{safe_name(artist)} - {safe_name(title)}"
    dest = os.path.join(watch_dir, f"{base}.{audio_format}")
    if os.path.exists(dest):
        dest = os.path.join(watch_dir, f"{base} ({int(time.time())}).{audio_format}")
    try:
        # shutil.move handles cross-device moves (EXDEV) by falling back to
        # copy+delete; os.replace would fail across mounts (e.g. /tmp -> /home).
        shutil.move(final, dest)
    except OSError:
        on_err(f"could not move into watch folder (permission?): {artist} - {title}")
        return 1

    # Success: record ledger, print status, fire notification — in that order.
    on_add(track_id, artist, title)
    on_status("Added", f"{artist} - {title}")
    on_notify("Added to Apple Music", f"{artist} - {title}")
    return 0
