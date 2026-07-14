"""Subscribed-playlist file: one URL per line with `#` comments and blanks.

On-disk format is preserved from the Bash script. add/remove are idempotent;
list skips comments and blank lines. sync expands each URL via yt-dlp's flat
playlist extraction and is orchestrated by the pipeline (cli.py) which calls
`read_urls` to get the subscription list.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterator

_URL_RE = re.compile(r"^https?://")


def _ensure(path: str) -> None:
    """Create the subscriptions file (empty) and its parent dir if missing."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if not os.path.exists(path):
        open(path, "a", encoding="utf-8").close()  # noqa: SIM115


def add(path: str, url: str) -> bool:
    """Append a URL if not already subscribed. Returns True if newly added.

    Raises ValueError for a non-URL input (caller reports the error).
    """
    if not _URL_RE.match(url):
        raise ValueError(f"subscribe needs a URL (got: '{url}')")
    _ensure(path)
    if any(line.rstrip("\n") == url for line in _iter_raw_lines(path)):
        return False
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(url + "\n")
    return True


def remove(path: str, url: str) -> None:
    """Remove exact-match lines for url, keeping comments. Idempotent."""
    if not os.path.exists(path):
        return
    kept: list[str] = []
    for line in _iter_raw_lines(path):
        if line.rstrip("\n") != url:
            kept.append(line)
    with open(path, "w", encoding="utf-8") as fh:
        fh.writelines(kept)


def read_urls(path: str) -> Iterator[str]:
    """Yield subscribed URLs, skipping blank lines and `#` comments."""
    for line in _iter_raw_lines(path):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        yield stripped


def has_subscriptions(path: str) -> bool:
    """Return True if the subscriptions file contains at least one URL line."""
    for _ in read_urls(path):
        return True
    return False


def _iter_raw_lines(path: str) -> Iterator[str]:
    """Yield raw lines (with newline) from the file, empty if missing."""
    try:
        with open(path, encoding="utf-8") as fh:
            yield from fh
    except FileNotFoundError:
        return
