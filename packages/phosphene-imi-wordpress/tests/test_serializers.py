"""Unit tests for discrete serialization units in phosphene.imi_wordpress.serializers."""

from __future__ import annotations

from phosphene.imi_wordpress.domain import (
    DOI,
    Author,
    ContributorSequence,
    DOIRecord,
    DOIStatus,
    EditorialState,
    License,
    VersionInfo,
)
from phosphene.imi_wordpress.serializers.author_unit import AuthorMetaUnit
from phosphene.imi_wordpress.serializers.doi_unit import DoiMetaUnit
from phosphene.imi_wordpress.serializers.editorial_unit import EditorialStateUnit
from phosphene.imi_wordpress.serializers.keywords_unit import KeywordsUnit
from phosphene.imi_wordpress.serializers.license_unit import LicenseUnit
from phosphene.imi_wordpress.serializers.version_unit import VersionMetaUnit


def test_author_meta_unit() -> None:
    primary = Author(
        name="Dr. Jane Smith",
        orcid="0000-0002-1825-0097",
        affiliation="MIT",
        country="US",
        sequence=ContributorSequence.FIRST,
    )
    coauthors = (
        Author(name="Alice Coauthor", sequence=ContributorSequence.ADDITIONAL),
        Author(name="Bob Coauthor", sequence=ContributorSequence.ADDITIONAL),
    )

    serialized = AuthorMetaUnit.serialize(primary, coauthors)
    assert serialized["reg_author_name"] == "Dr. Jane Smith"
    assert serialized["reg_orcid"] == "0000-0002-1825-0097"
    assert serialized["reg_coauthors"] == "Alice Coauthor\nBob Coauthor"

    hydrated_primary, hydrated_coauthors = AuthorMetaUnit.hydrate(serialized)
    assert hydrated_primary.name == primary.name
    assert hydrated_primary.orcid == primary.orcid
    assert len(hydrated_coauthors) == 2
    assert hydrated_coauthors[0].name == "Alice Coauthor"
    assert hydrated_coauthors[0].sequence == ContributorSequence.ADDITIONAL


def test_doi_meta_unit() -> None:
    doi = DOI(suffix="imi.2026.042")
    record = DOIRecord(
        doi=doi,
        status=DOIStatus.ACTIVE,
        minted_date="2026-11-05",
        deposit_id="DEP-888",
    )

    serialized = DoiMetaUnit.serialize(record)
    assert serialized["reg_doi"] == "10.67767/imi.2026.042"
    assert serialized["reg_doi_url"] == "https://doi.org/10.67767/imi.2026.042"
    assert serialized["reg_doi_status"] == "active"

    hydrated = DoiMetaUnit.hydrate(serialized)
    assert hydrated.doi is not None
    assert hydrated.doi.value == "10.67767/imi.2026.042"
    assert hydrated.status == DOIStatus.ACTIVE
    assert hydrated.minted_date == "2026-11-05"


def test_version_meta_unit() -> None:
    version = VersionInfo(
        number=2,
        version_type="minor",
        history="revised abstract",
        prior_versions=("v1",),
    )

    serialized = VersionMetaUnit.serialize(version)
    assert serialized["reg_version"] == 2
    assert serialized["reg_prior_versions"] == "v1"

    hydrated = VersionMetaUnit.hydrate(serialized)
    assert hydrated.number == 2
    assert hydrated.version_type == "minor"
    assert hydrated.prior_versions == ("v1",)


def test_editorial_state_unit() -> None:
    serialized = EditorialStateUnit.serialize(EditorialState.LIVE_PREPRINT)
    assert serialized["post_status"] == "publish"
    assert serialized["pipeline_status"] == "preprint"

    hydrated = EditorialStateUnit.hydrate({"reg_pipeline_status": "preprint"})
    assert hydrated == EditorialState.LIVE_PREPRINT


def test_license_unit() -> None:
    serialized = LicenseUnit.serialize(License.CC_BY_4_0)
    assert serialized == "CC BY 4.0"

    hydrated = LicenseUnit.hydrate({"reg_license": "CC BY 4.0"})
    assert hydrated == License.CC_BY_4_0


def test_keywords_unit() -> None:
    keywords = ("astronomy", "spectroscopy", "interferometry")
    serialized = KeywordsUnit.serialize(keywords)
    assert serialized == "astronomy, spectroscopy, interferometry"

    hydrated = KeywordsUnit.hydrate({"reg_keywords": serialized})
    assert hydrated == keywords
