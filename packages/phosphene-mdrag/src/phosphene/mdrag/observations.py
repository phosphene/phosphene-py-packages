"""observations.py — Structural characterisation lens over GenealogyResult.

Applies pattern recognition to extracted genealogy morphisms and produces
typed Observation objects that surface implicit intellectual structure.

Three patterns are detected:

1. **Epistemic structure** — classifies the builds-on chain by source type.
   All-external sources = observational hypothesis (first-generation synthesis
   from documentation). Mixed corpus/external = theoretical synthesis.

2. **Convergence breadth** — counts and characterises converges-with entries.
   Cross-disciplinary convergence is load-bearing evidence; the observation
   surfaces how many independent lines are converging.

3. **Departure orientation** — classifies departs-from entries as methodological
   (departing from *how* research is done) or substantive (departing from
   *what* other researchers found). These are different intellectual claims.

These are not gap detections — they are characterisations of what the
genealogy is already doing, made explicit for the researcher.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .genealogy import GenealogyResult, MorphismTarget


class ObservationType(str, Enum):
    """Enumeration of observation pattern categories.

    Attributes:
        EPISTEMIC_STRUCTURE: Classification of the builds-on chain.
        CONVERGENCE_BREADTH: Characterisation of converges-with entries.
        DEPARTURE_ORIENTATION: Classification of departs-from entries.
        RESPONDS_TO_ORIENTATION: Classification of responds-to entries.
    """

    EPISTEMIC_STRUCTURE = "epistemic_structure"
    CONVERGENCE_BREADTH = "convergence_breadth"
    DEPARTURE_ORIENTATION = "departure_orientation"
    RESPONDS_TO_ORIENTATION = "responds_to_orientation"


@dataclass(frozen=True)
class Observation:
    """A single structural observation about a document's genealogy.

    Attributes:
        obs_type: The pattern category this observation belongs to.
        value: The classification value (e.g. 'observational', 'methodological').
        evidence: Brief evidence list — the entries that triggered this observation.
        note: A prose note surfacing the intellectual significance.
    """

    obs_type: ObservationType
    value: str
    evidence: list[str]
    note: str

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict for index emission.

        Returns:
            Dict with obs_type, value, evidence, and note keys.
        """
        return {
            "type": self.obs_type.value,
            "value": self.value,
            "evidence": self.evidence,
            "note": self.note,
        }


