"""Pure-domain tests: scoring, verdicts, dedup, gate. Zero network."""

from __future__ import annotations

from phosphene.refverify.domain.dedup import find_duplicates
from phosphene.refverify.domain.reference import (
    Reference,
    parse_bibliography_wikitext,
)
from phosphene.refverify.domain.scoring import (
    CandidateRecord,
    score_match,
    title_similarity,
)
from phosphene.refverify.domain.verdict import Verdict
from phosphene.refverify.domain.verify import gate_decision, verify_all, verify_one
from tests.fakes import PAPER, FakeClient

# --- wikitext adapter ---------------------------------------------------

BIB = """Feinman, Gary M., and David M. Carballo. (2018) [https://www.example.org/pub/1 Collaborative and Competitive Strategies in the Variability and Resiliency of Large-Scale Societies in Mesoamerica]. ''Economic Anthropology'' 5(1): 7-19.
Powers, Simon T. (2020) [https://doi.org/10.3389/fpos.2020.568704 The Evolution of Social Complexity]. ''Frontiers in Political Science''."""


def test_parse_bibliography_yields_references() -> None:
    refs = parse_bibliography_wikitext(BIB)
    assert len(refs) == 2
    assert refs[0].year == 2018
    assert refs[0].authors[0].startswith("Feinman")


def test_parse_extracts_doi_and_strips_markup() -> None:
    refs = parse_bibliography_wikitext(BIB)
    assert refs[1].doi == "10.3389/fpos.2020.568704"
    # no wiki markup survives
    for r in refs:
        assert "''" not in r.text
        assert "[https" not in r.text
        assert "]" not in r.text


def test_parse_link_text_kept_url_dropped() -> None:
    refs = parse_bibliography_wikitext(BIB)
    assert "Collaborative and Competitive" in refs[0].text
    assert "https://www.example.org" not in refs[0].text
    assert refs[0].url == "https://www.example.org/pub/1"


# --- scoring ------------------------------------------------------------


def test_title_similarity_identical_is_one() -> None:
    assert title_similarity(PAPER.title, PAPER.title) == 1.0


def test_score_match_strong() -> None:
    ref = Reference(
        text=PAPER.title,
        authors=("Gary M. Feinman", "David M. Carballo"),
        year=2018,
        doi="10.1111/eano.12110",
    )
    score, reasons = score_match(ref, PAPER)
    assert score >= 85.0
    assert any("author_token_overlap=1.00" in r for r in reasons)


def test_score_match_year_mismatch_penalized() -> None:
    ref = Reference(text=PAPER.title, authors=("Feinman",), year=2019)
    base_ref = Reference(text=PAPER.title, authors=("Feinman",), year=2018)
    s_base, _ = score_match(base_ref, PAPER)
    s_off, _ = score_match(ref, PAPER)
    assert s_off < s_base


# --- verify_one ---------------------------------------------------------


def test_doi_resolves_metadata_matches() -> None:
    ref = Reference(text=PAPER.title, authors=("Feinman",), year=2018, doi=PAPER.doi)
    client = FakeClient("crossref", by_doi_map={PAPER.doi: PAPER})
    result = verify_one(ref, [client])
    assert result.verdict is Verdict.VERIFIED
    assert result.matched_doi == PAPER.doi
    assert result.matched_source == "crossref"


def test_doi_resolves_but_title_differs() -> None:
    wrong = CandidateRecord(
        title="An Entirely Different Book About Something Else",
        authors=("Someone Else",),
        year=2015,
        doi="10.1111/eano.12110",
        source="crossref",
    )
    ref = Reference(text=PAPER.title, authors=("Feinman",), year=2018, doi=PAPER.doi)
    client = FakeClient("crossref", by_doi_map={PAPER.doi: wrong})
    result = verify_one(ref, [client])
    assert result.verdict is Verdict.METADATA_MISMATCH


def test_no_doi_strong_title_match() -> None:
    ref = Reference(
        text=PAPER.title,
        authors=("Gary M. Feinman", "David M. Carballo"),
        year=2018,
    )
    client = FakeClient("openalex", search_results=[PAPER])
    result = verify_one(ref, [client])
    assert result.verdict is Verdict.VERIFIED_SECONDARY


def test_nothing_matches_anywhere() -> None:
    ref = Reference(
        text="A Title Never Published Anywhere At All", authors=("Nobody",), year=1901
    )
    c1 = FakeClient("crossref", search_results=[])
    c2 = FakeClient("openalex", search_results=[])
    result = verify_one(ref, [c1, c2])
    assert result.verdict is Verdict.NOT_FOUND


def test_borderline_score_is_low_confidence() -> None:
    # title matches exactly, year corroborates, but NO author signal on
    # either side → 60 + 15 = 75 ∈ [65, 85) → low confidence, unconfirmed
    partial = CandidateRecord(
        title=PAPER.title, authors=(), year=2018, source="crossref"
    )
    ref = Reference(text=PAPER.title, authors=(), year=2018)
    client = FakeClient("crossref", search_results=[partial])
    result = verify_one(ref, [client])
    assert result.verdict is Verdict.LOW_CONFIDENCE


