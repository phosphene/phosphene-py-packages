"""Duplicate/orphan detection -- pure."""

from __future__ import annotations

from phosphene.refverify.domain.reference import Reference
from phosphene.refverify.domain.scoring import title_similarity


def find_duplicates(refs: list[Reference]) -> dict[int, int]:
    """Map of duplicate-index -> first-index for same-work citations.

    Same work = identical DOI, else title similarity >= 0.95.
    Returns {} when nothing repeats.
    """
    by_doi: dict[str, int] = {}
    dupes: dict[int, int] = {}
    for i, ref in enumerate(refs):
        if ref.doi:
            k = ref.doi.lower()
            if k in by_doi:
                dupes[i] = by_doi[k]
            else:
                by_doi[k] = i
                continue
        # title-based pass (no DOI)
        for j in range(i):
            other = refs[j]
            if other.doi or ref.doi:
                continue
            rt = ref.title or ref.text
            ot = other.title or other.text
            if title_similarity(rt, ot) >= 0.95:
                dupes[i] = j
                break
    return dupes
