import re
from typing import Any

from .patterns import COORDINATE_PATTERN


def uri_header_plugin(md):
    """Mistune plugin to parse 'uri: ...' at the start of the file (Legacy fallback)."""


def coordinate_plugin(md):
    """Mistune plugin to parse inline {:coordinate} patterns."""

    def parse_coordinate(inline: Any, m: re.Match, state: Any) -> tuple[str, str]:
        """Parses a coordinate inline pattern into a token.

        Args:
            inline: The Mistune inline parser instance.
            m: The regex match object.
            state: The Mistune parser state.

        Returns:
            A tuple of (token_type, value).
        """
        # In mistune 3.x, return (token_type, value) for inline tokens
        return "coordinate", m.group(1)

    md.inline.register(
        "coordinate", COORDINATE_PATTERN, parse_coordinate, before="link"
    )
