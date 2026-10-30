"""Phosphene Unified Myth & Cross-Domain Evidence Engine."""

from phosphene.myths.identity import IdentityBridgeManager, IdentityBridgeRecord
from phosphene.myths.projections import project_motifs_to_markdown, project_taxa_to_markdown
from phosphene.myths.provenance import SourceRecord, TimeHorizon
from phosphene.myths.store import MythStore

__all__ = [
    "SourceRecord",
    "TimeHorizon",
    "MythStore",
    "IdentityBridgeManager",
    "IdentityBridgeRecord",
    "project_motifs_to_markdown",
    "project_taxa_to_markdown",
]
