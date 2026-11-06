"""Discrete serialization unit for VersionInfo in WordPress postmeta.

@dft
- A1 (pure-io-separation): Pure transformation logic — zero I/O imports.
- A2 (determinism): Completely deterministic mappings.
- A4 (dft-docs): This docstring section.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from phosphene.imi_wordpress.delimited_text import join_lines, split_lines
from phosphene.imi_wordpress.domain import VersionInfo


class VersionMetaUnit:
    """Discrete serialization and hydration for version lineage and history."""

    @staticmethod
    def serialize(version: VersionInfo) -> dict[str, Any]:
        return {
            "reg_version": version.number,
            "reg_version_type": version.version_type,
            "reg_version_history": version.history,
            "reg_prior_versions": join_lines(version.prior_versions),
        }

    @staticmethod
    def hydrate(meta: Mapping[str, Any]) -> VersionInfo:
        try:
            raw_num = int(meta.get("reg_version", 1))
        except (ValueError, TypeError):
            raw_num = 1
        number = max(1, raw_num)

        version_type = str(meta.get("reg_version_type", "major"))
        history = str(meta.get("reg_version_history", ""))
        raw_priors = str(meta.get("reg_prior_versions", ""))
        prior_versions = split_lines(raw_priors)

        return VersionInfo(
            number=number,
            version_type=version_type or "major",
            history=history,
            prior_versions=prior_versions,
        )
