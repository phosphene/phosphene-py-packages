"""Canonical Spatio-Graphic Archival Models (CTS / CITE-2).

Codifies the 5 atomic decomposition primitives:
1. PropositionalKernel (LRM-E1_Work / CRM:E28_Concept) — CONSERVATIVE authorial canon only.
2. GraphemicInscription (CRMtex:TX1_Written_Text / CRM:E36_Visual_Item) — Proper name.
3. SpatialSelectorFrame (oa:FragmentSelector / CITE-ROI) — Proper name coordinate window.
4. InscriptionEvent (CRM:E12_Production / PROV-O:Activity) — Proper name historical event.
5. DirectedRhetoricalAssertion (CiTO:CitationAct) — Proper name directed relationship.

Built strictly on Phosphene Core InvariantStatic & InvariantDynamic with no inline regex.
"""

from __future__ import annotations

import enum
from typing import Annotated
from pydantic import Field, field_validator, model_validator
from phosphene.core.models import InvariantDynamic, InvariantStatic
from phosphene.spatiograph.patterns import (
    CITE2_URN_RE,
    CTS_URN_RE,
    SHA256_HEX_RE,
)

# ---------------------------------------------------------------------------
# Canonical URN String Conductance Gates (Validated via Named Patterns)
# ---------------------------------------------------------------------------

CtsUrn = Annotated[
    str,
    Field(description="Canonical Text Services URN string (validated via CTS_URN_RE)"),
]

Cite2Urn = Annotated[
    str,
    Field(description="CITE-2 URN string (validated via CITE2_URN_RE)"),
]

CanonicalUrn = CtsUrn | Cite2Urn


def _validate_cts_urn(v: str) -> str:
    if not CTS_URN_RE.match(v):
        raise ValueError(f"Invalid CTS URN syntax: '{v}'")
    return v


def _validate_cite2_urn(v: str) -> str:
    if not CITE2_URN_RE.match(v):
        raise ValueError(f"Invalid CITE-2 URN syntax: '{v}'")
    return v


def _validate_canonical_urn(v: str) -> str:
    if not (CTS_URN_RE.match(v) or CITE2_URN_RE.match(v)):
        raise ValueError(f"Invalid Canonical URN syntax (must be CTS or CITE-2): '{v}'")
    return v


# ---------------------------------------------------------------------------
# Predicates & Classes
# ---------------------------------------------------------------------------

class CitoPredicate(enum.StrEnum):
    """Citation Typing Ontology (CiTO) controlled predicates."""

    CITES_AS_AUTHORITY = "cito:citesAsAuthority"
    CRITIQUES = "cito:critiques"
    ALLUDES_TO = "cito:alludesTo"
    SCHEMATIZES = "cito:schematizes"
    DERIVES_FROM = "cito:derivesFrom"
    PARODIES = "cito:parodies"
    DISCUSSES = "cito:discusses"


# ---------------------------------------------------------------------------
# Spatial Geometry Primitives
# ---------------------------------------------------------------------------

class Point2D(InvariantStatic):
    x: float
    y: float


class SpatialBox(InvariantStatic):
    """Planar bounding box on a 2D canvas: [min_x, min_y, max_x, max_y]."""

    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @model_validator(mode="after")
    def _validate_bounds(self) -> SpatialBox:
        if self.max_x < self.min_x or self.max_y < self.min_y:
            raise ValueError(
                f"Degenerate bounding box: ({self.min_x}, {self.min_y}) to ({self.max_x}, {self.max_y})"
            )
        return self

    def overlaps(self, other: SpatialBox) -> bool:
        """Pure query determining whether two planar bounding boxes overlap."""
        return not (
            self.max_x < other.min_x
            or self.min_x > other.max_x
            or self.max_y < other.min_y
            or self.min_y > other.max_y
        )

    def contains_point(self, pt: Point2D) -> bool:
        """Pure query determining whether a 2D point falls inside the bounding box."""
        return (
            self.min_x <= pt.x <= self.max_x
            and self.min_y <= pt.y <= self.max_y
        )


# ---------------------------------------------------------------------------
# 1. Propositional Semantic Kernel (LRM-E1_Work / CRM:E28_Concept)
# CONSERVATIVE BUCKET: Restricted strictly to concepts that the author
# explicitly coined, investigated, or made the direct subject of a work.
# Requires an authorial warrant locator.
# ---------------------------------------------------------------------------

