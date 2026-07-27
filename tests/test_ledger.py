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


def test_has_after_clear_is_false(tmp_path: str) -> None:
    ledger = str(tmp_path / 'l.tsv')
    from addsong.ledger import add, clear, has
    add(ledger, 'V1', 'A', 'T')
    clear(ledger)
    assert has(ledger, 'V1') is False


def test_count_after_multiple_adds(tmp_path: str) -> None:
    ledger = str(tmp_path / 'l.tsv')
    from addsong.ledger import add, count
    add(ledger, 'V1', 'A', 'T')
    add(ledger, 'V2', 'B', 'U')
    add(ledger, 'V3', 'C', 'V')
    assert count(ledger) == 3


def test_read_rows_short_row_padded(tmp_path: str) -> None:
    ledger = str(tmp_path / 'l.tsv')
    from addsong.ledger import read_rows
    with open(ledger, 'w') as fh:
        fh.write('V1\tA\n')
    rows = list(read_rows(ledger))
    assert rows == [('V1', 'A', '', '')]


def test_has_finds_last_row(tmp_path: str) -> None:
    ledger = str(tmp_path / 'l.tsv')
    from addsong.ledger import add, has
    add(ledger, 'V1', 'A', 'T')
    add(ledger, 'V2', 'B', 'U')
    assert has(ledger, 'V2') is True


def test_has_does_not_match_partial(tmp_path: str) -> None:
    ledger = str(tmp_path / 'l.tsv')
    from addsong.ledger import add, has
    add(ledger, 'VID000', 'A', 'T')
    assert has(ledger, 'VID') is False


def test_count_empty_file_is_zero(tmp_path: str) -> None:
    ledger = str(tmp_path / 'l.tsv')
    from addsong.ledger import count
    open(ledger, 'w').close()
    assert count(ledger) == 0


def test_count_blank_lines_not_counted(tmp_path: str) -> None:
    ledger = str(tmp_path / 'l.tsv')
    from addsong.ledger import count
    with open(ledger, 'w') as fh:
        fh.write('\n\n\n')
    assert count(ledger) == 0


def test_add_then_read_rows_preserves_order(tmp_path: str) -> None:
    ledger = str(tmp_path / 'l.tsv')
    from addsong.ledger import add, read_rows
    add(ledger, 'V1', 'A', 'T1')
    add(ledger, 'V2', 'B', 'T2')
    rows = list(read_rows(ledger))
    assert rows[0][0] == 'V1'
    assert rows[1][0] == 'V2'


def test_has_with_special_chars_in_id(tmp_path: str) -> None:
    ledger = str(tmp_path / 'l.tsv')
    from addsong.ledger import add, has
    add(ledger, 'A_B-C', 'Artist', 'Title')
    assert has(ledger, 'A_B-C') is True
