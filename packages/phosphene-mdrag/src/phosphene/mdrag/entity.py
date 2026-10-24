"""Domain entity models for structured markdown extraction.

Defines the schemas and selectors used to extract formal records (e.g., OKRs,
Projects, Team Members) from unstructured markdown AST blocks.
"""

from __future__ import annotations

from typing import Any

from phosphene.mdrag.core import InvariantDynamic, InvariantStatic

from .query import BlockQuery


class FieldSelector(InvariantStatic):
    """A selector identifying where to extract a field from a block stream.

    Attributes:
        selector: The extraction DSL string (e.g., 'h2.text', 'metadata.id').
    """

    selector: str  # e.g., "h2.text", "metadata.id", "next(p).content"


class EntitySchema(InvariantStatic):
    """The axiomatic definition for an entity extracted from Markdown.

    Attributes:
        type: The formal entity type (e.g., 'team/okr').
        trigger_type: The block type that initiates extraction (e.g., 'heading').
        trigger_attrs: Attributes that must match on the trigger block.
        fields: Mapping of field names to their extraction selectors.
        description: Brief description of the entity's purpose.
    """

    type: str  # e.g. "team/okr"
    trigger_type: str  # e.g. "heading" (the block type that starts the entity)
    trigger_attrs: dict[str, Any] = {}  # e.g. {"level": 2}
    fields: dict[str, str]  # mapping of field_name -> selector_string
    description: str = ""

    def get_query(self) -> BlockQuery:
        """Returns a BlockQuery that matches the trigger for this entity."""
        return BlockQuery(type=self.trigger_type, attrs=self.trigger_attrs)


class Entity(InvariantDynamic):
    """A structured domain object extracted from a Markdown document.

    Attributes:
        type: The entity type matching the schema.
        uri: The canonical coordinate of the entity (file_uri#fragment).
        data: The extracted attributes.
    """

    type: str
    uri: str  # The coordinate of the entity (file_uri#fragment)
    data: dict[str, Any]
