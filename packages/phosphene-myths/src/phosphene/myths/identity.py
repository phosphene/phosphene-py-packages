"""Cross-Domain Identity Bridge Table (T-564).

Resolves cultural and linguistic entities across TRAMES, Berezkin, D-PLACE,
Glottolog, Pulotu, and Reich ancient DNA units.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import Field
from phosphene.core.models import InvariantStatic


IDENTITY_BRIDGE_SCHEMA = """
CREATE TABLE IF NOT EXISTS identity_bridge (
    bridge_id INTEGER PRIMARY KEY AUTOINCREMENT,
    taxon_id TEXT NOT NULL,
    trames_region_id INTEGER,
    berezkin_tradition_id INTEGER,
    dplace_society_id TEXT,
    glottocode TEXT,
    pulotu_id TEXT,
    reich_adna_group TEXT,
    confidence REAL DEFAULT 1.0,
    notes TEXT,
    FOREIGN KEY(taxon_id) REFERENCES taxa(taxon_id) ON DELETE CASCADE,
    UNIQUE(taxon_id)
);

CREATE INDEX IF NOT EXISTS idx_bridge_trames ON identity_bridge(trames_region_id);
CREATE INDEX IF NOT EXISTS idx_bridge_berezkin ON identity_bridge(berezkin_tradition_id);
CREATE INDEX IF NOT EXISTS idx_bridge_glotto ON identity_bridge(glottocode);
CREATE INDEX IF NOT EXISTS idx_bridge_dplace ON identity_bridge(dplace_society_id);
"""


class IdentityBridgeRecord(InvariantStatic):
    """Audited cross-walk mapping for a single cultural taxon."""

    taxon_id: str
    trames_region_id: Optional[int] = None
    berezkin_tradition_id: Optional[int] = None
    dplace_society_id: Optional[str] = None
    glottocode: Optional[str] = None
    pulotu_id: Optional[str] = None
    reich_adna_group: Optional[str] = None
    confidence: float = 1.0
    notes: Optional[str] = None


class IdentityBridgeManager:
    """Manages cross-domain identity mapping in SQLite."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.executescript(IDENTITY_BRIDGE_SCHEMA)

    def link_entity(self, record: IdentityBridgeRecord) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute(
                """
                INSERT OR REPLACE INTO identity_bridge (
                    taxon_id, trames_region_id, berezkin_tradition_id,
                    dplace_society_id, glottocode, pulotu_id, reich_adna_group,
                    confidence, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.taxon_id,
                    record.trames_region_id,
                    record.berezkin_tradition_id,
                    record.dplace_society_id,
                    record.glottocode,
                    record.pulotu_id,
                    record.reich_adna_group,
                    record.confidence,
                    record.notes,
                ),
            )

    def get_by_taxon_id(self, taxon_id: str) -> Optional[IdentityBridgeRecord]:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM identity_bridge WHERE taxon_id = ?", (taxon_id,)).fetchone()
            if not row:
                return None
            return IdentityBridgeRecord(
                taxon_id=row["taxon_id"],
                trames_region_id=row["trames_region_id"],
                berezkin_tradition_id=row["berezkin_tradition_id"],
                dplace_society_id=row["dplace_society_id"],
                glottocode=row["glottocode"],
                pulotu_id=row["pulotu_id"],
                reich_adna_group=row["reich_adna_group"],
                confidence=row["confidence"],
                notes=row["notes"],
            )

    def count_mappings(self) -> int:
        with sqlite3.connect(str(self.db_path)) as conn:
            return int(conn.execute("SELECT count(*) FROM identity_bridge").fetchone()[0])
