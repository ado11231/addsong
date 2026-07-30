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


def test_bash_has_format_values(tmp_path: str) -> None:
    from addsong.completion import render
    out = render('bash')
    assert 'm4a' in out
    assert 'mp3' in out
    assert 'flac' in out


def test_zsh_has_format_values(tmp_path: str) -> None:
    from addsong.completion import render
    out = render('zsh')
    assert 'm4a' in out
    assert 'mp3' in out


def test_fish_has_format_values(tmp_path: str) -> None:
    from addsong.completion import render
    out = render('fish')
    assert 'm4a' in out
    assert 'mp3' in out


def test_bash_has_quality_range(tmp_path: str) -> None:
    from addsong.completion import render
    out = render('bash')
    assert '0 1 2 3 4 5 6 7 8 9 10' in out


def test_zsh_has_quality_range(tmp_path: str) -> None:
    from addsong.completion import render
    out = render('zsh')
    assert '0 1 2 3 4 5 6 7 8 9 10' in out


def test_fish_has_quality_range(tmp_path: str) -> None:
    from addsong.completion import render
    out = render('fish')
    assert '0 1 2 3 4 5 6 7 8 9 10' in out


def test_all_shells_mention_subscribe(tmp_path: str) -> None:
    from addsong.completion import render, shells
    for s in shells():
        assert 'subscribe' in render(s)


def test_all_shells_mention_forget(tmp_path: str) -> None:
    from addsong.completion import render, shells
    for s in shells():
        assert 'forget' in render(s)


def test_all_shells_mention_dry_run(tmp_path: str) -> None:
    from addsong.completion import render, shells
    for s in shells():
        assert 'dry-run' in render(s)


def test_all_shells_mention_print_completion(tmp_path: str) -> None:
    from addsong.completion import render, shells
    for s in shells():
        assert 'print-completion' in render(s)


def test_shells_returns_tuple(tmp_path: str) -> None:
    from addsong.completion import shells
    assert isinstance(shells(), tuple)


def test_shells_contains_bash_zsh_fish(tmp_path: str) -> None:
    from addsong.completion import shells
    s = shells()
    assert 'bash' in s
    assert 'zsh' in s
    assert 'fish' in s
