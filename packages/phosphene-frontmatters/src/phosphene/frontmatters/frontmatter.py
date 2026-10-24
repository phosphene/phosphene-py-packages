"""Frontmatter processing for Research Stable markdown documents.

Provides high-fidelity YAML frontmatter processing with round-trip
formatting preservation and validation against Open-World models.
Supports the 'Shadow Patch' pattern for polite automation.

Legacy 'bare key' frontmatter (no --- delimiters) is supported for reading,
but will be migrated to standard YAML blocks on write.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from phosphene.mdrag.open_world import OpenRecord

from .core.manager import FrontmatterManager

# ──────────────────────────────────────────────────────────────────────
#  Model / Result types
# ──────────────────────────────────────────────────────────────────────


class OpenFrontmatter(OpenRecord):
    """An open-world primitive model for frontmatter.

    Acts as a bridge for un-schemaed documents, providing attribute
    access without rigid Pydantic rules.
    """


@dataclass(frozen=True)
class FrontmatterResult:
    """The result of parsing a markdown document.

    Attributes:
        model: The parsed OpenRecord model (Ideal state).
        body: The document body text.
        shadow: The ruamel.yaml shadow object (Physical state).
        source: Origin label (e.g., file path).
    """

    model: OpenRecord
    body: str
    shadow: Any
    source: str = "<string>"

    @property
    def fields(self) -> dict[str, Any]:
        """Returns the internal data as a raw dictionary."""
        return self.model.model_dump()

    def get(self, key: str, default: Any = None) -> Any:
        """Return field value by key, or default if absent.

        Supports both OpenRecord models (which expose ``.get()``) and
        Pydantic BaseModel subclasses (which do not). Falls back to
        ``getattr`` for models without a ``.get()`` method.
        """
        get_method = getattr(self.model, "get", None)
        if callable(get_method):
            return get_method(key, default)
        return getattr(self.model, key, default)

    def has(self, key: str) -> bool:
        """Return True if the key is present in the model.

        Supports both OpenRecord (``__contains__`` on ``_data``) and
        Pydantic models (``model_fields`` class attribute). Pydantic's
        ``__iter__`` yields ``(field, value)`` tuples, so ``key in model``
        silently returns False — we check ``model_fields`` instead.
        """
        if hasattr(self.model, "model_fields"):
            return key in self.model.model_fields
        try:
            return key in self.model
        except TypeError:
            return hasattr(self.model, key)


# ──────────────────────────────────────────────────────────────────────
#  Frontmatter API
# ──────────────────────────────────────────────────────────────────────


def parse(
    text: str, model_cls: type[OpenRecord] = OpenFrontmatter, source: str = "<string>"
) -> FrontmatterResult:
    """Parses frontmatter from markdown text using the high-fidelity manager."""
    manager = FrontmatterManager(model_cls)
    model, body, shadow = manager.load(text)
    return FrontmatterResult(model=model, body=body, shadow=shadow, source=source)


def read(
    path: Path, model_cls: type[OpenRecord] = OpenFrontmatter
) -> FrontmatterResult:
    """Reads a markdown file and parses its frontmatter."""
    text = Path(path).read_text(encoding="utf-8")
    return parse(text, model_cls=model_cls, source=str(path))


def write(result: FrontmatterResult, path: Path | None = None) -> str:
    """Serializes a FrontmatterResult back to a string and optionally saves to disk.

    Uses the Shadow Patch path: projects the Ideal model onto the existing
    Shadow to preserve human-authored comments and formatting.

    Args:
        result: FrontmatterResult from parse() or read().
        path: Optional file path to write the output to.

    Returns:
        The complete markdown document as a string.
    """
    manager = FrontmatterManager(result.model.__class__)
    content = manager.save(result.model, result.body, result.shadow)
    if path:
        Path(path).write_text(content, encoding="utf-8")
    return content


def render(data: dict[str, Any], body: str, path: Path | None = None) -> str:
    """Generate a markdown document from data + body. Pure serialisation.

    For generated (non-human-authored) content. No shadow, no patch,
    no comment preservation — there is no existing human content to protect.
    Uses the same ruamel.yaml engine as the Shadow Patch path via the
    shared render() method on FrontmatterManager.

    This function has no logic. It is a pure function: data in, string out.
    Any decisions about what to render belong in the caller.

    Args:
        data: Frontmatter data as a plain dict.
        body: Markdown body text.
        path: Optional file path to write the output to.

    Returns:
        Complete markdown string with --- delimited frontmatter.
    """
    manager = FrontmatterManager(OpenFrontmatter)
    content = manager.render(data, body)
    if path:
        Path(path).write_text(content, encoding="utf-8")
    return content
