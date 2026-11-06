"""Tests for MetadataExtractor — HTML metadata parsing for WordPress pages."""

from __future__ import annotations

import pytest

from phosphene.imi_wordpress.testing.metadata_extractor import MetadataExtractor, PageMetadata

# ---------------------------------------------------------------------------
# Inline HTML fixtures
# ---------------------------------------------------------------------------

MINIMAL_HTML = """\
<!DOCTYPE html>
<html>
<head>
<meta name="citation_title" content="Tool Use in Hominins">
<meta name="citation_author" content="Barsky, Deborah">
<meta property="og:title" content="Tool Use in Hominins">
<meta property="og:type" content="article">
<meta name="DC.title" content="Tool Use in Hominins">
<meta name="DC.creator" content="Barsky, Deborah">
<link rel="canonical" href="https://example.com/article/1">
<script type="application/ld+json">
{"@type": "ScholarlyArticle", "name": "Tool Use in Hominins"}
</script>
</head>
<body><p>Hello</p></body>
</html>
"""

YOAST_HTML = """\
<!DOCTYPE html>
<html>
<head>
<script type="application/ld+json" class="yoast-schema-graph">
{"@context": "https://schema.org", "@type": "WebPage"}
</script>
</head>
<body></body>
</html>
"""

MULTI_CITATION_HTML = """\
<html><head>
<meta name="citation_title" content="Article Title">
<meta name="citation_author" content="Author A">
<meta name="citation_doi" content="10.1234/test">
<meta name="citation_journal_title" content="Test Journal">
<meta name="citation_date" content="2026-07-15">
</head><body></body></html>
"""

MULTI_JSONLD_HTML = """\
<html><head>
<script type="application/ld+json">
{"@type": "Article", "name": "First"}
</script>
<script type="application/ld+json">
{"@type": "Organization", "name": "IMI"}
</script>
</head><body></body></html>
"""

MALFORMED_JSONLD_HTML = """\
<html><head>
<script type="application/ld+json">
{"@type": "Article", "name": "Valid"}
</script>
<script type="application/ld+json">
{this is not valid json at all}
</script>
<script type="application/ld+json">
{"@type": "BreadcrumbList", "name": "Also valid"}
</script>
</head><body></body></html>
"""

CANONICAL_REVERSED_HTML = """\
<html><head>
<link href="https://example.com/reversed" rel="canonical">
</head><body></body></html>
"""

EMPTY_HTML = ""

NO_YOAST_HTML = """\
<html><head>
<meta name="citation_title" content="No Yoast">
</head><body></body></html>
"""


# ---------------------------------------------------------------------------
# Citation extraction
# ---------------------------------------------------------------------------


class TestCitationExtraction:
    """Tests for Highwire Press citation meta tag extraction."""

    def test_basic_citation_tags(self) -> None:
        meta = MetadataExtractor.from_html(MINIMAL_HTML)
        assert meta.citation["citation_title"] == "Tool Use in Hominins"
        assert meta.citation["citation_author"] == "Barsky, Deborah"

    def test_multiple_citation_tags(self) -> None:
        meta = MetadataExtractor.from_html(MULTI_CITATION_HTML)
        assert len(meta.citation) == 5
        assert meta.citation["citation_doi"] == "10.1234/test"
        assert meta.citation["citation_journal_title"] == "Test Journal"
        assert meta.citation["citation_date"] == "2026-07-15"

    def test_no_citation_tags(self) -> None:
        html = "<html><head></head><body></body></html>"
        meta = MetadataExtractor.from_html(html)
        assert meta.citation == {}


# ---------------------------------------------------------------------------
# Open Graph extraction
# ---------------------------------------------------------------------------


class TestOpenGraphExtraction:
    """Tests for Open Graph og:* meta tag extraction."""

    def test_og_tags(self) -> None:
        meta = MetadataExtractor.from_html(MINIMAL_HTML)
        assert meta.open_graph["og:title"] == "Tool Use in Hominins"
        assert meta.open_graph["og:type"] == "article"

    def test_no_og_tags(self) -> None:
        html = "<html><head></head><body></body></html>"
        meta = MetadataExtractor.from_html(html)
        assert meta.open_graph == {}


