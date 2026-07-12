"""Interactive metadata review over /dev/tty.

Ports the Bash `review_meta()`. Shows the scraped artist/title and lets the user
accept (Enter), edit (E), or skip (S). Only invoked when the run is interactive
(see ui/constant flags); /dev/tty is opened fresh for read+write so it works
mid-pipeline regardless of stdin.

Returns (artist, title) on accept, or None on skip.
"""

from __future__ import annotations

import contextlib
from typing import IO


def _open_tty_rw() -> IO[str] | None:
    try:
        return open("/dev/tty", encoding="utf-8", errors="replace", newline="")  # noqa: SIM115
    except OSError:
        return None


def review_meta(artist: str, title: str, *, prog: str = "addsong") -> tuple[str, str] | None:
    """Prompt the user to accept/edit/skip the scraped metadata.

    Returns ``(artist, title)`` (possibly edited) on accept, or ``None`` on
    skip. If no controlling terminal is available, falls back to accepting the
    metadata as-is — the caller only routes here when the run is interactive.
    """
    cur_artist, cur_title = artist, title
    tty = _open_tty_rw()
    if tty is None:
        return cur_artist, cur_title

    try:
        while True:
            tty.write("\n")
            tty.write("  Review track \u266a\n")          # bold header in Bash
            tty.write(f"  Artist: {cur_artist}\n")
            tty.write(f"  Title:  {cur_title}\n")
            tty.write("\n")
            tty.write("  [Enter] Add  \u00b7  [E] Edit  \u00b7  [S] Skip\n")
            tty.write("  \u276f ")
            tty.flush()
            ans = tty.readline().strip()

            if ans in ("", "y", "Y"):
                # step up and clear for the result line, mirroring Bash
                tty.write("\033[A\033[2K\r")
                tty.flush()
                return cur_artist, cur_title
            if ans in ("s", "S"):
                tty.write("\033[A\033[2K\r")
                tty.flush()
                return None
            if ans in ("e", "E"):
                tty.write("  Edit (blank keeps the current value)\n")
                tty.write(f"  Artist [{cur_artist}]: ")
                tty.flush()
                x = tty.readline().rstrip("\n")
                if x.strip():
                    cur_artist = x.strip()
                tty.write(f"  Title  [{cur_title}]: ")
                tty.flush()
                x = tty.readline().rstrip("\n")
                if x.strip():
                    cur_title = x.strip()
                tty.flush()
                # loop to show updated values
                continue
            tty.write("  (Enter = Add, E = Edit, S = Skip)\n")
            tty.flush()
    finally:
        with contextlib.suppress(OSError):
            tty.close()


def confirm_forget(count: int) -> bool:
    """Prompt at /dev/tty to confirm forgetting ``count`` imported tracks.

    Returns True on yes, False on cancel. Raises RuntimeError when there's no
    controlling terminal — matching the Bash refusal to forget without a TTY.
    """
    tty = _open_tty_rw()
    if tty is None:
        raise RuntimeError(
            "refusing to forget imported tracks without confirmation (re-run with -y to confirm)"
        )
    try:
        tty.write(
            f"Forget {count} imported track(s)? Future runs may re-import them. [y/N] "
        )
        tty.flush()
        ans = tty.readline().strip().lower()
        return ans in ("y", "yes")
    finally:
        with contextlib.suppress(OSError):
            tty.close()


def open_tty_available() -> bool:
    """True if a controlling terminal is available right now (for preflight/forget)."""
    return _open_tty_rw() is not None
