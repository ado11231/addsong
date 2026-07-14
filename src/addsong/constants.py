"""Shared constants for addsong.

Mirrors the top-of-script configuration values from the original Bash
implementation, exposed here as module-level constants so every other module
can import them without recomputation.
"""

from __future__ import annotations

# Audio formats accepted by --format. The order is preserved for --help text.
AUDIO_FORMATS: tuple[str, ...] = (
    "m4a", "mp3", "flac", "opus", "vorbis", "wav", "aac", "alac", "best",
)

# Permanent yt-dlp errors that are never worth retrying. Matched case-insensitively
# against yt-dlp's stderr. Kept as one alternation string to preserve the Bash
# behaviour of a single grep -E pass.
YTDLP_HARD_ERRORS: str = (
    "private video|members-only|members only|video unavailable|"
    "this video is unavailable|is unavailable|has been removed|"
    "removed by the user|has been terminated|account.*terminated|"
    "confirm your age|age-restricted|sign in to confirm|"
    "not available in your country|not available on this app|"
    "blocked it in your country|copyright"
)

# Default config values.

DEFAULT_AUDIO_FORMAT = "m4a"
# yt-dlp VBR quality: 0 best, 10 worst.
DEFAULT_AUDIO_QUALITY = "0"
DEFAULT_RETRIES = 2        # extra attempts after the first
DEFAULT_RETRY_DELAY = 3    # base backoff seconds, grows per attempt

# State-file basenames (the directory is ~/.local/state/addsong by default,
# overrideable via ADDSONG_* env vars resolved in config.py).
LEDGER_BASENAME = "imported.tsv"
SUBSCRIPTIONS_BASENAME = "subscribed.tsv"
CONFIG_BASENAME = "config"

# Exit codes used across the pipeline. Keep in sync with the Bash script:
#   0 -> added, 2 -> skipped (duplicate or user skip), 1 -> failed.
EXIT_ADDED = 0
EXIT_SKIPPED = 2
EXIT_FAILED = 1
