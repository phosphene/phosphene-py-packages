"""Core data models for the mdrag document AST.

Defines the open-by-design Block model and the MarkdownAST root model.
Block is the single generic container for all block types — new block kinds
are added by convention (a new type string and attrs schema), not by touching
this file.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

if TYPE_CHECKING:
    from .query import BlockQuery

from pydantic import AfterValidator, Field, field_validator, model_validator

from .core import InvariantDynamic, InvariantStatic
from .logic import FRAGMENT_SEQ_INDEX, FRAGMENT_TYPE_INDEX, slugify, validate_hickey_uri

HickeyURI = Annotated[str, AfterValidator(validate_hickey_uri)]


class Metadata(InvariantDynamic):
    """Axiomatic Document Metadata — Phosphene 1.5 Structural Identity.

    Represents the ground-truth identity and architectural authority of a
    research document. Hardened with explicit layers for discovery,
    genealogical direction, and reasoning space for agentic intent.

    ``id`` is the ground truth — the stable Hickey coordinate that uniquely
    places this document in the namespace hierarchy. It maps to any namespacing
    scheme and is the field that registry contracts, pipeline contracts, and
    agent routing all depend on.

    ``uri`` is the URI-registry form: the same coordinate expressed as an
    addressable URI, optionally carrying version qualifiers (e.g.
    ``biol/sapolsky-robert-v1``). It is used by the team's URI registry
    convention and by the mdrag engine's addressing layer. When present, it
    is always related to ``id`` — the base coordinate is the same.

    In the Hickey model: ``id`` is the name. ``uri`` is the locator.
    Both can be present; ``id`` is required; ``uri`` is the optional
    registry-qualified form that helps the team work together.

    All other fields are open-world: unknown keys are preserved via
    ``extra='allow'`` (``InvariantDynamic`` mode), maintaining the
    Innovation Bucket pattern for research innovation.

    Attributes:
        id: The stable Hickey coordinate — ``namespace/slug`` format.
            Required. Ground truth for all registry and pipeline contracts.
        uri: Optional URI-registry form. May carry version suffix.
            Used by the mdrag engine and the URI registry convention.
        title: Optional document title.
        type: Optional document type (e.g., ``'person'``, ``'concept'``).
        ns: Optional explicit namespace identifier (e.g., ``'biol'``).
        status: Optional document status (e.g., ``'draft'``, ``'complete'``).
        tags: List of descriptive tags.
        summary: Optional high-level summary/abstract of the document.
        relevant_when: List of routing tags or conditions for context-matching.
        owner: The primary researcher or maintainer of the document.
        layers: List of architectural layers this document pertains to (Architectural Authority).
        direction: Optional genealogical vectoring direction (e.g., 'forward').
        reasoning: Dictionary containing the metadata's internal logic or priors.
        updated: ISO-8601 formatted last-update timestamp.
    """

    id: str
    uri: HickeyURI | None = None
    title: str | None = None
    type: str | None = None
    ns: str | None = None
    status: str | None = None
    tags: list[str] = Field(default_factory=list)
    summary: str | None = None
    relevant_when: list[str] = Field(default_factory=list)
    owner: str | None = None
    layers: list[int] = Field(default_factory=list)
    direction: str | None = None
    reasoning: dict[str, Any] = Field(default_factory=dict)
    updated: str | None = None

    @field_validator("updated", mode="before")
    @classmethod
    def coerce_updated_to_str(cls, v: object) -> str | None:
        """Coerce date/datetime objects to ISO strings.

        YAML parses bare dates (e.g. 2026-04-10) as datetime.date objects.
        We store updated as a plain ISO string throughout the system.

        Args:
            v: Raw value from YAML parsing.

        Returns:
            ISO-format string or None.
        """
        if v is None:
            return None
        import datetime

        if isinstance(v, (datetime.date, datetime.datetime)):
            return v.isoformat()
        return str(v)


class Block(InvariantStatic):
    """Generic open-by-design block container.

    The single model for all block types. The ``type`` field identifies the
    block kind; ``attrs`` carries all type-specific data. New block kinds
    register by convention — a new type string and a documented attrs schema —
    without modifying this file.

    This supersedes the closed union of named block types (HeadingBlock,
    ParagraphBlock, etc.) and decouples the model layer from the extractor
    system entirely.

    Attributes:
        type: The block kind identifier (e.g., 'heading', 'paragraph',
            'list', 'coordinate', 'narrative').
        attrs: Type-specific attributes. Schema is defined by convention
            for each block kind:

            heading:     {'level': int, 'text': str}
            paragraph:   {'content': str}
            list:        {'ordered': bool, 'items': list[str]}
            coordinate:  {'value': str}

    Examples:
        >>> Block(type='heading', attrs={'level': 1, 'text': 'Title'})
        >>> Block(type='paragraph', attrs={'content': 'Hello world.'})
        >>> Block(type='list', attrs={'ordered': False, 'items': ['A', 'B']})
        >>> Block(type='coordinate', attrs={'value': 'sci.bio/levin-v1'})
    """

    type: str
    attrs: dict[str, Any] = Field(default_factory=dict)

    def matches(self, query: BlockQuery) -> bool:
        """Returns True if this block matches the given query."""
        return query.matches(self)


class MarkdownAST(InvariantStatic):
    """Root model representing a fully parsed and validated mdrag document.

    Attributes:
        uri: The authoritative addressable URI for this document.
        metadata: Validated YAML front matter, or None for headerless docs.
        blocks: Ordered sequence of generic blocks extracted from the document.
    """

    uri: HickeyURI
    metadata: Metadata | None = None
    blocks: list[Block] = Field(default_factory=list)
    body: str = ""

    def addresses(self) -> list[tuple[str, int, Block]]:
        """Returns all canonical fragment addresses for blocks in this document.

        Each block may appear under multiple fragments:
        - Sequence index (always): ``#N`` (0-based)
        - Type+index (always): ``#type.K`` (1-based count per type)
        - Heading slug (headings only): ``#slug-of-heading-text``

        Returns:
            A list of ``(fragment, seq_index, block)`` triples. Multiple entries
            may share the same ``seq_index`` when a block has multiple fragments.

        Examples:
            >>> ast = engine.read_file("research-wiki/wiki/sci.bio/sapolsky-robert.md")
            >>> for fragment, idx, block in ast.addresses():
            ...     print(f"{ast.uri}#{fragment}")
        """
        result: list[tuple[str, int, Block]] = []
        type_counts: dict[str, int] = {}

        for seq, block in enumerate(self.blocks):
            btype = block.type
            type_counts[btype] = type_counts.get(btype, 0) + 1

            # Always: sequence index
            result.append((str(seq), seq, block))
            # Always: type.N (1-based)
            result.append((f"{btype}.{type_counts[btype]}", seq, block))
            # Heading slug
            if btype == "heading":
                text = block.attrs.get("text", "")
                if text:
                    result.append((slugify(text), seq, block))

        return result

    def resolve_fragment(self, fragment: str) -> Block | None:
        """Resolves a fragment string to the first matching block.

        Resolution order:
        1. Exact slug match on heading text (e.g., ``stress-and-dominance``)
        2. Type+index match (e.g., ``heading.2``)
        3. Raw sequence index (e.g., ``3``)

        Args:
            fragment: The fragment string (without leading ``#``).

        Returns:
            The first matching ``Block``, or ``None`` if no match is found.

        Examples:
            >>> block = ast.resolve_fragment("stress-and-dominance")
            >>> block = ast.resolve_fragment("heading.2")
            >>> block = ast.resolve_fragment("3")
        """
        # Pass 1: slug match (headings only)
        type_counts: dict[str, int] = {}
        for block in self.blocks:
            btype = block.type
            type_counts[btype] = type_counts.get(btype, 0) + 1
            if btype == "heading":
                text = block.attrs.get("text", "")
                if text and slugify(text) == fragment:
                    return block

        # Pass 2: type.N match
        m = FRAGMENT_TYPE_INDEX.match(fragment)
        if m:
            target_type, n_str = m.group(1), int(m.group(2))
            count = 0
            for block in self.blocks:
                if block.type == target_type:
                    count += 1
                    if count == n_str:
                        return block

        # Pass 3: raw sequence index
        m2 = FRAGMENT_SEQ_INDEX.match(fragment)
        if m2:
            idx = int(m2.group(1))
            if 0 <= idx < len(self.blocks):
                return self.blocks[idx]

        return None

    def find_blocks(self, query: BlockQuery) -> list[Block]:
        """Returns all blocks matching the given query.

        Args:
            query: The BlockQuery criteria.

        Returns:
            A list of matching Block objects.
        """
        return [b for b in self.blocks if b.matches(query)]

    def select(self, selector_str: str) -> Any:  # noqa: ANN401
        """Selects data from the AST using the Discovery DSL.

        This is the formal entry point for data extraction, replacing
        legacy heuristic selectors.

        Args:
            selector_str: The DSL selector string (e.g. 'heading.text').

        Returns:
            The extracted data, or None if not found.
        """
        from .query import Selector

        # Handle activation suffix
        activate = False
        if selector_str.endswith(".activate"):
            activate = True
            selector_str = selector_str[:-9]

        # Multi-block composition case
        if " >> " in selector_str:
            parts = selector_str.split(" >> ")
            results = []
            for part in parts:
                # Handle pipe definitions [src:tgt, src2:tgt2]
                if part.startswith("[") and part.endswith("]"):
                    pipe_def = part[1:-1]
                    mapping = {}
                    for item in pipe_def.split(","):
                        if ":" in item:
                            s, t = item.split(":", 1)
                            mapping[s.strip()] = t.strip()
                    results.append(mapping)
                else:
                    res = self.select(f"{part}.activate" if activate else part)
                    if res:
                        results.append(res)

            if activate:
                return self._activate_block(results)
            return results

        selector = Selector.parse(selector_str)

        # Metadata case
        if selector_str.startswith("metadata."):
            if not self.metadata:
                return None
            return getattr(
                self.metadata, selector.field, None
            ) or self.metadata.model_extra.get(selector.field)

        # Block query case
        # We need to handle the positional index for legacy support
        target_index = selector.query.index
        matches = self.find_blocks(selector.query)

        if not matches:
            return None

        target = matches[0]
        if target_index and len(matches) >= target_index:
            target = matches[target_index - 1]

        if activate:
            return self._activate_block(target)

        if not selector.field:
            return target

        # Extract field from target block
        if selector.field == "text":
            return target.attrs.get("text") or target.attrs.get("content")
        return target.attrs.get(selector.field)

    def _activate_block(self, block: Block | list[Any]) -> Any:
        """Internal: Dispatches block or pipeline to the first matching activator."""
        for activator in ACTIVATORS:
            result = activator(block)
            if result is not None:
                return result
        return None

    @model_validator(mode="before")
    @classmethod
    def conform_ast(cls, data: Any) -> dict[str, Any]:  # noqa: ANN401
        """Handles the legacy token-based construction path.

        When the engine passes pre-extracted blocks, this validator is a
        pass-through. When raw mistune tokens are passed (legacy path),
        it performs URI derivation, parity checking, and block extraction.

        Args:
            data: Either a pre-validated dict with 'uri' and 'blocks', or
                a legacy dict with 'tokens', 'metadata', and optional 'filepath'.

        Returns:
            A dict ready for Pydantic model instantiation.

        Raises:
            ValueError: If identity parity fails or document URI is missing.
        """
        if not isinstance(data, dict):
            return data
        # Fast path: engine has already extracted blocks via the registry
        if "tokens" not in data:
            return data

        def extract_text(token: dict[str, Any]) -> str:
            """Recursively extracts plain text from a mistune token."""
            if isinstance(token, dict):
                raw = token.get("raw") or token.get("text") or ""
                children = token.get("children", [])
                if children:
                    return "".join([extract_text(c) for c in children])
                return raw
            return ""

        tokens = data["tokens"]
        metadata = data["metadata"]
        uri = metadata.get("uri") if metadata else None

        if not uri:
            for t in tokens:
                p_text = extract_text(t)
                match = re.search(r"uri:\s*(\S+)", p_text)
                if match:
                    uri = match.group(1).strip()
                    break

        # id is the ground truth — if uri is still absent, derive from id.
        # Docs that carry only `id:` (no `uri:`) are valid; uri = id for routing.
        if not uri and metadata and metadata.get("id"):
            uri = metadata["id"]

        if metadata and metadata.get("id") and data.get("filepath"):
            doc_id = str(metadata["id"])
            filepath = str(data["filepath"])
            if "research-wiki/wiki/" in filepath:
                expected_id = filepath.split("research-wiki/wiki/")[-1].replace(
                    ".md", ""
                )
            else:
                expected_id = filepath.replace(".md", "")
            if doc_id != expected_id:
                raise ValueError(
                    f"Identity Mismatch: Metadata id '{doc_id}' does not match "
                    f"file path '{expected_id}'."
                )

        refined_blocks: list[dict[str, Any]] = []
        IGNORABLE_TOKENS = {"blank_line", "uri_header"}

        for t in tokens:
            if t["type"] in IGNORABLE_TOKENS:
                continue
            if t["type"] == "paragraph" and uri:
                p_text = extract_text(t).strip()
                if p_text == f"uri: {uri}":
                    continue

            block_type = t["type"]
            if block_type not in {"heading", "paragraph", "list", "coordinate"}:
                continue

            if block_type == "heading":
                child = t.get("children", [{}])[0]
                text = child.get("raw", "") or child.get("text", "")
                refined_blocks.append(
                    {
                        "type": "heading",
                        "attrs": {"level": t["attrs"]["level"], "text": text},
                    }
                )
            elif block_type == "paragraph":
                children = t.get("children", [])
                parts = []
                for child in children:
                    child_type = child.get("type")
                    if child_type == "text":
                        parts.append(child.get("raw", "") or child.get("text", ""))
                    elif child_type == "softbreak":
                        parts.append("\n")
                    elif child_type == "coordinate":
                        raw = child.get("raw", "") or child.get("text", "")
                        parts.append(f"{{:{raw}}}")
                content_str = "".join(parts)

                from .block_rules import parse_coordinate_or_axiom

                block = parse_coordinate_or_axiom(content_str)
                if block is not None:
                    refined_blocks.append(
                        {
                            "type": block.type,
                            "attrs": block.attrs,
                        }
                    )
                    continue

                refined_blocks.append(
                    {
                        "type": "paragraph",
                        "attrs": {"content": content_str},
                    }
                )
            elif block_type == "list":
                refined_blocks.append(
                    {
                        "type": "list",
                        "attrs": {
                            "ordered": t["attrs"]["ordered"],
                            "items": [
                                extract_text(item)
                                for item in t.get("children", [])
                                if extract_text(item).strip()
                            ],
                        },
                    }
                )
            elif block_type == "coordinate":
                refined_blocks.append(
                    {
                        "type": "coordinate",
                        "attrs": {"value": t.get("raw", "") or t.get("text", "")},
                    }
                )

        if not uri and "filepath" in data and data["filepath"]:
            filepath = str(data["filepath"])
            if "research-wiki/wiki/" in filepath:
                uri = filepath.split("research-wiki/wiki/")[-1].replace(".md", "")
            else:
                uri = Path(filepath).stem

        if not uri:
            raise ValueError(
                "Missing document identity: No 'id' or 'uri' found in YAML front matter or legacy header."  # noqa: E501
            )

        metadata = metadata or {}
        if not metadata.get("uri"):
            metadata["uri"] = uri
        if not metadata.get("id"):
            if data.get("filepath"):
                filepath = str(data["filepath"])
                if "research-wiki/wiki/" in filepath:
                    metadata["id"] = filepath.split("research-wiki/wiki/")[-1].replace(
                        ".md", ""
                    )
                else:
                    metadata["id"] = Path(filepath).stem
            else:
                metadata["id"] = uri

        return {"uri": uri, "metadata": metadata, "blocks": refined_blocks}


# ─────────────────────────────────────────────────────────────────────────────
# ACTIVATOR REGISTRY
# ─────────────────────────────────────────────────────────────────────────────

ACTIVATORS: list[Callable[[Block], Any]] = []


def register_activator(activator: Callable[[Block], Any]) -> None:
    """Registers a new morphic activator for the AST.

    An activator is a callable that takes a Block and returns an executable
    object (e.g. a ScientificModel) or None.
    """
    ACTIVATORS.append(activator)
