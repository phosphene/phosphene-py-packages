"""Discrete serialization unit for Keywords in WordPress postmeta.

@dft
- A1 (pure-io-separation): Pure transformation logic — zero I/O imports.
- A2 (determinism): Completely deterministic mappings.
- A4 (dft-docs): This docstring section.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from phosphene.imi_wordpress.delimited_text import join_commas, split_commas


class KeywordsUnit:
    """Discrete serialization and hydration for keyword collections."""

    @staticmethod
    def serialize(keywords: tuple[str, ...]) -> str:
        return join_commas(keywords)

    @staticmethod
    def hydrate(meta: Mapping[str, Any]) -> tuple[str, ...]:
        raw = str(meta.get("reg_keywords", ""))
        return split_commas(raw)
