"""Discrete serialization unit for EditorialState to WP post_status and reg_pipeline_status.

@dft
- A1 (pure-io-separation): Pure transformation logic — zero I/O imports.
- A2 (determinism): Completely deterministic mappings.
- A4 (dft-docs): This docstring section.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from phosphene.imi_wordpress.domain import EditorialState


class EditorialStateUnit:
    """Discrete serialization and hydration for editorial lifecycle states."""

    @staticmethod
    def serialize(state: EditorialState) -> dict[str, str]:
        post_status = "publish" if state.is_published else "draft"
        pipeline_status = {
            EditorialState.LIVE_PREPRINT: "preprint",
            EditorialState.PUBLISHED: "published",
            EditorialState.WITHDRAWN: "withdrawn",
            EditorialState.PENDING_REVIEW: "pending_review",
            EditorialState.UNDER_REVIEW: "under_review",
        }.get(state, "draft")

        return {
            "post_status": post_status,
            "pipeline_status": pipeline_status,
        }

    @staticmethod
    def hydrate(meta: Mapping[str, Any], post_status: str = "") -> EditorialState:
        pipeline = str(meta.get("reg_pipeline_status", "")).strip()
        mapping = {
            "preprint": EditorialState.LIVE_PREPRINT,
            "published": EditorialState.PUBLISHED,
            "withdrawn": EditorialState.WITHDRAWN,
            "pending_review": EditorialState.PENDING_REVIEW,
            "under_review": EditorialState.UNDER_REVIEW,
        }
        if pipeline in mapping:
            return mapping[pipeline]
        return EditorialState.PUBLISHED if post_status == "publish" else EditorialState.DRAFT
