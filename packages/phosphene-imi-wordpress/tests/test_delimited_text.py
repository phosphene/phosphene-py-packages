"""Unit tests for dedicated newline and comma delimited list parser."""

from __future__ import annotations

from phosphene.imi_wordpress.delimited_text import (
    join_commas,
    join_lines,
    split_commas,
    split_lines,
)


def test_split_lines() -> None:
    raw = "  Author One  \r\n\r\n  Author Two \nAuthor Three\n  "
    assert split_lines(raw) == ("Author One", "Author Two", "Author Three")
    assert split_lines("") == ()
    assert split_lines("   \n \r\n ") == ()


def test_join_lines() -> None:
    items = ["Line 1", "  Line 2  ", "", "Line 3"]
    assert join_lines(items) == "Line 1\nLine 2\nLine 3"


def test_split_commas() -> None:
    raw = "  geology,  climate change , , paleontology "
    assert split_commas(raw) == ("geology", "climate change", "paleontology")
    assert split_commas("") == ()


def test_join_commas() -> None:
    items = ["term 1", "  term 2 ", "", "term 3"]
    assert join_commas(items) == "term 1, term 2, term 3"
