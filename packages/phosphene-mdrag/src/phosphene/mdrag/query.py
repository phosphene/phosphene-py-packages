"""Discovery DSL — formal query and selector models for mdrag documents.

This module provides the structural foundation for non-heuristic discovery.
Instead of regex-scraping or positional heuristics, we use formal queries
to find blocks and selectors to extract fields.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import Field

from .core import InvariantStatic


class BlockQuery(InvariantStatic):
    """A formal query for matching blocks in a stream.

    Attributes:
        type: Match blocks of this exact type (e.g. 'heading').
        attrs: Match blocks where these attributes match exactly.
        text_regex: Match blocks where the primary text (text, content, or value)
            matches this regex.
    """

    type: str | None = None
    attrs: dict[str, Any] = Field(default_factory=dict)
    text_regex: str | None = None
    index: int | None = None  # 1-based index for positional matching

    def matches(self, block: Any) -> bool:  # noqa: ANN401
        """Returns True if the block matches all query criteria."""
        if self.type and block.type != self.type:
            return False

        for k, v in self.attrs.items():
            if block.attrs.get(k) != v:
                return False

        if self.text_regex:
            text = (
                block.attrs.get("text")
                or block.attrs.get("content")
                or block.attrs.get("value")
                or ""
            )
            if not re.search(self.text_regex, text):
                return False

        return True


class Selector(InvariantStatic):
    """A formal selector for traversing and extracting data from an AST.

    A ``Selector`` is a *parsed representation only* — it does not execute
    anything itself.  Execution (walking the AST, applying the query,
    extracting the field) is the responsibility of ``MarkdownAST.select()``
    in the engine layer.  This separation keeps the data model pure and
    makes selectors serializable and unit-testable without a live AST.

    Lifecycle::

        raw string  ──► Selector.parse()  ──► Selector  ──► MarkdownAST.select()

    Attributes:
        query: The ``BlockQuery`` that identifies the target block(s).
        field: Optional dot-path into the matched block's attributes
            (e.g. ``"text"``, ``"attrs.id"``).  When ``None``, the full
            block is returned by the engine.
    """

    query: BlockQuery
    field: str | None = None  # e.g. "text", "attrs.id"

    @classmethod
    def parse(cls, selector_str: str) -> Selector:
        """Parses a legacy or DSL string into a formal Selector object.

        Supported formats:
            - type.field (e.g. "heading.text")
            - metadata.key (e.g. "metadata.id")
            - list.N.items (e.g. "list.1.items")
        """
        # 1. Metadata case
        if selector_str.startswith("metadata."):
            return cls(
                query=BlockQuery(type="metadata"),  # Virtual query for metadata
                field=selector_str.split(".", 1)[1],
            )

        # 2. Positional legacy case: paragraph.1, list.1.items
        # We map these to a query with a sequence constraint
        pos_match = re.match(r"([a-z]+)\.(\d+)(?:\.(.+))?", selector_str)
        if pos_match:
            btype, pos, field = pos_match.groups()
            return cls(
                query=BlockQuery(type=btype, index=int(pos)), field=field or "content"
            )

        # 3. Simple type.field case: heading.text
        if "." in selector_str:
            btype, field = selector_str.split(".", 1)
            return cls(query=BlockQuery(type=btype), field=field)

        # 4. Fallback: just a type
        return cls(query=BlockQuery(type=selector_str))
