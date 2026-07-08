"""Metadata string helpers: filename-safe names and zero-network URL id parsing.

`clean_meta()` — the Unicode-aware title scrubber — lands in a dedicated commit
because it has its own large parity-test surface. This module holds the two
simpler pure-string helpers that are tested alongside the path helpers.
"""

from __future__ import annotations

import re

# 11-char YouTube id alphabet, used by id_from_url.
_YT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def safe_name(s: str) -> str:
    """Make a string safe as a filename: no path separators or colons.

    Mirrors the Bash `safe_name()`: slash, colon, and backslash become `_`.
    """
    return s.replace("/", "_").replace(":", "_").replace("\\", "_")


def id_from_url(url: str) -> str | None:
    """Extract an 11-char YouTube id from a URL with no network.

    Handles watch, youtu.be, shorts, and embed URLs. Returns the id on match,
    or None for non-YouTube URLs (yt-dlp is the fallback in the caller).
    """
    id_part: str | None
    if "youtu.be/" in url:
        id_part = url.split("youtu.be/", 1)[1]
    elif "/shorts/" in url:
        id_part = url.split("/shorts/", 1)[1]
    elif "/embed/" in url:
        id_part = url.split("/embed/", 1)[1]
    elif "v=" in url:
        id_part = url.split("v=", 1)[1]
    else:
        return None

    # Strip trailing params (?: &), path separators, or fragments.
    id_part = re.split(r"[?&/#]", id_part, maxsplit=1)[0]
    if _YT_ID_RE.match(id_part):
        return id_part
    return None
