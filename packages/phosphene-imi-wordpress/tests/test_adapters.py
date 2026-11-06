"""Unit tests for PreprintPayloadAdapter and wire schema contracts.

These tests run in pure Python with zero I/O, zero network, and zero mocks.
"""

from __future__ import annotations

from phosphene.imi_wordpress.adapters import (
    PreprintPayloadAdapter,
    SchemaJsonLd,
    WordPressPayload,
)
from phosphene.imi_wordpress.domain import (
    DOI,
    Author,
    DOIRecord,
    DOIStatus,
    EditorialState,
    License,
    PreprintEntry,
    VersionInfo,
)


def _make_sample_entry(
    *,
    state: EditorialState = EditorialState.DRAFT,
    doi_status: DOIStatus = DOIStatus.UNASSIGNED,
    with_doi: bool = False,
    slug: str = "",
    withdrawal_notice: str = "",
) -> PreprintEntry:
    doi = DOI(suffix="imi.2026.042") if with_doi else None
    doi_record = DOIRecord(
        doi=doi,
        status=doi_status,
        minted_date="2026-11-01" if with_doi else "",
        deposit_id="cr-dep-9912" if with_doi else "",
    )
    return PreprintEntry(
        title="Decarbonizing Heavy Industry",
        primary_author=Author(
            name="Alice Smith",
            orcid="0000-0001-2345-6789",
            affiliation="Energy Institute",
            country="United States",
        ),
        slug=slug,
        editorial_state=state,
        abstract="Comprehensive analysis of hydrogen substitution in steel manufacturing.",
        methodology="simulation",
        license=License.CC_BY_4_0,
        declaration=True,
        keywords=("energy", "hydrogen", "steel"),
        coauthors=(
            Author(name="Bob Jones"),
            Author(name="Carol White"),
        ),
        destination_url="https://observatory.wiki/Heavy_Industry",
        published_destination="Observatory",
        pdf_url="https://ind.media/pdf/industry-v1.pdf",
        schema_type="ScholarlyArticle",
        registry_id="IMI-2026-042",
        doi_record=doi_record,
        version=VersionInfo(
            number=1,
            version_type="major",
            history="Initial preprint",
            prior_versions=(),
        ),
        withdrawal_notice=withdrawal_notice,
    )


class TestPreprintPayloadAdapterWordPress:
    """Tests for PreprintPayloadAdapter.to_wordpress()."""

    def test_draft_payload_mapping(self) -> None:
        entry = _make_sample_entry(state=EditorialState.DRAFT)
        payload: WordPressPayload = PreprintPayloadAdapter.to_wordpress(entry)

        assert payload["title"] == "Decarbonizing Heavy Industry"
        assert payload["status"] == "draft"
        assert "slug" not in payload

        meta = payload["meta"]
        assert meta["reg_author_name"] == "Alice Smith"
        assert meta["reg_orcid"] == "0000-0001-2345-6789"
        assert meta["reg_affiliation"] == "Energy Institute"
        assert meta["reg_country"] == "United States"
        assert (
            meta["reg_abstract"]
            == "Comprehensive analysis of hydrogen substitution in steel manufacturing."
        )
        assert meta["reg_methodology"] == "simulation"
        assert meta["reg_license"] == "CC BY 4.0"
        assert meta["reg_declaration"] is True
        assert meta["reg_keywords"] == "energy, hydrogen, steel"
        assert meta["reg_coauthors"] == "Bob Jones\nCarol White"
        assert meta["reg_destination_url"] == "https://observatory.wiki/Heavy_Industry"
        assert meta["reg_published_destination"] == "Observatory"
        assert meta["reg_pdf_url"] == "https://ind.media/pdf/industry-v1.pdf"
        assert meta["reg_schema_type"] == "ScholarlyArticle"
        assert meta["reg_registry_id"] == "IMI-2026-042"
        assert meta["reg_pipeline_status"] == "draft"
        assert meta["reg_version"] == 1
        assert meta["reg_version_type"] == "major"
        assert meta["reg_version_history"] == "Initial preprint"
        assert meta["reg_prior_versions"] == ""
        assert meta["reg_doi"] == ""
        assert meta["reg_doi_url"] == ""
        assert meta["reg_doi_status"] == "unassigned"
        assert "reg_withdrawal_notice" not in meta

    def test_live_preprint_status_mapping(self) -> None:
        entry = _make_sample_entry(
            state=EditorialState.LIVE_PREPRINT,
            with_doi=True,
            doi_status=DOIStatus.ACTIVE,
            slug="decarbonizing-heavy-industry",
        )
        payload = PreprintPayloadAdapter.to_wordpress(entry)

        assert payload["status"] == "publish"
        assert payload.get("slug") == "decarbonizing-heavy-industry"

        meta = payload["meta"]
        assert meta["reg_pipeline_status"] == "preprint"
        assert meta["reg_doi"] == "10.67767/imi.2026.042"
        assert meta["reg_doi_url"] == "https://doi.org/10.67767/imi.2026.042"
        assert meta["reg_doi_status"] == "active"
        assert meta["reg_doi_minted_date"] == "2026-11-01"
        assert meta["reg_crossref_deposit_id"] == "cr-dep-9912"

    def test_published_status_mapping(self) -> None:
        entry = _make_sample_entry(state=EditorialState.PUBLISHED)
        payload = PreprintPayloadAdapter.to_wordpress(entry)

        assert payload["status"] == "publish"
        assert payload["meta"]["reg_pipeline_status"] == "published"

    def test_withdrawn_status_mapping(self) -> None:
        entry = _make_sample_entry(
            state=EditorialState.WITHDRAWN,
            with_doi=True,
            doi_status=DOIStatus.WITHDRAWN,
            withdrawal_notice="Withdrawn due to experimental error.",
        )
        payload = PreprintPayloadAdapter.to_wordpress(entry)

        assert payload["status"] == "publish"
        assert payload["meta"]["reg_pipeline_status"] == "withdrawn"
        assert payload["meta"]["reg_doi_status"] == "withdrawn"
        assert payload["meta"]["reg_doi"] == "10.67767/imi.2026.042"
        assert payload["meta"]["reg_withdrawal_notice"] == "Withdrawn due to experimental error."


