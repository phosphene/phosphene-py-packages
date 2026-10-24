"""genealogy.py — Morphism extraction from the Genealogy convention.

Extracts typed morphisms from the ``## Genealogy`` section of five-block
research wiki documents. Produces two separated structures:

- **Forward morphisms** — the document's account of its intellectual lineage:
  what it builds on, converges with, departs from, and responds to.
- **Downstream declarations** — the document's account of its own influence,
  declared from the inside.

These are kept separate because they are different epistemic acts. The
relationship between them (reconciliation, inversion consistency) is a derived
operation over two clean structures, not a merged dataset.

Target classification:
- ``corpus`` — bullet item contains a ``[[namespace/slug]]`` wiki link
- ``external`` — plain text; raw form preserved as-is

The raw text of every target is always preserved, regardless of classification.
Open-world principle: we do not know what the external references will tell us.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .models import MarkdownAST

# Morphism type keys — tied to this concrete vocabulary, this convention
FORWARD_SECTIONS: dict[str, str] = {
    "Builds on:": "builds-on",
    "Converges with:": "converges-with",
    "Departs from:": "departs-from",
    "Responds to:": "responds-to",
}

DOWNSTREAM_LABEL = "Downstream:"

# Wiki link pattern: [[namespace/slug]] or [[namespace/slug]] with optional gloss
_WIKI_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


@dataclass(frozen=True)
class MorphismTarget:
    """A single morphism target extracted from a Genealogy bullet item.

    Attributes:
        raw_text: The full bullet text as authored, always preserved.
        uri: Extracted corpus URI if the item contained a [[wiki link]], else None.
        resolved: True if a corpus URI was found; False for external references.
    """

    raw_text: str
    uri: str | None
    resolved: bool

    @classmethod
    def from_text(cls, text: str) -> MorphismTarget:
        """Construct a MorphismTarget by classifying a raw bullet text.

        Extracts a ``[[uri]]`` wiki link if present; otherwise marks the
        target as external and preserves the raw text.

        Args:
            text: Raw bullet item text from the Genealogy section.

        Returns:
            A classified, frozen MorphismTarget.
        """
        text = text.strip()
        match = _WIKI_LINK_RE.search(text)
        if match:
            return cls(raw_text=text, uri=match.group(1), resolved=True)
        # Non-empty text that is not a valid target (e.g. incomplete "[")
        if not text or text in {"[", "]", "[["}:
            return cls(raw_text=text, uri=None, resolved=False)
        return cls(raw_text=text, uri=None, resolved=False)


@dataclass
class GenealogyResult:
    """Extracted morphism structures from a single document's Genealogy section.

    Attributes:
        source_uri: The document's corpus URI (the morphism source).
        forward: Typed forward morphisms — maps morphism type → list of targets.
                 Types: 'builds-on', 'converges-with', 'departs-from', 'responds-to'.
        downstream: Author-declared downstream influence targets.
                    Separated from forward morphisms — different epistemic act.
    """

    source_uri: str
    forward: dict[str, list[MorphismTarget]] = field(default_factory=dict)
    downstream: list[MorphismTarget] = field(default_factory=list)

    def has_content(self) -> bool:
        """Return True if at least one non-empty morphism was extracted.

        Returns:
            True if any forward or downstream targets were found.
        """
        return bool(self.downstream) or any(
            targets for targets in self.forward.values()
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict for index emission.

        Returns:
            Dict with 'source_uri', 'forward', and 'downstream' keys.
            Empty lists/dicts are omitted.
        """
        result: dict[str, Any] = {"source_uri": self.source_uri}
        forward_out: dict[str, list[dict]] = {}
        for mtype, targets in self.forward.items():
            valid = [t for t in targets if t.raw_text and t.raw_text not in {"[", "]"}]
            if valid:
                forward_out[mtype] = [
                    {"raw": t.raw_text, "uri": t.uri, "resolved": t.resolved}
                    for t in valid
                ]
        if forward_out:
            result["forward"] = forward_out
        downstream_out = [
            {"raw": t.raw_text, "uri": t.uri, "resolved": t.resolved}
            for t in self.downstream
            if t.raw_text and t.raw_text not in {"[", "]"}
        ]
        if downstream_out:
            result["downstream"] = downstream_out
        return result


class GenealogyExtractor:
    """Extracts morphism structures from a MarkdownAST's Genealogy section.

    Operates on the mdrag block sequence. The Genealogy section follows the
    five-block convention:

        ## Genealogy
        Builds on:
        - item...
        Converges with:
        - item...
        Departs from:
        - item...
        Responds to:
        - item...
        Downstream:
        - item...

    Paragraph blocks carry the subsection labels; list blocks carry the items.
    """

    def extract(self, ast: MarkdownAST) -> GenealogyResult | None:
        """Extract morphisms from the Genealogy section of a document AST.

        Scans the block sequence for a level-2 heading with text 'Genealogy',
        then parses the alternating paragraph-label / list-items structure
        until the next level-2 heading.

        Args:
            ast: Parsed MarkdownAST for the document.

        Returns:
            GenealogyResult if a Genealogy section is found, None otherwise.
            Returns None (not an empty result) when the section is absent —
            absence and emptiness are distinguished.
        """
        blocks = ast.blocks
        genealogy_start = None

        for i, block in enumerate(blocks):
            if (
                block.type == "heading"
                and block.attrs.get("level") == 2
                and block.attrs.get("text") == "Genealogy"
            ):
                genealogy_start = i
                break

        if genealogy_start is None:
            return None

        result = GenealogyResult(source_uri=str(ast.uri))
        current_type: str | None = None
        is_downstream = False

        for block in blocks[genealogy_start + 1 :]:
            # Stop at next ## heading
            if block.type == "heading" and block.attrs.get("level", 0) <= 2:
                break

            if block.type == "paragraph":
                label = block.attrs.get("content", "").strip()
                if label in FORWARD_SECTIONS:
                    current_type = FORWARD_SECTIONS[label]
                    is_downstream = False
                    if current_type not in result.forward:
                        result.forward[current_type] = []
                elif label == DOWNSTREAM_LABEL:
                    current_type = None
                    is_downstream = True
                else:
                    current_type = None
                    is_downstream = False

            elif block.type == "list":
                items = block.attrs.get("items", [])
                targets = [MorphismTarget.from_text(str(item)) for item in items]
                if is_downstream:
                    result.downstream.extend(targets)
                elif current_type is not None:
                    result.forward.setdefault(current_type, []).extend(targets)

        return result
