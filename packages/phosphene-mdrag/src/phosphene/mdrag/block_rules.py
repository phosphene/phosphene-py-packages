"""Block extraction rule system for the mdrag engine.

Defines the BlockExtractor abstract base and concrete extractors for each
supported block type. The ExtractorRegistry dispatches tokens to their
registered extractor, decoupling block-type logic from the engine core.

Each extractor owns exactly one concern: extracting a typed Block from a
raw mistune token. Extractors never raise — malformed input returns None.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any

from phosphene.mdrag.models import Block

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_text(token: dict[str, Any]) -> str:
    """Recursively extracts plain text from a mistune token.

    Walks the token tree depth-first, concatenating raw/text values.
    Returns an empty string for unrecognised structures.

    Args:
        token: A mistune token dictionary.

    Returns:
        The flattened plain-text content of the token and its children.
    """
    if not isinstance(token, dict):
        return ""
    children = token.get("children", [])
    if children:
        return "".join(_extract_text(c) for c in children)
    return token.get("raw", "") or token.get("text", "")


# ---------------------------------------------------------------------------
# Protocol / Abstract Base
# ---------------------------------------------------------------------------


class BlockExtractor(ABC):
    """Abstract base for a discrete block-type extraction unit.

    Each concrete subclass owns the extraction logic for one or more closely
    related token types. The contract on ``extract`` is strict: it must never
    raise. Malformed or unrecognisable input returns None, and the registry
    treats None as "skip this token."
    """

    @property
    @abstractmethod
    def handles(self) -> frozenset[str]:
        """The set of mistune token types this extractor accepts."""
        ...

    def can_handle(self, token: dict[str, Any]) -> bool:
        """Returns True if this extractor handles the given token type.

        Args:
            token: A mistune token dictionary.

        Returns:
            True if ``token['type']`` is in ``self.handles``.
        """
        return token.get("type") in self.handles

    @abstractmethod
    def extract(self, token: dict[str, Any]) -> Block | None:
        """Extracts a typed Block from a mistune token.

        Args:
            token: A mistune token dictionary whose type is in ``self.handles``.

        Returns:
            A typed Block instance, or None to signal the token should be
            skipped. Never raises.
        """
        ...


# ---------------------------------------------------------------------------
# Concrete extractors
# ---------------------------------------------------------------------------


class HeadingExtractor(BlockExtractor):
    """Extracts HeadingBlock from mistune heading tokens.

    Handles level and text. Returns None for headings with no text content.
    """

    @property
    def handles(self) -> frozenset[str]:
        """Token types handled: heading."""
        return frozenset({"heading"})

    def extract(self, token: dict[str, Any]) -> Block | None:
        """Extracts level and text from a heading token.

        Args:
            token: A mistune heading token.

        Returns:
            A HeadingBlock, or None if text is empty.
        """
        children = token.get("children", [])
        if not children:
            return None
        text = children[0].get("raw", "") or children[0].get("text", "")
        if not text.strip():
            return None
        level = token.get("attrs", {}).get("level", 1)
        return Block(type="heading", attrs={"level": level, "text": text})


class ParagraphExtractor(BlockExtractor):
    """Extracts ParagraphBlock (or CoordinateBlock) from paragraph tokens.

    Applies coordinate discrimination: a paragraph whose sole child is a
    text node matching COORDINATE_PATTERN is promoted to a CoordinateBlock.
    All other paragraphs are flattened to a content string.
    """

    @property
    def handles(self) -> frozenset[str]:
        """Token types handled: paragraph."""
        return frozenset({"paragraph"})

    def extract(self, token: dict[str, Any]) -> Block | None:
        """Extracts a ParagraphBlock or Coordinate/Axiom block from a paragraph token.

        Args:
            token: A mistune paragraph token.

        Returns:
            A Coordinate or Axiom block, or a ParagraphBlock for general content.
        """
        children = token.get("children", [])

        # General inline content: flatten to string
        parts: list[str] = []
        for child in children:
            child_type = child.get("type")
            if child_type == "text":
                parts.append(child.get("raw", "") or child.get("text", ""))
            elif child_type == "softbreak":
                parts.append("\n")
            elif child_type == "coordinate":
                raw = child.get("raw", "") or child.get("text", "")
                parts.append(f"{{:{raw}}}")
            else:
                # Unknown inline type: extract text best-effort
                parts.append(_extract_text(child))

        content = "".join(parts)
        if not content.strip():
            return None

        # Coordinate/Axiom discrimination
        block = parse_coordinate_or_axiom(content)
        if block is not None:
            return block

        return Block(type="paragraph", attrs={"content": content})


class ListExtractor(BlockExtractor):
    """Extracts ListBlock from mistune list tokens.

    Delegates item text extraction to ``_extract_text``. Items that yield
    empty strings after stripping are skipped (Q1: None policy applied
    per item, not per list).
    """

    @property
    def handles(self) -> frozenset[str]:
        """Token types handled: list."""
        return frozenset({"list"})

    def extract(self, token: dict[str, Any]) -> Block | None:
        """Extracts a ListBlock from a list token.

        Args:
            token: A mistune list token.

        Returns:
            A ListBlock with zero or more items. Returns None only if the
            token itself is structurally malformed (no attrs).
        """
        attrs = token.get("attrs")
        if attrs is None:
            return None
        ordered: bool = attrs.get("ordered", False)
        items: list[str] = []
        for item in token.get("children", []):
            text = _extract_text(item).strip()
            if text:
                items.append(text)
        return Block(type="list", attrs={"ordered": ordered, "items": items})


class TableExtractor(BlockExtractor):
    """Extracts TableBlock from mistune table tokens."""

    @property
    def handles(self) -> frozenset[str]:
        """Token types handled: table."""
        return frozenset({"table"})

    def extract(self, token: dict[str, Any]) -> Block | None:
        """Extracts rows and header from a table token."""
        header_token = token.get("children", [])[0]
        body_token = token.get("children", [])[1]

        def extract_row(row_token: dict[str, Any]) -> list[str]:
            return [_extract_text(cell) for cell in row_token.get("children", [])]

        header = extract_row(header_token.get("children", [])[0])
        rows = [extract_row(row) for row in body_token.get("children", [])]

        return Block(type="table", attrs={"header": header, "rows": rows})


class CoordinateExtractor(BlockExtractor):
    """Extracts CoordinateBlock from mistune coordinate tokens.

    Coordinate tokens are produced by the coordinate_plugin grammar extension.
    """

    @property
    def handles(self) -> frozenset[str]:
        """Token types handled: coordinate."""
        return frozenset({"coordinate"})

    def extract(self, token: dict[str, Any]) -> Block | None:
        """Extracts a CoordinateBlock from a coordinate token.

        Args:
            token: A mistune coordinate token.

        Returns:
            A CoordinateBlock, or None if the value is empty.
        """
        value = (token.get("raw", "") or token.get("text", "")).strip()
        if not value:
            return None
        return Block(type="coordinate", attrs={"value": value})


class AxiomExtractor(BlockExtractor):
    """Extracts Axiom blocks from namespaced coordinate tokens.

    Handles coordinates like {:axiom/entity: id='team/okr'} or {:okr/mapping: ...}.
    Extracts the namespace and all key=value attributes.
    """

    @property
    def handles(self) -> frozenset[str]:
        """Token types handled: coordinate."""
        return frozenset({"coordinate"})


def parse_coordinate_or_axiom(text: str) -> Block | None:
    """Parses a raw coordinate or axiom block string (like '{:type: attrs}')."""
    text_stripped = text.strip()
    if not (text_stripped.startswith("{:") and text_stripped.endswith("}")):
        return None

    inner = text_stripped[2:-1].strip()
    if ":" not in inner:
        # Plain coordinate
        return Block(type="coordinate", attrs={"value": inner})

    # Namespaced axiom/coordinate
    prefix, remainder = inner.split(":", 1)
    axiom_type = prefix.strip()

    # Parse attributes: key=val, key='val', key="val", key=[...]
    attrs: dict[str, Any] = {}

    # Extract id=VALUE
    id_match = re.search(r"\bid=([^,\s\]}]+)", remainder)
    if id_match:
        attrs["id"] = id_match.group(1).strip().strip("'").strip('"')

    # Extract any list attribute, e.g. patterns=[...] or deferred=[...]
    list_matches = re.finditer(r"(\w+)=\s*\[(.*?)\]", remainder)
    for m in list_matches:
        key = m.group(1)
        val_list = [
            p.strip().strip("'").strip('"') for p in m.group(2).split(",") if p.strip()
        ]
        attrs[key] = val_list

    # General key=val parser for other attributes (that are not lists)
    kv_matches = re.finditer(
        r"(\w+)\s*=\s*(?:'([^']*)'|\"([^\"]*)\"|([^,\s\]}]+))", remainder
    )
    for m in kv_matches:
        key = m.group(1)
        if key in attrs:
            continue
        val = m.group(2) or m.group(3) or m.group(4)
        if val is not None:
            attrs[key] = val.strip()

    return Block(type=axiom_type, attrs=attrs)


class AxiomExtractor(BlockExtractor):
    """Extracts Axiom blocks from namespaced coordinate tokens.

    Handles coordinates like {:axiom/entity: id='team/okr'} or {:okr/mapping: ...}.
    Extracts the namespace and all key=value attributes.
    """

    @property
    def handles(self) -> frozenset[str]:
        """Token types handled: coordinate."""
        return frozenset({"coordinate"})

    def extract(self, token: dict[str, Any]) -> Block | None:
        """Extracts an axiom block from a coordinate token.

        Args:
            token: A mistune coordinate token.

        Returns:
            An axiom Block, or None if prefix doesn't match namespaced pattern.
        """
        raw = (token.get("raw", "") or token.get("text", "")).strip()
        if ":" not in raw:
            return None
        return parse_coordinate_or_axiom(f"{{:{raw}}}")


class WCIExtractor(BlockExtractor):
    """Extracts formal WCI (Woodchipper Credibility Index) blocks.

    Handles {:wci: score=85, band='Landmark', components='N=9,E=9,P=8,C=9,S=9,Sc=9,L=9,M=9'}.
    """

    @property
    def handles(self) -> frozenset[str]:
        """Token types handled: coordinate."""
        return frozenset({"coordinate"})

    def extract(self, token: dict[str, Any]) -> Block | None:
        """Extracts a WCI block from a coordinate token."""
        raw = (token.get("raw", "") or token.get("text", "")).strip()
        if not raw.startswith("wci:"):
            return None

        # Use the AxiomExtractor logic but specifically for wci
        # We reuse the logic by calling a helper or just reimplementing
        prefix, remainder = raw.split(":", 1)

        attrs: dict[str, Any] = {}
        # Simple key=val parser
        assignments = re.findall(r"(\w+)=([^,\s\]}]+)", remainder)
        for key, val in assignments:
            val_clean = val.strip().strip("'").strip('"')
            # Coerce numbers
            if val_clean.replace(".", "").isdigit():
                attrs[key] = float(val_clean) if "." in val_clean else int(val_clean)
            else:
                attrs[key] = val_clean

        return Block(type="wci", attrs=attrs)


class FencedAxiomExtractor(BlockExtractor):
    """Extracts formal Axiom blocks from fenced code blocks.

    Handles code blocks with language 'axiom/*', parsing the content as JSON.
    """

    @property
    def handles(self) -> frozenset[str]:
        """Token types handled: block_code."""
        return frozenset({"block_code"})

    def extract(self, token: dict[str, Any]) -> Block | None:
        """Extracts an axiom block from a fenced code block."""
        attrs = token.get("attrs", {})
        info = attrs.get("info", "")
        if not info.startswith("axiom/"):
            return None

        content = token.get("raw", "").strip()
        import json

        try:
            data = json.loads(content)
            return Block(type=info, attrs=data)
        except (json.JSONDecodeError, TypeError):
            return None


class FencedBlockDispatcher(BlockExtractor):
    """Unified dispatcher for all fenced JSON code blocks.

    Replaces ``FencedAxiomExtractor`` as the single ``block_code`` handler.
    Dispatches on the info string:

    - ``axiom/*`` → axiom block (same logic as ``FencedAxiomExtractor``)
    - ``reading-event`` → reading-event block (spec: eval/reading-event-v1.md)
    - anything else → None (innovation bucket via engine)

    Example reading-event block in a wiki document::

        ```reading-event
        {
          "id": "re-2026-05-10-body-grammar-v3-cr",
          "paper": "projects/woodchipper/body-grammar-v3",
          "event_type": "close-read",
          "date": "2026-05-10",
          "participants": ["jan", "edphos"]
        }
        ```
    """

    @property
    def handles(self) -> frozenset[str]:
        """Token types handled: block_code.

        Returns:
            Frozenset containing 'block_code'.
        """
        return frozenset({"block_code"})

    def extract(self, token: dict[str, Any]) -> Block | None:
        """Dispatch a fenced code block to the appropriate handler by info string.

        Args:
            token: A mistune block_code token.

        Returns:
            A typed Block or None.
        """
        import json as _json

        attrs = token.get("attrs", {})
        info = (attrs.get("info", "") or "").strip()
        content = token.get("raw", "").strip()

        if info.startswith("axiom/"):
            try:
                data = _json.loads(content)
                return Block(type=info, attrs=data)
            except (_json.JSONDecodeError, TypeError):
                return None

        if info == "reading-event":
            try:
                data = _json.loads(content)
                return Block(type="reading-event", attrs=data)
            except (_json.JSONDecodeError, TypeError):
                return None

        return None


class ConsumedTokenExtractor(BlockExtractor):
    """Handles tokens that are consumed at earlier pipeline stages.

    URI headers and blank lines are processed during URI derivation and
    are never emitted as blocks. Registering them here keeps the registry's
    dispatch table exhaustive — unknown token warnings are reserved for
    genuinely unexpected types.
    """

    @property
    def handles(self) -> frozenset[str]:
        """Token types handled: uri_header, blank_line."""
        return frozenset({"uri_header", "blank_line"})

    def extract(self, token: dict[str, Any]) -> Block | None:
        """Returns None — these tokens produce no blocks.

        Args:
            token: A consumed token (uri_header or blank_line).

        Returns:
            Always None.
        """
        return None


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class ExtractorRegistry:
    """Maps token types to their registered BlockExtractor.

    The registry is the dispatch table for the engine. Each token type
    maps to exactly one extractor. Tokens whose type is not registered
    are silently skipped.
    """

    def __init__(self) -> None:
        """Initialises an empty registry."""
        self._extractors: dict[str, BlockExtractor] = {}

    def register(self, extractor: BlockExtractor) -> None:
        """Registers an extractor for all of its handled token types.

        If a token type is already registered, the new extractor replaces
        the previous one.

        Args:
            extractor: The BlockExtractor to register.
        """
        for token_type in extractor.handles:
            self._extractors[token_type] = extractor

    def dispatch(self, token: dict[str, Any]) -> Block | None:
        """Dispatches a token to its registered extractor.

        Implements the FKA non-destructive parsing rule: unregistered token
        types are never dropped. They are preserved in the innovation bucket
        as Block(type="unknown/{token_type}", attrs={"raw": token}).

        Registered extractors that return None (e.g. ConsumedTokenExtractor
        for blank_line/uri_header, or malformed tokens) still return None —
        those are intentional skips, not unknown types.

        Args:
            token: A mistune token dictionary.

        Returns:
            A typed Block if the token is known or unknown (innovation bucket),
            or None only for intentionally consumed/malformed tokens.
        """
        token_type = token.get("type", "untyped")
        extractor = self._extractors.get(token_type)
        if extractor is None:
            # Innovation bucket: unknown type — preserve, never drop
            return Block(type=f"unknown/{token_type}", attrs={"raw": token})
        return extractor.extract(token)

    def is_registered(self, token_type: str) -> bool:
        """Returns True if a token type has a registered extractor.

        Args:
            token_type: The mistune token type string.

        Returns:
            True if registered, False otherwise.
        """
        return token_type in self._extractors


# ---------------------------------------------------------------------------
# Default registry factory
# ---------------------------------------------------------------------------


def default_registry() -> ExtractorRegistry:
    """Creates and returns the standard wiki document ExtractorRegistry.

    Registers extractors for all v1 block types: heading, paragraph,
    list, coordinate, and consumed tokens (uri_header, blank_line).

    Returns:
        A fully configured ExtractorRegistry.
    """
    registry = ExtractorRegistry()
    registry.register(HeadingExtractor())
    registry.register(ParagraphExtractor())
    registry.register(ListExtractor())
    registry.register(TableExtractor())
    registry.register(CoordinateExtractor())
    registry.register(AxiomExtractor())
    registry.register(
        FencedBlockDispatcher()
    )  # replaces FencedAxiomExtractor; handles axiom/* + reading-event
    registry.register(WCIExtractor())
    registry.register(ConsumedTokenExtractor())
    return registry
