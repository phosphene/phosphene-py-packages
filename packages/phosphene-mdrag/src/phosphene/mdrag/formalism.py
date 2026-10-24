"""formalism.py — Formalism block: frontmatter-native read, write, and render.

Implements the formalism block convention using the frontmatters + mdrag
stack exclusively. Formalisms are stored as a ``formalisms:`` YAML sequence
in document frontmatter; the ``## The Formalism`` body section is a
human-readable rendering produced by ``FormalismRenderer``.

Three concerns, three classes:

- ``FormalismReader`` — reads ``formalisms:`` from frontmatter via
  ``phosphene.frontmatters.frontmatter.read()``.
- ``FormalismWriter`` — patches ``formalisms:`` back into frontmatter via
  the shadow-patch write path; preserves all existing formatting.
- ``FormalismRenderer`` — renders a ``FormalismResult`` as the canonical
  ``## The Formalism`` markdown section. Pure; no IO.

No regular expressions. No raw string parsing. Data is YAML; structure is
AST headings. The two concerns are separated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from phosphene.frontmatters.frontmatter import read as fm_read
from phosphene.frontmatters.frontmatter import write as fm_write

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

#: Canonical field names accepted in a frontmatter formalism entry.
KNOWN_FIELDS: frozenset[str] = frozenset(
    {
        "name",
        "expression",
        "variables",
        "operational_role",
        "tension",
        "source",
        "ct_structure",
    }
)

#: Frontmatter key under which formalism entries are stored.
FORMALISMS_KEY: str = "formalisms"

#: Level-2 heading texts that introduce the rendered formalism section.
FORMALISM_HEADINGS: frozenset[str] = frozenset(
    {"The Formalism", "Formalisms", "Formalism"}
)


@dataclass(frozen=True)
class FormalismEntry:
    """A single named formalism entry.

    Attributes:
        name: The formalism's display name (used as ``###`` heading when rendered).
        expression: The mathematical expression or formula. Required.
        operational_role: What the formula does in the theory's own terms. Required.
        tension: Where the formalism exposes internal failure or empirical mismatch.
            Required — embeds the Hilbert/Braithwaite testing protocol in structure.
        variables: Optional list of ``symbol: definition`` strings.
        source: Optional attribution string (author, year).
        ct_structure: Optional category-theoretic object the formalism maps to.
        extra_fields: Any frontmatter fields beyond the known set, preserved
            open-world.
    """

    name: str
    expression: str
    operational_role: str
    tension: str
    variables: list[str] = field(default_factory=list)
    source: str = ""
    ct_structure: str = ""
    extra_fields: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FormalismEntry:
        """Construct a FormalismEntry from a raw frontmatter dict.

        Known fields are mapped to typed attributes. Unknown fields are
        preserved in ``extra_fields`` under the open-world assumption.

        Args:
            data: Raw dict from a ``formalisms:`` frontmatter entry.

        Returns:
            A typed, frozen FormalismEntry.
        """
        known = {k: v for k, v in data.items() if k in KNOWN_FIELDS}
        extra = {k: v for k, v in data.items() if k not in KNOWN_FIELDS}
        variables = known.pop("variables", [])
        if isinstance(variables, str):
            variables = [variables]
        return cls(
            name=known.get("name", ""),
            expression=known.get("expression", ""),
            operational_role=known.get("operational_role", ""),
            tension=known.get("tension", ""),
            variables=list(variables),
            source=known.get("source", ""),
            ct_structure=known.get("ct_structure", ""),
            extra_fields=extra,
        )

    def is_valid(self) -> bool:
        """Return True if the entry has the minimum required content.

        A valid entry has a non-empty expression, operational_role, and
        tension. Name is also required for rendered output.

        Returns:
            True if all required fields are non-empty.
        """
        return bool(
            self.name.strip()
            and self.expression.strip()
            and self.operational_role.strip()
            and self.tension.strip()
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict suitable for frontmatter storage.

        Empty optional fields are omitted. Extra fields are merged at
        the top level.

        Returns:
            Dict representation for the ``formalisms:`` frontmatter sequence.
        """
        out: dict[str, Any] = {
            "name": self.name,
            "expression": self.expression,
            "operational_role": self.operational_role,
            "tension": self.tension,
        }
        if self.variables:
            out["variables"] = list(self.variables)
        if self.source:
            out["source"] = self.source
        if self.ct_structure:
            out["ct_structure"] = self.ct_structure
        out.update(self.extra_fields)
        return out


