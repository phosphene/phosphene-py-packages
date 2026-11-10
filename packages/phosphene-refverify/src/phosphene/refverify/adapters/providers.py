"""Provider adapters -- thin httpx clients behind the LookupClient port.

Each adapter: normalize the provider's JSON -> CandidateRecord. No logic
beyond mapping; scoring/verdicts are domain work. Politeness: contact
email parameter (Crossref/OpenAlex etiquette), bounded timeout, and an
optional cache in front. arXiv is a different beast (Atom XML, no DOI
by default) -- wired as its own adapter for the fallback chain.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Callable
from typing import Any, ClassVar

import httpx

from phosphene.refverify.adapters.cache import FileCache
from phosphene.refverify.domain.scoring import CandidateRecord

USER_AGENT = "refverify/0.1 (observatory-wiki; mailto:refverify@observatory.wiki)"


def _venue_name(item: dict[str, Any]) -> str:
    """Provider-agnostic venue extraction from an OpenAlex work record."""
    src = (item.get("primary_location") or {}).get("source") or {}
    return str(src.get("display_name") or "")


def _cache_key(provider: str, kind: str, **params: object) -> str:
    flat = "&".join(f"{k}={v}" for k, v in sorted(params.items()) if v is not None)
    return f"{provider}:{kind}:{flat}"


class _Cached:
    """Mixin: cache-first wrapper around raw fetch functions."""

    cache: FileCache | None

    def _cached_fetch(
        self,
        provider: str,
        kind: str,
        fetch: Callable[[], dict | None],
        **params: object,
    ) -> dict | None:
        key = _cache_key(provider, kind, **params)
        if self.cache is not None:
            hit = self.cache.get(key)
            if hit is not None:
                return hit
        result = fetch()
        if result is not None and self.cache is not None:
            self.cache.set(key, result)
        return result


class CrossrefClient(_Cached):
    """https://api.crossref.org -- works/{doi}, works?query.bibliographic."""

    name = "crossref"

    def __init__(
        self,
        client: httpx.Client | None = None,
        mailto: str = "refverify@observatory.wiki",
        cache: FileCache | None = None,
    ) -> None:
        self.client = client or httpx.Client(
            base_url="https://api.crossref.org",
            headers={"User-Agent": USER_AGENT},
            timeout=10.0,
        )
        self.mailto = mailto
        self.cache = cache

    def _normalize(self, item: dict) -> CandidateRecord:
        title = (item.get("title") or [""])[0]
        authors = tuple(
            f"{a.get('given', '')} {a.get('family', '')}".strip()
            for a in item.get("author", [])
        )
        parts = item.get("issued", {}).get("date-parts", [[]])
        year = parts[0][0] if parts and parts[0] else None
        return CandidateRecord(
            title=title,
            authors=authors,
            year=year,
            doi=item.get("DOI"),
            venue=(item.get("container-title") or [""])[0] or "",
            source=self.name,
        )

    def by_doi(self, doi: str) -> CandidateRecord | None:
        payload = self._cached_fetch(
            self.name,
            "doi",
            fetch=lambda: self._get(f"/works/{doi}"),
            doi=doi,
        )
        if payload is None:
            return None
        return self._normalize(payload["message"])

    def search(
        self, title: str, author: str | None = None, year: int | None = None
    ) -> list[CandidateRecord]:
        params: dict[str, str | int] = {"rows": 10, "query.bibliographic": title}
        if author:
            # surname only: full "Surname, Given" strings degrade Crossref ranking
            params["query.author"] = author.split(",")[0].strip()
        if year:
            params["filter"] = f"from-pub-date:{year},until-pub-date:{year}"
        payload = self._cached_fetch(
            self.name,
            "search",
            fetch=lambda: self._get("/works", params=params),
            title=title,
            author=author,
            year=year,
        )
        if payload is None:
            return []
        return [self._normalize(it) for it in payload["message"]["items"]]

    def _get(self, path: str, params: dict | None = None) -> dict | None:
        """GET wrapper. NOTE: params must carry the full query — httpx
        replaces (not merges) a URL's raw query string when params is set."""
        try:
            r = self.client.get(path, params={**(params or {}), "mailto": self.mailto})
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError:
            return None


