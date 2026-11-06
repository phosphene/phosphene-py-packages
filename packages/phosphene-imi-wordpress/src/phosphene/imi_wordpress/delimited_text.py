"""Dedicated utility for parsing and assembling newline- and comma-delimited lists.

Enforces strict whitespace trimming, carriage-return scrubbing, and null/empty omission.

@dft
- A1 (pure-io-separation): Pure string parsing logic — zero I/O imports.
- A2 (determinism): Pure string manipulation, completely deterministic.
- A4 (dft-docs): This docstring section.
"""

from __future__ import annotations

from collections.abc import Iterable


def split_lines(raw: str) -> tuple[str, ...]:
    """Parse newline-delimited text into a clean tuple of trimmed, non-empty strings."""
    if not raw.strip():
        return ()
    normalized = raw.replace("\r", "")
    return tuple(line.strip() for line in normalized.split("\n") if line.strip())


def join_lines(items: Iterable[str]) -> str:
    """Join an iterable of items with newline delimiters, omitting empty elements."""
    filtered = [str(item).strip() for item in items if str(item).strip()]
    return "\n".join(filtered)


def split_commas(raw: str) -> tuple[str, ...]:
    """Parse comma-delimited text into a clean tuple of trimmed, non-empty strings."""
    if not raw.strip():
        return ()
    return tuple(item.strip() for item in raw.split(",") if item.strip())


def join_commas(items: Iterable[str]) -> str:
    """Join an iterable of items with comma delimiters, omitting empty elements."""
    filtered = [str(item).strip() for item in items if str(item).strip()]
    return ", ".join(filtered)
