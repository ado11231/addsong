"""CLI entry point: argparse, subcommands, mutual-exclusivity, exit codes.

Behaviour:
  - subcommands peeked before flags: subscribe/unsubscribe/list/sync/forget.
  - --from / --playlist / --results / a URL/search arg are mutually exclusive.
  - a bare non-URL argument defaults to --results 1 (a single YouTube search).
  - unquoted bare words are joined into the query (no quoting needed).
  - exit codes 0 (added), 2 (skipped), 1 (failed); top-level 1 if anything failed.
  - --version / --help honored whether or not a subcommand was named.
"""

from __future__ import annotations

import argparse
import sys

from addsong import __version__
from addsong import pipeline as pipe
from addsong.config import load_config
from addsong.constants import AUDIO_FORMATS, EXIT_FAILED
from addsong.pipeline import Flags, Run
from addsong.platform import default_watch_dir, detect_os
from addsong.review import open_tty_available
from addsong.ui import UI

_PROG = "addsong"

_SUBCOMMANDS = ("subscribe", "unsubscribe", "list", "sync", "forget")


def _detect_have_tty() -> bool:
    """True if a controlling terminal is openable right now."""
    return open_tty_available()


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=_PROG,
        description="download a song and auto-import it into Apple Music.",
        add_help=False,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("-h", "--help", action="store_true", help="show this help and exit")
    p.add_argument("--version", action="store_true", help="print the version and exit")
    p.add_argument("--playlist", action="store_true", help="treat the URL as a playlist")
    p.add_argument("--from", dest="from_file", metavar="FILE",
                   help="read URLs (one per line) from FILE, or - for stdin")
    p.add_argument("--results", metavar="N",
                   help="free-text YouTube search; import top N results (1-50)")
    p.add_argument("-y", "--yes", action="store_true", help="don't prompt; accept metadata")
    p.add_argument("--review", action="store_true", help="always prompt to review metadata")
    p.add_argument("--reimport", action="store_true", help="import even if already imported")
    p.add_argument(
        "-n", "--dry-run", action="store_true", help="resolve/show metadata; import nothing"
    )
    p.add_argument("-q", "--quiet", action="store_true", help="suppress info banners and status")
    p.add_argument("-v", "--verbose", action="store_true", help="surface yt-dlp/ffmpeg stderr")
    p.add_argument("--no-progress", action="store_true", help="use spinner instead of real bar")
    p.add_argument("--format", metavar="FMT", help=f"audio format: {' '.join(AUDIO_FORMATS)}")
    p.add_argument("--quality", metavar="N", help="audio quality 0-10, 0=best")
    p.add_argument("--notify", action="store_true", help="fire desktop notification per import")
    p.add_argument("--no-color", action="store_true", help="disable colored output")
    p.add_argument(
        "--print-completion",
        metavar="SHELL",
        help="print a shell completion script (bash/zsh/fish) and exit",
    )

    # Positional: the URL or free-text query. Bare words are joined by argparse
    # into a single string via nargs='*' so "queen bohemian rhapsody" stays whole
    # without the user quoting it (bare words are joined into one query).
    p.add_argument("query", nargs="*", help="URL or free-text YouTube search")
    return p


def _validate_and_resolve(parser: argparse.ArgumentParser, ns) -> int:  # type: ignore[no-untyped-def]
    """Apply mutual-exclusivity and resolve --results/--from/--query.

    Returns 0 on success or an exit code (already reported + raised via SystemExit).
    Raises SystemExit on error.
    """
    # --results range and integer checks (rejects 0, non-int, >50).
    if ns.results is not None:
        try:
            ns.results = int(ns.results)
        except ValueError:
            parser.error(f"--results needs a positive integer (got: '{ns.results}')")
        if ns.results <= 0:
            parser.error(f"--results needs a positive integer (got: '{ns.results}')")
        if ns.results > 50:
            parser.error("--results is capped at 50 (use a playlist URL for more)")

    # --format allowlist and --quality range.
    if ns.format is not None:
        if ns.format not in AUDIO_FORMATS:
            parser.error(
                f"--format must be one of: {' '.join(AUDIO_FORMATS)} (got: '{ns.format}')"
            )
    if ns.quality is not None:
        try:
            q = int(ns.quality)
        except ValueError:
            parser.error(f"--quality must be an integer 0-10 (got: '{ns.quality}')")
        if q < 0 or q > 10:
            parser.error(f"--quality must be an integer 0-10 (got: '{ns.quality}')")
    return 0


def _mutual_exclusivity(ns, query: str) -> None:  # type: ignore[no-untyped-def]
    """Apply the --from / --playlist / --results / URL mutual-exclusivity rules."""
    has_from = bool(ns.from_file)
    has_playlist = bool(ns.playlist)
    has_results = ns.results is not None and ns.results > 0
    has_url = bool(query)

    if has_from:
        if has_playlist or has_results:
            _die("--from is exclusive with --playlist/--results")
        if has_url:
            _die("--from is exclusive with a URL/search argument")
    elif has_playlist:
        if has_results:
            _die("--playlist is exclusive with --results")
        if not has_url:
            _die("--playlist needs a URL")
        if not _is_url(query):
            _die(f"--playlist needs a URL (got: '{query}')")
    elif has_results:
        if not has_url:
            _die("--results needs a query (try: addsong --results 3 \"80s disco mix\")")
        if _is_url(query):
            _die("--results and a URL are mutually exclusive")


