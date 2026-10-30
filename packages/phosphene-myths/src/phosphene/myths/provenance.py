"""Canonical Ingestion Provenance Envelopes (T-561).

Guarantees complete cryptographic lineage, capture timestamping,
and epistemological time-horizon categorization for external datasets.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional
from pydantic import Field, field_validator
from phosphene.core.models import InvariantStatic


class TimeHorizon(str, Enum):
    """Epistemological time-horizon classification for cross-domain evidence."""

    ETHNOGRAPHIC_OBSERVATION = "ethnographic_observation"
    HISTORICAL_TEXTUAL = "historical_textual"
    ARCHAEOLOGICAL_SAMPLE = "archaeological_sample"
    PALEOLITHIC_INFERRED = "paleolithic_inferred"


class SourceRecord(InvariantStatic):
    """Cryptographic provenance envelope for an ingested external dataset."""

    source_id: str
    title: str
    doi_or_url: str
    fetch_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    sha256: str
    extractor_commit: Optional[str] = None
    time_horizon: TimeHorizon
    description: Optional[str] = None

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, v: str) -> str:
        clean = v.strip().lower()
        if len(clean) != 64 or not all(c in "0123456789abcdef" for c in clean):
            raise ValueError(f"Invalid sha256 hex digest: {v}")
        return clean

    @classmethod
    def from_file(
        cls,
        file_path: str | Path,
        source_id: str,
        title: str,
        doi_or_url: str,
        time_horizon: TimeHorizon,
        extractor_commit: Optional[str] = None,
        description: Optional[str] = None,
    ) -> SourceRecord:
        """Create a SourceRecord from a local file, computing its sha256 hash."""
        p = Path(file_path)
        if not p.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        h = hashlib.sha256()
        with p.open("rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)

        return cls(
            source_id=source_id,
            title=title,
            doi_or_url=doi_or_url,
            sha256=h.hexdigest(),
            extractor_commit=extractor_commit,
            time_horizon=time_horizon,
            description=description,
        )
