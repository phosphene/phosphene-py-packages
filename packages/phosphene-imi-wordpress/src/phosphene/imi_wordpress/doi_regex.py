"""Dedicated utility for ISO 26324 DOI grammar and protocol prefix handling.

Provides discrete operations for syntax validation, protocol stripping,
and canonical prefix/suffix decomposition.

@dft
- A1 (pure-io-separation): Pure string parsing logic — zero I/O imports.
- A2 (determinism): Pure regex patterns, completely deterministic.
- A4 (dft-docs): This docstring section.
"""

from __future__ import annotations

import re

# ISO 26324 DOI standard regex: prefix starting with '10.' followed by 4-9 digits, slash, and suffix (including SICI delimiters <>)
DOI_SYNTAX = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9<>]+$")

# Resolving URL and URI prefixes (case-insensitive)
PROTOCOL_PREFIX = re.compile(r"^(https?://(dx\.)?doi\.org/|doi:)", re.IGNORECASE)


def is_valid_doi(candidate: str | None) -> bool:
    """Determine if a candidate string satisfies ISO 26324 DOI syntax."""
    if not candidate:
        return False
    return bool(DOI_SYNTAX.match(candidate.strip()))


def strip_protocol_prefix(raw: str | None) -> str:
    """Strip leading URL or URI prefixes (e.g. 'https://doi.org/' or 'doi:')."""
    if not raw:
        return ""
    return PROTOCOL_PREFIX.sub("", raw.strip()).strip()


def split_doi(canonical_doi: str) -> tuple[str, str] | None:
    """Parse and split a DOI into its prefix and suffix parts.

    Returns (prefix, suffix) if syntax is valid, or None if invalid.
    """
    clean = strip_protocol_prefix(canonical_doi)
    if not is_valid_doi(clean):
        return None
    prefix, suffix = clean.split("/", 1)
    return prefix, suffix
