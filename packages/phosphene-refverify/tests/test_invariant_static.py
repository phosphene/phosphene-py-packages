"""Tests verifying InvariantStatic axiomatic contracts for domain models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from phosphene.refverify.domain.reference import Reference
from phosphene.refverify.domain.scoring import CandidateRecord
from phosphene.refverify.domain.verdict import Verdict, VerdictResult


def test_reference_invariant_static_contract():
    ref = Reference(text="Author (2020) Title", title="Title", year=2020)

    # Immutability
    with pytest.raises((ValidationError, TypeError)):
        ref.title = "Mutated"  # type: ignore[misc]

    # Schema integrity: rejects undefined fields
    with pytest.raises(ValidationError):
        Reference(text="Test", undefined_field="disallowed")  # type: ignore[call-arg]

    # Value object hashability
    ref_map = {ref: "stored"}
    assert ref_map[ref] == "stored"


def test_candidate_record_invariant_static_contract():
    cand = CandidateRecord(title="Canonical Title", source="crossref")

    # Immutability
    with pytest.raises((ValidationError, TypeError)):
        cand.title = "Mutated"  # type: ignore[misc]

    # Schema integrity: rejects undefined fields
    with pytest.raises(ValidationError):
        CandidateRecord(title="Title", extra_leak="disallowed")  # type: ignore[call-arg]


def test_verdict_result_invariant_static_contract():
    res = VerdictResult(verdict=Verdict.VERIFIED, score=98.5)

    # Immutability
    with pytest.raises((ValidationError, TypeError)):
        res.score = 50.0  # type: ignore[misc]

    # Schema integrity: rejects undefined fields
    with pytest.raises(ValidationError):
        VerdictResult(verdict=Verdict.VERIFIED, score=98.5, spurious=True)  # type: ignore[call-arg]