class OpenAlexClient(_Cached):
    """https://api.openalex.org -- works/doi:{doi}, works?search="""

    name = "openalex"

    def __init__(
        self,
        client: httpx.Client | None = None,
        mailto: str = "refverify@observatory.wiki",
        cache: FileCache | None = None,
    ) -> None:
        self.client = client or httpx.Client(
            base_url="https://api.openalex.org",
            headers={"User-Agent": USER_AGENT},
            timeout=10.0,
        )
        self.mailto = mailto
        self.cache = cache

    def _normalize(self, item: dict) -> CandidateRecord:
        authors = tuple(
            a.get("author", {}).get("display_name", "")
            for a in item.get("authorships", [])
        )
        year = item.get("publication_year")
        doi = (item.get("doi") or "").removeprefix("https://doi.org/")
        return CandidateRecord(
            title=item.get("title") or "",
            authors=authors,
            year=year,
            doi=doi or None,
            venue=_venue_name(item),
            source=self.name,
        )

    def by_doi(self, doi: str) -> CandidateRecord | None:
        payload = self._cached_fetch(
            self.name,
            "doi",
            fetch=lambda: self._get(f"/works/doi:{doi}"),
            doi=doi,
        )
        if payload is None:
            return None
        rec = self._normalize(payload)
        rec.venue = (
            rec.venue.get("display_name", "") if isinstance(rec.venue, dict) else ""
        )
        return rec

    def search(
        self, title: str, author: str | None = None, year: int | None = None
    ) -> list[CandidateRecord]:
        params = {"search": title, "per-page": 5}
        if year:
            params["filter"] = f"publication_year:{year}"
        payload = self._cached_fetch(
            self.name,
            "search",
            fetch=lambda: self._get("/works", params=params),
            title=title,
            author=author,
            year=year,
        )
        if payload is None:
            return []
        return [self._normalize(it) for it in payload.get("results", [])]

    def _get(self, path: str, params: dict | None = None) -> dict | None:
        try:
            r = self.client.get(path, params={**(params or {}), "mailto": self.mailto})
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError:
            return None


class ArxivClient(_Cached):
    """http://export.arxiv.org/api/query -- Atom XML, id-based."""

    name = "arxiv"
    _NS: ClassVar[dict[str, str]] = {"a": "http://www.w3.org/2005/Atom"}

    def __init__(
        self, client: httpx.Client | None = None, cache: FileCache | None = None
    ) -> None:
        self.client = client or httpx.Client(
            base_url="https://export.arxiv.org",
            headers={"User-Agent": USER_AGENT},
            timeout=10.0,
        )
        self.cache = cache

    def _normalize(self, entry: ET.Element) -> tuple[CandidateRecord, str]:
        title = (entry.findtext("a:title", "", self._NS) or "").strip()
        authors = tuple(
            (e.text or "").strip() for e in entry.findall("a:author/a:name", self._NS)
        )
        published = entry.findtext("a:published", "", self._NS) or ""
        year = int(published[:4]) if published[:4].isdigit() else None
        raw_id = entry.findtext("a:id", "", self._NS) or ""
        arxiv_id = raw_id.rsplit("/abs/", 1)[-1]
        return CandidateRecord(
            title=title,
            authors=authors,
            year=year,
            doi=None,
            venue="arXiv",
            source=self.name,
        ), arxiv_id

    def by_doi(self, doi: str) -> CandidateRecord | None:
        return None  # arXiv has no DOI lookup; title search only

    def search(
        self, title: str, author: str | None = None, year: int | None = None
    ) -> list[CandidateRecord]:
        payload = self._cached_fetch(
            self.name,
            "search",
            fetch=lambda: self._get(title),
            title=title,
        )
        if payload is None:
            return []
        root = ET.fromstring(payload)
        return [self._normalize(e)[0] for e in root.findall("a:entry", self._NS)]

    def _get(self, title: str) -> str | None:
        try:
            r = self.client.get(
                "/api/query",
                params={"search_query": f'ti:"{title[:200]}"', "max_results": 5},
            )
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.text
        except httpx.HTTPError:
            return None


def default_chain(cache: FileCache | None = None) -> list:
    """Fallback order per editorial-pipeline#22: Crossref -> OpenAlex -> arXiv."""
    return [
        CrossrefClient(cache=cache),
        OpenAlexClient(cache=cache),
        ArxivClient(cache=cache),
    ]
