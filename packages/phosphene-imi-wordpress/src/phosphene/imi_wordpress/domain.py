"""Pure domain models for the IMI scholarly preprint registry.

This module models the core business reality of a scholarly preprint registration
independent of any wire protocol, transport format, or WordPress schema.

@dft
- A1 (pure-io-separation): Pure domain logic — zero I/O imports.
- A2 (determinism): Immutable frozen dataclasses, no non-deterministic calls.
- A4 (dft-docs): This docstring section.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum

from phosphene.imi_wordpress.doi_regex import (
    is_valid_doi,
    strip_protocol_prefix,
)
from phosphene.imi_wordpress.orcid_regex import (
    canonicalize_orcid,
    is_valid_orcid,
    to_orcid_uri,
)

# IMI's registered Crossref prefix (Member 57537)
IMI_DOI_PREFIX = "10.67767"


class ContributorSequence(StrEnum):
    """Contributor ordering sequence for scholarly schemas."""

    FIRST = "first"
    ADDITIONAL = "additional"


class License(StrEnum):
    """Scholarly publication licenses."""

    CC_BY_NC_SA_4_0 = "CC BY-NC-SA 4.0"
    CC_BY_4_0 = "CC BY 4.0"
    CC0_1_0 = "CC0 1.0"

    @property
    def url(self) -> str:
        """Canonical Creative Commons URI."""
        return {
            License.CC_BY_NC_SA_4_0: "https://creativecommons.org/licenses/by-nc-sa/4.0/",
            License.CC_BY_4_0: "https://creativecommons.org/licenses/by/4.0/",
            License.CC0_1_0: "https://creativecommons.org/publicdomain/zero/1.0/",
        }[self]

    @property
    def spdx(self) -> str:
        """Standard SPDX identifier."""
        return {
            License.CC_BY_NC_SA_4_0: "CC-BY-NC-SA-4.0",
            License.CC_BY_4_0: "CC-BY-4.0",
            License.CC0_1_0: "CC0-1.0",
        }[self]

    @classmethod
    def from_spdx(cls, spdx: str) -> License:
        """Resolve a License from its SPDX identifier."""
        lookup = {
            "CC-BY-NC-SA-4.0": cls.CC_BY_NC_SA_4_0,
            "CC-BY-4.0": cls.CC_BY_4_0,
            "CC0-1.0": cls.CC0_1_0,
        }
        val = spdx.strip().upper()
        if val not in lookup:
            raise ValueError(f"Unknown SPDX license identifier: {spdx}")
        return lookup[val]


class DOIStatus(StrEnum):
    """Lifecycle status of a Digital Object Identifier."""

    UNASSIGNED = "unassigned"
    PENDING = "pending"
    ACTIVE = "active"
    WITHDRAWN = "withdrawn"

    def can_transition_to(self, target: DOIStatus) -> bool:
        """Determine if a transition to the target status is permitted."""
        if self == DOIStatus.UNASSIGNED:
            return target == DOIStatus.PENDING
        if self == DOIStatus.PENDING:
            return target in (DOIStatus.ACTIVE, DOIStatus.UNASSIGNED)
        if self == DOIStatus.ACTIVE:
            return target == DOIStatus.WITHDRAWN
        return False

    @property
    def is_minted(self) -> bool:
        """True if the DOI has been minted with Crossref."""
        return self in (DOIStatus.ACTIVE, DOIStatus.WITHDRAWN)

    @property
    def is_resolvable(self) -> bool:
        """True if the DOI resolves to a public landing page."""
        return self == DOIStatus.ACTIVE


class EditorialState(StrEnum):
    """Jan's 5-state preprint editorial lifecycle plus withdrawal."""

    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    UNDER_REVIEW = "under_review"
    LIVE_PREPRINT = "live_preprint"
    PUBLISHED = "published"
    WITHDRAWN = "withdrawn"

    @property
    def is_published(self) -> bool:
        """True if the state requires a publicly indexable landing page."""
        return self in (
            EditorialState.LIVE_PREPRINT,
            EditorialState.PUBLISHED,
            EditorialState.WITHDRAWN,
        )

    @property
    def is_reviewing(self) -> bool:
        """True if the article is actively in peer or editorial review."""
        return self in (
            EditorialState.PENDING_REVIEW,
            EditorialState.UNDER_REVIEW,
        )

    def can_transition_to(self, target: EditorialState) -> bool:
        """Determine if a transition to the target state is permitted."""
        valid_transitions = {
            EditorialState.DRAFT: (EditorialState.PENDING_REVIEW, EditorialState.LIVE_PREPRINT),
            EditorialState.PENDING_REVIEW: (EditorialState.UNDER_REVIEW, EditorialState.DRAFT),
            EditorialState.UNDER_REVIEW: (EditorialState.LIVE_PREPRINT, EditorialState.DRAFT),
            EditorialState.LIVE_PREPRINT: (EditorialState.PUBLISHED, EditorialState.WITHDRAWN),
            EditorialState.PUBLISHED: (EditorialState.WITHDRAWN,),
            EditorialState.WITHDRAWN: (),
        }
        return target in valid_transitions.get(self, ())

    @property
    def badge_mode(self) -> str:
        """Visual advisory token corresponding to this editorial state."""
        return {
            EditorialState.DRAFT: "draft",
            EditorialState.PENDING_REVIEW: "pending",
            EditorialState.UNDER_REVIEW: "under_review",
            EditorialState.LIVE_PREPRINT: "preprint",
            EditorialState.PUBLISHED: "published",
            EditorialState.WITHDRAWN: "withdrawn",
        }[self]


