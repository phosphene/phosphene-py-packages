"""Unit and integration tests for SQLite CanonicalStore and SpatioGraphComposer."""

import pytest
from phosphene.spatiograph.models import (
    CitoPredicate,
    DirectedRhetoricalAssertion,
    ExternalBibliographicAuthority,
    GraphemicInscription,
    PlanarCanvas,
    PropositionalKernel,
    SpatialBox,
    SpatialSelectorFrame,
)
from phosphene.spatiograph.orchestrator import SpatioGraphComposer
from phosphene.spatiograph.store import CanonicalStore


@pytest.fixture
def store() -> CanonicalStore:
    return CanonicalStore(":memory:")


def test_spatial_rtree_indexing_and_query(store: CanonicalStore) -> None:
    canvas_urn = "urn:cite2:phosphene:visuals.canvases:altar_021"
    store.register_canvas(
        PlanarCanvas(
            urn=canvas_urn,
            pixel_width=1000,
            pixel_height=1000,
            media_sha256="a" * 64,
        )
    )

    # Register two selectors
    sel_1 = SpatialSelectorFrame(
        urn="urn:cite2:phosphene:selectors:sel_staff_left",
        canvas_urn=canvas_urn,
        bounding_box=SpatialBox(min_x=100, min_y=100, max_x=300, max_y=300),
    )
    sel_2 = SpatialSelectorFrame(
        urn="urn:cite2:phosphene:selectors:sel_stone_right",
        canvas_urn=canvas_urn,
        bounding_box=SpatialBox(min_x=600, min_y=600, max_x=800, max_y=800),
    )

    store.register_spatial_selector(sel_1)
    store.register_spatial_selector(sel_2)

    # Query window hitting only sel_1
    window = SpatialBox(min_x=50, min_y=50, max_x=250, max_y=250)
    hits = store.query_spatial_window(canvas_urn, window)

    assert len(hits) == 1
    assert hits[0]["selector_urn"] == sel_1.urn


def test_recursive_influence_pathway_traversal(store: CanonicalStore) -> None:
    # Build a 3-hop citation graph: A -> B -> C -> D
    edges = [
        DirectedRhetoricalAssertion(
            urn="urn:cite2:phosphene:relations:edge_1",
            source_urn="urn:cite2:phosphene:inscriptions:inscr_a",
            target_urn="urn:cts:phosphene:pendell.concepts:concept_b",
            predicate=CitoPredicate.SCHEMATIZES,
        ),
        DirectedRhetoricalAssertion(
            urn="urn:cite2:phosphene:relations:edge_2",
            source_urn="urn:cts:phosphene:pendell.concepts:concept_b",
            target_urn="urn:cite2:phosphene:external.authorities:snyder_1969",
            predicate=CitoPredicate.CITES_AS_AUTHORITY,
        ),
        DirectedRhetoricalAssertion(
            urn="urn:cite2:phosphene:relations:edge_3",
            source_urn="urn:cite2:phosphene:external.authorities:snyder_1969",
            target_urn="urn:cite2:phosphene:external.authorities:brownton_rainbow",
            predicate=CitoPredicate.CRITIQUES,
        ),
    ]

    for e in edges:
        store.register_edge(e)

    # Traverse from root inscription
    pathway = store.traverse_influence_pathway("urn:cite2:phosphene:inscriptions:inscr_a", max_depth=3)

    assert len(pathway) == 3
    assert pathway[0]["depth"] == 1
    assert pathway[0]["target_urn"] == "urn:cts:phosphene:pendell.concepts:concept_b"
    assert pathway[1]["depth"] == 2
    assert pathway[1]["target_urn"] == "urn:cite2:phosphene:external.authorities:snyder_1969"
    assert pathway[2]["depth"] == 3
    assert pathway[2]["target_urn"] == "urn:cite2:phosphene:external.authorities:brownton_rainbow"


def test_joint_spatiograph_orchestrator(store: CanonicalStore) -> None:
    canvas_urn = "urn:cite2:phosphene:visuals.canvases:altar_021"
    store.register_canvas(
        PlanarCanvas(
            urn=canvas_urn,
            pixel_width=1000,
            pixel_height=1000,
            media_sha256="f" * 64,
        )
    )

    # 1. Author-canonical Propositional Kernel
    kernel = PropositionalKernel(
        urn="urn:cts:phosphene:pendell.concepts:mead_principle",
        authorial_term="The MEAD Principle",
        canonical_definition="Magic is Empowerment by Attention to Detail.",
        authorial_warrant_locator="urn:cts:phosphene:pendell.essays:ritual_art.p12",
    )
    store.register_propositional_kernel(kernel)

    # 2. Selector
    sel = SpatialSelectorFrame(
        urn="urn:cite2:phosphene:selectors:sel_altar_staffs",
        canvas_urn=canvas_urn,
        bounding_box=SpatialBox(min_x=150, min_y=200, max_x=450, max_y=600),
    )
    store.register_spatial_selector(sel)

    # 3. Inscription
    inscr = GraphemicInscription(
        urn="urn:cite2:phosphene:inscriptions:inscr_feather_staffs",
        selector_urn=sel.urn,
        represented_work_urn=kernel.urn,
        diplomatic_transcription="Feather-bound ceremonial staffs lying on painted altar",
    )
    store.register_inscription(inscr)

    # 4. Outbound Citation Edge from Inscription to External Authority
    auth = ExternalBibliographicAuthority(
        urn="urn:cite2:phosphene:external.authorities:snyder_1969",
        title="Earth House Hold",
        creator="Gary Snyder",
        year=1969,
    )
    store.register_external_authority(auth)

    edge = DirectedRhetoricalAssertion(
        urn="urn:cite2:phosphene:relations:edge_staff_snyder",
        source_urn=inscr.urn,
        target_urn=auth.urn,
        predicate=CitoPredicate.CITES_AS_AUTHORITY,
        context_gloss="Gary Snyder notes peyote user emergence in SF in late 1940s",
    )
    store.register_edge(edge)

    # Orchestrator Joint Resolution
    composer = SpatioGraphComposer(store)
    window = SpatialBox(min_x=100, min_y=150, max_x=500, max_y=650)
    report = composer.resolve_region_intellectual_context(canvas_urn, window)

    assert len(report["elements"]) == 1
    elem = report["elements"][0]
    assert elem["selector_urn"] == sel.urn
    assert elem["authorial_term"] == "The MEAD Principle"
    assert elem["authorial_warrant"] == "urn:cts:phosphene:pendell.essays:ritual_art.p12"
    assert len(elem["network_influences"]) == 1
    assert elem["network_influences"][0]["target_urn"] == auth.urn
