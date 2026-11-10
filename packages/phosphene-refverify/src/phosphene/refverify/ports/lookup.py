"""LookupClient port -- the domain names what it needs, the world supplies it.

Implementations live in adapters/ (httpx-backed) and tests (fakes).
The domain never imports an adapter.
"""

from __future__ import annotations

from typing import Protocol

from phosphene.refverify.domain.scoring import CandidateRecord


class LookupClient(Protocol):
    """Bibliographic provider lookup. Fall back across a list of these."""

    name: str

    def by_doi(self, doi: str) -> CandidateRecord | None:
        """Exact identifier lookup. None when the DOI does not resolve."""
        ...

    def search(
        self, title: str, author: str | None = None, year: int | None = None
    ) -> list[CandidateRecord]:
        """Title search -- may return several candidates, may return []."""
        ...
