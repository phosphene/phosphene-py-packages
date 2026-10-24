"""URI validation, slugification, and fragment pattern helpers for mdrag.

Defines the Hickey-style URI validator used by Pydantic models, the slugify
helper for heading-to-fragment conversion, and compiled regex patterns for
section fragment parsing.
"""

from __future__ import annotations

import re

from .patterns import URI_PATTERN

# Regex for section fragment: #{type}.{N}, #{N}, or #{slug}
FRAGMENT_TYPE_INDEX = re.compile(r"^([a-z]+)\.(\d+)$")
FRAGMENT_SEQ_INDEX = re.compile(r"^(\d+)$")


def validate_hickey_uri(v: str) -> str:
    """Validate that a string conforms to the Hickey-style URI format.

    The format is ``namespace/slug`` where namespace contains letters,
    numbers, and dots (must start with letter/number), and the slug
    contains letters, numbers, and hyphens.

    Args:
        v: The URI string to validate.

    Returns:
        The validated URI string, unchanged.

    Raises:
        ValueError: If the URI format is invalid.
    """
    if not URI_PATTERN.match(v):
        raise ValueError(
            f"Invalid URI format: '{v}'. "
            "Expected 'namespace/slug' (e.g., 'sci.bio/sapolsky-v1')."
        )
    return v


def slugify(text: str) -> str:
    """Convert heading text to a URL-safe fragment slug.

    Lowercases, replaces non-alphanumeric characters with hyphens,
    and collapses consecutive hyphens.

    Args:
        text: The raw heading text (e.g., ``'Stress and Dominance'``).

    Returns:
        A slug suitable for use as a URI fragment
        (e.g., ``'stress-and-dominance'``).

    Examples:
        >>> slugify('Stress and Dominance')
        'stress-and-dominance'
        >>> slugify('Block 1: Origins')
        'block-1-origins'
    """
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def get_namespace(uri: str) -> str | None:
    """Extract the namespace component from a Hickey-style URI.

    Args:
        uri: The full URI string (e.g., ``'sci.bio/sapolsky-v1'``).

    Returns:
        The namespace portion (e.g., ``'sci.bio'``), or ``None`` if
        the URI is invalid.
    """
    match = URI_PATTERN.match(uri)
    return match.group(1) if match else None