@dataclass(frozen=True, slots=True, kw_only=True)
class DOI:
    """Scholarly Digital Object Identifier value object.

    Constructive and immutable. Defaults to IMI's Crossref prefix (10.67767).
    """

    suffix: str
    prefix: str = IMI_DOI_PREFIX

    def __post_init__(self) -> None:
        pfx = self.prefix.strip()
        sfx = self.suffix.strip()
        if not is_valid_doi(f"{pfx}/{sfx}"):
            raise ValueError(f"Malformed DOI: {pfx}/{sfx}")

    @property
    def value(self) -> str:
        """The canonical DOI identifier string, e.g. '10.67767/imi.2026.001'."""
        return f"{self.prefix}/{self.suffix}"

    @property
    def url(self) -> str:
        """The permanent resolution URL, e.g. 'https://doi.org/10.67767/imi.2026.001'."""
        return f"https://doi.org/{self.value}"

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_string(cls, raw: str) -> DOI:
        """Parse a DOI string into a structured DOI value object.

        Splits on the first slash if present; otherwise assumes the string is
        a suffix under IMI's prefix.
        """
        clean = strip_protocol_prefix(raw)
        if "/" in clean:
            pfx, sfx = clean.split("/", 1)
            return cls(suffix=sfx, prefix=pfx)
        return cls(suffix=clean)


@dataclass(frozen=True, slots=True, kw_only=True)
class DOIRecord:
    """Scholarly DOI registration and state record. Pure data."""

    doi: DOI | None = None
    status: DOIStatus = DOIStatus.UNASSIGNED
    minted_date: str = ""
    deposit_id: str = ""

    def __post_init__(self) -> None:
        if self.status == DOIStatus.ACTIVE and self.doi is None:
            raise ValueError("An ACTIVE DOIRecord must have a non-null DOI instance.")

    @property
    def is_minted(self) -> bool:
        return self.status.is_minted

    @property
    def is_resolvable(self) -> bool:
        return self.status.is_resolvable

    def with_pending(self, deposit_id: str) -> DOIRecord:
        if not self.status.can_transition_to(DOIStatus.PENDING):
            raise ValueError(f"Cannot transition DOIRecord from {self.status.value} to pending.")
        return replace(self, status=DOIStatus.PENDING, deposit_id=deposit_id)

    def with_active(self, minted_date: str) -> DOIRecord:
        if not self.status.can_transition_to(DOIStatus.ACTIVE):
            raise ValueError(f"Cannot transition DOIRecord from {self.status.value} to active.")
        if self.doi is None:
            raise ValueError("Cannot activate DOIRecord without an assigned DOI.")
        return replace(self, status=DOIStatus.ACTIVE, minted_date=minted_date)

    def with_withdrawn(self) -> DOIRecord:
        if not self.status.can_transition_to(DOIStatus.WITHDRAWN):
            raise ValueError(f"Cannot transition DOIRecord from {self.status.value} to withdrawn.")
        return replace(self, status=DOIStatus.WITHDRAWN)


@dataclass(frozen=True, slots=True, kw_only=True)
class Author:
    """Scholarly contributor value object.

    Shared contract between primary author and co-authors to eliminate
    primitive obsession.
    """

    name: str
    orcid: str = ""
    affiliation: str = ""
    country: str = ""
    sequence: ContributorSequence = ContributorSequence.FIRST
    role: str = "author"

    def __post_init__(self) -> None:
        clean = canonicalize_orcid(self.orcid)
        if clean and not is_valid_orcid(clean):
            raise ValueError(f"Malformed ORCID: {self.orcid}")
        object.__setattr__(self, "orcid", clean)

    @property
    def orcid_url(self) -> str:
        return to_orcid_uri(self.orcid)

    @property
    def is_primary(self) -> bool:
        return self.sequence == ContributorSequence.FIRST


@dataclass(frozen=True, slots=True, kw_only=True)
class VersionInfo:
    """Preprint version lineage value object."""

    number: int = 1
    version_type: str = "major"  # major, minor, patch
    history: str = ""  # changelog / revision notes
    prior_versions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.number < 1:
            raise ValueError(f"Version number must be positive: {self.number}")

    def formatted(self) -> str:
        return f"v{self.number}"

    def increment(self, version_type: str = "major", notes: str = "") -> VersionInfo:
        new_prior = tuple(dict.fromkeys((*self.prior_versions, self.formatted())))
        return VersionInfo(
            number=self.number + 1,
            version_type=version_type,
            history=notes,
            prior_versions=new_prior,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PreprintEntry:
    """Pure domain entity representing a scholarly preprint registry record.

    Axioms:
    - Pure business entity with zero knowledge of WordPress or wire serialization.
    - Preserves semantic collection types (tuple of keywords, tuple of authors).
    - Immutable with native slots for compact memory representation.
    """

    title: str
    primary_author: Author
    slug: str = ""
    editorial_state: EditorialState = EditorialState.DRAFT
    abstract: str = ""
    methodology: str = ""
    license: License = License.CC_BY_NC_SA_4_0
    declaration: bool = True
    keywords: tuple[str, ...] = ()
    coauthors: tuple[Author, ...] = ()
    destination_url: str = ""
    published_destination: str = "Observatory"
    pdf_url: str = ""
    schema_type: str = "ScholarlyArticle"
    registry_id: str = ""
    doi_record: DOIRecord = field(default_factory=DOIRecord)
    version: VersionInfo = field(default_factory=VersionInfo)
    withdrawal_notice: str = ""

    def all_authors(self) -> tuple[Author, ...]:
        return (self.primary_author, *self.coauthors)

    def with_editorial_state(self, state: EditorialState) -> PreprintEntry:
        return replace(self, editorial_state=state)

    def with_doi_record(self, doi_record: DOIRecord) -> PreprintEntry:
        return replace(self, doi_record=doi_record)
