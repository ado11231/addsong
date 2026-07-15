"""yt-dlp subprocess wrapper with retry and hard-error classification.

stdout is captured to a file (or streamed to a progress callback), stderr to a
file, and transient failures retry with linear backoff. Permanent errors
(private/unavailable/region-locked/etc., matched against
`YTDLP_HARD_ERRORS`) return immediately without retrying.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from collections.abc import Callable

from addsong.constants import YTDLP_HARD_ERRORS

YTDLP_BIN = "yt-dlp"

_HARD_ERROR_RE = re.compile(YTDLP_HARD_ERRORS, re.IGNORECASE)

ProgressCallback = Callable[[str], None]
RetryCallback = Callable[[int, int, int], None]


def _is_hard_error(stderr_path: str) -> bool:
    try:
        with open(stderr_path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return False
    return bool(_HARD_ERROR_RE.search(text))


def _nonempty(path: str) -> bool:
    try:
        return os.path.getsize(path) > 0
    except OSError:
        return False


def _dump(path: str) -> None:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            sys.stderr.write(fh.read())
    except OSError:
        pass


def _invoke(
    args: list[str],
    stderr_path: str,
    stdout_path: str | None,
    on_progress: ProgressCallback | None,
) -> int:
    """Run yt-dlp once. Returns its exit code."""
    with open(stderr_path, "wb") as err:
        if on_progress is not None:
            proc = subprocess.Popen([YTDLP_BIN, *args], stdout=subprocess.PIPE, stderr=err)
            assert proc.stdout is not None
            for raw in iter(proc.stdout.readline, b""):
                on_progress(raw.decode("utf-8", "replace").rstrip("\n"))
            proc.wait()
            return int(proc.returncode)
        if stdout_path is not None:
            with open(stdout_path, "wb") as out:
                proc = subprocess.Popen([YTDLP_BIN, *args], stdout=out, stderr=err)
                proc.wait()
                return int(proc.returncode)
        proc = subprocess.Popen([YTDLP_BIN, *args], stdout=subprocess.DEVNULL, stderr=err)
        proc.wait()
        return int(proc.returncode)


def run_ytdlp(
    args: list[str],
    *,
    retries: int,
    retry_delay: int,
    verbose: bool,
    stderr_path: str,
    stdout_path: str | None = None,
    on_progress: ProgressCallback | None = None,
    on_retry: RetryCallback | None = None,
) -> int:
    """Run yt-dlp with retry-on-transient, no-retry-on-hard-error semantics.

    Captures stderr to ``stderr_path``. If ``on_progress`` is given, stdout is
    streamed to it line-by-line (used by the progress bar); elif ``stdout_path``
    is given, stdout is written to that file; otherwise stdout is discarded.

    Returns yt-dlp's exit code (0 on success).
    """
    attempt = 0
    while True:
        rc = _invoke(args, stderr_path, stdout_path, on_progress)
        if rc == 0:
            if verbose and _nonempty(stderr_path):
                _dump(stderr_path)
            return 0
        # Failed: surface stderr under verbose first.
        if verbose and _nonempty(stderr_path):
            _dump(stderr_path)
        if _is_hard_error(stderr_path):
            return rc
        attempt += 1
        if attempt > retries:
            return rc
        if on_retry is not None:
            on_retry(attempt, retries, attempt * retry_delay)
        time.sleep(attempt * retry_delay)
