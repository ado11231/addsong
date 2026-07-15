"""Config and environment resolution.

Loads KEY=VALUE defaults from the config file (parsed, not exec'd, so arbitrary
code can't run), then lets real environment variables override them. Only
ADDSONG_* keys are honored.

Every other module reads resolved values from the `Config` dataclass returned
by `load_config()` rather than touching os.environ directly, so tests can build
a Config or mutate env vars in a fixture and the rest of the pipeline picks it
up without globals.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from addsong.constants import (
    DEFAULT_AUDIO_FORMAT,
    DEFAULT_AUDIO_QUALITY,
    DEFAULT_RETRIES,
    DEFAULT_RETRY_DELAY,
    LEDGER_BASENAME,
    SUBSCRIPTIONS_BASENAME,
)

# Only ADDSONG_* keys are read from the config file.
_KEY_RE = re.compile(r"^ADDSONG_\w+$")


def _is_truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _is_falsy(value: str) -> bool:
    return value.strip().lower() in {"0", "false", "no", "off"}


def _strip_quotes(value: str) -> str:
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        return v[1:-1]
    return v


def _state_dir() -> Path:
    """Return the per-user state directory: $XDG_STATE_HOME or ~/.local/state."""
    xdg = os.environ.get("XDG_STATE_HOME")
    if xdg:
        return Path(xdg)
    return Path.home() / ".local" / "state"


@dataclass
class Config:
    """Resolved configuration values, after env-over-file precedence."""

    # Paths
    watch_dir: str = ""
    ledger: str = ""
    subscriptions: str = ""
    config_file: str = ""

    # Audio
    audio_format: str = DEFAULT_AUDIO_FORMAT
    audio_quality: str = DEFAULT_AUDIO_QUALITY

    # Retry behaviour
    retries: int = DEFAULT_RETRIES
    retry_delay: int = DEFAULT_RETRY_DELAY

    # UI / behaviour flags settable from env (flags from argv override these
    # in cli.py, but the env defaults are read here so --help text and the
    # pipeline both see them).
    progress: bool = True
    notify: bool = False

    def state_dir(self) -> Path:
        """Return the directory holding ledger + subscriptions files."""
        return Path(self.ledger).parent


def _parse_config_file(path: str) -> dict[str, str]:
    """Parse an ADDSONG_* KEY=VALUE file. Env wins over file at call sites."""
    values: dict[str, str] = {}
    try:
        with open(path, encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                if not _KEY_RE.match(key):
                    # Ignore non-ADDSONG_* keys (security: never load arbitrary keys).
                    continue
                values[key] = _strip_quotes(value)
    except FileNotFoundError:
        pass
    return values


def _get(file_values: dict[str, str], key: str, default: str = "") -> str:
    """Return env value if set, else file value, else default.

    Environment variables override the config file — a file value is only used
    when the env var was not already set.
    """
    if key in os.environ:
        return os.environ[key]
    return file_values.get(key, default)


def load_config() -> Config:
    """Build a Config from the config file plus environment overrides.

    Honors, in precedence order (env wins)::
        ADDSONG_CONFIG, ADDSONG_WATCH_DIR, ADDSONG_AUDIO_FORMAT,
        ADDSONG_AUDIO_QUALITY, ADDSONG_LEDGER, ADDSONG_SUBSCRIPTIONS,
        ADDSONG_RETRIES, ADDSONG_RETRY_DELAY, ADDSONG_PROGRESS, ADDSONG_NOTIFY
    """
    config_file = os.environ.get(
        "ADDSONG_CONFIG", str(Path.home() / ".config" / "addsong" / "config")
    )
    file_values = _parse_config_file(config_file)

    state = _state_dir() / "addsong"

    watch_dir = _get(file_values, "ADDSONG_WATCH_DIR", "")
    ledger = _get(file_values, "ADDSONG_LEDGER", str(state / LEDGER_BASENAME))
    subscriptions = _get(
        file_values, "ADDSONG_SUBSCRIPTIONS", str(state / SUBSCRIPTIONS_BASENAME)
    )

    audio_format = _get(file_values, "ADDSONG_AUDIO_FORMAT", DEFAULT_AUDIO_FORMAT)
    audio_quality = _get(file_values, "ADDSONG_AUDIO_QUALITY", DEFAULT_AUDIO_QUALITY)

    retries_raw = _get(file_values, "ADDSONG_RETRIES", str(DEFAULT_RETRIES))
    retry_delay_raw = _get(file_values, "ADDSONG_RETRY_DELAY", str(DEFAULT_RETRY_DELAY))

    progress_raw = _get(file_values, "ADDSONG_PROGRESS", "")
    notify_raw = _get(file_values, "ADDSONG_NOTIFY", "")

    progress = True
    if progress_raw and _is_falsy(progress_raw):
        progress = False

    notify = _is_truthy(notify_raw) if notify_raw else False

    try:
        retries = int(retries_raw)
    except ValueError:
        retries = DEFAULT_RETRIES
    try:
        retry_delay = int(retry_delay_raw)
    except ValueError:
        retry_delay = DEFAULT_RETRY_DELAY

    return Config(
        watch_dir=watch_dir,
        ledger=ledger,
        subscriptions=subscriptions,
        config_file=config_file,
        audio_format=audio_format,
        audio_quality=audio_quality,
        retries=retries,
        retry_delay=retry_delay,
        progress=progress,
        notify=notify,
    )
