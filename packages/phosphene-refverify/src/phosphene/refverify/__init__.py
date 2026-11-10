"""phosphene-refverify -- reference-verification quality-control gate.

Pure domain (Reference, Verdict, scoring, deduplication, verification)
paired with provider protocol ports (LookupClient) and network adapters.
"""

from __future__ import annotations

from phosphene.refverify.domain.reference import Reference
from phosphene.refverify.domain.verdict import Verdict, VerdictResult
from phosphene.refverify.domain.verify import gate_decision, verify_all, verify_one
from phosphene.refverify.ports.lookup import CandidateRecord, LookupClient

__all__ = [
    "CandidateRecord",
    "LookupClient",
    "Reference",
    "Verdict",
    "VerdictResult",
    "gate_decision",
    "verify_all",
    "verify_one",
]