@dataclass
class FormalismResult:
    """All formalism entries for a single document.

    Attributes:
        source_uri: The document's corpus URI.
        entries: List of FormalismEntry objects in document order.
    """

    source_uri: str
    entries: list[FormalismEntry] = field(default_factory=list)

    def has_content(self) -> bool:
        """Return True if at least one valid entry exists.

        Returns:
            True if any entry passes ``is_valid()``.
        """
        return any(e.is_valid() for e in self.entries)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict for index emission.

        Returns:
            Dict with source_uri and valid entries list.
        """
        return {
            "source_uri": self.source_uri,
            "entries": [e.to_dict() for e in self.entries if e.is_valid()],
        }


# ---------------------------------------------------------------------------
# Reader
# ---------------------------------------------------------------------------


class FormalismReader:
    """Reads formalism entries from a document's frontmatter.

    Uses ``phosphene.frontmatters.frontmatter.read()`` to parse the
    ``formalisms:`` YAML key. No body parsing. No regex.
    """

    def read(self, path: Path) -> FormalismResult | None:
        """Read formalisms from a document's frontmatter.

        Returns None when the document has no ``formalisms:`` key —
        absence and emptiness are distinguished.

        Args:
            path: Absolute or relative path to the markdown document.

        Returns:
            FormalismResult if the key exists, None otherwise.
        """
        result = fm_read(path)
        raw = result.get(FORMALISMS_KEY, None)
        if raw is None:
            return None
        source_uri = result.get("uri", str(path))
        entries = [
            FormalismEntry.from_dict(item) for item in raw if isinstance(item, dict)
        ]
        return FormalismResult(source_uri=str(source_uri), entries=entries)


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------


class FormalismWriter:
    """Writes formalism entries into a document's frontmatter.

    Uses the shadow-patch write path from ``phosphene.frontmatters`` to
    preserve all existing formatting, comments, and non-formalism fields.
    """

    def _patch(self, path: Path, entries: list[dict[str, Any]]) -> None:
        """Internal: update formalisms in both model and shadow, then write.

        The shadow-patch engine projects the ideal model onto the shadow.
        For open-world fields that already exist in the model, the model's
        value wins over any shadow-only update. Both must be updated in
        concert to ensure the written output reflects the intended state.

        Args:
            path: Absolute or relative path to the markdown document.
            entries: Serialised entry dicts to store under FORMALISMS_KEY.
        """
        fm_result = fm_read(path)
        setattr(fm_result.model, FORMALISMS_KEY, entries)
        fm_result.shadow[FORMALISMS_KEY] = entries
        fm_write(fm_result, path)

    def write(self, path: Path, result: FormalismResult) -> None:
        """Patch the ``formalisms:`` key in a document's frontmatter.

        Reads the existing document, updates both the ideal model and shadow
        with the serialised entries, and writes back. Only valid entries are
        persisted. All other frontmatter fields and body content are preserved.

        Args:
            path: Absolute or relative path to the markdown document.
            result: The FormalismResult to serialise into frontmatter.
        """
        self._patch(path, [e.to_dict() for e in result.entries if e.is_valid()])

    def add_entry(self, path: Path, entry: FormalismEntry) -> None:
        """Append a single formalism entry to an existing document.

        If the document already has a ``formalisms:`` key, the new entry
        is appended. If the key is absent, it is created.

        Args:
            path: Absolute or relative path to the markdown document.
            entry: The FormalismEntry to append. Must pass is_valid().

        Raises:
            ValueError: If the entry does not pass is_valid().
        """
        if not entry.is_valid():
            raise ValueError(
                f"FormalismEntry '{entry.name}' is not valid: "
                "expression, operational_role, and tension are required."
            )
        fm_result = fm_read(path)
        existing = list(getattr(fm_result.model, FORMALISMS_KEY, None) or [])
        existing.append(entry.to_dict())
        self._patch(path, existing)


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


class FormalismRenderer:
    """Renders a FormalismResult as the canonical ## The Formalism section.

    Pure: no IO, no state. Produces the human-readable body section from
    the structured frontmatter data. The rendered section is the display
    view; frontmatter is the source of truth.
    """

    def render(self, result: FormalismResult) -> str:
        """Render a FormalismResult as a ## The Formalism markdown section.

        Only valid entries are rendered. The section heading adjusts
        automatically: ``## The Formalism`` for a single entry,
        ``## Formalisms`` for multiple.

        Args:
            result: The FormalismResult to render.

        Returns:
            A markdown string for the ## The Formalism / ## Formalisms block.
        """
        valid = [e for e in result.entries if e.is_valid()]
        if not valid:
            return ""

        heading = "The Formalism" if len(valid) == 1 else "Formalisms"
        lines: list[str] = [f"## {heading}", ""]

        for entry in valid:
            lines.append(f"### {entry.name}")
            lines.append("")
            lines.append(f"**Expression:** `{entry.expression}`")
            lines.append("")
            if entry.variables:
                lines.append("**Variables:**")
                for var in entry.variables:
                    lines.append(f"- {var}")
                lines.append("")
            lines.append(f"**Operational Role:** {entry.operational_role}")
            lines.append("")
            lines.append(f"**Tension / Perturbation:** {entry.tension}")
            if entry.source:
                lines.append("")
                lines.append(f"**Source:** {entry.source}")
            if entry.ct_structure:
                lines.append("")
                lines.append(f"**CT Structure:** {entry.ct_structure}")
            lines.append("")

        return "\n".join(lines)

    def render_entry(self, entry: FormalismEntry) -> str:
        """Render a single FormalismEntry as a ### subsection.

        Args:
            entry: The FormalismEntry to render. Must pass is_valid().

        Returns:
            A markdown string for the ### subsection, or empty string if invalid.
        """
        if not entry.is_valid():
            return ""
        result = FormalismResult(source_uri="", entries=[entry])
        rendered = self.render(result)
        lines = rendered.splitlines()
        # Strip the ## heading line and the blank line after it
        if lines and lines[0].startswith("## "):
            lines = lines[2:]
        return "\n".join(lines)
