"""Generate rounded, brand-colored badge SVGs for the README.

Hand-built (no shields.io, no deps) so we get:
  - rounded corners (rx=4) on the outer badge + subtle outline
  - true brand colors from simple-icons
  - the real brand logo paths from simple-icons (loaded from _logo_paths.json)
  - the authentic two-tone Python mark, on a white chip so both the
    blue and yellow snakes read on the blue label
  - a clean bold system-font stack
  - zero cache lag (SVGs are committed to the repo, GitHub renders them instantly)

Run:  python assets/badges/_make_badges.py
Outputs:  assets/badges/{pypi,python,license,ytdlp,ffmpeg}.svg
"""

from __future__ import annotations

import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(HERE, "_logo_paths.json"), encoding="utf-8") as fh:
    LOGOS: dict[str, str] = json.load(fh)

_BRAND = {
    "python": "#3776AB",
    "pypi": "#3775A9",
    "youtube": "#FF0000",
    "ffmpeg": "#007808",
}

# Layout constants (all in SVG user units; the badge is 24 tall).
H = 24
RX = 4
FONT = 10
LS = 0.4  # letter-spacing
LOGO_SIZE = 14
LOGO_X = 10  # left edge of a plain (single-path) logo
TEXT_AFTER_LOGO = 30  # where label text starts when there is a logo
TEXT_NO_LOGO = 11  # ...and when there isn't
LABEL_RPAD = 12  # breathing room after the label text, before the seam
VALUE_LPAD = 11  # padding on each side of the value text
VALUE_RPAD = 11
BASELINE = 15.5  # text baseline; optically centers the caps in the 24-tall badge

# Bounding box of the two-tone Python mark within its 128x128 canvas,
# centered on (64, 64); used to crop it tightly into the logo chip.
_PY_VIEWBOX = "12.2 12.2 103.6 103.6"


def _text_w(s: str, caps: bool) -> float:
    """Rough advance width for the bold system font, with letter-spacing.

    Overestimating a touch is fine (a little extra padding); underestimating
    clips the glyphs, so the factors lean generous.
    """
    per = FONT * (0.66 if caps else 0.64)
    return per * len(s) + LS * max(0, len(s) - 1)


def _python_logo() -> str:
    """The two-tone Python mark, sized/placed like the other single-path logos.

    The top snake is white (a blue snake would disappear on the blue label);
    the bottom snake keeps its brand yellow, tying into the value chip.
    """
    logo_y = (H - LOGO_SIZE) // 2
    return (
        f'  <svg x="{LOGO_X + 1}" y="{logo_y}" width="{LOGO_SIZE}" '
        f'height="{LOGO_SIZE}" viewBox="{_PY_VIEWBOX}">\n'
        f'    <path fill="#fff" d="{LOGOS["python_top"]}" '
        'transform="translate(0 10.26)"/>\n'
        f'    <path fill="#FFD43B" d="{LOGOS["python_bottom"]}" '
        'transform="translate(0 10.26)"/>\n'
        '  </svg>\n'
    )


def _badge(
    label: str,
    value: str,
    label_bg: str,
    value_bg: str,
    logo_path: str | None = None,
    logo_color: str = "#fff",
    value_text_color: str = "#fff",
    two_tone_py: bool = False,
) -> str:
    if two_tone_py:
        logo_svg = _python_logo()
        text_x = TEXT_AFTER_LOGO
    elif logo_path:
        logo_y = (H - LOGO_SIZE) // 2
        logo_svg = (
            f'  <g transform="translate({LOGO_X + 1},{logo_y}) '
            f'scale({LOGO_SIZE / 24})" fill="{logo_color}">\n'
            f'    <path d="{logo_path}"/>\n'
            "  </g>\n"
        )
        text_x = TEXT_AFTER_LOGO
    else:
        logo_svg = ""
        text_x = TEXT_NO_LOGO

    label_w = math.ceil(text_x + _text_w(label.upper(), caps=True) + LABEL_RPAD)
    value_caps = value.upper() == value
    value_w = math.ceil(VALUE_LPAD + _text_w(value, value_caps) + VALUE_RPAD)
    total = label_w + value_w

    # The value is centered in its chip, so it stays balanced no matter how the
    # width estimate rounds. Labels stay left-aligned after their logo.
    value_text = (
        f'    <text x="{label_w + value_w / 2:g}" y="{BASELINE}" text-anchor="middle" '
        f'fill="{value_text_color}">{value}</text>\n'
    )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total}" height="{H}" '
        f'viewBox="0 0 {total} {H}" role="img" aria-label="{label}: {value}">\n'
        f'  <title>{label}: {value}</title>\n'
        '  <linearGradient id="g" x2="0" y2="100%">\n'
        '    <stop offset="0" stop-color="#fff" stop-opacity=".10"/>\n'
        '    <stop offset="1" stop-color="#000" stop-opacity=".06"/>\n'
        '  </linearGradient>\n'
        '  <clipPath id="r"><rect width="100%" height="100%" rx="4"/></clipPath>\n'
        '  <g clip-path="url(#r)">\n'
        f'    <rect width="{label_w}" height="{H}" fill="{label_bg}"/>\n'
        f'    <rect x="{label_w}" width="{value_w}" height="{H}" fill="{value_bg}"/>\n'
        '    <rect width="100%" height="100%" fill="url(#g)"/>\n'
        '  </g>\n'
        f'  <rect width="{total}" height="{H}" rx="4" fill="none" '
        'stroke="#000" stroke-opacity=".08"/>\n'
        f'{logo_svg}'
        '  <g font-family="\'Segoe UI\',\'Helvetica Neue\',Arial,sans-serif" '
        f'font-size="{FONT}" font-weight="700" letter-spacing=".4">\n'
        f'    <text x="{text_x}" y="{BASELINE}" fill="#fff">{label.upper()}</text>\n'
        f'{value_text}'
        '  </g>\n'
        '</svg>\n'
    )


def main() -> None:
    specs = [
        ("pypi", dict(label="PyPI", value="v1.0.1", label_bg=_BRAND["pypi"],
                      value_bg="#1E88E5", logo_path=LOGOS["pypi"])),
        ("python", dict(label="Python", value="3.11 - 3.14", label_bg=_BRAND["python"],
                        value_bg="#FFD43B", two_tone_py=True, value_text_color="#3776AB")),
        ("license", dict(label="License", value="MIT", label_bg="#4A4A4A",
                         value_bg="#2EA44F")),
        ("ytdlp", dict(label="Powered by", value="yt-dlp", label_bg=_BRAND["youtube"],
                       value_bg="#282828", logo_path=LOGOS["youtube"])),
        ("ffmpeg", dict(label="Tagged with", value="ffmpeg", label_bg=_BRAND["ffmpeg"],
                        value_bg="#0cb50c", logo_path=LOGOS["ffmpeg"])),
    ]
    for fname, kw in specs:
        svg = _badge(**kw)
        out = os.path.join(HERE, fname + ".svg")
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(svg)
        print(f"wrote {out}  ({len(svg)} bytes)")


if __name__ == "__main__":
    main()
