"""SQLite System of Record & Schema Management for Myth Engine (T-562).

Implements relational storage with foreign key constraints and WAL mode,
migrating flat JSON registries into an audited relational system of record.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import Field
from phosphene.core.models import InvariantStatic
from phosphene.myths.provenance import SourceRecord, TimeHorizon

MYTHS_DB_SCHEMA = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    doi_or_url TEXT NOT NULL,
    fetch_timestamp TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    extractor_commit TEXT,
    time_horizon TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS taxa (
    taxon_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    canonical_slug TEXT NOT NULL UNIQUE,
    region TEXT,
    centroid_lat REAL,
    centroid_lon REAL,
    lifestyle_mode TEXT,
    language_family TEXT,
    metadata_json TEXT
);

CREATE TABLE IF NOT EXISTS motifs (
    motif_id TEXT PRIMARY KEY,
    short_name TEXT NOT NULL,
    description TEXT,
    berezkin_ref TEXT,
    atu_type TEXT,
    tmi_code TEXT,
    metadata_json TEXT
);

CREATE TABLE IF NOT EXISTS occurrences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    taxon_id TEXT NOT NULL,
    motif_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    verbatim_evidence TEXT,
    page_ref TEXT,
    FOREIGN KEY(taxon_id) REFERENCES taxa(taxon_id) ON DELETE CASCADE,
    FOREIGN KEY(motif_id) REFERENCES motifs(motif_id) ON DELETE CASCADE,
    FOREIGN KEY(source_id) REFERENCES sources(source_id) ON DELETE CASCADE,
    UNIQUE(taxon_id, motif_id, source_id)
);

CREATE TABLE IF NOT EXISTS matrices (
    matrix_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    source_id TEXT NOT NULL,
    taxon_count INTEGER NOT NULL,
    character_count INTEGER NOT NULL,
    matrix_data_json TEXT NOT NULL,
    FOREIGN KEY(source_id) REFERENCES sources(source_id)
);

CREATE INDEX IF NOT EXISTS idx_occ_taxon ON occurrences(taxon_id);
CREATE INDEX IF NOT EXISTS idx_occ_motif ON occurrences(motif_id);
CREATE INDEX IF NOT EXISTS idx_occ_source ON occurrences(source_id);
"""


class MythStore:
    """Authoritative relational store for unified myth datasets."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.executescript(MYTHS_DB_SCHEMA)

    def insert_source(self, source: SourceRecord) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO sources (
                    source_id, title, doi_or_url, fetch_timestamp, sha256,
                    extractor_commit, time_horizon, description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source.source_id,
                    source.title,
                    source.doi_or_url,
                    source.fetch_timestamp,
                    source.sha256,
                    source.extractor_commit,
                    source.time_horizon.value,
                    source.description,
                ),
            )

    def get_source(self, source_id: str) -> Optional[SourceRecord]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM sources WHERE source_id = ?", (source_id,)).fetchone()
            if not row:
                return None
            return SourceRecord(
                source_id=row["source_id"],
                title=row["title"],
                doi_or_url=row["doi_or_url"],
                fetch_timestamp=row["fetch_timestamp"],
                sha256=row["sha256"],
                extractor_commit=row["extractor_commit"],
                time_horizon=TimeHorizon(row["time_horizon"]),
                description=row["description"],
            )

    def insert_taxon(
        self,
        taxon_id: str,
        name: str,
        canonical_slug: str,
        region: Optional[str] = None,
        centroid_lat: Optional[float] = None,
        centroid_lon: Optional[float] = None,
        lifestyle_mode: Optional[str] = None,
        language_family: Optional[str] = None,
        metadata_json: Optional[str] = None,
    ) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO taxa (
                    taxon_id, name, canonical_slug, region,
                    centroid_lat, centroid_lon, lifestyle_mode, language_family, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    taxon_id,
                    name,
                    canonical_slug,
                    region,
                    centroid_lat,
                    centroid_lon,
                    lifestyle_mode,
                    language_family,
                    metadata_json,
                ),
            )

    def insert_motif(
        self,
        motif_id: str,
        short_name: str,
        description: Optional[str] = None,
        berezkin_ref: Optional[str] = None,
        atu_type: Optional[str] = None,
        tmi_code: Optional[str] = None,
        metadata_json: Optional[str] = None,
    ) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO motifs (
                    motif_id, short_name, description, berezkin_ref,
                    atu_type, tmi_code, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    motif_id,
                    short_name,
                    description,
                    berezkin_ref,
                    atu_type,
                    tmi_code,
                    metadata_json,
                ),
            )

    def insert_occurrence(
        self,
        taxon_id: str,
        motif_id: str,
        source_id: str,
        confidence: float = 1.0,
        verbatim_evidence: Optional[str] = None,
        page_ref: Optional[str] = None,
    ) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO occurrences (
                    taxon_id, motif_id, source_id, confidence, verbatim_evidence, page_ref
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    taxon_id,
                    motif_id,
                    source_id,
                    confidence,
                    verbatim_evidence,
                    page_ref,
                ),
            )

    def count_taxa(self) -> int:
        with self._get_connection() as conn:
            return int(conn.execute("SELECT count(*) FROM taxa").fetchone()[0])

    def count_motifs(self) -> int:
        with self._get_connection() as conn:
            return int(conn.execute("SELECT count(*) FROM motifs").fetchone()[0])

    def count_occurrences(self) -> int:
        with self._get_connection() as conn:
            return int(conn.execute("SELECT count(*) FROM occurrences").fetchone()[0])
