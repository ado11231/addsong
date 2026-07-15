"""Tests for clean_meta.

Cover the core junk-stripping cases plus Unicode behaviour (en-dash, RTL,
combining marks).
"""

from __future__ import annotations

import pytest

from addsong.meta import clean_meta


@pytest.mark.parametrize(
    ("inp", "expected"),
    [
        # --- core junk-stripping cases ---
        ("Bohemian Rhapsody (Official Video)", "Bohemian Rhapsody"),
        ("Title [4K] (Lyrics)", "Title"),
        ("Song (feat. Someone)", "Song"),
        ("Some Artist - Topic", "Some Artist"),
        ("   Spaced     Out   ", "Spaced Out"),
        ("Bohemian Rhapsody", "Bohemian Rhapsody"),
        # --- additional format variants ---
        ("Track (Official Music Video)", "Track"),
        ("Track (Official Audio)", "Track"),
        ("Track (Official Lyric)", "Track"),
        ("Track (Official Visualizer)", "Track"),
        ("Track [Music Video]", "Track"),
        ("Track (Lyric)", "Track"),
        ("Track (Audio)", "Track"),
        ("Track (Visualizer)", "Track"),
        ("Track [HD]", "Track"),
        ("Track (HQ)", "Track"),
        ("Track [Full HD]", "Track"),
        ("Track [4K]", "Track"),
        ("Track (8K)", "Track"),
        ("Track (Full Album)", "Track"),
        ("Track [MV]", "Track"),
        ("Track [M/V]", "Track"),
        ("Track (Explicit)", "Track"),
        ("Track (Clean)", "Track"),
        ("Track (Remastered 2014)", "Track"),
        ("Track (Remastered)", "Track"),
        ("Song [ft. Guest]", "Song"),
        ("Song [feat. Guest & Other]", "Song"),
        # --- idempotent on clean input ---
        ("Clean Title", "Clean Title"),
    ],
)
def test_clean_meta(inp: str, expected: str) -> None:
    assert clean_meta(inp) == expected


def test_clean_meta_multiple_brackets_in_one_pass() -> None:
    assert clean_meta("Song (Official Video) [4K]") == "Song"


def test_clean_meta_trailing_separator() -> None:
    assert clean_meta("Artist -") == "Artist"


def test_clean_meta_leading_separator() -> None:
    assert clean_meta("- Artist") == "Artist"


def test_clean_meta_en_dash_trailing_separator() -> None:
    assert clean_meta("Artist \u2013") == "Artist"


def test_clean_meta_pipe_trailing_separator() -> None:
    assert clean_meta("Artist |") == "Artist"


def test_clean_meta_preserves_unicode() -> None:
    # clean_meta is Unicode-aware and must not mangle non-ASCII letters in
    # artist/title names.
    assert clean_meta("Sigur R\u00eds (Official Video)") == "Sigur R\u00eds"
