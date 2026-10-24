"""YamlStyle annotations for phosphene-frontmatters.

Provides metadata classes for use with typing.Annotated to specify YAML
morphological preferences (Implementation Adumbrations) that the shadow-patch
engine should respect during synchronization.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class YamlStyle:
    """Metadata class for specifying YAML serialization styles.

    Attributes:
        scalar_style: The YAML scalar style to use (e.g., '|', '>', '"', "'").
            None for default.
        indent: Custom indentation for this specific field.
        order: The relative order of this field in the generated YAML mapping.
    """

    scalar_style: str | None = None
    indent: int | None = None
    order: int | None = None
