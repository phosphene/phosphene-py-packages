"""Reference value object — pure, parsing-agnostic.

A Reference is what the citation *claims*: the fields as they appear in
the article's Bibliography field. Normalization happens here; parsing
(wikitext, bibtex, anything) happens in adapters and feeds this.

House format (wiki-content/articles):
    Authors. (Year) [https://url Title]. ''Venue'' vol(issue): pages.
Parsing contract:
  - title  = wiki-link text when present; else the span after "(Year) "
    up to the first sentence break; else the whole cleaned line
  - authors = everything before "(Year)", split on ", and " / " and "
    (surname-first chunks keep their pre-comma surname; given-first
    chunks keep the last token)
  - doi/arxiv_id/url extracted by regex from the raw line
"""

from __future__ import annotations

import re
from phosphene.core.models import InvariantStatic

_DOI_RE = re.compile(r"\b(10\.\d{4,9}/[^\s,;\"']+)", re.IGNORECASE)
_YEAR_PAREN_RE = re.compile(r"\((\d{4})\)")
_YEAR_RE = re.compile(r"\b(1[5-9]\d{2}|20\d{2})\b")
_ARXIV_RE = re.compile(r"\b(\d{4}\.\d{4,5})(?:v\d+)?\b")
_WIKI_LINK_RE = re.compile(r"\[https?://\S+\s+([^\]]+)\]")
_WIKI_URL_RE = re.compile(r"\[(https?://\S+)(?:\s+[^\]]*)?\]")
_ITALIC_RE = re.compile(r"''(.+?)''")
_BOLD_RE = re.compile(r"'{3}(.+?)'{3}")
_AUTHOR_SPLIT_RE = re.compile(r",?\s+and\s+|\s+and\s+", re.IGNORECASE)


class Reference(InvariantStatic):
    """One bibliography entry, normalized. Empty string = absent.

    text  -- full cleaned entry line (display + dedup fallback)
    title -- best-effort work title (scoring input); "" when unparseable
    """

    text: str
    title: str = ""
    authors: tuple[str, ...] = ()
    year: int | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    url: str | None = None

    @property
    def has_identifier(self) -> bool:
        return self.doi is not None or self.arxiv_id is not None

    def key(self) -> str:
        """Stable identity for dedup + cache keys: doi, else normalized title."""
        if self.doi:
            return f"doi:{self.doi.lower()}"
        return f"title:{normalize_title(self.title or self.text)}"


def normalize_title(title: str) -> str:
    """Lowercase, strip wiki markup/punctuation, collapse whitespace."""
    t = title
    t = _WIKI_LINK_RE.sub(r"\1", t)
    t = _WIKI_URL_RE.sub("", t)
    t = t.replace("''", "'")  # bold/italic quote runs -> single quote
    t = t.lower()
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def clean_wikitext(raw: str) -> str:
    """Strip wiki markup from a bibliography entry line.

    ``[url Text]`` keeps the link text; bare ``[url]`` is dropped;
    ''italic'' and '''bold''' markers removed.
    """
    t = _WIKI_LINK_RE.sub(r"\1", raw)
    t = _WIKI_URL_RE.sub("", t)
    t = _BOLD_RE.sub(r"\1", t)
    t = _ITALIC_RE.sub(r"\1", t)
    return t.strip()


def _extract_title(cleaned: str, link_title: str | None) -> str:
    """Best-effort title from a cleaned bibliography line."""
    if link_title:
        return link_title.strip()
    m = _YEAR_PAREN_RE.search(cleaned)
    if m:
        after = cleaned[m.end() :].lstrip(" ")
        # title runs to the first sentence break (". " / ".:''" patterns)
        stop = re.search(r"\.\s", after)
        title = after[: stop.start()] if stop else after
        return title.strip().strip(".").strip()
    return ""


def _extract_authors(cleaned: str) -> tuple[str, ...]:
    """Authors from the pre-year head of the entry."""
    m = _YEAR_PAREN_RE.search(cleaned)
    head = cleaned[: m.start()] if m else cleaned.split(". ")[0]
    head = head.strip().strip(".").strip()
    if not head:
        return ()
    chunks = [c.strip().strip(".").strip() for c in _AUTHOR_SPLIT_RE.split(head)]
    return tuple(c for c in chunks if c)


def from_wikitext_entry(raw: str) -> Reference:
    """One Bibliography-field line -> normalized Reference."""
    cleaned = clean_wikitext(raw)
    url_m = _WIKI_URL_RE.search(raw)
    doi_m = _DOI_RE.search(raw)
    arxiv_m = _ARXIV_RE.search(raw)

    paren_m = _YEAR_PAREN_RE.search(cleaned)
    year_m = _YEAR_RE.search(cleaned)
    # prefer the parenthesized year (page numbers / edition years exist too)
    year = (
        int(paren_m.group(1)) if paren_m else (int(year_m.group(1)) if year_m else None)
    )

    link_m = _WIKI_LINK_RE.search(raw)
    return Reference(
        text=cleaned,
        title=_extract_title(cleaned, link_m.group(1) if link_m else None),
        authors=_extract_authors(cleaned),
        year=year,
        doi=doi_m.group(1) if doi_m else None,
        arxiv_id=arxiv_m.group(1) if arxiv_m else None,
        url=url_m.group(1) if url_m else None,
    )


def parse_bibliography_wikitext(bibliography: str) -> list[Reference]:
    """The ``|Bibliography=`` field -> list of References.

    Entries are newline-separated; blank lines are separators, not entries.
    """
    entries = [line.strip() for line in bibliography.splitlines() if line.strip()]
    return [from_wikitext_entry(e) for e in entries]
