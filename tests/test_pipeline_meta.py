"""Tests for parse_meta (yt-dlp metadata-block parsing) and finalize_track.

parse_meta reads an 8-line --print block. The heuristic split "Artist - Title"
and clean_meta integration are covered, plus the NA->empty normalization and
the empty-title fallback.
"""

from __future__ import annotations

import os
import stat

import pytest

from addsong.ffmpeg import finalize_track
from addsong.meta import parse_meta

# --- parse_meta ----------------------------------------------------------


def test_parse_meta_structured_youtube_music_metadata() -> None:
    block = "VID000\nRaw Title\nUploader\nTrack Name\nArtist Name\nAlbum\n2021\n3"
    tm = parse_meta(block)
    assert tm is not None
    assert tm.id == "VID000"
    assert tm.artist == "Artist Name"
    assert tm.title == "Track Name"
    assert tm.album == "Album"
    assert tm.year == "2021"
    assert tm.track_no == "3"


def test_parse_meta_heuristic_split() -> None:
    # No structured track/artist: heuristic "Artist - Title" split.
    block = "VID000\nQueen - Bohemian Rhapsody (Official Video)\nqueenofficial\nNA\nNA\nNA\nNA\nNA"
    tm = parse_meta(block)
    assert tm is not None
    assert tm.artist == "Queen"
    assert tm.title == "Bohemian Rhapsody"


def test_parse_meta_falls_back_to_uploader_when_no_separator() -> None:
    block = "VID000\nSome Random Title\nsomeuploader\nNA\nNA\nNA\nNA\nNA"
    tm = parse_meta(block)
    assert tm is not None
    assert tm.artist == "someuploader"
    assert tm.title == "Some Random Title"


def test_parse_meta_returns_none_for_empty_block() -> None:
    assert parse_meta("") is None


def test_parse_meta_normalizes_na_to_empty() -> None:
    block = "VID000\nTitle\nUploader\nNA\nNA\nNA\nNA\nNA"
    tm = parse_meta(block)
    assert tm is not None
    assert tm.album == ""
    assert tm.year == ""
    assert tm.track_no == ""


def test_parse_meta_title_never_empty_falls_back_to_raw() -> None:
    # Title that cleans to empty (e.g. only a separator) falls back to raw title.
    block = "VID000\n-\nUploader\nNA\nNA\nNA\nNA\nNA"
    tm = parse_meta(block)
    assert tm is not None
    assert tm.title == "-"


def _make_ffmpeg(bin_dir: str, body: str) -> None:
    """Install a fake ffmpeg with the given stub body."""
    script = os.path.join(bin_dir, "ffmpeg")
    with open(script, "w") as fh:
        fh.write("#!/usr/bin/env bash\n")
        fh.write(body)
    os.chmod(script, os.stat(script).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


# --- finalize_track ------------------------------------------------------


@pytest.fixture()
def ff_stub_path(monkeypatch: pytest.MonkeyPatch, tmp_path: str) -> str:
    bin_dir = os.path.join(tmp_path, "bin")
    os.makedirs(bin_dir, exist_ok=True)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")
    return bin_dir


def test_finalize_track_success_writes_tagged_file_and_callbacks(
    ff_stub_path: str, tmp_path: str
) -> None:
    _make_ffmpeg(ff_stub_path, 'out="${@: -1}"; printf "tagged" > "$out"; exit 0')
    staging = tmp_path / "stage"
    staging.mkdir()
    (staging / "VID000.m4a").write_bytes(b"audio")
    watch = tmp_path / "watch"
    watch.mkdir()

    ledger: list[tuple[str, str, str]] = []
    statuses: list[tuple[str, str]] = []
    notifies: list[tuple[str, str]] = []
    errs: list[str] = []

    rc = finalize_track(
        str(staging), "VID000", "Test Uploader", "Test Title", "", "", "",
        watch_dir=str(watch), audio_format="m4a", verbose=False,
        on_status=lambda k, r: statuses.append((k, r)),
        on_notify=lambda t, b: notifies.append((t, b)),
        on_add=lambda i, a, t: ledger.append((i, a, t)),
        on_err=lambda m: errs.append(m),
    )
    assert rc == 0
    assert ledger == [("VID000", "Test Uploader", "Test Title")]
    assert statuses == [("Added", "Test Uploader - Test Title")]
    assert notifies == [("Added to Apple Music", "Test Uploader - Test Title")]
    assert errs == []
    assert os.path.isfile(str(watch / "Test Uploader - Test Title.m4a"))


def test_finalize_track_missing_staged_file_returns_failure(
    ff_stub_path: str, tmp_path: str
) -> None:
    staging = tmp_path / "stage"
    staging.mkdir()
    watch = tmp_path / "watch"
    watch.mkdir()
    errs: list[str] = []
    rc = finalize_track(
        str(staging), "VID000", "Artist", "Title", "", "", "",
        watch_dir=str(watch), audio_format="m4a", verbose=False,
        on_status=lambda k, r: None,
        on_notify=lambda t, b: None,
        on_add=lambda i, a, t: None,
        on_err=lambda m: errs.append(m),
    )
    assert rc == 1
    assert errs and "no .m4a produced" in errs[0]
    assert not any(os.listdir(str(watch)))


def test_finalize_track_tagging_failure_returns_failure(
    ff_stub_path: str, tmp_path: str
) -> None:
    _make_ffmpeg(ff_stub_path, 'echo "ERROR: tagging failed" >&2; exit 1')
    staging = tmp_path / "stage"
    staging.mkdir()
    (staging / "VID000.m4a").write_bytes(b"audio")
    watch = tmp_path / "watch"
    watch.mkdir()
    errs: list[str] = []
    rc = finalize_track(
        str(staging), "VID000", "Artist", "Title", "", "", "",
        watch_dir=str(watch), audio_format="m4a", verbose=False,
        on_status=lambda k, r: None,
        on_notify=lambda t, b: None,
        on_add=lambda i, a, t: None,
        on_err=lambda m: errs.append(m),
    )
    assert rc == 1
    assert errs and "tagging failed" in errs[0]


def test_finalize_track_collision_safe_naming(
    ff_stub_path: str, tmp_path: str
) -> None:
    _make_ffmpeg(ff_stub_path, 'out="${@: -1}"; printf "tagged" > "$out"; exit 0')
    staging = tmp_path / "stage"
    staging.mkdir()
    (staging / "VID000.m4a").write_bytes(b"audio")
    watch = tmp_path / "watch"
    watch.mkdir()
    # Pre-existing file at the destination name.
    (watch / "Artist - Title.m4a").write_bytes(b"old")

    rc = finalize_track(
        str(staging), "VID000", "Artist", "Title", "", "", "",
        watch_dir=str(watch), audio_format="m4a", verbose=False,
        on_status=lambda k, r: None,
        on_notify=lambda t, b: None,
        on_add=lambda i, a, t: None,
        on_err=lambda m: None,
    )
    assert rc == 0
    # Original kept; new file has a timestamp suffix.
    files = sorted(os.listdir(str(watch)))
    assert "Artist - Title.m4a" in files
    assert any(f.startswith("Artist - Title (") and f.endswith(".m4a") for f in files)
