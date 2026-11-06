"""Pure unit tests for domain-agnostic utils (phosphene.utils).

Tests text, HTML, and wikitext utilities in total isolation at T0.
No database, no network, no external services.

OKR: @okr_publish_pipeline
"""

from __future__ import annotations

import pytest

from phosphene.utils.html import (
    MetaTag,
    extract_jsonld,
    extract_meta_tags,
    render_meta_tags,
)
from phosphene.utils.text import (
    extract_url_slug,
    extract_url_title,
    humanize_slug,
    join_delimited,
    parse_command_line,
    slugify,
)
from phosphene.utils.wikitext import render_wikitext_template


class TestSlugify:
    """Tests for slugify text utility."""

    def test_standard_ascii(self) -> None:
        assert slugify("Why Care Work Matters") == "why-care-work-matters"

    def test_unicode_accents_normalized(self) -> None:
        assert slugify("Dégrowth in Agrarian Systéms") == "degrowth-in-agrarian-systems"

    def test_punctuation_and_em_dashes(self) -> None:
        assert (
            slugify("Land Reform — A New Paradigm! (Vol. 2)") == "land-reform-a-new-paradigm-vol-2"
        )

    def test_collapses_consecutive_hyphens(self) -> None:
        assert slugify("Foo  --  Bar...Baz") == "foo-bar-baz"

    def test_strips_leading_trailing_hyphens(self) -> None:
        assert slugify("---Leading and Trailing---") == "leading-and-trailing"

    def test_empty_string_returns_empty(self) -> None:
        assert slugify("") == ""
        assert slugify("   ") == ""

    def test_max_length_truncation(self) -> None:
        assert (
            slugify("A Very Long Article Headline That Needs Truncating", max_length=11)
            == "a-very-long"
        )


class TestJoinDelimited:
    """Tests for join_delimited utility."""

    def test_standard_comma_join(self) -> None:
        assert join_delimited(["Economics", "Agriculture"]) == "Economics, Agriculture"

    def test_null_omission_filters_empty_items(self) -> None:
        assert join_delimited(["Economics", "", "  ", "Degrowth", "   "]) == "Economics, Degrowth"

    def test_empty_collection(self) -> None:
        assert join_delimited([]) == ""
        assert join_delimited(["", "  "]) == ""

    def test_custom_delimiter(self) -> None:
        assert join_delimited(["Author 1", "Author 2"], delimiter="\n") == "Author 1\nAuthor 2"


class TestCommandLineParser:
    """Tests for parse_command_line utility."""

    def test_simple_url(self) -> None:
        url, flags = parse_command_line("/syndicate https://observatory.wiki/Article_Title")
        assert url == "https://observatory.wiki/Article_Title"
        assert flags == {}

    def test_url_with_flags(self) -> None:
        text = "/syndicate --outlets=wordpress,pardot --dry-run https://observatory.wiki/Article"
        url, flags = parse_command_line(text)
        assert url == "https://observatory.wiki/Article"
        assert flags == {"outlets": "wordpress,pardot", "dry-run": "true"}

    def test_no_url(self) -> None:
        url, flags = parse_command_line("/syndicate --force")
        assert url == ""
        assert flags == {"force": "true"}


class TestExtractUrlSlug:
    """Tests for extract_url_slug utility."""

    def test_path_slug_extracted(self) -> None:
        assert (
            extract_url_slug("https://observatory.wiki/Cave_Art_in_France") == "Cave_Art_in_France"
        )

    def test_query_and_hash_stripped(self) -> None:
        assert extract_url_slug("https://observatory.wiki/Article?version=2#section") == "Article"

    def test_no_path_returns_url(self) -> None:
        assert extract_url_slug("https://observatory.wiki") == "https://observatory.wiki"


class TestHtmlMetaTags:
    """Tests for MetaTag POPO and rendering."""

    def test_valid_meta_tag(self) -> None:
        tag = MetaTag(name="citation_title", content="Study of Systems")
        assert tag.name == "citation_title"
        assert tag.content == "Study of Systems"

    def test_empty_name_rejected(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            MetaTag(name="", content="Value")

    def test_render_meta_tags_escapes_attributes(self) -> None:
        tags = [
            MetaTag(name="citation_title", content='Study & "Research"'),
            MetaTag(name="citation_author", content="O'Connor <Scholar>"),
        ]
        rendered = render_meta_tags(tags)
        assert (
            '<meta name="citation_title" content="Study &amp; &quot;Research&quot;" />' in rendered
        )
        assert (
            '<meta name="citation_author" content="O&#x27;Connor &lt;Scholar&gt;" />' in rendered
        )

    def test_extract_meta_tags(self) -> None:
        html_doc = """
        <html>
        <head>
            <meta name="citation_title" content="Test Title" />
            <meta name="citation_author" content="Dr. Smith" />
            <meta name="other_meta" content="Ignore" />
        </head>
        </html>
        """
        all_tags = extract_meta_tags(html_doc)
        assert all_tags["citation_title"] == "Test Title"
        assert all_tags["other_meta"] == "Ignore"

        citation_only = extract_meta_tags(html_doc, prefix="citation_")
        assert "citation_title" in citation_only
        assert "other_meta" not in citation_only


class TestJsonLdExtractor:
    """Tests for extract_jsonld utility."""

    def test_valid_jsonld(self) -> None:
        html = '<script type="application/ld+json">{"@context": "https://schema.org", "@type": "Preprint"}</script>'
        data = extract_jsonld(html)
        assert data["@type"] == "Preprint"

    def test_malformed_json_returns_empty_dict(self) -> None:
        html = '<script type="application/ld+json">{"unclosed: json</script>'
        assert extract_jsonld(html) == {}

    def test_missing_jsonld_returns_empty_dict(self) -> None:
        assert extract_jsonld("<html><body>No LD</body></html>") == {}


class TestWikitextTemplateRenderer:
    """Tests for render_wikitext_template."""

    def test_render_template_without_body(self) -> None:
        output = render_wikitext_template("Preprint", {"Version": "1", "Status": "Active"})
        assert output == "{{Preprint|Version=1|Status=Active}}"

    def test_render_template_with_body(self) -> None:
        output = render_wikitext_template(
            "Article",
            {"Headline": "Test", "Author": "Writer"},
            body="Article narrative text.",
        )
        assert output == "{{Article|Headline=Test|Author=Writer}}\n\nArticle narrative text."


class TestHumanizeSlug:
    """Tests for humanize_slug utility."""

    def test_underscores_and_hyphens(self) -> None:
        assert humanize_slug("Cave_Art_in_France") == "Cave Art in France"
        assert humanize_slug("climate-crisis-2026") == "climate crisis 2026"

    def test_empty_string(self) -> None:
        assert humanize_slug("") == ""


class TestExtractUrlTitle:
    """Tests for extract_url_title utility."""

    def test_extract_and_humanize(self) -> None:
        assert (
            extract_url_title("https://observatory.wiki/Cave_Art_in_France")
            == "Cave Art in France"
        )
        assert (
            extract_url_title("https://observatory.wiki/climate-crisis-2026?v=1#sec")
            == "climate crisis 2026"
        )

    def test_no_path_returns_raw_url(self) -> None:
        assert extract_url_title("https://observatory.wiki") == "https://observatory.wiki"
