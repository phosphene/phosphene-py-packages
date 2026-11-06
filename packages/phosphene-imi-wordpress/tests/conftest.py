"""Shared test fixtures for imi-wordpress."""

from __future__ import annotations

import pytest

from phosphene.imi_wordpress.dryrun import DryRunWPClient


@pytest.fixture
def dry_run_client() -> DryRunWPClient:
    """Provide a fresh DryRunWPClient instance."""
    return DryRunWPClient()


@pytest.fixture
def sample_draft() -> dict[str, str]:
    """Provide a sample article draft dict."""
    return {
        "title": "Why Care Work Matters",
        "author": "Jane Smith",
        "category": "Economy",
        "source_url": "https://example.com/care-work",
    }
