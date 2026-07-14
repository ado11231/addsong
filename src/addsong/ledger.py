"""Import ledger: dedup TSV keyed by video id.

On-disk format is preserved exactly from the Bash script so existing users'
dedup ledgers survive the upgrade:

    id<TAB>artist<TAB>title<TAB>YYYY-MM-DDTHH:MM:SS

one import per line. `has()` reads the file to dedup; `add()` appends a row.
"""

from __future__ import annotations

import contextlib
import os
from collections.abc import Iterator
from datetime import datetime


def has(path: str, track_id: str) -> bool:
    """Return True if track_id is already in the ledger."""
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if not line:
                    continue
                row = line.rstrip("\n").split("\t")
                if row and row[0] == track_id:
                    return True
    except FileNotFoundError:
        return False
    return False


def add(path: str, track_id: str, artist: str, title: str) -> None:
    """Append an import row to the ledger, creating its parent dir."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(f"{track_id}\t{artist}\t{title}\t{ts}\n")


def clear(path: str) -> None:
    """Remove the ledger file (used by `forget`)."""
    with contextlib.suppress(FileNotFoundError):
        os.remove(path)


def count(path: str) -> int:
    """Return the number of rows in the ledger (0 if missing/empty)."""
    try:
        with open(path, encoding="utf-8") as fh:
            return sum(1 for line in fh if line.strip())
    except FileNotFoundError:
        return 0


def read_rows(path: str) -> Iterator[tuple[str, str, str, str]]:
    """Yield (id, artist, title, timestamp) tuples — powers the `history` view."""
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                parts = line.rstrip("\n").split("\t")
                # Defensive: tolerate short rows.
                while len(parts) < 4:
                    parts.append("")
                yield parts[0], parts[1], parts[2], parts[3]
    except FileNotFoundError:
        return
