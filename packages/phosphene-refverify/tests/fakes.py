"""Fake LookupClients for pure-domain tests. Zero network."""

from __future__ import annotations

from phosphene.refverify.domain.scoring import CandidateRecord


class FakeClient:
    def __init__(
        self,
        name: str,
        by_doi_map: dict[str, CandidateRecord | None] | None = None,
        search_results: list[CandidateRecord] | None = None,
    ) -> None:
        self.name = name
        self.by_doi_map = by_doi_map or {}
        self.search_results = search_results or []
        self.by_doi_calls: list[str] = []
        self.search_calls: list[tuple] = []

    def by_doi(self, doi: str) -> CandidateRecord | None:
        self.by_doi_calls.append(doi)
        return self.by_doi_map.get(doi)

    def search(
        self, title: str, author: str | None = None, year: int | None = None
    ) -> list[CandidateRecord]:
        self.search_calls.append((title, author, year))
        return self.search_results


PAPER = CandidateRecord(
    title="Collaborative and Competitive Strategies in the Variability and Resiliency of Large-Scale Societies in Mesoamerica",
    authors=("Gary M. Feinman", "David M. Carballo"),
    year=2018,
    doi="10.1111/eano.12110",
    venue="Economic Anthropology",
    source="crossref",
)
