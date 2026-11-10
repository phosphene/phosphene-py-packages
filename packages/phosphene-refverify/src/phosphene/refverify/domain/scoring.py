"""Pure matching scorer: citation ↔ candidate provider record.

Thresholds and semantics live HERE, once (singular place of reason):

  score >= VERIFIED_HIGH        -> confident match
  LOW_CONFIDENCE_LOW <= s < VERIFIED_HIGH -> borderline
  score < LOW_CONFIDENCE_LOW    -> no real match

Score components (0-100 weighted): title similarity (60), author surname
overlap (25), year agreement (15). Uses difflib (stdlib) -- zero deps; if
integration runs prove the pure scorer insufficient, upgrade is a
deliberate package change, not a vendored shortcut.
"""

from __future__ import annotations

from phosphene.core.models import InvariantStatic
from difflib import SequenceMatcher

from phosphene.refverify.domain.reference import Reference, normalize_title

VERIFIED_HIGH = 85.0
LOW_CONFIDENCE_LOW = 65.0

_WEIGHT_TITLE = 60.0
_WEIGHT_AUTHOR = 25.0
_WEIGHT_YEAR = 15.0


class CandidateRecord(InvariantStatic):
    """Normalized provider record -- what the port returns."""

    title: str
    authors: tuple[str, ...] = ()
    year: int | None = None
    doi: str | None = None
    venue: str = ""
    source: str = ""  # provider name, e.g. "crossref"


def _author_tokens(names: tuple[str, ...]) -> set[str]:
    """Author token set for overlap scoring.

    Fuzzy by design (weight 25/100): every multi-character token of every
    name is a candidate -- initials (single letters) are dropped so
    ``Gary M. Feinman`` and ``Feinman, Gary M.`` tokenize identically.
    Given-name tokens stay in the set; title weight (60) plus threshold
    placement keep the false-match risk bounded.
    """
    out: set[str] = set()
    for n in names:
        for tok in n.replace(".", "").replace(",", " ").split():
            if len(tok) > 1:
                out.add(tok.lower())
    return out


def title_similarity(a: str, b: str) -> float:
    """0-1 SequenceMatcher on normalized titles (token-order sensitive)."""
    na, nb = normalize_title(a), normalize_title(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def author_token_overlap(
    ref_authors: tuple[str, ...], cand_authors: tuple[str, ...]
) -> float:
    """0-1 overlap of author token sets (0 when either side is empty)."""
    ra, ca = _author_tokens(ref_authors), _author_tokens(cand_authors)
    if not ra or not ca:
        return 0.0
    return len(ra & ca) / len(ra | ca)


def _ref_title(ref: Reference) -> str:
    """Scoring input: parsed work title, falling back to the full line."""
    return ref.title or ref.text


def score_match(ref: Reference, cand: CandidateRecord) -> tuple[float, list[str]]:
    """Score a citation against a candidate; returns (score 0-100, reasons)."""
    reasons: list[str] = []

    t_sim = title_similarity(_ref_title(ref), cand.title)
    reasons.append(f"title_similarity={t_sim:.2f}")

    if not _author_tokens(ref.authors) or not _author_tokens(cand.authors):
        a_sim = 0.0
        if ref.authors and cand.authors:
            reasons.append("authors_present_no_overlap=0.00")
    else:
        a_sim = author_token_overlap(ref.authors, cand.authors)
        reasons.append(f"author_token_overlap={a_sim:.2f}")

    if ref.year is None or cand.year is None:
        y_sim = 0.0
        reasons.append("year_missing")
    elif ref.year == cand.year:
        y_sim = 1.0
    elif abs(ref.year - cand.year) == 1:
        y_sim = 0.5
        reasons.append(f"year_off_by_one({ref.year} vs {cand.year})")
    else:
        y_sim = 0.0
        reasons.append(f"year_mismatch({ref.year} vs {cand.year})")

    score = _WEIGHT_TITLE * t_sim + _WEIGHT_AUTHOR * a_sim + _WEIGHT_YEAR * y_sim
    return round(score, 1), reasons


def best_candidate(
    ref: Reference, candidates: list[CandidateRecord]
) -> tuple[CandidateRecord | None, float, list[str]]:
    """Highest-scoring candidate (ties -> earliest). None when list empty."""
    best: CandidateRecord | None = None
    best_score = -1.0
    best_reasons: list[str] = []
    for cand in candidates:
        score, reasons = score_match(ref, cand)
        if score > best_score:
            best, best_score, best_reasons = cand, score, reasons
    return best, max(best_score, 0.0), best_reasons
