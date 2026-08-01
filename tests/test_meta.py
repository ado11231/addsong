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


def test_triple_brackets(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Track (Audio) [4K] (Official Video)') == 'Track'


def test_feat_before_bracket_junk(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Song (feat. X) (Official Video)') == 'Song'


def test_only_bracket_junk(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('(Official Video)') == ''


def test_remaster_with_year(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Song (Remastered 2009)') == 'Song'


def test_remastered_no_year(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Song (Remastered)') == 'Song'


def test_full_hd_bracket(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Track [Full HD]') == 'Track'


def test_mv_slash(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Track [M/V]') == 'Track'


def test_explicit_clean(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Track (Explicit)') == 'Track'


def test_clean_tag(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Track (Clean)') == 'Track'


def test_official_visualizer(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Track (Official Visualizer)') == 'Track'


def test_official_lyric(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Track (Official Lyric)') == 'Track'


def test_official_audio(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Track (Official Audio)') == 'Track'


def test_music_video_brackets(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Track [Music Video]') == 'Track'


def test_lyric_single(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Track (Lyric)') == 'Track'


def test_visualizer_only(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Track (Visualizer)') == 'Track'


def test_hd_brackets(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Track [HD]') == 'Track'


def test_hq_parens(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Track (HQ)') == 'Track'


def test_eight_k(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Track (8K)') == 'Track'


def test_full_album(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Track (Full Album)') == 'Track'


def test_feat_with_ampersand(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Song (feat. Guest & Other)') == 'Song'


def test_ft_dot(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Song (ft. Guest)') == 'Song'


def test_feat_dot(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Song (feat. Guest)') == 'Song'


def test_topic_suffix_only(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Artist - Topic') == 'Artist'


def test_leading_pipe(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('| Song') == 'Song'


def test_leading_dash_space(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('- Song') == 'Song'


def test_trailing_en_dash(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Song –') == 'Song'


def test_double_space_collapse(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Song  With    Spaces') == 'Song With Spaces'


def test_unicode_accented(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Café del Mar') == 'Café del Mar'


def test_japanese_title(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('フェニックス') == 'フェニックス'


def test_empty_string(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('') == ''


def test_only_whitespace(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('   ') == ''


def test_only_brackets_no_keyword(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Song (not junk)') == 'Song (not junk)'


def test_parens_with_text(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Song (live version)') == 'Song (live version)'


def test_square_no_keyword(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Song [2024]') == 'Song [2024]'


def test_extra_song_with_parens_live(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Song (Live)') == 'Song (Live)'


def test_extra_song_with_acoustic(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Song (Acoustic Version)') == 'Song (Acoustic Version)'


def test_extra_song_remix_in_parens(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Song (Remix)') == 'Song (Remix)'


def test_extra_official_music_video_short(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('T (Official Music Video)') == 'T'


def test_extra_topic_suffix_with_space(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Artist - Topic ') == 'Artist'


def test_extra_trailing_space_only(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Song   ') == 'Song'


def test_extra_leading_space_only(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('   Song') == 'Song'


def test_extra_tab_in_title(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Song\tTitle') == 'Song\tTitle'


def test_extra_feat_at_start(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('(feat. X) Song') == 'Song'


def test_extra_multiple_feat(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Song (feat. A) (feat. B)') == 'Song'


def test_extra_en_dash_in_title(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Song – Title') == 'Song – Title'


def test_extra_pipe_in_middle(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Song | Title') == 'Song | Title'


def test_extra_bracket_with_number(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('Song [2023]') == 'Song [2023]'


def test_extra_multiple_spaces_collapse(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('  Song   Title  ') == 'Song Title'


def test_extra_official_video_caps(tmp_path: str) -> None:
    from addsong.meta import clean_meta
    assert clean_meta('SONG (OFFICIAL VIDEO)') == 'SONG'
