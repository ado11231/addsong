"""Console UI: colors, status lines, banners, spinner, progress bar, notify.

All informational output (err/say/status/banner) is written to **stderr** so
stdout stays clean for scripted use. Spinner and progress render to
``/dev/tty`` so they don't pollute piped output.

Color honors --no-color / NO_COLOR / no-TTY, falling back to plain text. The
spinner is skipped (command runs synchronously with no animation) when there's
no TTY or under --quiet/--verbose.
"""

from __future__ import annotations

import os
import re
import subprocess
import threading
import time
from collections.abc import Callable
from typing import IO

from rich.console import Console
from rich.markup import escape as _escape
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
)


def _open_tty() -> IO[str] | None:
    """Open /dev/tty for writing; return None if there's no controlling terminal."""
    try:
        return open("/dev/tty", "w", encoding="utf-8", errors="replace")  # noqa: SIM115
    except OSError:
        return None


_PROG_RE = re.compile(
    r"\[download\]\s+([0-9.]+)%.*?(?:\s+at\s+([0-9.]+\S+/s))?(?:.*?ETA\s+(\S+))?"
)


class UI:
    """All user-facing output for a single addsong run."""

    def __init__(
        self,
        *,
        prog: str = "addsong",
        have_tty: bool = False,
        quiet: bool = False,
        verbose: bool = False,
        no_color: bool = False,
        progress: bool = True,
        notify: bool = False,
        os_mode: str = "other",
    ) -> None:
        self.prog = prog
        self.have_tty = have_tty
        self.quiet = quiet
        self.verbose = verbose
        self.progress = progress
        self.notify = notify
        self.os_mode = os_mode

        colorsys = not (no_color or bool(os.environ.get("NO_COLOR")))
        # rich detects whether each output file is a real terminal itself;
        # `have_tty` only gates whether we open /dev/tty for the spinner/progress.
        # `no_color` disables our markup colors even at a TTY.
        no_color_flag = not colorsys or not have_tty
        self.console = Console(stderr=True, no_color=no_color_flag)
        self.tty: Console | None = None
        if have_tty:
            tty_file = _open_tty()
            if tty_file is not None:
                self.tty = Console(file=tty_file, no_color=no_color_flag)

    # --- text output -------------------------------------------------------

    def err(self, msg: str) -> None:
        """Error line to stderr with the program prefix."""
        self.console.print(
            f"[bold red]{self.prog}:[/bold red] {_escape(msg)}", highlight=False
        )

    def say(self, msg: str) -> None:
        """Info line to stderr, suppressed under --quiet. Markup is escaped."""
        if not self.quiet:
            self.console.print(_escape(msg), highlight=False)

    def say_markup(self, msg: str) -> None:
        """Info line that carries rich markup (e.g. colored totals).

        Used by finish_batch where the color tags are intentional; user-supplied
        fragments in the message must already be escaped by the caller.
        """
        if not self.quiet:
            self.console.print(msg, highlight=False)

    def banner(self, msg: str) -> None:
        """Cyan »-prefixed banner line, suppressed under --quiet."""
        if not self.quiet:
            self.console.print(f"[cyan]»[/cyan] {_escape(msg)}", highlight=False)

    def status(self, keyword: str, rest: str) -> None:
        """Aligned status line colored by keyword. Suppressed under --quiet.

        Icons only render when color is on; without a TTY the line is plain
        ``keyword`` + rest so scripted greps still match.
        """
        if self.quiet:
            return
        key = keyword.lower()
        if key.startswith("added") or key.startswith("would add") or key.startswith("subscribed"):
            color = "bold green"
        elif key.startswith("skipped") or key.startswith("already") or "subscribed" in key:
            color = "yellow"
        elif key.startswith("failed"):
            color = "bold red"
        else:
            color = ""
        # Resolved-once icon lives inside the color branch, so when there's no
        # color we emit keyword+rest plainly — that's what scripted greps lock onto.
        if color and self.console.color_system is not None:
            icon = {"bold green": "✓ ", "yellow": "• ", "bold red": "✗ "}[color]
            self.console.print(
                f"  [{color}]{icon}{_escape(keyword):<8}[/{color}] {_escape(rest)}",
                highlight=False,
            )
        else:
            self.console.print(
                f"  {_escape(keyword):<8} {_escape(rest)}", highlight=False
            )

    # --- summarize ---------------------------------------------------------

    def finish_batch(self, verb: str, n_added: int, n_skipped: int, n_failed: int) -> None:
        """End-of-run summary line. Failures are red when nonzero."""
        fcolor = "bold red" if n_failed > 0 else "dim"
        self.say_markup(
            f"Done. {_escape(verb)} [bold green]{n_added}[/bold green], "
            f"skipped [yellow]{n_skipped}[/yellow], "
            f"failed [{fcolor}]{n_failed}[/{fcolor}]."
        )

    # --- retry -------------------------------------------------------------

    def on_retry(self, attempt: int, retries: int, delay: int) -> None:
        """Transient-retry notice line."""
        self.err(f"transient error, retrying ({attempt}/{retries}) in {delay}s...")

    # --- spinner -----------------------------------------------------------

    _SPIN_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def with_spinner(self, label: str, fn: Callable[[], int]) -> int:
        """Run fn() behind a spinner on /dev/tty; propagate its exit code.

        Without a TTY or under --quiet/--verbose, fn() runs synchronously with
        no animation.
        """
        if not self.have_tty or self.quiet or self.verbose or self.tty is None:
            return fn()

        stopped = threading.Event()

        def _spin() -> None:
            assert self.tty is not None
            f = self.tty.file
            i = 0
            f.write("\033[?25l")  # hide cursor
            f.flush()
            while not stopped.is_set():
                frame = self._SPIN_FRAMES[i % len(self._SPIN_FRAMES)]
                f.write(f"\r  {frame} {label}")
                f.flush()
                i += 1
                time.sleep(0.1)
            f.write("\r\033[K\033[?25h")  # clear line, show cursor
            f.flush()

        thread = threading.Thread(target=_spin, daemon=True)
        thread.start()
        try:
            return fn()
        finally:
            stopped.set()
            thread.join()

    # --- progress bar + download orchestration -----------------------------

    def download_track(
        self,
        staging: str,
        label: str,
        args: list[str],
        *,
        retries: int,
        retry_delay: int,
        stderr_path: str | None = None,
        on_retry: Callable[[int, int, int], None] | None = None,
    ) -> int:
        """Download one track via run_ytdlp, choosing progress bar / spinner / none."""
        from addsong.ytdlp import run_ytdlp

        err_path = stderr_path or os.path.join(staging, "dl.err")
        use_bar = (
            self.progress
            and self.have_tty
            and not self.quiet
            and not self.verbose
            and self.tty is not None
        )
        if use_bar:
            return self._download_with_progress(
                label, args, retries, retry_delay, err_path, on_retry
            )
        return self.with_spinner(
            label,
            lambda: run_ytdlp(
                args,
                retries=retries,
                retry_delay=retry_delay,
                verbose=self.verbose,
                stderr_path=err_path,
                on_retry=on_retry or self.on_retry,
            ),
        )

    def _download_with_progress(
        self,
        label: str,
        args: list[str],
        retries: int,
        retry_delay: int,
        err_path: str,
        on_retry: Callable[[int, int, int], None] | None,
    ) -> int:
        from addsong.ytdlp import run_ytdlp

        assert self.tty is not None
        progress = Progress(
            TextColumn("[bold green]{task.fields[label]}"),
            BarColumn(),
            TextColumn("{task.percentage:>5.1f}%"),
            DownloadColumn(),
            TimeRemainingColumn(),
            console=self.tty,
            transient=True,
        )
        task_id = progress.add_task("dl", label=label, total=100.0)

        def _on_line(line: str) -> None:
            m = _PROG_RE.search(line)
            if m:
                pct = float(m.group(1))
                progress.update(task_id, completed=min(pct, 100.0))

        progress.start()
        try:
            return run_ytdlp(
                args,
                retries=retries,
                retry_delay=retry_delay,
                verbose=self.verbose,
                stderr_path=err_path,
                on_progress=_on_line,
                on_retry=on_retry or self.on_retry,
            )
        finally:
            progress.stop()

    # --- desktop notification ---------------------------------------------

    def fire_notify(self, title: str, body: str) -> None:
        """Best-effort desktop notification. No-op unless --notify is on."""
        if not self.notify:
            return
        if self.os_mode == "mac":
            for cmd in (("terminal-notifier", "-title", title, "-message", body),):
                if _which(cmd[0]):
                    subprocess.run(
                        cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False
                    )
                    return
            if _which("osascript"):
                t = title.replace('"', '\\"')
                b = body.replace('"', '\\"')
                subprocess.run(
                    ["osascript", "-e", f'display notification "{b}" with title "{t}"'],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
                )
        else:
            if _which("notify-send"):
                subprocess.run(
                    ["notify-send", title, body],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
                )


def _which(name: str) -> bool:
    """True if an executable is on PATH (shutil.which without the import cost)."""
    from shutil import which

    return which(name) is not None
