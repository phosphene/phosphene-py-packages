"""Joint Spatio-Graphic Reassembly Orchestrator.

Implements Assembly Paradigms:
- Spatial Canvas Superposition
- Topological Intertextual Synthesis
Resolving a planar coordinate window into an interactive intellectual provenance web.
"""

from __future__ import annotations

from typing import Any

from phosphene.spatiograph.models import (
    Cite2Urn,
    SpatialBox,
)
from phosphene.spatiograph.store import CanonicalStore


class SpatioGraphComposer:
    """Joint spatio-graphic orchestrator composing planar coordinates and citation graphs."""

    def __init__(self, store: CanonicalStore) -> None:
        self.store = store

    def resolve_region_intellectual_context(
        self,
        canvas_urn: Cite2Urn,
        viewport: SpatialBox,
        citation_depth: int = 2,
    ) -> dict[str, Any]:
        """Resolves 2D spatial intersection against decomposed elements and walks the citation graph."""
        captured_elements = self.store.query_spatial_window(canvas_urn, viewport)

        composite_result: dict[str, Any] = {
            "canvas": canvas_urn,
            "viewport": {
                "min_x": viewport.min_x,
                "min_y": viewport.min_y,
                "max_x": viewport.max_x,
                "max_y": viewport.max_y,
            },
            "elements": [],
        }

        for elem in captured_elements:
            element_report: dict[str, Any] = {
                "selector_urn": elem["selector_urn"],
                "inscription_urn": elem["inscription_urn"],
                "transcription": elem["diplomatic_transcription"],
                "represented_work": elem["represented_work_urn"],
                "authorial_term": elem["authorial_term"],
                "authorial_warrant": elem["authorial_warrant_locator"],
                "network_influences": [],
            }

            # Graph traversal starting from the inscription (or represented work)
            start_urn = elem["inscription_urn"] or elem["represented_work_urn"]
            if start_urn:
                lineage = self.store.traverse_influence_pathway(
                    start_urn, max_depth=citation_depth
                )
                element_report["network_influences"] = lineage

            composite_result["elements"].append(element_report)

        return composite_result
