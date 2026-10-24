"""Frontmatter Orchestrator for phosphene-frontmatters.

Provides the high-level API for interacting with markdown documents that
contain high-fidelity YAML frontmatter. Uses python-frontmatter for
boundary detection and ruamel.yaml for formatting-preserving serialization.
"""

from __future__ import annotations

from io import StringIO
from typing import TYPE_CHECKING, Any, TypeVar

import frontmatter
from ruamel.yaml import YAML

from .patch import apply_shadow_patch

if TYPE_CHECKING:
    from phosphene.mdrag.open_world import OpenRecord

T = TypeVar("T", bound="OpenRecord")


class FrontmatterManager:
    """Orchestrates high-fidelity frontmatter synchronization.

    Attributes:
        model_cls: The OpenRecord (or Ideal model) class used for validation.
        yaml: The ruamel.yaml instance configured for round-trip preservation.
    """

    def __init__(self, model_cls: type[T]) -> None:
        """Initializes the manager.

        Args:
            model_cls: The OpenRecord class serving as the Ideal contract.
        """
        self.model_cls = model_cls
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.indent(mapping=2, sequence=4, offset=2)

    def load(self, text: str) -> tuple[T, str, Any]:
        """Parses a markdown document into its Ideal model and Shadow object.

        Args:
            text: The raw markdown content.

        Returns:
            A tuple of (validated_model, body_text, ruamel_shadow_obj).
        """
        # 0. Legacy Bare-key handling
        # If text doesn't start with --- but visually begins with key:value pairs,
        # we wrap the first block in --- to enable standard parsing.
        cleaned_text = text.lstrip()
        if cleaned_text and not cleaned_text.startswith("---"):
            first_block = cleaned_text.split("\n\n")[0]
            # Simple heuristic: if it has lines and every line looks like a YAML key-value pair
            if first_block and all(
                ":" in line
                for line in first_block.splitlines()
                if line.strip() and not line.strip().startswith("#")
            ):
                text = (
                    "---\n"
                    + first_block
                    + "\n---\n\n"
                    + text[len(first_block) :].lstrip()
                )

        # 1. Detect boundaries and extract raw parts
        post = frontmatter.loads(text)

        # 2. Extract the raw metadata string for ruamel
        # Detect standard delimiters and extract the block.
        metadata_str = ""
        if text.strip().startswith("---"):
            # Parts: 0 (pre-delimiter), 1 (YAML), 2 (Body)
            parts = text.split("---", 2)
            if len(parts) >= 3:
                metadata_str = parts[1]

        # 3. Load into ruamel Shadow object
        # If we found a raw block, use it. Otherwise uses {} as base.
        if metadata_str:
            shadow_obj = self.yaml.load(metadata_str)
        else:
            # Bare keys or No Metadata case
            # We treat the existing post.metadata as the starting point
            # if it was a bare key document.
            shadow_obj = post.metadata
        if shadow_obj is None:
            shadow_obj = {}

        # 3. Validate into the Ideal model (OpenRecord)
        # Note: we use post.metadata as the source for validation because
        # python-frontmatter handles bare keys and various delimiters well.
        model = self.model_cls.model_validate(post.metadata)

        return model, post.content, shadow_obj

    def render(self, data: dict[str, Any] | CommentedMap, body: str) -> str:
        """Serialise data + body to a markdown string. Pure.

        No logic, no decisions, no state. Accepts either a plain dict or
        a ruamel.yaml CommentedMap. A plain dict is wrapped in a fresh
        CommentedMap (generate path — no comments to preserve). A CommentedMap
        is dumped directly, preserving any comments it carries (save path).

        This is the single serialisation code path for the entire package.
        Both save() and the public render() API route through here.

        Args:
            data: Frontmatter data — plain dict or CommentedMap.
            body: Markdown body text.

        Returns:
            Complete markdown string with --- delimited frontmatter.
        """
        from ruamel.yaml.comments import CommentedMap

        if not isinstance(data, CommentedMap):
            data = CommentedMap(data)
        stream = StringIO()
        self.yaml.dump(data, stream)
        yaml_text = stream.getvalue().strip()
        output: list[str] = []
        if yaml_text:
            output.append("---\n")
            output.append(yaml_text)
            output.append("\n---\n\n")
        output.append(body.strip() + "\n")
        return "".join(output)

    def save(self, model: T, body: str, shadow_obj: Any) -> str:
        """Serializes the document back to Markdown with preserved formatting.

        Projects the Ideal model onto the Shadow via apply_shadow_patch,
        then delegates to render() passing the patched CommentedMap directly.
        Comments and formatting encoded in the Shadow are preserved because
        the CommentedMap is passed through without conversion to plain dict.

        Args:
            model: The updated Ideal model (OpenRecord).
            body: The markdown body text.
            shadow_obj: The ruamel.yaml Shadow object to patch and serialize.

        Returns:
            The complete markdown document as a string.
        """
        from ruamel.yaml.comments import CommentedMap

        if not isinstance(shadow_obj, CommentedMap):
            new_map = CommentedMap()
            if isinstance(shadow_obj, dict):
                new_map.update(shadow_obj)
            shadow_obj = new_map
        apply_shadow_patch(shadow_obj, model)
        return self.render(shadow_obj, body)