# ---------------------------------------------------------------------------
# Dublin Core extraction
# ---------------------------------------------------------------------------


class TestDublinCoreExtraction:
    """Tests for Dublin Core DC.* meta tag extraction."""

    def test_dc_tags(self) -> None:
        meta = MetadataExtractor.from_html(MINIMAL_HTML)
        assert meta.dublin_core["DC.title"] == "Tool Use in Hominins"
        assert meta.dublin_core["DC.creator"] == "Barsky, Deborah"

    def test_no_dc_tags(self) -> None:
        html = "<html><head></head><body></body></html>"
        meta = MetadataExtractor.from_html(html)
        assert meta.dublin_core == {}


# ---------------------------------------------------------------------------
# JSON-LD parsing
# ---------------------------------------------------------------------------


class TestJsonLdParsing:
    """Tests for JSON-LD script block parsing."""

    def test_single_jsonld(self) -> None:
        meta = MetadataExtractor.from_html(MINIMAL_HTML)
        assert len(meta.jsonld) == 1
        assert meta.jsonld[0]["@type"] == "ScholarlyArticle"

    def test_multiple_jsonld_blocks(self) -> None:
        meta = MetadataExtractor.from_html(MULTI_JSONLD_HTML)
        assert len(meta.jsonld) == 2
        types = {block["@type"] for block in meta.jsonld}
        assert types == {"Article", "Organization"}

    def test_malformed_jsonld_skipped(self) -> None:
        meta = MetadataExtractor.from_html(MALFORMED_JSONLD_HTML)
        assert len(meta.jsonld) == 2
        types = {block["@type"] for block in meta.jsonld}
        assert "Article" in types
        assert "BreadcrumbList" in types

    def test_no_jsonld(self) -> None:
        html = "<html><head></head><body></body></html>"
        meta = MetadataExtractor.from_html(html)
        assert meta.jsonld == []


# ---------------------------------------------------------------------------
# Yoast detection
# ---------------------------------------------------------------------------


class TestYoastDetection:
    """Tests for Yoast SEO schema graph detection."""

    def test_yoast_present(self) -> None:
        meta = MetadataExtractor.from_html(YOAST_HTML)
        assert meta.yoast_present is True

    def test_yoast_absent(self) -> None:
        meta = MetadataExtractor.from_html(NO_YOAST_HTML)
        assert meta.yoast_present is False


# ---------------------------------------------------------------------------
# Canonical URL
# ---------------------------------------------------------------------------


class TestCanonicalUrl:
    """Tests for canonical URL extraction."""

    def test_canonical_standard_order(self) -> None:
        meta = MetadataExtractor.from_html(MINIMAL_HTML)
        assert meta.canonical_url == "https://example.com/article/1"

    def test_canonical_reversed_attr_order(self) -> None:
        meta = MetadataExtractor.from_html(CANONICAL_REVERSED_HTML)
        assert meta.canonical_url == "https://example.com/reversed"

    def test_no_canonical(self) -> None:
        html = "<html><head></head><body></body></html>"
        meta = MetadataExtractor.from_html(html)
        assert meta.canonical_url is None


# ---------------------------------------------------------------------------
# Empty / edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge-case tests for MetadataExtractor."""

    def test_empty_html_returns_empty_metadata(self) -> None:
        meta = MetadataExtractor.from_html(EMPTY_HTML)
        assert meta.citation == {}
        assert meta.open_graph == {}
        assert meta.dublin_core == {}
        assert meta.jsonld == []
        assert meta.yoast_present is False
        assert meta.canonical_url is None

    def test_page_metadata_is_frozen(self) -> None:
        meta = MetadataExtractor.from_html(MINIMAL_HTML)
        with pytest.raises(AttributeError):
            meta.yoast_present = True  # type: ignore[misc]

    def test_from_html_returns_page_metadata_type(self) -> None:
        meta = MetadataExtractor.from_html(MINIMAL_HTML)
        assert isinstance(meta, PageMetadata)
