"""Tests for config-file parsing.

We set ADDSONG_CONFIG and other env vars in the process, call load_config(),
and assert the resolved Config.
"""

from __future__ import annotations

import os

import pytest

from addsong.config import load_config


def test_config_file_supplies_addsong_defaults(
    tmp_path: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = tmp_path / "config"
    cfg.write_text("ADDSONG_AUDIO_FORMAT=mp3\n")
    monkeypatch.setenv("ADDSONG_CONFIG", str(cfg))
    # Clear any leaked env so the file is the sole source.
    monkeypatch.delenv("ADDSONG_AUDIO_FORMAT", raising=False)
    assert load_config().audio_format == "mp3"


def test_env_var_overrides_config_file(tmp_path: str, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = tmp_path / "config"
    cfg.write_text("ADDSONG_AUDIO_FORMAT=mp3\n")
    monkeypatch.setenv("ADDSONG_CONFIG", str(cfg))
    monkeypatch.setenv("ADDSONG_AUDIO_FORMAT", "flac")
    assert load_config().audio_format == "flac"


def test_config_parser_ignores_comments_and_non_addsong_keys(
    tmp_path: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = tmp_path / "config"
    cfg.write_text("# a comment\nEVIL=value\nADDSONG_AUDIO_FORMAT=ogg\n")
    monkeypatch.setenv("ADDSONG_CONFIG", str(cfg))
    monkeypatch.delenv("ADDSONG_AUDIO_FORMAT", raising=False)
    monkeypatch.delenv("EVIL", raising=False)
    c = load_config()
    assert c.audio_format == "ogg"
    assert "EVIL" not in os.environ  # security: arbitrary keys never exported


def test_config_parser_strips_surrounding_quotes(
    tmp_path: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = tmp_path / "config"
    cfg.write_text('ADDSONG_AUDIO_FORMAT="wav"\n')
    monkeypatch.setenv("ADDSONG_CONFIG", str(cfg))
    monkeypatch.delenv("ADDSONG_AUDIO_FORMAT", raising=False)
    assert load_config().audio_format == "wav"


def test_config_parser_strips_single_quotes(
    tmp_path: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = tmp_path / "config"
    cfg.write_text("ADDSONG_AUDIO_FORMAT='opus'\n")
    monkeypatch.setenv("ADDSONG_CONFIG", str(cfg))
    monkeypatch.delenv("ADDSONG_AUDIO_FORMAT", raising=False)
    assert load_config().audio_format == "opus"


def test_config_retries_and_retry_delay_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ADDSONG_RETRIES", raising=False)
    monkeypatch.delenv("ADDSONG_RETRY_DELAY", raising=False)
    c = load_config()
    assert c.retries == 2
    assert c.retry_delay == 3


def test_config_progress_env_disables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADDSONG_PROGRESS", "0")
    assert load_config().progress is False


def test_config_notify_env_enables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADDSONG_NOTIFY", "1")
    assert load_config().notify is True


def test_config_ledger_default_uses_xdg_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: str
) -> None:
    monkeypatch.delenv("ADDSONG_LEDGER", raising=False)
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    assert load_config().ledger == str(tmp_path / "addsong" / "imported.tsv")
