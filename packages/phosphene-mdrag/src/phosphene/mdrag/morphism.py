"""morphism.py — Layer 2 functional projection for mdrag documents.

Implements the Morphic 'Battery of Lenses' pattern, allowing for the functional
projection of a stable MarkdownAST into conformed research conventions
(e.g., LabProtocol, Critique).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .engine import MarkdownEngine
from .models import MarkdownAST
from .open_world import OpenRecord


@runtime_checkable
class Lens(Protocol):
    """Protocol for a late-bound functional projection (Lens).

    A Lens takes a validated MarkdownAST and returns an OpenRecord
    representing the conformed projection of that document, or None
    if the document does not support the convention.
    """

    def project(self, ast: MarkdownAST) -> OpenRecord | None:
        """Projects a document AST into a conformed representation.

        Args:
            ast: The stable MarkdownAST to lens.

        Returns:
            An OpenRecord containing the conformed data, or None if
            the convention's necessity criteria are not met.
        """
        ...


class MorphicLens:
    """A data-driven lens implementation that uses selectors.

    This lens uses a 'trigger' to determine applicability and a set of
    selectors to project AST blocks into an OpenRecord.
    """

    def __init__(
        self, name: str, trigger: dict[str, Any], selectors: dict[str, str]
    ) -> None:
        """Initialises the lens with a selection map.

        Args:
            name: Human-readable name of the convention.
            trigger: A dictionary pattern that triggers the lens
                (e.g. {'type': 'heading', 'text': 'Setup'}).
            selectors: A map of field names to AST selector strings.
        """
        self.name = name
        self.trigger = trigger
        self.selectors = selectors

    def project(self, ast: MarkdownAST) -> OpenRecord | None:
        """Projects the AST if the trigger is met.

        Currently uses simple heading-based triggers for Phase 1.

        Args:
            ast: The AST to lens.

        Returns:
            An OpenRecord or None.
        """
        # Phase 1: Simple trigger map check (e.g. {'type': 'heading', 'text': 'Setup'})
        trigger_type = self.trigger.get("type", "")
        if trigger_type == "heading":
            target_level = self.trigger.get("level", 2)
            target_text = self.trigger.get("text", "")

            found = False
            for block in ast.blocks:
                if (
                    block.type == "heading"
                    and block.attrs.get("level") == target_level
                    and block.attrs.get("text") == target_text
                ):
                    found = True
                    break
            if not found:
                return None
        elif trigger_type == "callout":
            # Phase 2 stub for callouts
            found = False
            for block in ast.blocks:
                if block.type == "paragraph":
                    content = block.attrs.get("content", "")
                    if content.startswith(
                        "> [!" + self.trigger.get("callout_type", "") + "]"
                    ):
                        found = True
                        break
            if not found:
                return None

        # Project each selector into the record's extra dictionary (Phase 2)
        data = {}
        for field, selector_str in self.selectors.items():
            val = ast.select(selector_str)
            if val is not None:
                data[field] = val

        return OpenRecord(convention=self.name, matched_trigger=self.trigger, **data)


class MorphismRegistry:
    """Registry for managing and applying the 'Battery of Lenses'.

    Provides a central dispatch for conventional discovery, allowing the system
    to treat documents as a superposition of conventions.
    """

    def __init__(self) -> None:
        """Initialises an empty morphism registry."""
        self._lenses: dict[str, Lens] = {}

    def register(self, name: str, lens: Lens) -> None:
        """Registers a named morphic lens.

        Args:
            name: The canonical name of the research convention (e.g. 'lab-protocol').
            lens: An object implementing the Lens protocol.
        """
        self._lenses[name] = lens

    def discover(self, ast: MarkdownAST) -> dict[str, OpenRecord]:
        """Performs a conventional discovery sweep across an AST.

        Applies all registered lenses and returns a map of successful projections.

        Args:
            ast: The MarkdownAST to explore.

        Returns:
            A dictionary mapping convention names to their successful projections.
        """
        projections: dict[str, OpenRecord] = {}
        for name, lens in self._lenses.items():
            result = lens.project(ast)
            if result is not None:
                projections[name] = result
        return projections

    def load_from_index(self, path: str) -> None:
        """Loads morphic lenses from a generated hot-lookup index.

        Args:
            path: Path to the .md file containing the index frontmatter.
        """
        engine = MarkdownEngine()
        try:
            doc = engine.read_file(path)
        except (OSError, ValueError):
            return

        if not doc.metadata:
            return

        index_map = getattr(doc.metadata, "index", {})
        for convention_id, data in index_map.items():
            if not isinstance(data, dict):
                continue

            trigger = data.get("trigger", {})
            selectors = data.get("selectors", {})
            lens = MorphicLens(name=convention_id, trigger=trigger, selectors=selectors)
            self.register(convention_id, lens)


def default_morphism_registry() -> MorphismRegistry:
    """Creates a standard morphism registry with core research lenses.

    Returns:
        A pre-configured MorphismRegistry.
    """
    registry = MorphismRegistry()
    # TODO: Register standard lenses once implemented
    return registry
