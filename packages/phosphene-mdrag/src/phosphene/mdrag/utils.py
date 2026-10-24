"""utils.py — Shared mdrag utilities for structural extraction and manipulation."""

from __future__ import annotations

import re
from typing import NamedTuple


class BlockRegion(NamedTuple):
    """A region of text extracted from a larger document.

    Attributes:
        before: Text preceding the extracted region.
        content: The core extracted text content.
        after: Text following the extracted region.
    """

    before: str
    content: str
    after: str


def extract_evolve_block(code: str) -> BlockRegion:
    """Extract the EVOLVE-BLOCK region from Python source code.

    Uses a marker-based approach but enforces the 'before/content/after'
    triplet structure to ensure lossless replacement.

    Args:
        code: Full Python source code.

    Returns:
        BlockRegion containing the split source code.
    """
    start_marker = "# EVOLVE-BLOCK-START"
    end_marker = "# EVOLVE-BLOCK-END"

    # Use regex to find markers at start of line (more robust than find)
    start_match = re.search(rf"^{start_marker}", code, re.MULTILINE)
    end_match = re.search(rf"^{end_marker}", code, re.MULTILINE)

    if not start_match or not end_match:
        return BlockRegion(before="", content=code, after="")

    start_idx = start_match.start()
    end_idx = end_match.end()

    # Content is between the lines containing the markers
    # We want to preserve the markers in before/after
    before = code[: start_idx + len(start_marker)]
    content = code[start_idx + len(start_marker) : end_match.start()].strip("\n")
    after = code[end_match.start() :]

    return BlockRegion(before=before, content=content, after=after)


def replace_evolve_block(original: str, new_content: str) -> str:
    """Replace the EVOLVE-BLOCK content in original source code.

    Args:
        original: The original full source code string.
        new_content: The new content to place between markers.

    Returns:
        Full source code with the core block replaced.
    """
    region = extract_evolve_block(original)
    return f"{region.before}\n{new_content.strip()}\n{region.after}"
