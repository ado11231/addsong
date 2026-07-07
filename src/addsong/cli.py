"""CLI entry point.

This is a minimal stub during scaffolding: it only handles --version so the
console-script entry point resolves. The full argparse surface, subcommands, and
pipeline dispatch land in a later commit.
"""

from __future__ import annotations

import sys

from addsong import __version__


def main(argv: list[str] | None = None) -> int:
    """Run the addsong CLI. Returns a process exit code."""
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] == "--version":
        print(f"addsong {__version__}")
        return 0
    print("addsong: not implemented yet (scaffold)", file=sys.stderr)
    return 1
