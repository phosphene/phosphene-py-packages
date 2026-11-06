"""Discrete serialization unit for License in WordPress postmeta.

@dft
- A1 (pure-io-separation): Pure transformation logic — zero I/O imports.
- A2 (determinism): Completely deterministic mappings.
- A4 (dft-docs): This docstring section.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from phosphene.imi_wordpress.domain import License


class LicenseUnit:
    """Discrete serialization and hydration for publication licenses."""

    @staticmethod
    def serialize(license_: License) -> str:
        return license_.value

    @staticmethod
    def hydrate(meta: Mapping[str, Any]) -> License:
        raw = str(meta.get("reg_license", "")).strip()
        try:
            return License(raw)
        except ValueError:
            return License.CC_BY_NC_SA_4_0
