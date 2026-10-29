"""Unit tests for spatiograph models and canonical constraints."""

import pytest
from pydantic import ValidationError
from phosphene.spatiograph.models import (
    CitoPredicate,
    DirectedRhetoricalAssertion,
    ExternalBibliographicAuthority,
    GraphemicInscription,
    InscriptionEvent,
    PlanarCanvas,
    Point2D,
    PropositionalKernel,
    SpatialBox,
    SpatialSelectorFrame,
)


def test_cts_urn_valid() -> None:
    kernel = PropositionalKernel(
        urn="urn:cts:phosphene:pendell.concepts:mead_principle",
        authorial_term="The MEAD Principle",
        canonical_definition="Magic is Empowerment by Attention to Detail.",
        authorial_warrant_locator="urn:cts:phosphene:pendell.essays:ritual_art.p12",
    )
    assert kernel.urn == "urn:cts:phosphene:pendell.concepts:mead_principle"
    assert kernel.epistemic_tier == "author-canonical"


def test_cts_urn_invalid_format() -> None:
    with pytest.raises(ValidationError):
        PropositionalKernel(
            urn="invalid_urn_string",
            authorial_term="Invalid",
            canonical_definition="Def",
            authorial_warrant_locator="urn:cts:phosphene:pendell.essays:ritual_art.p12",
        )


def test_spatial_box_overlap() -> None:
    box_a = SpatialBox(min_x=10.0, min_y=10.0, max_x=50.0, max_y=50.0)
    box_b = SpatialBox(min_x=40.0, min_y=40.0, max_x=80.0, max_y=80.0)
    box_c = SpatialBox(min_x=60.0, min_y=60.0, max_x=90.0, max_y=90.0)

    assert box_a.overlaps(box_b) is True
    assert box_a.overlaps(box_c) is False
    assert box_a.contains_point(Point2D(x=25.0, y=25.0)) is True
    assert box_a.contains_point(Point2D(x=55.0, y=25.0)) is False


def test_spatial_box_degenerate_raises() -> None:
    with pytest.raises(ValidationError):
        SpatialBox(min_x=50.0, min_y=10.0, max_x=10.0, max_y=50.0)


def test_primitives_are_invariant_static() -> None:
    canvas = PlanarCanvas(
        urn="urn:cite2:phosphene:visuals.canvases:altar_021",
        pixel_width=1200,
        pixel_height=800,
        media_sha256="e" * 64,
    )
    # Frozen mutation check
    with pytest.raises(ValidationError):
        canvas.pixel_width = 1400  # type: ignore[misc]

    # Extra forbidden check
    with pytest.raises(ValidationError):
        PlanarCanvas(
            urn="urn:cite2:phosphene:visuals.canvases:altar_021",
            pixel_width=1200,
            pixel_height=800,
            media_sha256="e" * 64,
            unexpected_field="disallowed",  # type: ignore[call-arg]
        )


def test_external_authority_is_invariant_dynamic() -> None:
    # Allows unexpected vendor attributes without throwing
    auth = ExternalBibliographicAuthority(
        urn="urn:cite2:phosphene:external.authorities:snyder_1969",
        title="Earth House Hold",
        creator="Gary Snyder",
        year=1969,
        crossref_funder_id="ext-999",
        openalex_concept_score=0.98,
    )
    assert auth.title == "Earth House Hold"
    assert getattr(auth, "crossref_funder_id") == "ext-999"


def test_directed_rhetorical_assertion() -> None:
    edge = DirectedRhetoricalAssertion(
        urn="urn:cite2:phosphene:relations.citations:cite_01",
        source_urn="urn:cite2:phosphene:inscriptions:inscr_loeffler_p1",
        target_urn="urn:cite2:phosphene:external.authorities:snyder_1969",
        predicate=CitoPredicate.CITES_AS_AUTHORITY,
        context_gloss="Gary mentions late-1940s SF peyote circle users",
    )
    assert edge.predicate == CitoPredicate.CITES_AS_AUTHORITY
    assert edge.source_urn.startswith("urn:cite2:")
