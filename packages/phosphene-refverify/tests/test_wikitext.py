"""Pure tests: wikitext field extraction for editorial gate intake."""

from __future__ import annotations

from phosphene.refverify.domain.wikitext import (
    extract_article_field,
    has_article_template,
)

ARTICLE = """{{Article
|Title=Test Article
|Lead=Some lead text.
|Bibliography=Feinman, Gary M., and David M. Carballo. (2018) [https://example.org/1 Collaborative Strategies]. ''Economic Anthropology'' 5(1): 7-19.
Powers, Simon T. (2020) [https://doi.org/10.3389/fpos.2020.568704 The Evolution of Social Complexity]. ''Frontiers in Political Science''.
|Sources=ARCHIVE-123
|Status=Reviewed
}}"""


def test_extracts_single_line_field() -> None:
    assert extract_article_field(ARTICLE, "Title") == "Test Article"


def test_extracts_multiline_bibliography() -> None:
    bib = extract_article_field(ARTICLE, "Bibliography")
    lines = bib.splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("Feinman")
    assert lines[1].startswith("Powers")


def test_stops_at_next_field() -> None:
    bib = extract_article_field(ARTICLE, "Bibliography")
    assert "ARCHIVE-123" not in bib
    assert "Reviewed" not in bib


def test_missing_field_is_empty() -> None:
    assert extract_article_field(ARTICLE, "Nonexistent") == ""


def test_empty_field_is_empty() -> None:
    page = "{{Article\n|Title=X\n|Bibliography=\n|Sources=Y\n}}"
    assert extract_article_field(page, "Bibliography") == ""


def test_inline_value_after_equals() -> None:
    page = "{{Article\n|Bibliography=One ref here.\n|Sources=S\n}}"
    assert extract_article_field(page, "Bibliography") == "One ref here."


def test_has_article_template() -> None:
    assert has_article_template(ARTICLE)
    assert not has_article_template("Just prose.")
    assert not has_article_template("{{Draft\n|Title=X\n}}")
