"""Tests for the subscriptions layer.

subscribe appends, rejects non-URLs, and dedupes by exact line; unsubscribe
removes and is idempotent; list skips blanks and `#` comments and prints a
hint when empty; plus the empty-file detection that powers sync's early exit.
"""

from __future__ import annotations

import pytest

from addsong import subscriptions as subs


def _setup(tmp_path: str) -> str:
    path = str(tmp_path / "subs.tsv")
    open(path, "a", encoding="utf-8").close()  # noqa: SIM115
    return path


def test_subscribe_appends_a_url(tmp_path: str) -> None:
    path = _setup(tmp_path)
    assert subs.add(path, "https://www.youtube.com/playlist?list=PLabc") is True
    with open(path) as fh:
        assert fh.read().strip() == "https://www.youtube.com/playlist?list=PLabc"


def test_subscribe_rejects_a_non_url(tmp_path: str) -> None:
    path = _setup(tmp_path)
    with pytest.raises(ValueError, match="needs a URL"):
        subs.add(path, "not a url")


def test_subscribe_is_idempotent_exact_line_dedup(tmp_path: str) -> None:
    path = _setup(tmp_path)
    assert subs.add(path, "https://youtu.be/PLabc") is True
    assert subs.add(path, "https://youtu.be/PLabc") is False  # already present
    with open(path) as fh:
        lines = [ln for ln in fh.read().splitlines() if ln]
    assert lines.count("https://youtu.be/PLabc") == 1


def test_unsubscribe_removes_a_url(tmp_path: str) -> None:
    path = _setup(tmp_path)
    subs.add(path, "https://youtu.be/PLabc")
    subs.add(path, "https://youtu.be/PLxyz")
    subs.remove(path, "https://youtu.be/PLabc")
    with open(path) as fh:
        lines = [ln for ln in fh.read().splitlines() if ln]
    assert "https://youtu.be/PLabc" not in lines
    assert "https://youtu.be/PLxyz" in lines


def test_unsubscribe_is_idempotent_when_not_subscribed(tmp_path: str) -> None:
    path = _setup(tmp_path)
    subs.remove(path, "https://youtu.be/never")  # must not raise
    assert list(subs.read_urls(path)) == []


def test_unsubscribe_preserves_comments(tmp_path: str) -> None:
    path = _setup(tmp_path)
    with open(path, "w") as fh:
        fh.write("# keep me\nhttps://youtu.be/PLabc\n")
    subs.remove(path, "https://youtu.be/PLabc")
    with open(path) as fh:
        assert "# keep me" in fh.read()


def test_list_skips_blanks_and_comments(tmp_path: str) -> None:
    path = _setup(tmp_path)
    with open(path, "w") as fh:
        fh.write("# my subscriptions\n\nhttps://youtu.be/AA\n# trailing note\nhttps://youtu.be/BB\n")
    assert list(subs.read_urls(path)) == ["https://youtu.be/AA", "https://youtu.be/BB"]


def test_has_subscriptions_true_when_populated(tmp_path: str) -> None:
    path = _setup(tmp_path)
    with open(path, "w") as fh:
        fh.write("# only comment\nhttps://youtu.be/AA\n")
    assert subs.has_subscriptions(path) is True


def test_has_subscriptions_false_when_empty(tmp_path: str) -> None:
    path = _setup(tmp_path)
    with open(path, "w") as fh:
        fh.write("# only comment\n\n")
    assert subs.has_subscriptions(path) is False


def test_has_subscriptions_false_when_missing(tmp_path: str) -> None:
    assert subs.has_subscriptions(str(tmp_path / "missing.tsv")) is False
