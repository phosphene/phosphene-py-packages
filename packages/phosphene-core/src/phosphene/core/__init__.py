"""Phosphene Core — shared foundation for the Phosphene ecosystem.

This package provides the fundamental building blocks used across all
Phosphene packages: base model classes, shared protocols, and common
type definitions. It has minimal dependencies (only Pydantic) to ensure
it can be imported by any Phosphene package without circular dependencies.

The core philosophical principle is mode-based modeling: the choice between
Static/Dynamic and Invariant/Mutable is an architectural decision that
affects correctness, not just convenience.

Exported Classes:
    InvariantStatic: Fixed-width, read-only record (Axioms)
    InvariantDynamic: Read-only snapshot of arbitrary data (OWA Ingestion)
    MutableStatic: Controlled state machine (State management)
    MutableDynamic: Flexible, type-aware dictionary (Bridges/Prototypes)
"""

from .models import InvariantDynamic, InvariantStatic, MutableDynamic, MutableStatic

__all__ = [
    "InvariantStatic",
    "InvariantDynamic",
    "MutableStatic",
    "MutableDynamic",
]

__version__ = "0.1.0"