class PropositionalKernel(InvariantStatic):
    """Primitive 1: Author-canonical intellectual concept or motif."""

    urn: CtsUrn
    authorial_term: str = Field(description="The exact term or title used by the author")
    canonical_definition: str = Field(description="The author's own definition or formulation")
    authorial_warrant_locator: CtsUrn = Field(
        description="CTS URN locator to the primary passage establishing the authorial warrant"
    )
    epistemic_tier: str = Field(default="author-canonical", frozen=True)

    @field_validator("urn", "authorial_warrant_locator")
    @classmethod
    def _validate_urn_fields(cls, v: str) -> str:
        return _validate_cts_urn(v)


# ---------------------------------------------------------------------------
# 2. Graphemic Inscription (CRMtex:TX1_Written_Text / CRM:E36_Visual_Item)
# Proper Name: Unrepeatable physical or digital mark made by the author.
# ---------------------------------------------------------------------------

class GraphemicInscription(InvariantStatic):
    """Primitive 2: Diplomatic transcription or visual symbol cluster."""

    urn: Cite2Urn
    selector_urn: Cite2Urn | None = None
    represented_work_urn: CtsUrn
    diplomatic_transcription: str
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)

    @field_validator("urn")
    @classmethod
    def _validate_urn(cls, v: str) -> str:
        return _validate_cite2_urn(v)

    @field_validator("selector_urn")
    @classmethod
    def _validate_selector_urn(cls, v: str | None) -> str | None:
        if v is not None:
            return _validate_cite2_urn(v)
        return None

    @field_validator("represented_work_urn")
    @classmethod
    def _validate_cts_field(cls, v: str) -> str:
        return _validate_cts_urn(v)


# ---------------------------------------------------------------------------
# 3. Spatial-Temporal Selector Frame (oa:FragmentSelector / CITE-ROI)
# Proper Name: Coordinate region on a digital or physical canvas.
# ---------------------------------------------------------------------------

class PlanarCanvas(InvariantStatic):
    """2D coordinate space container ($W \times H$) anchored to media blob."""

    urn: Cite2Urn
    pixel_width: int
    pixel_height: int
    media_sha256: str
    mime_type: str = "image/jpeg"

    @field_validator("urn")
    @classmethod
    def _validate_urn(cls, v: str) -> str:
        return _validate_cite2_urn(v)

    @field_validator("media_sha256")
    @classmethod
    def _validate_sha(cls, v: str) -> str:
        if not SHA256_HEX_RE.match(v):
            raise ValueError(f"Invalid SHA-256 hash: '{v}'")
        return v


class SpatialSelectorFrame(InvariantStatic):
    """Primitive 3: Planar Region of Interest (ROI) on a canvas."""

    urn: Cite2Urn
    canvas_urn: Cite2Urn
    bounding_box: SpatialBox
    polygon_vertices: tuple[Point2D, ...] = ()

    @field_validator("urn", "canvas_urn")
    @classmethod
    def _validate_urn(cls, v: str) -> str:
        return _validate_cite2_urn(v)


# ---------------------------------------------------------------------------
# 4. Inscription Event (CRM:E12_Production / PROV-O:Activity)
# Proper Name: Historical creation or revision event.
# ---------------------------------------------------------------------------

class InscriptionEvent(InvariantStatic):
    """Primitive 4: Contextual activity of production."""

    urn: Cite2Urn
    agent: str
    timestamp: str | None = None
    toolchain: str | None = None
    place: str | None = None
    notes: str | None = None

    @field_validator("urn")
    @classmethod
    def _validate_urn(cls, v: str) -> str:
        return _validate_cite2_urn(v)


# ---------------------------------------------------------------------------
# 5. Directed Rhetorical Assertion (CiTO:CitationAct / oa:Annotation)
# Proper Name: Directed rhetorical link between URNs.
# ---------------------------------------------------------------------------

class DirectedRhetoricalAssertion(InvariantStatic):
    """Primitive 5: Directed citation or schematization vector."""

    urn: Cite2Urn
    source_urn: CanonicalUrn
    target_urn: CanonicalUrn
    predicate: CitoPredicate
    context_gloss: str | None = None

    @field_validator("urn")
    @classmethod
    def _validate_edge_urn(cls, v: str) -> str:
        return _validate_cite2_urn(v)

    @field_validator("source_urn", "target_urn")
    @classmethod
    def _validate_endpoint_urns(cls, v: str) -> str:
        return _validate_canonical_urn(v)


# ---------------------------------------------------------------------------
# Open-World Ingestion Gate (InvariantDynamic)
# ---------------------------------------------------------------------------

class ExternalBibliographicAuthority(InvariantDynamic):
    """External scholarly record (DOI, Crossref, OpenAlex, ARK)."""

    urn: Cite2Urn
    doi: str | None = None
    title: str
    creator: str | None = None
    year: int | None = None

    @field_validator("urn")
    @classmethod
    def _validate_urn(cls, v: str) -> str:
        return _validate_cite2_urn(v)
