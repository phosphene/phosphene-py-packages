"""Discrete serialization unit for primary author and coauthors in WordPress postmeta.

@dft
- A1 (pure-io-separation): Pure transformation logic — zero I/O imports.
- A2 (determinism): Completely deterministic mappings.
- A4 (dft-docs): This docstring section.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from phosphene.imi_wordpress.delimited_text import join_lines, split_lines
from phosphene.imi_wordpress.domain import Author, ContributorSequence


class AuthorMetaUnit:
    """Discrete serialization and hydration for author contributor collections."""

    @staticmethod
    def serialize(primary: Author, coauthors: tuple[Author, ...] = ()) -> dict[str, str]:
        coauthor_names = [a.name for a in coauthors]
        return {
            "reg_author_name": primary.name,
            "reg_orcid": primary.orcid,
            "reg_affiliation": primary.affiliation,
            "reg_country": primary.country,
            "reg_coauthors": join_lines(coauthor_names),
        }

    @staticmethod
    def hydrate(meta: Mapping[str, Any]) -> tuple[Author, tuple[Author, ...]]:
        primary = Author(
            name=str(meta.get("reg_author_name", "")),
            orcid=str(meta.get("reg_orcid", "")),
            affiliation=str(meta.get("reg_affiliation", "")),
            country=str(meta.get("reg_country", "")),
            sequence=ContributorSequence.FIRST,
        )

        raw_coauthors = str(meta.get("reg_coauthors", ""))
        lines = split_lines(raw_coauthors)
        coauthors = tuple(
            Author(name=line, sequence=ContributorSequence.ADDITIONAL) for line in lines
        )

        return primary, coauthors
