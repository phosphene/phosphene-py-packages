"""phosphene.mdrag package root."""

from __future__ import annotations

from phosphene.mdrag.discovery import (
    DiscoveryEngine,
    DocumentInterface,
    DocumentRegistry,
    FilesystemDocumentRegistry,
)

__all__ = [
    "DiscoveryEngine",
    "DocumentInterface",
    "DocumentRegistry",
    "FilesystemDocumentRegistry",
]