def _is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")


def _die(msg: str) -> None:
    print(f"{_PROG}: error: {msg}", file=sys.stderr)
    raise SystemExit(EXIT_FAILED)


def _emit_help(parser: argparse.ArgumentParser) -> str:
    """Render the --help text, annotated with subcommands and examples.

    argparse alone can't express the rich USAGE block; we prepend a custom
    epilog so `addsong --help` stays useful.
    """
    return parser.format_help()


def _build_run(ns, config, have_tty: bool) -> Run:  # type: ignore[no-untyped-def]
    os_mode = detect_os()
    watch_dir = config.watch_dir or default_watch_dir(os_mode)
    audio_format = ns.format if ns.format is not None else config.audio_format
    audio_quality = ns.quality if ns.quality is not None else config.audio_quality

    notify = ns.notify or config.notify
    progress = (not ns.no_progress) and config.progress

    ui = UI(
        prog=_PROG,
        have_tty=have_tty,
        quiet=ns.quiet,
        verbose=ns.verbose,
        no_color=ns.no_color,
        progress=progress,
        notify=notify,
        os_mode=os_mode,
    )

    flags = Flags(
        playlist=ns.playlist,
        assume_yes=ns.yes,
        review_force=ns.review,
        reimport=ns.reimport,
        dry_run=ns.dry_run,
    )
    return Run(
        config=config,
        ui=ui,
        flags=flags,
        have_tty=have_tty,
        os_mode=os_mode,
        watch_dir=watch_dir,
        audio_format=audio_format,
        audio_quality=audio_quality,
    )


def main(argv: list[str] | None = None) -> int:
    """Run the addsong CLI. Returns a process exit code."""
    args = sys.argv[1:] if argv is None else argv

    # Subcommand peek: bare word in the known set is never treated as a URL.
    subcmd = ""
    if args and args[0] in _SUBCOMMANDS:
        subcmd = args[0]
        rest = args[1:]
        # --help / --version alone honored immediately, even for subcommands.
        if rest and rest[0] in ("-h", "--help"):
            _print_help()
            return 0
        if rest and rest[0] == "--version":
            print(f"{_PROG} {__version__}")
            return 0
        args = rest

    parser = _build_parser()
    ns = parser.parse_args(args)

    if ns.help:
        _print_help()
        return 0
    if ns.version:
        print(f"{_PROG} {__version__}")
        return 0
    if ns.print_completion is not None:
        return _print_completion(ns.print_completion)

    _validate_and_resolve(parser, ns)
    query = " ".join(ns.query) if ns.query else ""

    # Default: a bare non-URL argument is a 1-result YouTube search.
    if not subcmd and not ns.from_file and not ns.playlist and (ns.results is None) and query:
        if not _is_url(query):
            ns.results = 1

    # Subcommands that resolve before preflight.
    config = load_config()
    have_tty = _detect_have_tty()

    if subcmd == "subscribe":
        if not query:
            _die("subscribe needs a URL")
        from addsong import subscriptions as subs
        try:
            added = subs.add(config.subscriptions, query)
        except ValueError as e:
            _die(str(e))
        # UI for the status line needs a Run (for colors); build a minimal one.
        run = _build_run(ns, config, have_tty)
        run.ui.status("Subscribed:" if added else "Already subscribed:", query)
        return 0

    if subcmd == "unsubscribe":
        if not query:
            _die("unsubscribe needs a URL")
        from addsong import subscriptions as subs
        subs.remove(config.subscriptions, query)
        run = _build_run(ns, config, have_tty)
        run.ui.status("Unsubscribed:", query)
        return 0

    if subcmd == "list":
        from addsong import subscriptions as subs
        urls = list(subs.read_urls(config.subscriptions))
        if not urls:
            print(
                f'No subscriptions yet. Try: {_PROG} subscribe '
                f'"https://www.youtube.com/playlist?list=..."'
            )
            return 0
        for u in urls:
            print(u)
        return 0

    if subcmd == "forget":
        run = _build_run(ns, config, have_tty)
        # forget skips preflight — it touches only the ledger file.
        try:
            pipe.builtin_forget(run, yes=ns.yes)
        except SystemExit as e:
            return int(e.code) if e.code is not None else 0
        return 0

    if subcmd == "sync":
        if not _has_subscriptions(config):
            _die("no subscriptions yet -- see 'addsong list'")
        run = _build_run(ns, config, have_tty)
        pipe.preflight(run)
        try:
            pipe.builtin_sync(run)
        except SystemExit as e:
            return int(e.code) if e.code is not None else 0
        return 0

    # No subcommand: enforce mutual-exclusivity, then run the import flow.
    _mutual_exclusivity(ns, query)
    if not ns.from_file and not ns.playlist and (ns.results is None) and not query:
        _print_help(to_stderr=True)
        return EXIT_FAILED

    run = _build_run(ns, config, have_tty)
    pipe.preflight(run)

    try:
        if ns.from_file:
            pipe.builtin_from_file(run, ns.from_file)
        elif ns.playlist:
            pipe.builtin_playlist(run, query)
        elif ns.results:
            pipe.builtin_search(run, query, ns.results)
        else:
            # Single URL.
            rev = pipe.interactive_for(run, playlist=False)
            rc = pipe.process_one(run, query, rev)
            if rc == 0:
                pipe.note_imported(run, 1)
                return 0
            return 0 if rc == 2 else EXIT_FAILED
    except SystemExit as e:
        return int(e.code) if e.code is not None else 0
    return 0


