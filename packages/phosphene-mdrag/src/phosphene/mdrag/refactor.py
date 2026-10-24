"""Structurally-aware transformer for research wiki documents.

Applies namespace migration, WikiLink normalisation, and identity parity
correction to MarkdownAST objects. Operates on the generic Block model —
no named block classes imported.
"""

from __future__ import annotations

import re

from .models import Block, MarkdownAST

# Namespace mapping for the wiki audit
NS_MAPPING = {
    "bio": "sci.bio",
    "origins": "sci.origins",
}


class RefactorTransformer:
    """Structurally-aware transformer for research documents."""

    def __init__(self, filepath: str):
        """Initializes the transformer with a target file path.

        Args:
            filepath: The path to the file being refactored, used to derive
                the expected document identity.
        """
        self.filepath = filepath
        # Standardize expected ID from filepath
        if "research-wiki/wiki/" in filepath:
            self.expected_id = filepath.split("research-wiki/wiki/")[-1].replace(
                ".md", ""
            )
        else:
            self.expected_id = filepath.replace(".md", "")

    def transform(self, ast: MarkdownAST) -> MarkdownAST:
        """Applies structural and content refactoring rules to a MarkdownAST.

        This includes updating metadata (id, ns, uri), normalizing WikiLinks,
        and ensuring consistency across all block types.

        Args:
            ast: The input MarkdownAST model.

        Returns:
            A new, refactored MarkdownAST model.
        """
        new_metadata = ast.metadata

        # 1. Update Metadata
        if ast.metadata:
            update_data = {"id": self.expected_id}

            # Update Namespace if legacy
            current_ns = ast.metadata.ns or getattr(ast.metadata, "namespace", None)
            if current_ns in NS_MAPPING:
                update_data["ns"] = NS_MAPPING[current_ns]

            # Seed URI if legacy
            current_uri = ast.metadata.uri
            for old, new in NS_MAPPING.items():
                if current_uri.startswith(f"{old}/"):
                    update_data["uri"] = current_uri.replace(f"{old}/", f"{new}/")

            # Use dictionary manipulation to remove extra legacy fields
            from .models import Metadata

            meta_dict = ast.metadata.model_dump()
            meta_dict.update(update_data)
            if "namespace" in meta_dict:
                del meta_dict["namespace"]

            # Remediate links in metadata fields (related, etc)
            if "related" in meta_dict and isinstance(meta_dict["related"], list):
                # Ensure we don't double-nest or fail on non-strings
                meta_dict["related"] = [
                    self._fix_links(lnk) if isinstance(lnk, str) else lnk
                    for lnk in meta_dict["related"]
                ]

            new_metadata = Metadata.model_validate(meta_dict)

        # 2. Transform Blocks (WikiLinks and Slugs)
        new_blocks = []
        for block in ast.blocks:
            new_blocks.append(self._transform_block(block))

        return ast.model_copy(
            update={
                "metadata": new_metadata,
                "blocks": new_blocks,
                "uri": new_metadata.uri if new_metadata else ast.uri,
            }
        )

    def _transform_block(self, block: Block) -> Block:
        """Recursively transforms a single block's content.

        Args:
            block: A Markdown block (Paragraph, Heading, etc.).

        Returns:
            A new block with transformed content.
        """
        if block.type == "paragraph":
            return block.model_copy(
                update={
                    "attrs": {
                        **block.attrs,
                        "content": self._fix_links(block.attrs["content"]),
                    }
                }
            )
        elif block.type == "heading":
            return block.model_copy(
                update={
                    "attrs": {
                        **block.attrs,
                        "text": self._fix_links(block.attrs["text"]),
                    }
                }
            )
        elif block.type == "list":
            new_items = [self._fix_links(item) for item in block.attrs["items"]]
            return block.model_copy(
                update={"attrs": {**block.attrs, "items": new_items}}
            )
        return block

    def _fix_links(self, text: str) -> str:
        """Normalizes WikiLinks and Coordinate slugs within a text string.

        This performs namespace mapping and converts display names to
        lowercase kebab-case slugs.

        Args:
            text: The raw text content to process.

        Returns:
            The transformed text with normalized links.
        """
        # 1. Namespace mapping
        for old, new in NS_MAPPING.items():
            text = text.replace(f"[[{old}/", f"[[{new}/")
            text = text.replace(f"{{{old}/", f"{{{new}/")

        # 2. Slugification (Lowercase and kebab-case)
        # Pattern: [[sci.bio/Michael Levin]] -> [[sci.bio/michael-levin]]
        def slugify_match(match: re.Match) -> str:
            """Slugifies a wiki link or reference match.

            Args:
                match: The regex match object for a wiki link.

            Returns:
                The slugified replacement string.
            """
            prefix = match.group(1)  # [[ or {
            ns_slug = match.group(2)  # sci.bio/Michael Levin
            suffix = match.group(3)  # ]] or }

            if "/" in ns_slug:
                ns, slug = ns_slug.split("/", 1)
                slug = slug.lower().strip().replace(" ", "-")
                return f"{prefix}{ns}/{slug}{suffix}"
            return match.group(0)

        # Match [[ns/slug]] or {ns/slug}
        text = re.sub(r"(\[\[|{)(.*?)(\]\]|})", slugify_match, text)
        return text


def refactor_file(engine, filepath: str) -> str:
    """Orchestrates the end-to-end refactoring of a single Markdown file.

    Args:
        engine: The MarkdownEngine instance to use for reading.
        filepath: Path to the markdown file on disk.

    Returns:
        The refactored Markdown text as a string.
    """
    ast = engine.read(filepath)
    transformer = RefactorTransformer(filepath)
    transformed_ast = transformer.transform(ast)

    # We need a renderer to go back to Markdown string
    # Assuming MarkdownAST/engine will provide a render method or similar
    # For now, we'll use a placeholder or implement a simple one
    from .renderer import MarkdownRenderer

    renderer = MarkdownRenderer()
    return renderer.render(transformed_ast)
