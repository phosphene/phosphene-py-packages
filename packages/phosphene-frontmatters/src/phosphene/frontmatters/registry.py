"""Registry scanning and filtering for platform markdown assets.

Provides a functional pipeline for discovering, parsing, and filtering
markdown documents by their frontmatter fields. Updated to support
schema-driven discovery using Pydantic models.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from phosphene.mdrag.open_world import OpenRecord

from .frontmatter import (
    FrontmatterResult,
    OpenFrontmatter,
    read,
)

T = TypeVar("T", bound="OpenRecord")


# ──────────────────────────────────────────────────────────────────────
#  RegistryEntry — the unit of work
# ──────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RegistryEntry:
    """A single discovered markdown document with its parsed frontmatter.

    Attributes:
        path: Absolute path to the source file.
        result: High-fidelity parsed result for this document.
    """

    path: Path
    result: FrontmatterResult

    def get(self, field: str, default: Any = None) -> Any:
        """Return a frontmatter field value.

        Args:
            field: Frontmatter field name.
            default: Value returned when the field is absent.
        """
        return self.result.get(field, default)

    def has(self, field: str) -> bool:
        """Return True if the frontmatter contains the given field."""
        return self.result.has(field)


# ──────────────────────────────────────────────────────────────────────
#  scan — directory discovery
# ──────────────────────────────────────────────────────────────────────


def scan(
    root: Path,
    glob: str = "**/*.md",
    model_cls: type[OpenRecord] = OpenFrontmatter,
) -> list[RegistryEntry]:
    """Scan a directory for markdown files and parse their frontmatter.

    Discovers all files matching the glob pattern under root, parses
    each into the given model, and returns a list of RegistryEntry objects.

    Args:
        root: Directory to scan. Must exist.
        glob: Glob pattern relative to root.
        model_cls: Pydantic model class to use for validation.

    Returns:
        List of RegistryEntry, sorted by path.
    """
    if not root.exists():
        raise FileNotFoundError(f"Registry root not found: {root}")

    entries: list[RegistryEntry] = []
    for path in sorted(root.glob(glob)):
        if not path.is_file():
            continue
        try:
            result = read(path, model_cls=model_cls)
            entries.append(RegistryEntry(path=path, result=result))
        except UnicodeDecodeError:
            continue
        except Exception:
            import traceback

            traceback.print_exc()
            continue

    return entries


# ──────────────────────────────────────────────────────────────────────
#  filter_by — field-based selection
# ──────────────────────────────────────────────────────────────────────


def filter_by(
    entries: list[RegistryEntry],
    field: str,
    value: Any = None,
) -> list[RegistryEntry]:
    """Filter registry entries by frontmatter field presence or value."""
    if value is None:
        return [e for e in entries if e.has(field)]
    return [e for e in entries if e.get(field) == value]


# ──────────────────────────────────────────────────────────────────────
#  sort_by — field-based ordering
# ──────────────────────────────────────────────────────────────────────


def sort_by(
    entries: list[RegistryEntry],
    field: str,
    default: Any = "",
    reverse: bool = False,
) -> list[RegistryEntry]:
    """Sort registry entries by a frontmatter field value."""
    return sorted(entries, key=lambda e: e.get(field, default), reverse=reverse)


# ──────────────────────────────────────────────────────────────────────
#  iter_namespace — yield entries matching a URI prefix
# ──────────────────────────────────────────────────────────────────────


def iter_namespace(
    entries: list[RegistryEntry],
    prefix: str,
) -> Iterator[RegistryEntry]:
    """Yield entries whose URI field starts with the given prefix."""
    for entry in entries:
        uri = entry.get("uri")
        if uri and str(uri).startswith(prefix):
            yield entry
