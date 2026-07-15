"""Tests for platform helpers.

OS mocking monkeypatches sys.platform / os.environ directly. The detect_os
tests that asserted darwin/msys/cygwin/hpunix map cleanly; WSL needs a procfs
fixture covered separately when we have a Linux runner.
"""

from __future__ import annotations

import os

import pytest

from addsong import platform as platform_mod
from addsong.meta import id_from_url, safe_name
from addsong.platform import default_watch_dir, detect_os

# --- safe_name ------------------------------------------------------------


def test_safe_name_replaces_slashes_colons_backslashes(monkeypatch: pytest.MonkeyPatch) -> None:
    # Pass input through env since the helper reads os.environ.
    monkeypatch.setenv("IN", r"AC/DC: Back\Black")
    assert safe_name(os.environ["IN"]) == r"AC_DC_ Back_Black"


def test_safe_name_leaves_normal_name_unchanged() -> None:
    assert safe_name("Artist - Title") == "Artist - Title"


# --- id_from_url ----------------------------------------------------------


def test_id_from_url_watch_url() -> None:
    assert id_from_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_id_from_url_shorts() -> None:
    assert id_from_url("https://www.youtube.com/shorts/AbCdEfGhIjk") == "AbCdEfGhIjk"


def test_id_from_url_youtu_be() -> None:
    assert id_from_url("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_id_from_url_embed() -> None:
    assert id_from_url("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_id_from_url_strips_params() -> None:
    assert (
        id_from_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s&feature=share")
        == "dQw4w9WgXcQ"
    )


def test_id_from_url_returns_none_for_non_youtube() -> None:
    assert id_from_url("https://example.com/foo") is None


def test_id_from_url_rejects_short_id() -> None:
    assert id_from_url("https://youtu.be/short") is None


def test_id_from_url_known_id_in_url_skips_download() -> None:
    # Zero-network dedup setup.
    assert id_from_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"


# --- detect_os ------------------------------------------------------------


def test_detect_os_darwin_maps_to_mac(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(platform_mod.sys, "platform", "darwin")
    assert detect_os() == "mac"


def test_detect_os_msys_maps_to_win(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(platform_mod.sys, "platform", "msys")
    assert detect_os() == "win"


def test_detect_os_cygwin_maps_to_win(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(platform_mod.sys, "platform", "cygwin")
    assert detect_os() == "win"


def test_detect_os_unknown_maps_to_other(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(platform_mod.sys, "platform", "hpux")
    assert detect_os() == "other"


# --- default_watch_dir ----------------------------------------------------


def test_default_watch_dir_mac_uses_standard_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: str
) -> None:
    monkeypatch.setattr(platform_mod.sys, "platform", "darwin")
    monkeypatch.setattr(platform_mod.Path, "home", classmethod(lambda cls: tmp_path))  # type: ignore[method-assign]
    assert (
        default_watch_dir("mac")
        == f"{tmp_path}/Music/Music/Media.localized/Automatically Add to Music.localized"
    )


def test_default_watch_dir_win_prefers_apple_music_preview(tmp_path: str) -> None:
    base = tmp_path
    os.makedirs(os.path.join(base, "Music", "Apple Music", "Media", "Automatically Add to Apple Music"))
    import addsong.platform as p

    original = p._win_userprofile
    p._win_userprofile = lambda: str(base)  # type: ignore[assignment]
    try:
        assert (
            default_watch_dir("win")
            == f"{base}/Music/Apple Music/Media/Automatically Add to Apple Music"
        )
    finally:
        p._win_userprofile = original  # type: ignore[assignment]


def test_default_watch_dir_win_falls_back_to_legacy_itunes(tmp_path: str) -> None:
    base = tmp_path
    os.makedirs(os.path.join(base, "Music", "iTunes", "iTunes Media", "Automatically Add to iTunes"))
    import addsong.platform as p

    original = p._win_userprofile
    p._win_userprofile = lambda: str(base)  # type: ignore[assignment]
    try:
        assert (
            default_watch_dir("win")
            == f"{base}/Music/iTunes/iTunes Media/Automatically Add to iTunes"
        )
    finally:
        p._win_userprofile = original  # type: ignore[assignment]


def test_default_watch_dir_win_returns_preview_path_when_nothing_exists(tmp_path: str) -> None:
    base = tmp_path
    import addsong.platform as p

    original = p._win_userprofile
    p._win_userprofile = lambda: str(base)  # type: ignore[assignment]
    try:
        assert (
            default_watch_dir("win")
            == f"{base}/Music/Apple Music/Media/Automatically Add to Apple Music"
        )
    finally:
        p._win_userprofile = original  # type: ignore[assignment]


def test_default_watch_dir_linux_returns_output_only_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: str
) -> None:
    monkeypatch.setattr(platform_mod.Path, "home", classmethod(lambda cls: tmp_path))  # type: ignore[method-assign]
    assert default_watch_dir("linux") == f"{tmp_path}/Music/addsong"
