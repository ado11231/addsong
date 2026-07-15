"""Platform detection and watch-folder path resolution.

Detection reads `os.name` / `sys.platform` plus, on Linux,
`/proc/sys/kernel/osrelease` for a WSL marker.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

OSMode = str  # "mac" | "win" | "wsl" | "linux" | "other"

_WSL_RE = re.compile(r"microsoft", re.IGNORECASE)


def detect_os() -> OSMode:
    """Return one of mac/win/wsl/linux/other based on the current platform.

    Uses `sys.platform` plus a WSL procfs probe on Linux.
    """
    if sys.platform == "darwin":
        return "mac"
    if os.name == "nt" or sys.platform in {"msys", "cygwin"}:
        # Git Bash / MSYS / Cygwin on Windows.
        return "win"
    if sys.platform.startswith("linux"):
        try:
            with open("/proc/sys/kernel/osrelease", encoding="utf-8") as fh:
                if _WSL_RE.search(fh.read()):
                    return "wsl"
        except OSError:
            pass
        return "linux"
    return "other"


def _win_userprofile() -> str:
    """Return the Windows user root, honoring USERPROFILE then HOME."""
    return os.environ.get("USERPROFILE") or str(Path.home())


def default_watch_dir(os_mode: OSMode | None = None) -> str:
    """Return the per-OS watch/output folder.

    macOS: the Apple Music "Automatically Add to Music" folder. Windows/WSL:
    probes Apple Music preview then legacy iTunes, returning the preview path
    when neither exists (preflight tells the user to open Music once). Linux
    and other: an output-only folder the app creates itself.
    """
    os_mode = os_mode if os_mode is not None else detect_os()
    home = str(Path.home())

    if os_mode == "mac":
        return os.path.join(
            home, "Music", "Music", "Media.localized", "Automatically Add to Music.localized"
        )

    if os_mode == "win":
        base = _win_userprofile()
        candidates = [
            os.path.join(base, "Music", "Apple Music", "Media", "Automatically Add to Apple Music"),
            os.path.join(base, "Music", "iTunes", "iTunes Media", "Automatically Add to iTunes"),
        ]
        for d in candidates:
            if os.path.isdir(d):
                return d
        # Neither found: return the preview path; preflight reports it missing.
        return candidates[0]

    if os_mode == "wsl":
        # Probe Windows libraries reachable under /mnt/[c-z].
        import glob

        apple = glob.glob(
            "/mnt/[c-z]/Users/*/Music/Apple Music/Media/Automatically Add to Apple Music"
        )
        for d in apple:
            if os.path.isdir(d):
                return d
        itunes = glob.glob(
            "/mnt/[c-z]/Users/*/Music/iTunes/iTunes Media/Automatically Add to iTunes"
        )
        for d in itunes:
            if os.path.isdir(d):
                return d
        return os.path.join(home or "/tmp", "Music", "addsong")

    # Linux and other: output-only.
    return os.path.join(home or "/tmp", "Music", "addsong")
