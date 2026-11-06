"""Tests for CitationMetaGenerator — Google Scholar citation meta tags.

TDD: these tests are written BEFORE the implementation exists.
All 8 must fail (ImportError) on first run, then pass after implementation.
"""

from __future__ import annotations

from phosphene.imi_wordpress.citation import CitationMetaGenerator, generate_citation_meta


class TestCitationMetaGenerator:
    """Unit tests for CitationMetaGenerator frozen dataclass."""

    def test_citation_title(self) -> None:
        """Rendered output contains citation_title meta tag."""
        gen = CitationMetaGenerator(
            title="The Evolution of Cooperation",
            author="Robert Axelrod",
        )
        html = gen.render()
        assert '<meta name="citation_title" content="The Evolution of Cooperation"' in html

    def test_citation_author(self) -> None:
        """Rendered output contains citation_author meta tag."""
        gen = CitationMetaGenerator(
            title="Selfish Gene",
            author="Richard Dawkins",
        )
        html = gen.render()
        assert '<meta name="citation_author" content="Richard Dawkins"' in html

    def test_citation_publisher(self) -> None:
        """Publisher defaults to Independent Media Institute."""
        gen = CitationMetaGenerator(
            title="Test Article",
            author="Test Author",
        )
        html = gen.render()
        assert '<meta name="citation_publisher" content="Independent Media Institute"' in html

    def test_citation_publication_date(self) -> None:
        """When published_date is set, citation_publication_date appears."""
        gen = CitationMetaGenerator(
            title="Test Article",
            author="Test Author",
            published_date="2026/06/21",
        )
        html = gen.render()
        assert '<meta name="citation_publication_date" content="2026/06/21"' in html

    def test_citation_journal_title_when_provided(self) -> None:
        """When journal is set, citation_journal_title appears."""
        gen = CitationMetaGenerator(
            title="Test Article",
            author="Test Author",
            journal="Observatory Magazine",
        )
        html = gen.render()
        assert '<meta name="citation_journal_title" content="Observatory Magazine"' in html

    def test_missing_optional_fields_not_rendered(self) -> None:
        """Optional fields (published_date, journal, doi) omitted when None."""
        gen = CitationMetaGenerator(
            title="Test Article",
            author="Test Author",
        )
        html = gen.render()
        assert "citation_publication_date" not in html
        assert "citation_journal_title" not in html
        assert "citation_doi" not in html

    def test_html_escaping(self) -> None:
        """Special characters in content are HTML-escaped."""
        gen = CitationMetaGenerator(
            title='Art & Science: A "Bold" <Approach>',
            author="O'Brien & Partners",
        )
        html = gen.render()
        assert "&amp;" in html
        assert "&quot;" in html or "&#x27;" in html or "&#39;" in html
        assert "&lt;" in html
        assert "&gt;" in html

    def test_generate_citation_meta_convenience(self) -> None:
        """generate_citation_meta() returns same output as .render()."""
        html = generate_citation_meta(
            title="Convenience Test",
            author="Convenience Author",
            published_date="2026/01/01",
        )
        assert '<meta name="citation_title" content="Convenience Test"' in html
        assert '<meta name="citation_author" content="Convenience Author"' in html
        assert '<meta name="citation_publication_date" content="2026/01/01"' in html