@dataclass
class DocumentObservations:
    """All observations for a single document's genealogy.

    Attributes:
        source_uri: The document's corpus URI.
        observations: List of Observation objects produced by the lens.
    """

    source_uri: str
    observations: list[Observation] = field(default_factory=list)

    def has_content(self) -> bool:
        """Return True if any observations were produced.

        Returns:
            True if the observations list is non-empty.
        """
        return bool(self.observations)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict for index emission.

        Returns:
            Dict with source_uri and observations list.
        """
        return {
            "source_uri": self.source_uri,
            "observations": [o.to_dict() for o in self.observations],
        }


# ---------------------------------------------------------------------------
# Pattern detectors
# ---------------------------------------------------------------------------


def _classify_epistemic_structure(
    targets: list[MorphismTarget],
) -> tuple[str, str]:
    """Classify the epistemic structure of a builds-on chain.

    Args:
        targets: The builds-on morphism targets.

    Returns:
        Tuple of (value, note). Value is one of: 'observational',
        'synthetic', 'derivative'. Note is a prose characterisation.
    """
    if not targets:
        return "absent", "No builds-on sources recorded."

    resolved = [t for t in targets if t.resolved]
    external = [t for t in targets if not t.resolved]

    if not resolved:
        return (
            "observational",
            f"All {len(external)} builds-on sources are external documentation — "
            "no corpus URIs. This is a first-generation observational hypothesis: "
            "primary synthesis from existing scholarship, not building on prior "
            "corpus theory.",
        )
    if resolved and external:
        ratio = f"{len(resolved)} corpus / {len(external)} external"
        return (
            "synthetic",
            f"Builds-on chain is mixed ({ratio}): combines corpus theory with "
            "external scholarship. This is a theoretical synthesis — it extends "
            "existing corpus work while grounding in external documentation.",
        )
    return (
        "derivative",
        f"All {len(resolved)} builds-on sources are corpus URIs. "
        "This document is primarily derivative of existing corpus theory.",
    )


def _classify_convergence_breadth(
    targets: list[MorphismTarget],
) -> tuple[str, str]:
    """Classify the breadth and character of converges-with entries.

    Args:
        targets: The converges-with morphism targets.

    Returns:
        Tuple of (value, note).
    """
    if not targets:
        return "absent", "No converges-with entries recorded."

    count = len(targets)
    resolved_count = sum(1 for t in targets if t.resolved)

    if count == 1:
        t = targets[0]
        label = t.uri if t.resolved else t.raw_text.split(" — ")[0].strip()
        return (
            "focused",
            f"Single convergence with {label!r}. "
            "Focused alignment — one independent line of support.",
        )

    evidence = []
    for t in targets:
        label = t.uri if t.resolved else t.raw_text.split(" — ")[0].strip()
        evidence.append(label)

    note = (
        f"{count} independent convergences recorded"
        + (
            f" ({resolved_count} corpus, {count - resolved_count} external)"
            if resolved_count
            else ""
        )
        + ". Multi-line convergence is load-bearing: independent researchers "
        "reaching overlapping territory from different starting points "
        "strengthens the evidential case."
    )
    return "broad", note


def _classify_departure_orientation(
    targets: list[MorphismTarget],
) -> tuple[str, str]:
    """Classify departs-from entries as methodological or substantive.

    Methodological departures concern how research is done.
    Substantive departures concern what other researchers concluded.

    Args:
        targets: The departs-from morphism targets.

    Returns:
        Tuple of (value, note).
    """
    if not targets:
        return "absent", "No departs-from entries recorded."

    # Heuristic: methodological departure markers in the raw text
    method_markers = {
        "method",
        "methodolog",
        "framework",
        "approach",
        "paradigm",
        "protocol",
        "syntax",
        "sound correspondence",
        "universal grammar",
        "structur",
        "innate",
        "a priori",
    }
    substantive_markers = {
        "rejects",
        "refutes",
        "counter",
        "contrary",
        "opposed",
        "denies",
        "disagree",
        "wrong",
        "incorrect",
        "gene-centric",
        "determinist",
        "reducti",
    }

    method_count = 0
    substantive_count = 0
    evidence = []

    for t in targets:
        raw = t.raw_text.lower()
        label = t.raw_text.split(" — ")[0].strip()
        evidence.append(label)
        if any(m in raw for m in method_markers):
            method_count += 1
        elif any(m in raw for m in substantive_markers):
            substantive_count += 1

    if method_count > 0 and substantive_count == 0:
        return (
            "methodological",
            f"All {len(targets)} departs-from entries concern methodology, not conclusions. "
            "This is a research contribution at the level of method — establishing "
            "a new way of approaching the problem, not merely disagreeing with answers.",
        )
    if substantive_count > 0 and method_count == 0:
        return (
            "substantive",
            f"All {len(targets)} departs-from entries concern other researchers' conclusions. "
            "This positions the work against specific empirical or theoretical claims.",
        )
    if method_count > 0 and substantive_count > 0:
        return (
            "mixed",
            f"Departs-from entries span both methodology ({method_count}) and "
            f"substantive conclusions ({substantive_count}). "
            "The research is staking out both a methodological and an empirical position.",
        )
    return (
        "uncategorised",
        f"{len(targets)} departs-from entries recorded. "
        "Orientation could not be automatically classified — review for context.",
    )


def _classify_responds_to(
    targets: list[MorphismTarget],
) -> tuple[str, str]:
    """Classify responds-to entries as practical, theoretical, or interpretive.

    Args:
        targets: The responds-to morphism targets.

    Returns:
        Tuple of (value, note).
    """
    if not targets:
        return "absent", "No responds-to entries recorded."

    practical_markers = {
        "resource",
        "constraint",
        "cost",
        "budget",
        "practical",
        "demand",
        "gap",
        "challenge",
        "problem",
        "scale",
    }
    interpretive_markers = {
        "misread",
        "misinterpret",
        "misconception",
        "narrative",
        "myth",
        "public",
        "popular",
        "correcting",
    }

    practical_count = 0
    interpretive_count = 0
    evidence = []

    for t in targets:
        raw = t.raw_text.lower()
        label = t.raw_text.split(" — ")[0].strip()[:60]
        evidence.append(label)
        if any(m in raw for m in practical_markers):
            practical_count += 1
        elif any(m in raw for m in interpretive_markers):
            interpretive_count += 1

    if practical_count > 0 and interpretive_count == 0:
        return (
            "practical",
            f"Responds to a practical challenge ({practical_count} entries). "
            "The research is positioned as a solution to a resource or methodological "
            "constraint, not primarily as a theoretical response.",
        )
    if interpretive_count > 0:
        return (
            "interpretive",
            f"Responds to misreadings or public misconceptions ({interpretive_count} entries). "
            "Corrective positioning — establishing what the research does and does not claim.",
        )
    return (
        "theoretical",
        f"{len(targets)} responds-to entries recorded. "
        "Responds to theoretical challenges or open questions in the field.",
    )


# ---------------------------------------------------------------------------
# Main lens
# ---------------------------------------------------------------------------


class ObservationsLens:
    """Applies structural characterisation patterns to a GenealogyResult.

    Produces DocumentObservations containing typed Observation objects.
    These are characterisations of what the genealogy is already doing —
    not gap detections.
    """

    def observe(self, result: GenealogyResult) -> DocumentObservations:
        """Apply all pattern detectors to a GenealogyResult.

        Args:
            result: Extracted genealogy morphisms for one document.

        Returns:
            DocumentObservations with all detected patterns.
        """
        doc_obs = DocumentObservations(source_uri=result.source_uri)

        builds_on = result.forward.get("builds-on", [])
        converges_with = result.forward.get("converges-with", [])
        departs_from = result.forward.get("departs-from", [])
        responds_to = result.forward.get("responds-to", [])

        # Epistemic structure
        if builds_on:
            value, note = _classify_epistemic_structure(builds_on)
            evidence = [t.raw_text.split(" — ")[0].strip()[:50] for t in builds_on]
            doc_obs.observations.append(
                Observation(
                    obs_type=ObservationType.EPISTEMIC_STRUCTURE,
                    value=value,
                    evidence=evidence,
                    note=note,
                )
            )

        # Convergence breadth
        if converges_with:
            value, note = _classify_convergence_breadth(converges_with)
            evidence = [
                (t.uri if t.resolved else t.raw_text.split(" — ")[0].strip()[:50])
                for t in converges_with
            ]
            doc_obs.observations.append(
                Observation(
                    obs_type=ObservationType.CONVERGENCE_BREADTH,
                    value=value,
                    evidence=evidence,
                    note=note,
                )
            )

        # Departure orientation
        if departs_from:
            value, note = _classify_departure_orientation(departs_from)
            evidence = [t.raw_text.split(" — ")[0].strip()[:50] for t in departs_from]
            doc_obs.observations.append(
                Observation(
                    obs_type=ObservationType.DEPARTURE_ORIENTATION,
                    value=value,
                    evidence=evidence,
                    note=note,
                )
            )

        # Responds-to orientation
        if responds_to:
            valid = [
                t for t in responds_to if t.raw_text and t.raw_text not in {"[", "]"}
            ]
            if valid:
                value, note = _classify_responds_to(valid)
                evidence = [t.raw_text.split(" — ")[0].strip()[:60] for t in valid]
                doc_obs.observations.append(
                    Observation(
                        obs_type=ObservationType.RESPONDS_TO_ORIENTATION,
                        value=value,
                        evidence=evidence,
                        note=note,
                    )
                )

        return doc_obs
