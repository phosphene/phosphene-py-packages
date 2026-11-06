"""Discrete serialization unit for DOIRecord and lifecycle status in WordPress postmeta.

@dft
- A1 (pure-io-separation): Pure transformation logic — zero I/O imports.
- A2 (determinism): Completely deterministic mappings.
- A4 (dft-docs): This docstring section.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from phosphene.imi_wordpress.domain import DOI, DOIRecord, DOIStatus


class DoiMetaUnit:
    """Discrete serialization and hydration for DOI metadata and status."""

    @staticmethod
    def serialize(record: DOIRecord) -> dict[str, str]:
        return {
            "reg_doi": record.doi.value if record.doi else "",
            "reg_doi_url": record.doi.url if record.doi else "",
            "reg_doi_status": record.status.value,
            "reg_doi_minted_date": record.minted_date,
            "reg_crossref_deposit_id": record.deposit_id,
        }

    @staticmethod
    def hydrate(meta: Mapping[str, Any]) -> DOIRecord:
        raw_doi = str(meta.get("reg_doi", "")).strip()
        doi = DOI.from_string(raw_doi) if raw_doi else None

        raw_status = str(meta.get("reg_doi_status", "")).strip()
        try:
            status = DOIStatus(raw_status)
        except ValueError:
            status = DOIStatus.UNASSIGNED

        # Invariant guard: if ACTIVE but no DOI, status reverts to UNASSIGNED
        if status == DOIStatus.ACTIVE and doi is None:
            status = DOIStatus.UNASSIGNED

        return DOIRecord(
            doi=doi,
            status=status,
            minted_date=str(meta.get("reg_doi_minted_date", "")),
            deposit_id=str(meta.get("reg_crossref_deposit_id", "")),
        )
