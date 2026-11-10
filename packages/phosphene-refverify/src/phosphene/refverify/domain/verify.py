"""Verification orchestration -- pure.

verify_one: a Reference + ordered provider ports -> VerdictResult.
verify_all: whole bibliography + duplicate pass.
gate_decision: verdicts -> pass / warn / block publication decisions.

No network, no clock, no I/O. Concurrency lives in the CLI layer.
"""

from __future__ import annotations

from collections.abc import Sequence

from phosphene.refverify.domain.dedup import find_duplicates
from phosphene.refverify.domain.reference import Reference
from phosphene.refverify.domain.scoring import (
    LOW_CONFIDENCE_LOW,
    VERIFIED_HIGH,
    CandidateRecord,
    best_candidate,
    score_match,
    title_similarity,
)
from phosphene.refverify.domain.verdict import Verdict, VerdictResult
from phosphene.refverify.ports.lookup import LookupClient

_STRONG_TITLE_AGREEMENT = 0.8  # DOI-path metadata agreement bar


def verify_one(ref: Reference, clients: Sequence[LookupClient]) -> VerdictResult:
    """Check one reference against the provider ports, in fallback order.

    Identifier path first (DOI -> by_doi per client). If the DOI resolves,
    metadata agreement decides: agree -> verified; disagree ->
    metadata_mismatch (score still reported). If the DOI resolves nowhere
    or no DOI was cited, fall back to title search across clients.
    """
    fallback_note = ""
    if ref.doi:
        for client in clients:
            cand = client.by_doi(ref.doi)
            if cand is None:
                continue
            score, reasons = score_match(ref, cand)
            if _metadata_agrees(ref, cand):
                return VerdictResult(
                    verdict=Verdict.VERIFIED,
                    score=score,
                    reasons=tuple(reasons),
                    matched_title=cand.title,
                    matched_doi=cand.doi,
                    matched_source=client.name,
                )
            return VerdictResult(
                verdict=Verdict.METADATA_MISMATCH,
                score=score,
                reasons=tuple(reasons),
                matched_title=cand.title,
                matched_doi=cand.doi,
                matched_source=client.name,
            )
        # DOI resolves nowhere -> try title search; the DOI may be mistyped.
        fallback_note = f"doi_unresolved({ref.doi})"

    return _verify_by_title_search(ref, clients, fallback_note)


def _verify_by_title_search(
    ref: Reference, clients: Sequence[LookupClient], fallback_note: str
) -> VerdictResult:
    """Title-search fallback across all clients (no identifier or dead DOI)."""
    # query with the parsed work title — the full entry line (authors, venue,
    # pages) pollutes bibliographic search and costs ranking quality
    query_title = ref.title or ref.text
    gathered: list[CandidateRecord] = []
    for client in clients:
        author = ref.authors[0] if ref.authors else None
        gathered.extend(client.search(query_title, author, ref.year))

    if not gathered:
        reasons = (fallback_note,) if fallback_note else ()
        return VerdictResult(verdict=Verdict.NOT_FOUND, score=0.0, reasons=reasons)

    cand, score, reasons = best_candidate(ref, gathered)
    assert cand is not None
    if score >= VERIFIED_HIGH:
        verdict = _search_match_verdict(ref, cand, reasons)
    elif score >= LOW_CONFIDENCE_LOW:
        verdict = Verdict.LOW_CONFIDENCE
    else:
        verdict = Verdict.NOT_FOUND
    if fallback_note:
        reasons.insert(0, fallback_note)
    return VerdictResult(
        verdict=verdict,
        score=score,
        reasons=tuple(reasons),
        matched_title=cand.title,
        matched_doi=cand.doi,
        matched_source=cand.source,
    )


def _search_match_verdict(
    ref: Reference, cand: CandidateRecord, reasons: list[str]
) -> Verdict:
    """Verdict for a strong title-search hit.

    Both sides carry DOIs and they disagree -> verified-secondary with a
    flag (matched by title, different DOI). Cited DOI + resolved DOI in
    agreement -> verified. No DOI on one side -> verified-secondary.
    """
    if ref.doi and cand.doi:
        if ref.doi.lower() == cand.doi.lower():
            return Verdict.VERIFIED
        reasons.append(f"doi_disagrees(cited={ref.doi}, found={cand.doi})")
    return Verdict.VERIFIED_SECONDARY


def _metadata_agrees(ref: Reference, cand: CandidateRecord) -> bool:
    """Does the resolved record's metadata agree with the citation?

    Agreement = title similarity >= 0.8 AND no hard year contradiction
    (missing years are neutral; a gap > 1 year is a mismatch signal but
    alone not fatal when the title matches strongly).
    """
    cited_title = ref.title or ref.text
    if title_similarity(cited_title, cand.title) < _STRONG_TITLE_AGREEMENT:
        return False
    return not (ref.year and cand.year and abs(ref.year - cand.year) > 1)


def verify_all(
    refs: Sequence[Reference], clients: Sequence[LookupClient]
) -> list[VerdictResult]:
    """Verify every reference, then apply the duplicate pass.

    Duplicated entries (same work cited twice) get Verdict.DUPLICATE
    while the first occurrence keeps its own verdict.
    """
    results = [verify_one(r, clients) for r in refs]
    dupes = find_duplicates(list(refs))
    if not dupes:
        return results
    out = list(results)
    for idx, first in dupes.items():
        out[idx] = VerdictResult(
            verdict=Verdict.DUPLICATE,
            score=results[idx].score,
            reasons=(f"duplicate_of_entry_{first + 1}",),
        )
    return out


def gate_decision(verdicts: Sequence[Verdict]) -> str:
    """Publish-gate mapping.

    block  -- any metadata_mismatch, not_found, or duplicate
    warn   -- only low_confidence / verified-secondary remain
    pass   -- everything verified
    """
    v = set(verdicts)
    if v & {Verdict.METADATA_MISMATCH, Verdict.NOT_FOUND, Verdict.DUPLICATE}:
        return "block"
    if v & {Verdict.LOW_CONFIDENCE}:
        return "warn"
    return "pass"
