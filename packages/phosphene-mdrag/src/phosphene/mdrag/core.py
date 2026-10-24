"""Axiomatic Model Vitals — State & Schema Control abstractions.

This module defines the project's four Pydantic Operational Modes, providing
a formal vocabulary for reasoning about model state (vitality) and schema
rigidity (extra keys).

Modes:
- InvariantStatic: Fixed-width, read-only record (Axioms).
- InvariantDynamic: Read-only snapshot of arbitrary data (OWA Ingestion).
- MutableStatic: Controlled state machine (State management).
- MutableDynamic: Flexible, type-aware dictionary (Bridges/Prototypes).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class InvariantStatic(BaseModel):
    """A fixed-width, read-only record.

    Rigid adherence to defined types and prevents all modifications
    post-creation. High-integrity mode for system definitions.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")


class InvariantDynamic(BaseModel):
    """A read-only snapshot of arbitrary data.

    Accepts any provided keys during initialization and locks them against
    mutation. FKA-compliant mode for ingestion and discovery.
    """

    model_config = ConfigDict(frozen=True, extra="allow")


class MutableStatic(BaseModel):
    """A controlled state machine.

    Strictly enforces defined schema but allows updating specific fields
    throughout the object's lifecycle.
    """

    model_config = ConfigDict(frozen=False, extra="forbid")


class MutableDynamic(BaseModel):
    """A flexible, type-aware dictionary.

    Accepts any input and allows unrestricted updates to defined and
    arbitrary attributes.
    """

    model_config = ConfigDict(frozen=False, extra="allow")
