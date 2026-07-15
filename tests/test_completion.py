"""Tests for `addsong --print-completion {bash,zsh,fish}`."""

from __future__ import annotations

from addsong.cli import main
from addsong.completion import render, shells


def _run(*args: str) -> tuple[int, str, str]:
    import contextlib
    import io

    err, out = io.StringIO(), io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
        try:
            rc = main(list(args))
        except SystemExit as e:
            rc = int(e.code) if e.code is not None else 0
    return rc, err.getvalue(), out.getvalue()


def test_render_each_shell_has_signature_markers() -> None:
    assert "complete -F _addsong addsong" in render("bash")
    assert "#compdef addsong" in render("zsh")
    assert "# fish completion for addsong" in render("fish")


def test_render_lists_all_subcommands_and_flags() -> None:
    # Bare flag names (without the leading --) appear in every shell's output:
    # bash/zsh write `--flag`, fish writes `-l flag`.
    long_flags = ("playlist", "from", "results", "yes", "review", "reimport",
                  "dry-run", "quiet", "verbose", "no-progress", "format",
                  "quality", "notify", "no-color", "help", "version",
                  "print-completion")
    for shell in shells():
        out = render(shell)
        for name in ("subscribe", "unsubscribe", "list", "sync", "forget"):
            assert name in out
        for flag in long_flags:
            assert flag in out


def test_render_unknown_shell_raises() -> None:
    try:
        render("powershell")
    except ValueError as e:
        assert "powershell" in str(e)
    else:
        raise AssertionError("expected ValueError for unknown shell")


def test_cli_print_completion_bash_exits_zero() -> None:
    rc, _err, out = _run("--print-completion", "bash")
    assert rc == 0
    assert "complete -F _addsong addsong" in out


def test_cli_print_completion_zsh_exits_zero() -> None:
    rc, _err, out = _run("--print-completion", "zsh")
    assert rc == 0
    assert "#compdef addsong" in out


def test_cli_print_completion_fish_exits_zero() -> None:
    rc, _err, out = _run("--print-completion", "fish")
    assert rc == 0
    assert "# fish completion for addsong" in out


def test_cli_print_completion_rejects_unknown_shell() -> None:
    rc, err, _out = _run("--print-completion", "tcsh")
    assert rc == 1
    assert "--print-completion wants one of: bash zsh fish" in err
    assert "tcsh" in err


def test_cli_print_completion_lists_subcommands() -> None:
    _rc, _err, out = _run("--print-completion", "bash")
    for name in ("subscribe", "unsubscribe", "list", "sync", "forget"):
        assert name in out


def test_help_documents_print_completion() -> None:
    rc, _err, out = _run("--help")
    assert rc == 0
    assert "--print-completion" in out
