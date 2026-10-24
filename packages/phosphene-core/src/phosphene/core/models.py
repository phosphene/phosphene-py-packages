"""Phosphene Core Models — shared foundation classes for the Phosphene ecosystem.

This module provides the four canonical Pydantic operational modes that form
the foundation for all structured data modeling across Phosphene packages.
These base classes embody the fundamental distinction between Static (controlled
schema) and Dynamic (open-world ingestion), crossed with Invariant (immutable)
and Mutable (state-machine) semantics.

The mode selection is an architectural decision that affects correctness,
not just convenience. Static modes prevent unknown-field errors from becoming
information loss or schema rot. Invariant modes prevent accidental mutation
of logical records. The combinations address the four fundamental data patterns
in scientific computing systems.

Base Classes:
    InvariantStatic: Fixed-width, read-only record (Axioms).
    InvariantDynamic: Read-only snapshot of arbitrary data (OWA Ingestion).
    MutableStatic: Controlled state machine (State management).
    MutableDynamic: Flexible, type-aware dictionary (Bridges/Prototypes).

The distinction between Static (extra='forbid') and Dynamic (extra='allow')
is the critical one: Static means you control the schema and unknown fields
are errors. Dynamic means you're ingesting data from the open world and
unknown fields are information. Conflating them causes either information
loss (ignoring extras in static mode) or schema rot (allowing extras in
what should be a fixed schema).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class InvariantStatic(BaseModel):
    """A fixed-width, read-only record.

    Rigid adherence to defined types and prevents all modifications
    post-creation. High-integrity mode for system definitions.
    Rejects unknown keys — extra='forbid'.

    Use this mode for:
    - Axioms and formal definitions where schema drift is an error
    - System configuration that should never accept undefined fields
    - Value objects representing logical propositions or mathematical structures
    - API contracts where unknown fields indicate client/server mismatch

    Example:
        class Reference(InvariantStatic):
            author: str
            title: str
            year: int
            doi: str | None = None

    The frozen=True constraint ensures these objects can be safely used as
    dictionary keys, cached without fear of mutation, and reasoned about
    as mathematical values rather than stateful entities.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")


class InvariantDynamic(BaseModel):
    """A read-only snapshot of arbitrary data.

    Accepts any provided keys during initialization and locks them against
    mutation. FKA-compliant mode for ingestion and discovery.
    Accepts unknown keys — extra='allow'.

    Use this mode for:
    - Ingesting data from external APIs where the schema may evolve
    - Capturing metadata from documents or datasets with unknown structure
    - Preserving full fidelity during ETL processes where information loss is unacceptable
    - Representing "foreign key abstractions" where you don't control the source format

    Example:
        class DocumentMetadata(InvariantDynamic):
            title: str
            # May also contain arbitrary fields from various document formats
            # like 'dc:creator', 'custom_taxonomy', etc.

    The extra='allow' policy preserves information that would otherwise be lost,
    while frozen=True prevents accidental modification of what should be treated
    as an immutable snapshot of external state.
    """

    model_config = ConfigDict(frozen=True, extra="allow")


class MutableStatic(BaseModel):
    """A controlled state machine.

    Strictly enforces defined schema but allows updating specific fields
    throughout the object's lifecycle. Rejects unknown keys.

    Use this mode for:
    - Objects that represent mutable system state with well-defined transitions
    - Registries or indices that accumulate entries over time
    - Configuration objects that may be updated but must maintain schema integrity
    - Any stateful entity where mutation is intended but schema drift is an error

    Example:
        class ProjectRegistry(MutableStatic):
            projects: dict[str, Project]
            last_updated: datetime

            def add_project(self, project: Project) -> None:
                self.projects[project.id] = project
                self.last_updated = datetime.now()

    The extra='forbid' constraint prevents accidental addition of undefined
    attributes during the object's lifetime, while frozen=False enables
    legitimate state updates through defined methods.
    """

    model_config = ConfigDict(frozen=False, extra="forbid")


class MutableDynamic(BaseModel):
    """A flexible, type-aware dictionary.

    Accepts any input and allows unrestricted updates to defined and
    arbitrary attributes.

    Use this mode for:
    - Intermediate objects during parsing or transformation pipelines
    - Prototype objects where the final schema is still being discovered
    - Bridge objects that need to accumulate heterogeneous data before normalization
    - Scratch objects that collect information before being converted to stricter types

    Example:
        class LoaderState(MutableDynamic):
            source_path: str
            # May accumulate arbitrary fields during processing

        loader = LoaderState(source_path="/data/input.json")
        loader.discovered_fields = field_analysis
        loader.validation_errors = validation_results

    This is the most permissive mode and should be used sparingly in production
    code. It's primarily useful for exploratory work, data archaeology, and
    situations where you need maximum flexibility at the cost of type safety.
    """

    model_config = ConfigDict(frozen=False, extra="allow")