class TestPreprintPayloadAdapterJsonLd:
    """Tests for PreprintPayloadAdapter.to_jsonld()."""

    def test_creative_work_status_for_live_preprint(self) -> None:
        entry = _make_sample_entry(
            state=EditorialState.LIVE_PREPRINT,
            with_doi=True,
            doi_status=DOIStatus.ACTIVE,
        )
        jsonld: SchemaJsonLd = PreprintPayloadAdapter.to_jsonld(entry)

        assert jsonld["@context"] == "https://schema.org"
        assert jsonld["@type"] == "ScholarlyArticle"
        assert jsonld["headline"] == "Decarbonizing Heavy Industry"
        assert jsonld["creativeWorkStatus"] == "Preprint"
        assert jsonld["identifier"] == "https://doi.org/10.67767/imi.2026.042"
        assert jsonld["sameAs"] == "https://doi.org/10.67767/imi.2026.042"

        # Check all authors represented
        authors = jsonld["author"]
        assert len(authors) == 3
        assert authors[0] == {"@type": "Person", "name": "Alice Smith"}
        assert authors[1] == {"@type": "Person", "name": "Bob Jones"}
        assert authors[2] == {"@type": "Person", "name": "Carol White"}

    def test_creative_work_status_for_draft_omitted(self) -> None:
        entry = _make_sample_entry(state=EditorialState.DRAFT)
        jsonld = PreprintPayloadAdapter.to_jsonld(entry)
        assert "creativeWorkStatus" not in jsonld

    def test_creative_work_status_for_withdrawn(self) -> None:
        entry = _make_sample_entry(state=EditorialState.WITHDRAWN)
        jsonld = PreprintPayloadAdapter.to_jsonld(entry)
        assert jsonld["creativeWorkStatus"] == "Retracted"


class TestPreprintPayloadAdapterCitationMeta:
    """Tests for PreprintPayloadAdapter.to_citation_meta()."""

    def test_citation_meta_active_doi(self) -> None:
        entry = _make_sample_entry(
            state=EditorialState.LIVE_PREPRINT,
            with_doi=True,
            doi_status=DOIStatus.ACTIVE,
        )
        html = PreprintPayloadAdapter.to_citation_meta(entry)

        assert '<meta name="citation_title" content="Decarbonizing Heavy Industry" />' in html
        assert '<meta name="citation_author" content="Alice Smith" />' in html
        assert '<meta name="citation_author" content="Bob Jones" />' in html
        assert '<meta name="citation_author" content="Carol White" />' in html
        assert '<meta name="citation_publisher" content="Independent Media Institute" />' in html
        assert (
            '<meta name="citation_abstract" content="Comprehensive analysis of hydrogen substitution in steel manufacturing." />'
            in html
        )
        assert '<meta name="citation_keywords" content="energy, hydrogen, steel" />' in html
        assert (
            '<meta name="citation_fulltext_html_url" content="https://observatory.wiki/Heavy_Industry" />'
            in html
        )
        assert (
            '<meta name="citation_pdf_url" content="https://ind.media/pdf/industry-v1.pdf" />'
            in html
        )
        assert '<meta name="citation_doi" content="10.67767/imi.2026.042" />' in html

    def test_citation_doi_omitted_when_not_active(self) -> None:
        entry = _make_sample_entry(
            state=EditorialState.DRAFT,
            with_doi=True,
            doi_status=DOIStatus.PENDING,
        )
        html = PreprintPayloadAdapter.to_citation_meta(entry)
        assert "citation_doi" not in html

    def test_to_citation_tags_returns_typed_meta_tags(self) -> None:
        """Verify pure data projection yields typed MetaTag list."""
        from phosphene.utils.html import MetaTag

        entry = _make_sample_entry(
            state=EditorialState.LIVE_PREPRINT,
            with_doi=True,
            doi_status=DOIStatus.ACTIVE,
        )
        tags = PreprintPayloadAdapter.to_citation_tags(entry)
        assert all(isinstance(t, MetaTag) for t in tags)
        tag_dict = {t.name: t.content for t in tags}
        assert tag_dict["citation_title"] == "Decarbonizing Heavy Industry"
        assert tag_dict["citation_doi"] == "10.67767/imi.2026.042"
        assert tag_dict["citation_publisher"] == "Independent Media Institute"
