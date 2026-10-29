"""Tests for IIIF 3.0 Manifest & W3C Web Annotation exporter."""

import json
from phosphene.spatiograph import (
    CanonicalStore,
    GraphemicInscription,
    PlanarCanvas,
    Point2D,
    SpatialBox,
    SpatialSelectorFrame,
)
from phosphene.spatiograph.exporters.iiif import (
    build_iiif_manifest,
    build_w3c_fragment_selector,
    build_w3c_svg_selector,
    project_inscription_to_w3c_annotation,
    project_planar_canvas_to_iiif,
)


def test_build_w3c_fragment_selector():
    canvas = PlanarCanvas(
        urn="urn:cite2:pendell:canvases.circle1",
        pixel_width=1000,
        pixel_height=2000,
        media_sha256="a" * 64,
    )
    box = SpatialBox(min_x=0.1, min_y=0.2, max_x=0.5, max_y=0.8)
    frame = SpatialSelectorFrame(
        urn="urn:cite2:pendell:visuals.circle1:roi",
        canvas_urn=canvas.urn,
        bounding_box=box,
    )

    frag = build_w3c_fragment_selector(frame, canvas)
    assert frag.type == "FragmentSelector"
    assert frag.value == "xywh=pixel:100,400,400,1200"


def test_build_w3c_svg_selector():
    canvas = PlanarCanvas(
        urn="urn:cite2:pendell:canvases.circle1",
        pixel_width=1000,
        pixel_height=1000,
        media_sha256="a" * 64,
    )
    box = SpatialBox(min_x=0.0, min_y=0.0, max_x=0.5, max_y=0.5)
    vertices = (
        Point2D(x=0.1, y=0.1),
        Point2D(x=0.4, y=0.1),
        Point2D(x=0.25, y=0.4),
    )
    frame = SpatialSelectorFrame(
        urn="urn:cite2:pendell:visuals.circle1:triangle",
        canvas_urn=canvas.urn,
        bounding_box=box,
        polygon_vertices=vertices,
    )

    svg_sel = build_w3c_svg_selector(frame, canvas)
    assert svg_sel is not None
    assert svg_sel.type == "SvgSelector"
    assert 'points="100,100 400,100 250,400"' in svg_sel.value


def test_project_inscription_to_w3c_annotation():
    canvas = PlanarCanvas(
        urn="urn:cite2:pendell:canvases.circle1",
        pixel_width=800,
        pixel_height=600,
        media_sha256="b" * 64,
    )
    frame = SpatialSelectorFrame(
        urn="urn:cite2:pendell:visuals.circle1:label",
        canvas_urn=canvas.urn,
        bounding_box=SpatialBox(min_x=0.0, min_y=0.0, max_x=1.0, max_y=0.5),
    )
    inscr = GraphemicInscription(
        urn="urn:cite2:pendell:inscriptions.label_1",
        selector_urn=frame.urn,
        represented_work_urn="urn:cts:pendell:pharmako_poeia:circle",
        diplomatic_transcription="Tabula Smaragdina",
    )

    anno = project_inscription_to_w3c_annotation(inscr, canvas, frame)
    assert anno.type == "Annotation"
    assert anno.body.value == "Tabula Smaragdina"
    assert anno.target.selector.value == "xywh=pixel:0,0,800,300"


def test_canonical_store_iiif_export_roundtrip():
    store = CanonicalStore(":memory:")

    canvas = PlanarCanvas(
        urn="urn:cite2:pendell:canvases.botanikos_sample",
        pixel_width=1200,
        pixel_height=800,
        media_sha256="c" * 64,
    )
    store.register_canvas(canvas, label="Botanikos Salve Label")

    frame = SpatialSelectorFrame(
        urn="urn:cite2:pendell:visuals.botanikos_sample:top_label",
        canvas_urn=canvas.urn,
        bounding_box=SpatialBox(min_x=0.1, min_y=0.1, max_x=0.9, max_y=0.4),
    )
    store.register_spatial_selector(frame)

    work_urn = "urn:cts:pendell:botanikos:label"
    store.register_canonical_entity(work_urn, "work", "Botanikos Label Work")

    inscr = GraphemicInscription(
        urn="urn:cite2:pendell:inscriptions.botanikos_01",
        selector_urn=frame.urn,
        represented_work_urn=work_urn,
        diplomatic_transcription="Botanikos Herbal Salve",
    )
    store.register_inscription(inscr)

    # Export single canvas
    iiif_canvas = store.export_canvas_to_iiif(canvas.urn)
    assert iiif_canvas is not None
    assert iiif_canvas.width == 1200
    assert iiif_canvas.height == 800
    assert len(iiif_canvas.annotations) == 1
    assert len(iiif_canvas.annotations[0].items) == 1
    assert iiif_canvas.annotations[0].items[0].body.value == "Botanikos Herbal Salve"

    # Export collection manifest
    manifest = store.export_collection_to_iiif_manifest(
        manifest_id="https://observatory.wiki/archives/manifests/botanikos",
        label="Botanikos Curated Collection",
        summary="Botanikos herbal designs and authorial annotations",
    )
    assert manifest.type == "Manifest"
    assert manifest.label.en[0] == "Botanikos Curated Collection"
    assert len(manifest.items) == 1
    assert manifest.items[0].id == iiif_canvas.id
