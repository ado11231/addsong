"""Metadata string helpers: filename-safe names, URL id parsing, and title scrubbing.

`clean_meta()` ports the Bash `perl -CSD -pe '...'` filter to Python `re`, with
an explicit loop for the "strip bracketed junk until none left" behaviour that
Perl expressed as `1 while s/...//gix`.
"""

from __future__ import annotations

import re

# 11-char YouTube id alphabet, used by id_from_url.
_YT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")

# --- clean_meta ---------------------------------------------------------------
#
# The patterns below are a line-by-line port of the Perl one-liner in the Bash
# script. Perl used /gix (global, ignorecase, extended-whitespace); Python
# compiles each as a standalone pattern with re.IGNORECASE and re.sub handles
# the global pass. The bracketed-junk pattern needs an outer loop (Perl's
# `1 while s/.../`) for nested cases, so _clean_bracketed repeats until stable.

# Bracketed junk: (Official Video), [4K], (Lyrics), (Audio), [MV], (Remastered 2014), etc.
_BRACKET_JUNK = re.compile(
    r"""
      \s*                  # leading whitespace before the bracket
      [\(\[]               # opening ( or [
      [^\)\]]*             # any chars except ) ]  (the bit before the keyword)
      \b                   # word boundary before the keyword
      (?:
          official (?: \s+ (?:music\s+)? video | \s+ audio | \s+ lyrics? | \s+ visualizer )?
        | music\s+video
        | lyrics?
        | audio
        | video
        | visualizer
        | hd
        | hq
        | full\s*hd
        | 4k
        | 8k
        | full\s+album
        | mv
        | m/v
        | explicit
        | clean
        | remaster(?:ed)? (?: \s+ \d{4} )?
      )
      [^\)\]]*             # any chars after the keyword
      [\)\]]               # closing ) or ]
    """,
    re.IGNORECASE | re.VERBOSE,
)

# (feat. X) or [ft. X] blocks.
_FEAT_BLOCK = re.compile(r"\s*[\(\[]\s*(?:ft\.?|feat\.?)[^\)\]]*[\)\]]", re.IGNORECASE)

# Trailing " - Topic" suffix (YouTube Music topic channels).
_TOPIC_SUFFIX = re.compile(r"\s*-\s*topic\s*$", re.IGNORECASE)

# Trailing or leading separator: -, en-dash (U+2013), or |, with surrounding whitespace.
_TRAIL_SEP = re.compile(r"\s*[-\u2013|]\s*$")
_LEAD_SEP = re.compile(r"^\s*[-\u2013|]\s*")

# Runs of two or more whitespace chars collapse to one space.
_MULTI_WS = re.compile(r"\s{2,}")


def _clean_bracketed(s: str) -> str:
    """Repeatedly strip bracketed junk until no more matches (Perl `1 while s/`)."""
    prev: str | None = None
    while prev != s:
        prev = s
        s = _BRACKET_JUNK.sub("", s)
    return s


def clean_meta(value: str) -> str:
    """Clean a scraped title/artist string.

    Drops official-video/lyrics/4K/remaster brackets, feat. blocks, the trailing
    "- Topic" suffix, leading/trailing separators, and collapses whitespace.
    Mirrors the Bash `clean_meta()` Perl filter exactly.
    """
    s = _clean_bracketed(value)
    s = _FEAT_BLOCK.sub("", s)
    s = _TOPIC_SUFFIX.sub("", s)
    s = _TRAIL_SEP.sub("", s)
    s = _LEAD_SEP.sub("", s)
    s = _MULTI_WS.sub(" ", s)
    return s.strip()


def safe_name(s: str) -> str:
    """Make a string safe as a filename: no path separators or colons.

    Mirrors the Bash `safe_name()`: slash, colon, and backslash become `_`.
    """
    return s.replace("/", "_").replace(":", "_").replace("\\", "_")


def id_from_url(url: str) -> str | None:
    """Extract an 11-char YouTube id from a URL with no network.

    Handles watch, youtu.be, shorts, and embed URLs. Returns the id on match,
    or None for non-YouTube URLs (yt-dlp is the fallback in the caller).
    """
    id_part: str | None
    if "youtu.be/" in url:
        id_part = url.split("youtu.be/", 1)[1]
    elif "/shorts/" in url:
        id_part = url.split("/shorts/", 1)[1]
    elif "/embed/" in url:
        id_part = url.split("/embed/", 1)[1]
    elif "v=" in url:
        id_part = url.split("v=", 1)[1]
    else:
        return None

    # Strip trailing params (?: &), path separators, or fragments.
    id_part = re.split(r"[?&/#]", id_part, maxsplit=1)[0]
    if _YT_ID_RE.match(id_part):
        return id_part
    return None


# --- parse_meta ---------------------------------------------------------------
#
# Parses yt-dlp's 8-field --print block into structured track metadata. yt-dlp
# prints "NA" for missing fields; those become empty strings. If YouTube Music
# structured metadata (track + artist) is present it's used as-is; otherwise a
# heuristic "Artist - Title" split is attempted, falling back to the uploader as
# artist. The artist and title are run through clean_meta().


class TrackMeta:
    """Structured metadata for a single track, as parsed from yt-dlp output."""

    __slots__ = ("id", "artist", "title", "album", "year", "track_no")

    def __init__(
        self,
        id: str,
        artist: str,
        title: str,
        album: str = "",
        year: str = "",
        track_no: str = "",
    ) -> None:
        self.id = id
        self.artist = artist
        self.title = title
        self.album = album
        self.year = year
        self.track_no = track_no


def _NA(value: str) -> str:
    """yt-dlp prints 'NA' for missing fields; treat as empty."""
    return "" if value == "NA" else value


def parse_meta(block: str) -> TrackMeta | None:
    """Parse a yt-dlp 8-line metadata block into a TrackMeta, or None if no id.

    Reads only the first 8 lines so a retry that appends a second copy is safe.
    """
    lines = block.splitlines()
    if len(lines) < 1 or not lines[0]:
        return None
    # Pad to 8 fields so IndexError can never happen.
    padded = (lines + [""] * 8)[:8]
    id_ = padded[0]
    raw_title = padded[1]
    raw_uploader = padded[2]
    m_track = _NA(padded[3])
    m_artist = _NA(padded[4])
    m_album = _NA(padded[5])
    m_year = _NA(padded[6])
    m_trackno = _NA(padded[7])

    if m_track and m_artist:
        # Structured YouTube Music metadata — already clean.
        artist = m_artist
        title = m_track
    elif " - " in raw_title:
        artist, title = raw_title.split(" - ", 1)
        artist = clean_meta(artist)
        title = clean_meta(title)
    else:
        artist = clean_meta(raw_uploader)
        title = clean_meta(raw_title)

    # Title is never empty — fall back to the raw title.
    if not title:
        title = raw_title

    return TrackMeta(
        id=id_, artist=artist, title=title, album=m_album, year=m_year, track_no=m_trackno
    )
