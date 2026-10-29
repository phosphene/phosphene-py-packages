"""IIIF Presentation 3.0 & W3C Web Annotation Exporter.

Projects canonical spatio-graphic entities (PlanarCanvas, SpatialSelectorFrame,
GraphemicInscription, InscriptionEvent) into standards-compliant:
- W3C Web Annotation Data Model (REC-annotation-model-20170223)
- IIIF Presentation API 3.0 Manifests & AnnotationPages

Conforms to Phosphene standards:
- InvariantStatic models
- Pure transformation functions
- Strict typing and no inline regex
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Union
from pydantic import Field, HttpUrl
from phosphene.core.models import InvariantStatic
from phosphene.spatiograph.models import (
    GraphemicInscription,
    InscriptionEvent,
    PlanarCanvas,
    SpatialSelectorFrame,
)
from phosphene.spatiograph.patterns import CITE2_URN_RE, CTS_URN_RE


# ---------------------------------------------------------------------------
# W3C Web Annotation Data Model (REC-annotation-model-20170223)
# ---------------------------------------------------------------------------

class W3CAnnotationBody(InvariantStatic):
    """Textual body for a W3C Web Annotation (e.g. diplomatic transcription)."""

    type: str = "TextualBody"
    value: str
    format: str = "text/plain"
    language: Optional[str] = "en"


class W3CFragmentSelector(InvariantStatic):
    """W3C FragmentSelector using media fragment xywh syntax."""

    type: str = "FragmentSelector"
    conformsTo: str = "http://www.w3.org/TR/media-frags/"
    value: str = Field(description="Media fragment selector, e.g. 'xywh=pixel:10,20,100,200'")


class W3CSvgSelector(InvariantStatic):
    """W3C SvgSelector for polygonal or non-rectangular regions."""

    type: str = "SvgSelector"
    value: str = Field(description="SVG path or polygon string representation")


class W3CSpecificResource(InvariantStatic):
    """Target resource scoped by a selector on a source canvas."""

    type: str = "SpecificResource"
    source: str = Field(description="Target canvas URI or URN")
    selector: Union[W3CFragmentSelector, W3CSvgSelector]


class W3CAnnotation(InvariantStatic):
    """W3C Web Annotation."""

    id: str = Field(description="Unique URI / URN for the annotation")
    type: str = "Annotation"
    motivation: str = "supplementing"
    body: W3CAnnotationBody
    target: Union[str, W3CSpecificResource]


# ---------------------------------------------------------------------------
# IIIF Presentation API 3.0 Models
# ---------------------------------------------------------------------------

class IIIFLabel(InvariantStatic):
    """IIIF multi-language label map."""

    en: List[str] = Field(default_factory=list)

    @classmethod
    def from_string(cls, text: str) -> IIIFLabel:
        return cls(en=[text])


class IIIFAnnotationPage(InvariantStatic):
    """IIIF Presentation 3.0 AnnotationPage embedding W3C Annotations."""

    id: str
    type: str = "AnnotationPage"
    items: List[W3CAnnotation] = Field(default_factory=list)


class IIIFCanvas(InvariantStatic):
    """IIIF Presentation 3.0 Canvas projecting PlanarCanvas."""

    id: str
    type: str = "Canvas"
    label: IIIFLabel
    width: int
    height: int
    annotations: List[IIIFAnnotationPage] = Field(default_factory=list)


class IIIFManifest(InvariantStatic):
    """IIIF Presentation 3.0 Manifest wrapping an archival collection."""

    id: str
    type: str = "Manifest"
    label: IIIFLabel
    summary: Optional[IIIFLabel] = None
    items: List[IIIFCanvas] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Pure Transformation Units
# ---------------------------------------------------------------------------

def build_w3c_fragment_selector(
    frame: SpatialSelectorFrame,
    canvas: PlanarCanvas,
) -> W3CFragmentSelector:
    """Project normalized SpatialBox coordinates to pixel-space media fragment."""
    px_x = round(frame.bounding_box.min_x * canvas.pixel_width)
    px_y = round(frame.bounding_box.min_y * canvas.pixel_height)
    px_w = round((frame.bounding_box.max_x - frame.bounding_box.min_x) * canvas.pixel_width)
    px_h = round((frame.bounding_box.max_y - frame.bounding_box.min_y) * canvas.pixel_height)

    # Ensure minimum 1px dimensions if bounding box is non-zero
    if frame.bounding_box.max_x > frame.bounding_box.min_x and px_w == 0:
        px_w = 1
    if frame.bounding_box.max_y > frame.bounding_box.min_y and px_h == 0:
        px_h = 1

    fragment_value = f"xywh=pixel:{px_x},{px_y},{px_w},{px_h}"
    return W3CFragmentSelector(value=fragment_value)


def build_w3c_svg_selector(
    frame: SpatialSelectorFrame,
    canvas: PlanarCanvas,
) -> Optional[W3CSvgSelector]:
    """Project polygon vertices to an SVG polygon selector string."""
    if not frame.polygon_vertices:
        return None

    points_str = " ".join(
        f"{round(pt.x * canvas.pixel_width)},{round(pt.y * canvas.pixel_height)}"
        for pt in frame.polygon_vertices
    )
    svg_payload = f'<svg><polygon points="{points_str}" /></svg>'
    return W3CSvgSelector(value=svg_payload)


def project_inscription_to_w3c_annotation(
    inscription: GraphemicInscription,
    canvas: PlanarCanvas,
    selector: Optional[SpatialSelectorFrame] = None,
    base_uri: str = "https://observatory.wiki/archives",
) -> W3CAnnotation:
    """Project GraphemicInscription and SpatialSelectorFrame to a W3C Web Annotation."""
    anno_id = f"{base_uri}/annotations/{inscription.urn.split(':')[-1]}"
    canvas_target_id = f"{base_uri}/canvases/{canvas.urn.split(':')[-1]}"

    body = W3CAnnotationBody(
        value=inscription.diplomatic_transcription,
        format="text/plain",
    )

    if selector is not None:
        # Check if polygonal or rectangular
        target_selector: Union[W3CFragmentSelector, W3CSvgSelector]
        svg_sel = build_w3c_svg_selector(selector, canvas)
        if svg_sel is not None:
            target_selector = svg_sel
        else:
            target_selector = build_w3c_fragment_selector(selector, canvas)

        target = W3CSpecificResource(
            source=canvas_target_id,
            selector=target_selector,
        )
    else:
        target = canvas_target_id

    return W3CAnnotation(
        id=anno_id,
        body=body,
        target=target,
    )


def project_planar_canvas_to_iiif(
    canvas: PlanarCanvas,
    label: str,
    annotations: Sequence[W3CAnnotation] = (),
    base_uri: str = "https://observatory.wiki/archives",
) -> IIIFCanvas:
    """Project PlanarCanvas to an IIIF 3.0 Canvas with attached AnnotationPages."""
    canvas_slug = canvas.urn.split(":")[-1]
    canvas_id = f"{base_uri}/canvases/{canvas_slug}"

    annotation_pages: List[IIIFAnnotationPage] = []
    if annotations:
        page_id = f"{canvas_id}/page/1"
        annotation_pages.append(
            IIIFAnnotationPage(
                id=page_id,
                items=list(annotations),
            )
        )

    return IIIFCanvas(
        id=canvas_id,
        label=IIIFLabel.from_string(label or canvas_slug),
        width=canvas.pixel_width,
        height=canvas.pixel_height,
        annotations=annotation_pages,
    )


def build_iiif_manifest(
    manifest_id: str,
    label: str,
    summary: str,
    canvases: Sequence[IIIFCanvas],
) -> IIIFManifest:
    """Assemble collection of IIIF Canvases into an IIIF 3.0 Manifest."""
    return IIIFManifest(
        id=manifest_id,
        label=IIIFLabel.from_string(label),
        summary=IIIFLabel.from_string(summary) if summary else None,
        items=list(canvases),
    )
