"""Legacy body utilities for un-schemaed markdown documents.

These utilities preserve FKA logic for legacy documents that lack explicit
high-fidelity frontmatter attributes, allowing the platform to fall back
on structural inference (e.g. taking the first heading as a title).
"""

from __future__ import annotations


def extract_body_title(body: str) -> str:
    """Extract the first heading from the document body."""
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return ""


def extract_first_body_paragraph(body: str) -> str:
    """Extract the first non-heading paragraph from the document body."""
    para_lines: list[str] = []
    past_heading = False

    for line in body.splitlines():
        stripped = line.strip()

        if stripped.startswith("#"):
            if para_lines:
                break
            past_heading = True
            continue

        if not stripped and para_lines:
            break

        if stripped:
            if not past_heading:
                continue
            para_lines.append(stripped)

    return " ".join(para_lines)
