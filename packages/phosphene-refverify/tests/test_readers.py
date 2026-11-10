from __future__ import annotations

"""Tests for document readers."""

from pathlib import Path
from phosphene.refverify.domain.readers import (
    extract_from_markdown,
    extract_bibliography,
)


def test_extract_from_markdown_explicit_header():
    md = """# My Manuscript

Some text introducing concepts.

## References

* Doe, J. (2020). The First Study. Journal of Examples, 1(1), 1-10.
* Smith, A. (2021). Another Study. Science, 2(2), 20-30.

## Appendix
Extra details.
"""
    bib = extract_from_markdown(md)
    assert "Doe, J. (2020)" in bib
    assert "Smith, A. (2021)" in bib
    assert "Extra details" not in bib


def test_extract_from_markdown_fallback_bullets():
    md = """# Notes

* Doe, J. (2020). The First Study.
* Smith, A. (2021). Another Study.
"""
    bib = extract_from_markdown(md)
    assert "Doe, J. (2020)" in bib
    assert "Smith, A. (2021)" in bib


def test_extract_bibliography_dispatch_text(tmp_path: Path):
    p = tmp_path / "refs.txt"
    p.write_text("Doe, J. (2020). A test.")
    bib = extract_bibliography(p)
    assert bib.strip() == "Doe, J. (2020). A test."
