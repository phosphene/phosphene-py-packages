"""Dedicated utility for ISO 27729 (ISNI) ORCID identifier syntax and URI resolution.

Provides discrete operations for syntax validation, URI prefix stripping,
and canonical URI generation.

@dft
- A1 (pure-io-separation): Pure string parsing logic — zero I/O imports.
- A2 (determinism): Pure regex patterns, completely deterministic.
- A4 (dft-docs): This docstring section.
"""

from __future__ import annotations

import re

# ISO 27729 / ISNI ORCID standard regex: 16 digits hyphenated in 4 groups with check digit
ORCID_SYNTAX = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")

# Resolving URI prefixes (case-insensitive)
ORCID_URI_PREFIX = re.compile(r"^https?://orcid\.org/", re.IGNORECASE)


def is_valid_orcid(candidate: str | None) -> bool:
    """Determine if a candidate string satisfies canonical ORCID syntax."""
    if not candidate:
        return False
    return bool(ORCID_SYNTAX.match(candidate.strip()))


def canonicalize_orcid(raw: str | None) -> str:
    """Strip leading URI prefix (e.g. 'https://orcid.org/') and return canonical digits."""
    if not raw:
        return ""
    return ORCID_URI_PREFIX.sub("", raw.strip()).strip()


def to_orcid_uri(orcid: str | None) -> str:
    """Format a canonical ORCID into its full permanent URI."""
    clean = canonicalize_orcid(orcid)
    if not clean:
        return ""
    return f"https://orcid.org/{clean}"