def _has_subscriptions(config) -> bool:  # type: ignore[no-untyped-def]
    from addsong import subscriptions as subs
    return subs.has_subscriptions(config.subscriptions)


def _print_completion(shell: str) -> int:
    from addsong.completion import render, shells

    valid = shells()
    if shell not in valid:
        _die(f"--print-completion wants one of: {' '.join(valid)} (got: '{shell}')")
    sys.stdout.write(render(shell))
    return 0


def _print_help(to_stderr: bool = False) -> None:
    text = _help_text()
    (sys.stderr if to_stderr else sys.stdout).write(text)


def _help_text() -> str:
    return (
        f"{_PROG}: download a song and auto-import it into Apple Music.\n\n"
        "USAGE:\n"
        f"    {_PROG} [options] <url-or-query>\n"
        f"    {_PROG} subscribe <playlist-url>      subscribe to a playlist\n"
        f"    {_PROG} unsubscribe <playlist-url>     drop a subscription\n"
        f"    {_PROG} list                           show subscribed playlists\n"
        f"    {_PROG} sync [options]                 import new tracks from subscriptions\n"
        f"    {_PROG} forget [-y]                    reset dedup ledger\n"
        f"    {_PROG} --help\n\n"
        "SUBCOMMANDS:\n"
        "    subscribe <url>    Remember a playlist URL for repeat syncs.\n"
        "    unsubscribe <url>  Forget a playlist URL.\n"
        "    list               Print the currently subscribed playlist URLs.\n"
        "    sync               Re-import any new tracks from each subscribed playlist\n"
        "                       (already-imported tracks are skipped). Composes with\n"
        "                       --reimport, --dry-run, --review, -y.\n"
        "    forget             Forget every imported track so future adds treat each\n"
        "                       as new again. Prompts at a terminal; pass -y to skip.\n\n"
        "OPTIONS:\n"
        "    --playlist        Treat the URL as a playlist and import every track.\n"
        "    --from FILE       Read URLs (one per line) from FILE, or - for stdin.\n"
        "    --results N       Treat the argument as a free-text YouTube search and\n"
        "                      import the top N results (1-50; default 1 when the\n"
        "                      argument is not a URL).\n"
        "    -y, --yes         Don't prompt; accept the scraped/cleaned metadata.\n"
        "    --review          Always prompt to review metadata (even for playlists).\n"
        "    --reimport        Import even if this track was imported before.\n"
        "    -n, --dry-run     Resolve and show metadata; download/import nothing.\n"
        "    -q, --quiet       Suppress info banners and per-track status lines.\n"
        "    -v, --verbose     Surface yt-dlp/ffmpeg stderr for troubleshooting.\n"
        "    --no-progress     Use the spinner instead of yt-dlp's real download bar.\n"
        f"    --format FMT      Output audio format, one of: {' '.join(AUDIO_FORMATS)}\n"
        "                      (default: m4a; overrides ADDSONG_AUDIO_FORMAT).\n"
        "    --quality N       Audio quality 0-10, 0=best (default: 0).\n"
        "    --notify          Fire a desktop notification per imported track.\n"
        "    --no-color        Disable colored output (also honors NO_COLOR).\n"
        "    -h, --help        Show this help.\n"
        "    --version         Print the version and exit.\n"
        "    --print-completion SHELL\n"
        "                      Print a shell completion script (bash/zsh/fish)\n"
        "                      and exit. Install: `source <(addsong --print-completion bash)`.\n\n"
        "EXAMPLES:\n"
        f"    {_PROG} \"https://www.youtube.com/watch?v=...\"\n"
        f"    {_PROG} \"queen bohemian rhapsody\"\n"
        f"    {_PROG} --results 3 \"80s disco mix\"\n"
        f"    {_PROG} --playlist \"https://www.youtube.com/playlist?list=PL...\"\n"
        f"    {_PROG} subscribe \"https://www.youtube.com/playlist?list=PL...\"\n"
        f"    {_PROG} sync -y\n"
        f"    {_PROG} -y \"https://youtu.be/...\"\n"
        f"    {_PROG} --dry-run \"https://youtu.be/...\"\n"
        f"    {_PROG} --from songs.txt\n"
        f"    pbpaste | {_PROG} --from -\n"
    )
