"""Phosphene Spatio-Graphic Canonical Archival Engine.

Implements CTS / CITE-2 spatio-graphic archival primitives, spatial indexing,
influence graph traversals, and IIIF 3.0 / W3C Web Annotation projections.
"""

from phosphene.spatiograph.models import (
    CanonicalUrn,
    CitoPredicate,
    Cite2Urn,
    CtsUrn,
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
from phosphene.spatiograph.urns import (
    Cite2UrnModel,
    CiteRoi,
    CtsUrnModel,
    ExternalIdentifierModel,
)
from phosphene.spatiograph.orchestrator import SpatioGraphComposer
from phosphene.spatiograph.store import CanonicalStore
from phosphene.spatiograph.exporters.iiif import (
    IIIFAnnotationPage,
    IIIFCanvas,
    IIIFLabel,
    IIIFManifest,
    W3CAnnotation,
    W3CAnnotationBody,
    W3CFragmentSelector,
    W3CSpecificResource,
    W3CSvgSelector,
    build_iiif_manifest,
    build_w3c_fragment_selector,
    build_w3c_svg_selector,
    project_inscription_to_w3c_annotation,
    project_planar_canvas_to_iiif,
)

__all__ = [
    # Primitive Models
    "CanonicalUrn",
    "CitoPredicate",
    "Cite2Urn",
    "CtsUrn",
    "DirectedRhetoricalAssertion",
    "ExternalBibliographicAuthority",
    "GraphemicInscription",
    "InscriptionEvent",
    "PlanarCanvas",
    "Point2D",
    "PropositionalKernel",
    "SpatialBox",
    "SpatialSelectorFrame",
    # Structured URN Models
    "Cite2UrnModel",
    "CiteRoi",
    "CtsUrnModel",
    "ExternalIdentifierModel",
    # Orchestrator & Persistence
    "SpatioGraphComposer",
    "CanonicalStore",
    # IIIF & W3C Web Annotation Exporters
    "IIIFAnnotationPage",
    "IIIFCanvas",
    "IIIFLabel",
    "IIIFManifest",
    "W3CAnnotation",
    "W3CAnnotationBody",
    "W3CFragmentSelector",
    "W3CSpecificResource",
    "W3CSvgSelector",
    "build_iiif_manifest",
    "build_w3c_fragment_selector",
    "build_w3c_svg_selector",
    "project_inscription_to_w3c_annotation",
    "project_planar_canvas_to_iiif",
]