def test_fallback_chain_skips_empty_clients() -> None:
    ref = Reference(
        text=PAPER.title,
        authors=("Gary M. Feinman", "David M. Carballo"),
        year=2018,
    )
    empty = FakeClient("crossref", by_doi_map={}, search_results=[])
    hit = FakeClient("openalex", search_results=[PAPER])
    result = verify_one(ref, [empty, hit])
    assert result.verdict is Verdict.VERIFIED_SECONDARY
    assert empty.search_calls and hit.search_calls


# --- dedup --------------------------------------------------------------


def test_same_doi_cited_twice_flagged() -> None:
    r1 = Reference(text=PAPER.title, doi=PAPER.doi)
    r2 = Reference(text=PAPER.title + ".", doi=PAPER.doi)
    dupes = find_duplicates([r1, r2])
    assert dupes == {1: 0}


def test_no_duplicates_passes_clean() -> None:
    refs = parse_bibliography_wikitext(BIB)
    assert find_duplicates(refs) == {}


# --- verify_all + gate --------------------------------------------------


def test_verify_all_marks_duplicate_entry() -> None:
    refs = [
        Reference(text=PAPER.title, doi=PAPER.doi, year=2018),
        Reference(text=PAPER.title, doi=PAPER.doi, year=2018),
    ]
    client = FakeClient("crossref", by_doi_map={PAPER.doi: PAPER})
    results = verify_all(refs, [client])
    assert results[0].verdict is Verdict.VERIFIED
    assert results[1].verdict is Verdict.DUPLICATE
    assert results[1].reasons == ("duplicate_of_entry_1",)


def test_gate_blocks_on_mismatch() -> None:
    assert gate_decision([Verdict.METADATA_MISMATCH]) == "block"
    assert gate_decision([Verdict.VERIFIED, Verdict.NOT_FOUND]) == "block"
    assert gate_decision([Verdict.VERIFIED, Verdict.DUPLICATE]) == "block"


def test_gate_warns_on_low_confidence_only() -> None:
    assert gate_decision([Verdict.LOW_CONFIDENCE]) == "warn"
    assert gate_decision([Verdict.VERIFIED, Verdict.LOW_CONFIDENCE]) == "warn"


def test_gate_passes_all_verified() -> None:
    assert gate_decision([Verdict.VERIFIED]) == "pass"
    assert gate_decision([Verdict.VERIFIED, Verdict.VERIFIED_SECONDARY]) == "pass"


def test_gate_empty_is_pass() -> None:
    assert gate_decision([]) == "pass"


# --- fixture recorded payload contract (adapter smoke, offline) ---------


def test_crossref_normalization_shape() -> None:
    from phosphene.refverify.adapters.providers import CrossrefClient

    item = {
        "title": ["The Evolution of Social Complexity"],
        "author": [{"given": "Simon T.", "family": "Powers"}],
        "issued": {"date-parts": [[2020]]},
        "DOI": "10.3389/fpos.2020.568704",
        "container-title": ["Frontiers in Political Science"],
    }
    rec = CrossrefClient.__new__(CrossrefClient)  # normalize is instance-pure
    rec.name = "crossref"
    out = rec._normalize(item)
    assert out.title == "The Evolution of Social Complexity"
    assert out.authors == ("Simon T. Powers",)
    assert out.year == 2020
    assert out.doi == "10.3389/fpos.2020.568704"
    assert out.source == "crossref"


# --- title/author extraction (house format) -----------------------------


def test_wiki_link_text_is_title() -> None:
    refs = parse_bibliography_wikitext(BIB)
    assert refs[0].title == (
        "Collaborative and Competitive Strategies in the Variability "
        "and Resiliency of Large-Scale Societies in Mesoamerica"
    )


def test_no_link_title_from_post_year_span() -> None:
    ref = parse_bibliography_wikitext(
        "Powers, Simon T. (2020) The Evolution of Social Complexity. ''Frontiers'' 2: 5."
    )[0]
    assert ref.title == "The Evolution of Social Complexity"


def test_authors_survive_initials() -> None:
    refs = parse_bibliography_wikitext(BIB)
    toks = {
        t.lower().strip(",.")
        for a in refs[0].authors
        for t in a.replace(".", "").split()
        if len(t.strip(",.")) > 1
    }
    assert {"feinman", "gary", "david", "carballo"} <= toks


def test_paren_year_preferred_over_stray_year() -> None:
    # a stray page-year must not win over the parenthesized pub year
    ref = parse_bibliography_wikitext(
        "Doe, J. (1999) A Study. ''Journal of X'' 5(1): 7-2001."
    )[0]
    assert ref.year == 1999
