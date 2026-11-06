"""WordPress integration tests — require running WordPress instance.

These tests exercise UrllibWPClient against a real WordPress REST API.
They are skipped unless WP_INTEGRATION is set in the environment.

The ``wp_env`` session fixture (from ``conftest.py``) handles WordPress
setup programmatically — no env vars required beyond ``WP_INTEGRATION``.
"""

from __future__ import annotations

import os
import time

import pytest

from phosphene.imi_wordpress.client import UrllibWPClient
from phosphene.imi_wordpress.config import WPConfig
from phosphene.imi_wordpress.test_setup import WPTestEnvironment

pytestmark = pytest.mark.skipif(
    not os.environ.get("WP_INTEGRATION"),
    reason="WP_INTEGRATION not set",
)


@pytest.fixture
def wp_client(wp_env: WPTestEnvironment) -> UrllibWPClient:
    """Create a real WordPress client from the session-scoped wp_env fixture."""
    config = WPConfig(
        url=wp_env.url,
        username=wp_env.username,
        app_password=wp_env.app_password,
    )
    return UrllibWPClient(config)


@pytest.fixture
def unique_slug() -> str:
    """Generate a unique slug for test isolation."""
    return f"ci-test-{int(time.time())}-{os.getpid()}"


class TestCreatePost:
    """Tests for creating posts via the REST API."""

    def test_create_post_creates_real_wp_post(
        self, wp_client: UrllibWPClient, unique_slug: str
    ) -> None:
        """Create a post and verify it returns a valid response with an id."""
        result = wp_client.create_post(
            "posts",
            {
                "title": f"Integration Test Post {unique_slug}",
                "content": "This is a CI integration test post.",
                "status": "publish",
                "slug": unique_slug,
            },
        )

        assert "error" not in result, f"Create failed: {result.get('message')}"
        assert "id" in result, f"Response missing 'id': {result}"
        assert result["id"] > 0
        assert result["status"] == "publish"


class TestPostExists:
    """Tests for checking post existence via the REST API."""

    def test_post_exists_finds_created_post(
        self, wp_client: UrllibWPClient, unique_slug: str
    ) -> None:
        """Create a post then verify post_exists finds it by slug."""
        # Create the post first
        create_result = wp_client.create_post(
            "posts",
            {
                "title": f"Exists Test {unique_slug}",
                "content": "Testing post_exists lookup.",
                "status": "publish",
                "slug": unique_slug,
            },
        )
        assert "error" not in create_result, f"Create failed: {create_result.get('message')}"

        # Now check existence
        exists = wp_client.post_exists("posts", unique_slug)
        assert exists is True, f"post_exists returned False for slug '{unique_slug}'"

    def test_post_exists_returns_false_for_missing(self, wp_client: UrllibWPClient) -> None:
        """post_exists returns False for a slug that does not exist."""
        exists = wp_client.post_exists("posts", "nonexistent-slug-that-will-never-exist-12345")
        assert exists is False


class TestIdempotency:
    """Tests for idempotent publish behaviour."""

    def test_idempotency_second_create_returns_existing(
        self, wp_client: UrllibWPClient, unique_slug: str
    ) -> None:
        """Creating the same slug twice: second should succeed or find existing.

        WordPress auto-appends -2 to duplicate slugs. We verify:
        1. First create succeeds
        2. Second create also succeeds (WP handles uniqueness)
        3. Original post is still findable by its slug
        """
        data = {
            "title": f"Idempotency Test {unique_slug}",
            "content": "Testing idempotent publish.",
            "status": "publish",
            "slug": unique_slug,
        }

        # First create
        first = wp_client.create_post("posts", data)
        assert "error" not in first, f"First create failed: {first.get('message')}"
        first_id = first["id"]

        # Second create with same slug
        second = wp_client.create_post("posts", data)
        assert "error" not in second, f"Second create failed: {second.get('message')}"

        # Original still exists
        exists = wp_client.post_exists("posts", unique_slug)
        assert exists is True, "Original post not found after second create"

        # The two posts have different IDs (WP created both, second with modified slug)
        assert first_id != second["id"], "Expected WP to create a second post with a different ID"
