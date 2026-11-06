"""Unit tests for pure preprint domain models (Author, DOI, PreprintEntry).

These tests run in pure Python with zero I/O, zero network, and zero mocks.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from phosphene.imi_wordpress.domain import (
    DOI,
    IMI_DOI_PREFIX,
    Author,
    ContributorSequence,
    DOIRecord,
    DOIStatus,
    EditorialState,
    License,
    PreprintEntry,
    VersionInfo,
)


class TestAuthor:
    """Unit tests for the Author value object."""

    def test_instantiation_and_attributes(self) -> None:
        author = Author(
            name="Deborah Barsky",
            orcid="https://orcid.org/0000-0002-1234-5678",
            affiliation="Institut Catala de Paleoecologia Humana",
            country="Spain",
            sequence=ContributorSequence.FIRST,
        )
        assert author.name == "Deborah Barsky"
        assert author.orcid == "0000-0002-1234-5678"
        assert author.orcid_url == "https://orcid.org/0000-0002-1234-5678"
        assert author.affiliation == "Institut Catala de Paleoecologia Humana"
        assert author.country == "Spain"
        assert author.is_primary is True

    def test_default_optional_attributes(self) -> None:
        author = Author(name="Jane Doe")
        assert author.orcid == ""
        assert author.orcid_url == ""
        assert author.affiliation == ""
        assert author.country == ""
        assert author.sequence == ContributorSequence.FIRST
        assert author.is_primary is True

    def test_coauthor_sequence(self) -> None:
        coauthor = Author(name="Co Author", sequence=ContributorSequence.ADDITIONAL)
        assert coauthor.is_primary is False

    def test_malformed_orcid_rejected(self) -> None:
        with pytest.raises(ValueError, match="Malformed ORCID"):
            Author(name="Bad", orcid="not-an-orcid")

    def test_immutability(self) -> None:
        author = Author(name="Jane Doe")
        with pytest.raises(FrozenInstanceError):
            author.name = "Mutated"  # type: ignore[misc]

    def test_slots_present_and_no_dict(self) -> None:
        author = Author(name="Jane Doe")
        assert hasattr(author, "__slots__")
        assert not hasattr(author, "__dict__")

    def test_value_equality(self) -> None:
        a1 = Author(name="Jane Doe", orcid="0000-0001-2345-6789")
        a2 = Author(name="Jane Doe", orcid="0000-0001-2345-6789")
        assert a1 == a2
        assert hash(a1) == hash(a2)


class TestDOI:
    """Unit tests for the DOI value object."""

    def test_default_prefix_is_imi(self) -> None:
        doi = DOI(suffix="imi.2026.001")
        assert doi.prefix == IMI_DOI_PREFIX
        assert doi.prefix == "10.67767"
        assert doi.suffix == "imi.2026.001"
        assert doi.value == "10.67767/imi.2026.001"
        assert doi.url == "https://doi.org/10.67767/imi.2026.001"
        assert str(doi) == "10.67767/imi.2026.001"

    def test_custom_prefix(self) -> None:
        doi = DOI(prefix="10.1234", suffix="custom.001")
        assert doi.value == "10.1234/custom.001"
        assert doi.url == "https://doi.org/10.1234/custom.001"

    def test_from_string_with_protocol_stripping(self) -> None:
        doi = DOI.from_string("https://doi.org/10.67767/imi.2026.042")
        assert doi.prefix == "10.67767"
        assert doi.suffix == "imi.2026.042"

        doi_suffix_only = DOI.from_string("  imi.2026.099  ")
        assert doi_suffix_only.prefix == "10.67767"
        assert doi_suffix_only.suffix == "imi.2026.099"

    def test_malformed_doi_rejected(self) -> None:
        with pytest.raises(ValueError, match="Malformed DOI"):
            DOI(suffix="has spaces and ? bad chars")


class TestDOIRecord:
    """Unit tests for the DOIRecord lifecycle value object."""

    def test_defaults(self) -> None:
        record = DOIRecord()
        assert record.doi is None
        assert record.status == DOIStatus.UNASSIGNED
        assert record.is_minted is False
        assert record.is_resolvable is False

    def test_lifecycle_progression(self) -> None:
        doi = DOI(suffix="imi.2026.001")
        record = DOIRecord(doi=doi)

        pending = record.with_pending("DEP-100")
        assert pending.status == DOIStatus.PENDING
        assert pending.deposit_id == "DEP-100"

        active = pending.with_active("2026-11-05")
        assert active.status == DOIStatus.ACTIVE
        assert active.minted_date == "2026-11-05"
        assert active.is_minted is True
        assert active.is_resolvable is True

        withdrawn = active.with_withdrawn()
        assert withdrawn.status == DOIStatus.WITHDRAWN
        assert withdrawn.is_minted is True
        assert withdrawn.is_resolvable is False

    def test_active_without_doi_rejected(self) -> None:
        with pytest.raises(ValueError, match="ACTIVE DOIRecord must have a non-null DOI"):
            DOIRecord(doi=None, status=DOIStatus.ACTIVE)


class TestLicense:
    """Unit tests for the License enum."""

    def test_url_and_spdx(self) -> None:
        lic = License.CC_BY_4_0
        assert lic.url == "https://creativecommons.org/licenses/by/4.0/"
        assert lic.spdx == "CC-BY-4.0"
        assert License.from_spdx("CC-BY-NC-SA-4.0") == License.CC_BY_NC_SA_4_0


class TestEditorialState:
    """Unit tests for the EditorialState lifecycle enum."""

    def test_predicates(self) -> None:
        draft = EditorialState.DRAFT
        assert draft.is_published is False
        assert draft.is_reviewing is False
        assert draft.can_transition_to(EditorialState.PENDING_REVIEW) is True

        pending = EditorialState.PENDING_REVIEW
        assert pending.is_reviewing is True
        assert pending.badge_mode == "pending"

        under_review = EditorialState.UNDER_REVIEW
        assert under_review.is_reviewing is True
        assert under_review.badge_mode == "under_review"

        live = EditorialState.LIVE_PREPRINT
        assert live.is_published is True
        assert live.badge_mode == "preprint"


class TestVersionInfo:
    """Unit tests for the VersionInfo value object."""

    def test_formatting_and_increment(self) -> None:
        v1 = VersionInfo(number=1)
        assert v1.formatted() == "v1"

        v2 = v1.increment("minor", "bug fixes")
        assert v2.number == 2
        assert v2.formatted() == "v2"
        assert v2.history == "bug fixes"
        assert v2.prior_versions == ("v1",)


class TestPreprintEntry:
    """Unit tests for the PreprintEntry aggregate root."""

    def test_all_authors_and_withers(self) -> None:
        p_author = Author(name="Primary")
        c_author = Author(name="Coauthor", sequence=ContributorSequence.ADDITIONAL)

        entry = PreprintEntry(
            title="A Sample Title",
            primary_author=p_author,
            coauthors=(c_author,),
        )
        assert [a.name for a in entry.all_authors()] == ["Primary", "Coauthor"]

        promoted = entry.with_editorial_state(EditorialState.LIVE_PREPRINT)
        assert promoted.editorial_state == EditorialState.LIVE_PREPRINT
