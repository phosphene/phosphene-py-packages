"""Graduated Discovery Engine — Stage 2 Interface layer.

Provides an efficient query surface over the Workspace Registry, allowing
agents to reason about the knowledge graph using summaries and routing tags
(relevant_when) before committing to full document ingestion (Stage 3).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pydantic import Field

from phosphene.frontmatters import frontmatter
from phosphene.mdrag.core import InvariantStatic


@runtime_checkable
class DocumentRegistry(Protocol):
    """Protocol for reading registry configuration and namespace registries."""

    def read_index(self, registry_path: Path) -> dict[str, Any]:
        """Reads and returns the Stage 1 workspace index fields."""
        ...

    def read_namespace(self, registry_path: Path, relative_path: str) -> dict[str, Any]:
        """Reads and returns a Stage 2 namespace registry's fields."""
        ...


class FilesystemDocumentRegistry:
    """Standard filesystem-backed DocumentRegistry implementation."""

    def read_index(self, registry_path: Path) -> dict[str, Any]:
        """Reads Stage 1 registry index from filesystem."""
        if not registry_path.exists():
            raise FileNotFoundError(f"Stage 1 registry not found at {registry_path}")
        return frontmatter.read(registry_path).fields

    def read_namespace(self, registry_path: Path, relative_path: str) -> dict[str, Any]:
        """Reads Stage 2 namespace registry from filesystem."""
        workspace_root = registry_path.parent.parent
        ns_path = workspace_root / relative_path
        if not ns_path.exists():
            return {}
        return frontmatter.read(ns_path).fields


class DocumentInterface(InvariantStatic):
    """Stage 2 metadata record for a document.

    Provides enough context for an agent to decide if a document is
    relevant to the current task.

    Attributes:
        uri: The addressable Hickey coordinate.
        path: Path relative to workspace root.
        summary: Abstract or inferred first paragraph.
        relevant_when: Routing tags explaining when this doc should be loaded.
        sections: Map of slug -> Title for internal fragment navigation.
        owner: The primary researcher or maintainer.
        capabilities: List of detected morphic capabilities (lenses).
    """

    uri: str
    path: str
    summary: str = ""
    relevant_when: list[str] = Field(default_factory=list)
    owner: str = ""
    sections: dict[str, str] = Field(default_factory=dict)
    capabilities: list[str] = Field(default_factory=list)


class DiscoveryEngine:
    """Service for querying the Graduated Discovery Registry.

    Acts as a 'Registry Functor', projecting the physical tiered registries
    (WORKSPACE_REGISTRY.md + meta/namespaces/*.md) into a queryable Pythonic
    interface.
    """

    def __init__(
        self,
        registry_path: Path | None = None,
        registry: DocumentRegistry | None = None,
    ) -> None:
        """Initialises the engine.

        Args:
            registry_path: Path to the Stage 1 WORKSPACE_REGISTRY.md.
                Defaults to searching upwards for 'meta/WORKSPACE_REGISTRY.md'.
            registry: Optional DocumentRegistry interface for reading
                index/namespace registries.
        """
        if registry_path is None:
            # Heuristic to find meta/WORKSPACE_REGISTRY.md
            curr = Path(__file__).resolve()
            while curr != curr.parent:
                potential = curr / "meta" / "WORKSPACE_REGISTRY.md"
                if potential.exists():
                    registry_path = potential
                    break
                curr = curr.parent

        self.registry_path = registry_path
        self.registry = registry or FilesystemDocumentRegistry()
        self._registry: dict[str, Any] = {}
        self._initialized = False

    def load_registry(self, namespaces: list[str] | None = None) -> None:
        """Parses the tiered registry starting from Stage 1.

        Args:
            namespaces: Optional list of specific namespaces to load.
                        If None, all namespaces defined in Stage 1 are loaded.

        Raises:
            FileNotFoundError: If the registry files are missing.
            ValueError: If the registry format is malformed.
        """
        if not self.registry_path:
            raise FileNotFoundError("Stage 1 registry path is not specified.")

        # Load Stage 1 Index
        stage1 = self.registry.read_index(self.registry_path)
        ns_map = stage1.get("namespaces", {})
        if not ns_map:
            # Fallback for legacy monolithic registries
            self._registry = stage1.get("registry", {})
            self._initialized = True
            return

        self._registry = {}

        # Load Stage 2 Namespace Registries
        target_namespaces = namespaces or list(ns_map.keys())
        for ns in target_namespaces:
            if ns not in ns_map:
                continue

            ns_rel_path = ns_map[ns].get("registry")
            if not ns_rel_path:
                continue

            stage2 = self.registry.read_namespace(self.registry_path, ns_rel_path)
            self._registry.update(stage2.get("registry", {}))

        self._initialized = True

    def query(
        self, ns: str | None = None, relevant_when: str | list[str] | None = None
    ) -> list[DocumentInterface]:
        """Filters the registry for matching Stage 2 interfaces.

        Args:
            ns: Namespace prefix (e.g., 'biol').
            relevant_when: One or more routing tags to match.

        Returns:
            List of matching DocumentInterface records.
        """
        if not self._initialized:
            # If a specific namespace is requested, we can optimize by only loading that
            self.load_registry(namespaces=[ns] if ns else None)

        results = []

        target_tags = (
            [relevant_when] if isinstance(relevant_when, str) else (relevant_when or [])
        )

        for uri, data in self._registry.items():
            # Namespace filter
            if ns and not uri.startswith(f"{ns}/"):
                continue

            # Routing tag filter
            doc_tags = data.get("relevant_when", [])
            if target_tags and not any(tag in doc_tags for tag in target_tags):
                continue

            results.append(
                DocumentInterface(
                    uri=uri,
                    path=data.get("path", ""),
                    summary=data.get("summary", ""),
                    relevant_when=doc_tags,
                    owner=data.get("owner", ""),
                    sections=data.get("sections", {}),
                    capabilities=data.get("capabilities", []),
                )
            )

        return sorted(results, key=lambda x: x.uri)

    def get_interface(self, uri: str) -> DocumentInterface | None:
        """Retrieves the Stage 2 interface for a specific coordinate."""
        if not self._initialized:
            # Strategy: Extract namespace from URI and load only that one
            ns = uri.split("/")[0]
            self.load_registry(namespaces=[ns])

        data = self._registry.get(uri)
        if not data:
            return None

        return DocumentInterface(
            uri=uri,
            path=data.get("path", ""),
            summary=data.get("summary", ""),
            relevant_when=data.get("relevant_when", []),
            owner=data.get("owner", ""),
            sections=data.get("sections", {}),
            capabilities=data.get("capabilities", []),
        )
