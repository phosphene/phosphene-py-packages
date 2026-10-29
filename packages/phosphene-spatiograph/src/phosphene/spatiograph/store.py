"""SQLite-backed Canonical Spatio-Graphic Store.

Implements zero-daemon archival storage:
- Canonical entity registry (CTS / CITE URNs)
- Planar coordinate spatial indexing via SQLite R*Tree virtual tables
- Inscription and proposition linking with Authorial Warrant verification
- Directed rhetorical citation graphs with ANSI recursive CTE traversals
- IIIF 3.0 & W3C Web Annotation manifest projection
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterator, List, Optional

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
from phosphene.spatiograph.exporters.iiif import (
    IIIFCanvas,
    IIIFManifest,
    W3CAnnotation,
    build_iiif_manifest,
    project_inscription_to_w3c_annotation,
    project_planar_canvas_to_iiif,
)


class CanonicalStore:
    """Zero-daemon SQLite store for CTS/CITE spatio-graphic archival primitives."""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self.conn.cursor()

        # Core Catalog: Canonical Names
        cur.execute("""
        CREATE TABLE IF NOT EXISTS canonical_entities (
            urn TEXT PRIMARY KEY,
            entity_class TEXT NOT NULL,
            label TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Propositional Kernels (Authorial Canon Only)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS propositional_kernels (
            urn TEXT PRIMARY KEY REFERENCES canonical_entities(urn),
            authorial_term TEXT NOT NULL,
            canonical_definition TEXT NOT NULL,
            authorial_warrant_locator TEXT NOT NULL,
            epistemic_tier TEXT NOT NULL
        )
        """)

        # Planar Canvases
        cur.execute("""
        CREATE TABLE IF NOT EXISTS planar_canvases (
            canvas_urn TEXT PRIMARY KEY REFERENCES canonical_entities(urn),
            pixel_width INTEGER NOT NULL,
            pixel_height INTEGER NOT NULL,
            media_sha256 TEXT NOT NULL,
            mime_type TEXT NOT NULL
        )
        """)

        # Spatial Selectors Metadata
        cur.execute("""
        CREATE TABLE IF NOT EXISTS spatial_selectors (
            selector_urn TEXT PRIMARY KEY REFERENCES canonical_entities(urn),
            canvas_urn TEXT NOT NULL REFERENCES planar_canvases(canvas_urn),
            polygon_json TEXT
        )
        """)

        # SQLite R*Tree Virtual Table for Spatial Window Queries
        cur.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS spatial_rtree USING rtree(
            id INTEGER PRIMARY KEY,
            minX REAL,
            maxX REAL,
            minY REAL,
            maxY REAL
        )
        """)

        # Mapping between RTree integer ID and Selector URN
        cur.execute("""
        CREATE TABLE IF NOT EXISTS selector_rtree_map (
            rtree_id INTEGER PRIMARY KEY,
            selector_urn TEXT NOT NULL UNIQUE REFERENCES spatial_selectors(selector_urn)
        )
        """)

        # Inscriptions
        cur.execute("""
        CREATE TABLE IF NOT EXISTS inscriptions (
            inscription_urn TEXT PRIMARY KEY REFERENCES canonical_entities(urn),
            selector_urn TEXT REFERENCES spatial_selectors(selector_urn),
            represented_work_urn TEXT NOT NULL REFERENCES canonical_entities(urn),
            diplomatic_transcription TEXT NOT NULL,
            confidence_score REAL NOT NULL
        )
        """)

        # Inscription Events
        cur.execute("""
        CREATE TABLE IF NOT EXISTS inscription_events (
            event_urn TEXT PRIMARY KEY REFERENCES canonical_entities(urn),
            agent TEXT NOT NULL,
            timestamp TEXT,
            toolchain TEXT,
            place TEXT,
            notes TEXT
        )
        """)

        # Directed Rhetorical Citation Graph Edges
        cur.execute("""
        CREATE TABLE IF NOT EXISTS citation_graph_edges (
            edge_urn TEXT PRIMARY KEY REFERENCES canonical_entities(urn),
            source_urn TEXT NOT NULL REFERENCES canonical_entities(urn),
            target_urn TEXT NOT NULL REFERENCES canonical_entities(urn),
            predicate TEXT NOT NULL,
            context_gloss TEXT
        )
        """)

        # External Bibliographic Authorities
        cur.execute("""
        CREATE TABLE IF NOT EXISTS external_authorities (
            urn TEXT PRIMARY KEY REFERENCES canonical_entities(urn),
            doi TEXT,
            title TEXT NOT NULL,
            creator TEXT,
            year INTEGER,
            metadata_json TEXT
        )
        """)

        # Fast lookup indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_edge_source ON citation_graph_edges(source_urn)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_edge_target ON citation_graph_edges(target_urn)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_edge_traversal ON citation_graph_edges(source_urn, predicate, target_urn)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_inscr_canvas ON spatial_selectors(canvas_urn)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_inscr_selector ON inscriptions(selector_urn)")
        self.conn.commit()

    def register_canonical_entity(self, urn: CanonicalUrn, entity_class: str, label: str = "") -> None:
        """Register a base canonical entity identifier."""
        cur = self.conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO canonical_entities (urn, entity_class, label) VALUES (?, ?, ?)",
            (urn, entity_class, label or urn),
        )
        self.conn.commit()

    def register_propositional_kernel(self, kernel: PropositionalKernel) -> None:
        """Register an author-canonical propositional kernel with authorial warrant."""
        cur = self.conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO canonical_entities (urn, entity_class, label) VALUES (?, ?, ?)",
            (kernel.urn, "kernel", kernel.authorial_term),
        )
        cur.execute(
            """INSERT OR REPLACE INTO propositional_kernels
               (urn, authorial_term, canonical_definition, authorial_warrant_locator, epistemic_tier)
               VALUES (?, ?, ?, ?, ?)""",
            (
                kernel.urn,
                kernel.authorial_term,
                kernel.canonical_definition,
                kernel.authorial_warrant_locator,
                kernel.epistemic_tier,
            ),
        )
        self.conn.commit()

    def register_canvas(self, canvas: PlanarCanvas, label: str = "") -> None:
        """Register a 2D planar canvas anchored to media blob."""
        cur = self.conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO canonical_entities (urn, entity_class, label) VALUES (?, ?, ?)",
            (canvas.urn, "canvas", label or canvas.urn),
        )
        cur.execute(
            """INSERT OR REPLACE INTO planar_canvases
               (canvas_urn, pixel_width, pixel_height, media_sha256, mime_type)
               VALUES (?, ?, ?, ?, ?)""",
            (canvas.urn, canvas.pixel_width, canvas.pixel_height, canvas.media_sha256, canvas.mime_type),
        )
        self.conn.commit()

    def register_spatial_selector(self, selector: SpatialSelectorFrame, label: str = "") -> int:
        """Register a planar ROI and index it into the SQLite R*Tree."""
        cur = self.conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO canonical_entities (urn, entity_class, label) VALUES (?, ?, ?)",
            (selector.urn, "selector", label or selector.urn),
        )
        poly_json = json.dumps([{"x": p.x, "y": p.y} for p in selector.polygon_vertices])
        cur.execute(
            "INSERT OR REPLACE INTO spatial_selectors (selector_urn, canvas_urn, polygon_json) VALUES (?, ?, ?)",
            (selector.urn, selector.canvas_urn, poly_json),
        )

        # Upsert RTree entry
        row = cur.execute(
            "SELECT rtree_id FROM selector_rtree_map WHERE selector_urn = ?", (selector.urn,)
        ).fetchone()

        if row:
            rtree_id = row[0]
            cur.execute(
                "UPDATE spatial_rtree SET minX=?, maxX=?, minY=?, maxY=? WHERE id=?",
                (
                    selector.bounding_box.min_x,
                    selector.bounding_box.max_x,
                    selector.bounding_box.min_y,
                    selector.bounding_box.max_y,
                    rtree_id,
                ),
            )
        else:
            cur.execute(
                "INSERT INTO spatial_rtree (minX, maxX, minY, maxY) VALUES (?, ?, ?, ?)",
                (
                    selector.bounding_box.min_x,
                    selector.bounding_box.max_x,
                    selector.bounding_box.min_y,
                    selector.bounding_box.max_y,
                ),
            )
            rtree_id = cur.lastrowid
            cur.execute(
                "INSERT INTO selector_rtree_map (rtree_id, selector_urn) VALUES (?, ?)",
                (rtree_id, selector.urn),
            )

        self.conn.commit()
        return rtree_id

    def register_inscription(self, inscription: GraphemicInscription, label: str = "") -> None:
        """Register a diplomatic inscription linked to selector and work."""
        cur = self.conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO canonical_entities (urn, entity_class, label) VALUES (?, ?, ?)",
            (inscription.urn, "inscription", label or inscription.diplomatic_transcription[:64]),
        )
        cur.execute(
            """INSERT OR REPLACE INTO inscriptions
               (inscription_urn, selector_urn, represented_work_urn, diplomatic_transcription, confidence_score)
               VALUES (?, ?, ?, ?, ?)""",
            (
                inscription.urn,
                inscription.selector_urn,
                inscription.represented_work_urn,
                inscription.diplomatic_transcription,
                inscription.confidence_score,
            ),
        )
        self.conn.commit()

    def register_inscription_event(self, event: InscriptionEvent) -> None:
        """Register a proper-name inscription or production event."""
        cur = self.conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO canonical_entities (urn, entity_class, label) VALUES (?, ?, ?)",
            (event.urn, "event", f"{event.agent} ({event.toolchain or 'event'})"),
        )
        cur.execute(
            """INSERT OR REPLACE INTO inscription_events
               (event_urn, agent, timestamp, toolchain, place, notes)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                event.urn,
                event.agent,
                event.timestamp,
                event.toolchain,
                event.place,
                event.notes,
            ),
        )
        self.conn.commit()

    def register_external_authority(self, auth: ExternalBibliographicAuthority) -> None:
        """Register external scholarly or bibliographic authority."""
        cur = self.conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO canonical_entities (urn, entity_class, label) VALUES (?, ?, ?)",
            (auth.urn, "external_authority", auth.title),
        )
        metadata = dict(auth)
        cur.execute(
            """INSERT OR REPLACE INTO external_authorities
               (urn, doi, title, creator, year, metadata_json)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (auth.urn, auth.doi, auth.title, auth.creator, auth.year, json.dumps(metadata)),
        )
        self.conn.commit()

    def register_edge(self, edge: DirectedRhetoricalAssertion) -> None:
        """Register directed rhetorical / citation graph edge."""
        cur = self.conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO canonical_entities (urn, entity_class, label) VALUES (?, ?, ?)",
            (edge.urn, "edge", f"{edge.source_urn} -[{edge.predicate}]-> {edge.target_urn}"),
        )
        cur.execute(
            """INSERT OR REPLACE INTO citation_graph_edges
               (edge_urn, source_urn, target_urn, predicate, context_gloss)
               VALUES (?, ?, ?, ?, ?)""",
            (edge.urn, edge.source_urn, edge.target_urn, edge.predicate.value, edge.context_gloss),
        )
        self.conn.commit()

    def query_spatial_window(self, canvas_urn: Cite2Urn, window: SpatialBox) -> list[dict]:
        """Query R*Tree for selectors and inscriptions overlapping canvas window."""
        cur = self.conn.cursor()
        query = """
        SELECT
            s.selector_urn,
            s.canvas_urn,
            r.minX, r.maxX, r.minY, r.maxY,
            i.inscription_urn,
            i.represented_work_urn,
            i.diplomatic_transcription,
            k.authorial_term,
            k.authorial_warrant_locator
        FROM spatial_rtree r
        JOIN selector_rtree_map m ON r.id = m.rtree_id
        JOIN spatial_selectors s ON m.selector_urn = s.selector_urn
        LEFT JOIN inscriptions i ON s.selector_urn = i.selector_urn
        LEFT JOIN propositional_kernels k ON i.represented_work_urn = k.urn
        WHERE s.canvas_urn = ?
          AND r.minX <= ? AND r.maxX >= ?
          AND r.minY <= ? AND r.maxY >= ?
        """
        rows = cur.execute(
            query,
            (canvas_urn, window.max_x, window.min_x, window.max_y, window.min_y),
        ).fetchall()
        return [dict(r) for r in rows]

    def traverse_influence_pathway(
        self, start_urn: CanonicalUrn, max_depth: int = 3
    ) -> list[dict]:
        """Recursive ANSI SQL CTE traversing directed rhetorical citations up to max_depth."""
        cur = self.conn.cursor()
        query = """
        WITH RECURSIVE influence_pathway(source_urn, predicate, target_urn, depth, traversal_path) AS (
            SELECT
                e.source_urn,
                e.predicate,
                e.target_urn,
                1 AS depth,
                e.source_urn || ' -> ' || e.target_urn AS traversal_path
            FROM citation_graph_edges e
            WHERE e.source_urn = ?

            UNION ALL

            SELECT
                e.source_urn,
                e.predicate,
                e.target_urn,
                p.depth + 1,
                p.traversal_path || ' -> ' || e.target_urn
            FROM citation_graph_edges e
            JOIN influence_pathway p ON e.source_urn = p.target_urn
            WHERE p.depth < ?
              AND instr(p.traversal_path, e.target_urn) = 0
        )
        SELECT depth, source_urn, predicate, target_urn, traversal_path
        FROM influence_pathway
        ORDER BY depth ASC;
        """
        rows = cur.execute(query, (start_urn, max_depth)).fetchall()
        return [dict(r) for r in rows]

    def export_canvas_to_iiif(
        self,
        canvas_urn: Cite2Urn,
        base_uri: str = "https://observatory.wiki/archives",
    ) -> Optional[IIIFCanvas]:
        """Project a PlanarCanvas and its spatial inscriptions into an IIIF 3.0 Canvas."""
        cur = self.conn.cursor()
        canvas_row = cur.execute(
            "SELECT canvas_urn, pixel_width, pixel_height, media_sha256, mime_type FROM planar_canvases WHERE canvas_urn = ?",
            (canvas_urn,),
        ).fetchone()

        if not canvas_row:
            return None

        canvas = PlanarCanvas(
            urn=canvas_row["canvas_urn"],
            pixel_width=canvas_row["pixel_width"],
            pixel_height=canvas_row["pixel_height"],
            media_sha256=canvas_row["media_sha256"],
            mime_type=canvas_row["mime_type"],
        )

        # Get label from canonical_entities
        ent_row = cur.execute(
            "SELECT label FROM canonical_entities WHERE urn = ?", (canvas_urn,)
        ).fetchone()
        label = ent_row["label"] if ent_row else canvas.urn

        # Query all selectors on this canvas
        selector_rows = cur.execute(
            """
            SELECT
                s.selector_urn,
                s.polygon_json,
                r.minX, r.maxX, r.minY, r.maxY
            FROM spatial_selectors s
            JOIN selector_rtree_map m ON s.selector_urn = m.selector_urn
            JOIN spatial_rtree r ON m.rtree_id = r.id
            WHERE s.canvas_urn = ?
            """,
            (canvas_urn,),
        ).fetchall()

        selectors_by_urn = {}
        for s_row in selector_rows:
            poly_data = json.loads(s_row["polygon_json"]) if s_row["polygon_json"] else []
            vertices = tuple(Point2D(x=pt["x"], y=pt["y"]) for pt in poly_data)
            box = SpatialBox(
                min_x=s_row["minX"],
                min_y=s_row["minY"],
                max_x=s_row["maxX"],
                max_y=s_row["maxY"],
            )
            selectors_by_urn[s_row["selector_urn"]] = SpatialSelectorFrame(
                urn=s_row["selector_urn"],
                canvas_urn=canvas_urn,
                bounding_box=box,
                polygon_vertices=vertices,
            )

        # Query all inscriptions associated with this canvas's selectors
        annotations: List[W3CAnnotation] = []
        if selectors_by_urn:
            placeholders = ",".join("?" for _ in selectors_by_urn)
            inscr_rows = cur.execute(
                f"""
                SELECT
                    inscription_urn,
                    selector_urn,
                    represented_work_urn,
                    diplomatic_transcription,
                    confidence_score
                FROM inscriptions
                WHERE selector_urn IN ({placeholders})
                """,
                list(selectors_by_urn.keys()),
            ).fetchall()

            for i_row in inscr_rows:
                inscr = GraphemicInscription(
                    urn=i_row["inscription_urn"],
                    selector_urn=i_row["selector_urn"],
                    represented_work_urn=i_row["represented_work_urn"],
                    diplomatic_transcription=i_row["diplomatic_transcription"],
                    confidence_score=i_row["confidence_score"],
                )
                sel = selectors_by_urn.get(i_row["selector_urn"])
                anno = project_inscription_to_w3c_annotation(
                    inscription=inscr,
                    canvas=canvas,
                    selector=sel,
                    base_uri=base_uri,
                )
                annotations.append(anno)

        return project_planar_canvas_to_iiif(
            canvas=canvas,
            label=label,
            annotations=annotations,
            base_uri=base_uri,
        )

    def export_collection_to_iiif_manifest(
        self,
        manifest_id: str,
        label: str,
        summary: str = "",
        base_uri: str = "https://observatory.wiki/archives",
        limit_canvases: Optional[int] = None,
    ) -> IIIFManifest:
        """Export stored canvases and annotations as a complete IIIF 3.0 Presentation Manifest."""
        cur = self.conn.cursor()
        query = "SELECT canvas_urn FROM planar_canvases ORDER BY canvas_urn"
        if limit_canvases:
            query += f" LIMIT {limit_canvases}"

        canvas_urns = [r["canvas_urn"] for r in cur.execute(query).fetchall()]
        canvases: List[IIIFCanvas] = []
        for c_urn in canvas_urns:
            c_iiif = self.export_canvas_to_iiif(c_urn, base_uri=base_uri)
            if c_iiif is not None:
                canvases.append(c_iiif)

        return build_iiif_manifest(
            manifest_id=manifest_id,
            label=label,
            summary=summary,
            canvases=canvases,
        )
