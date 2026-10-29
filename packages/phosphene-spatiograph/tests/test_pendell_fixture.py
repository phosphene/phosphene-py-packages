"""Fixture and integration test mapping Dale Pendell Circle artifacts."""

from phosphene.spatiograph.models import (
    CitoPredicate,
    DirectedRhetoricalAssertion,
    ExternalBibliographicAuthority,
    GraphemicInscription,
    InscriptionEvent,
    PlanarCanvas,
    PropositionalKernel,
    SpatialBox,
    SpatialSelectorFrame,
)
from phosphene.spatiograph.orchestrator import SpatioGraphComposer
from phosphene.spatiograph.store import CanonicalStore


def test_pendell_circle_artifacts_end_to_end() -> None:
    store = CanonicalStore(":memory:")
    composer = SpatioGraphComposer(store)

    # 1. Register Authorial Propositional Kernels (Conservative author canon)
    kernel_circle = PropositionalKernel(
        urn="urn:cts:phosphene:pendell.concepts:medicine_circle",
        authorial_term="The Medicine Circle",
        canonical_definition="Non-hierarchical ceremonial containment technology for entheogenic journeying and purging.",
        authorial_warrant_locator="urn:cts:phosphene:pendell.pharmako_gnosis:p133#on_circles",
    )
    kernel_yunmen = PropositionalKernel(
        urn="urn:cts:phosphene:pendell.concepts:yunmen_correspondence",
        authorial_term="Yunmen Koan of Mutual Subdual",
        canonical_definition="Medicine and sickness subdue each other—they mutually correspond. The whole earth is medicine.",
        authorial_warrant_locator="urn:cts:phosphene:pendell.essays:medicine_circle_2.p1",
    )
    store.register_propositional_kernel(kernel_circle)
    store.register_propositional_kernel(kernel_yunmen)

    # 2. Register Planar Canvas for Altar Image (`posterpix307 021.jpg`)
    canvas_altar = PlanarCanvas(
        urn="urn:cite2:phosphene:visuals.canvases:posterpix307_021",
        pixel_width=1600,
        pixel_height=1200,
        media_sha256="4bb8ad8" + "0" * 57,
    )
    store.register_canvas(canvas_altar, label="Altar with ceremonial staffs and sacred surface")

    # 3. Spatial Selectors (Proper Names: physical bounding coordinates)
    sel_staffs = SpatialSelectorFrame(
        urn="urn:cite2:phosphene:selectors:sel_altar_staffs",
        canvas_urn=canvas_altar.urn,
        bounding_box=SpatialBox(min_x=200, min_y=300, max_x=700, max_y=800),
    )
    store.register_spatial_selector(sel_staffs, label="Ceremonial feather-bound staffs/pipes")

    # 4. Graphemic Inscription (Proper Name: diplomatic transcription of visual mark)
    inscr_staffs = GraphemicInscription(
        urn="urn:cite2:phosphene:inscriptions:inscr_altar_staffs",
        selector_urn=sel_staffs.urn,
        represented_work_urn=kernel_circle.urn,
        diplomatic_transcription="Overhead view: two decorated wooden pipes/staffs wrapped with feathers and beads on painted altar cloth.",
    )
    store.register_inscription(inscr_staffs)

    # 5. External Authorities
    auth_snyder = ExternalBibliographicAuthority(
        urn="urn:cite2:phosphene:external.authorities:snyder_1969",
        title="Earth House Hold",
        creator="Gary Snyder",
        year=1969,
    )
    auth_brownton = ExternalBibliographicAuthority(
        urn="urn:cite2:phosphene:external.authorities:brownton_rainbow",
        title="Interview on Rainbow Tribe Talking Stick Origins",
        creator="Page Brownton",
        year=2005,
    )
    store.register_external_authority(auth_snyder)
    store.register_external_authority(auth_brownton)

    # 6. Directed Rhetorical Links (CiTO)
    # Inscription -> cites Gary Snyder
    store.register_edge(
        DirectedRhetoricalAssertion(
            urn="urn:cite2:phosphene:relations:edge_1",
            source_urn=inscr_staffs.urn,
            target_urn=auth_snyder.urn,
            predicate=CitoPredicate.CITES_AS_AUTHORITY,
            context_gloss="Dale notes Snyder's record of peyote availability in late-1940s SF",
        )
    )
    # Gary Snyder -> critiques Brownton's account of transmission
    store.register_edge(
        DirectedRhetoricalAssertion(
            urn="urn:cite2:phosphene:relations:edge_2",
            source_urn=auth_snyder.urn,
            target_urn=auth_brownton.urn,
            predicate=CitoPredicate.CRITIQUES,
            context_gloss="Inquiry into whether circle was traditional or invented by 1960s Rainbow Tribe",
        )
    )

    # 7. Execute Spatio-Graphic Reassembly
    viewport = SpatialBox(min_x=150, min_y=250, max_x=750, max_y=850)
    report = composer.resolve_region_intellectual_context(canvas_altar.urn, viewport, citation_depth=2)

    assert len(report["elements"]) == 1
    elem = report["elements"][0]
    assert elem["represented_work"] == "urn:cts:phosphene:pendell.concepts:medicine_circle"
    assert elem["authorial_term"] == "The Medicine Circle"
    assert elem["authorial_warrant"] == "urn:cts:phosphene:pendell.pharmako_gnosis:p133#on_circles"
    assert len(elem["network_influences"]) == 2
    assert elem["network_influences"][0]["target_urn"] == auth_snyder.urn
    assert elem["network_influences"][1]["target_urn"] == auth_brownton.urn
