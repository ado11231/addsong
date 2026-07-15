"""Tests for the ledger TSV dedup layer."""

from __future__ import annotations

from addsong.ledger import add, clear, count, has, read_rows


def test_has_returns_false_for_missing_ledger(tmp_path: str) -> None:
    assert has(str(tmp_path / "missing.tsv"), "VID1") is False


def test_add_appends_a_row_and_has_finds_it(tmp_path: str) -> None:
    ledger = str(tmp_path / "ledger.tsv")
    add(ledger, "VID1", "Artist", "Title")
    assert has(ledger, "VID1") is True
    assert has(ledger, "VID2") is False


def test_add_creates_parent_directory(tmp_path: str) -> None:
    ledger = str(tmp_path / "nested" / "dir" / "ledger.tsv")
    add(ledger, "VID1", "A", "T")
    assert has(ledger, "VID1") is True


def test_count_reports_rows(tmp_path: str) -> None:
    ledger = str(tmp_path / "ledger.tsv")
    assert count(ledger) == 0
    add(ledger, "VID1", "A", "T")
    add(ledger, "VID2", "B", "U")
    assert count(ledger) == 2


def test_clear_removes_ledger(tmp_path: str) -> None:
    ledger = str(tmp_path / "ledger.tsv")
    add(ledger, "VID1", "A", "T")
    clear(ledger)
    assert has(ledger, "VID1") is False
    assert count(ledger) == 0


def test_clear_is_no_op_for_missing_ledger(tmp_path: str) -> None:
    clear(str(tmp_path / "missing.tsv"))  # must not raise


def test_read_rows_yields_parsed_tuples(tmp_path: str) -> None:
    ledger = str(tmp_path / "ledger.tsv")
    add(ledger, "VID1", "Artist1", "Title1")
    rows = list(read_rows(ledger))
    assert rows == [("VID1", "Artist1", "Title1", rows[0][3])]
    # timestamp is present and ISO-shaped.
    assert "T" in rows[0][3]


def test_read_rows_missing_file_yields_nothing(tmp_path: str) -> None:
    assert list(read_rows(str(tmp_path / "missing.tsv"))) == []


def test_existing_bash_ledger_is_read(tmp_path: str) -> None:
    # Confirm the stable on-disk ledger format is parsed correctly.
    ledger = str(tmp_path / "ledger.tsv")
    with open(ledger, "w", encoding="utf-8") as fh:
        fh.write("dQw4w9WgXcQ\tArtist\tTitle\t2024-01-01T00:00:00\n")
    assert has(ledger, "dQw4w9WgXcQ") is True
    rows = list(read_rows(ledger))
    assert rows == [("dQw4w9WgXcQ", "Artist", "Title", "2024-01-01T00:00:00")]
