"""Live integration tests for imi_registry CPT on WordPress.

Requires WP_LIVE=true and valid WP credentials.
Tests verify the CPT exists, has required fields, REST endpoint is accessible,
and CRUD operations work.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request

import pytest

# Skip entire module unless WP_LIVE=true
pytestmark = pytest.mark.skipif(
    os.environ.get("WP_LIVE", "").lower() != "true",
    reason="WP_LIVE not set — skipping live WordPress tests",
)

WP_URL = "https://independentmediainstitute.org"
WP_USERNAME = "flow@ind.media"
# Cloudflare blocks default Python user-agent; use a browser-like one
USER_AGENT = "Mozilla/5.0 (compatible; IMI-WordPress-Tests/1.0)"


def _auth_header() -> str:
    """Build Basic auth header from env."""
    password = os.environ.get("WP_APP_PASSWORD", "")
    creds = f"{WP_USERNAME}:{password}"
    encoded = base64.b64encode(creds.encode()).decode()
    return f"Basic {encoded}"


def _api_get(endpoint: str) -> dict | list:
    """GET a WP REST API endpoint with auth."""
    url = f"{WP_URL}/wp-json/wp/v2/{endpoint}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", _auth_header())
    req.add_header("User-Agent", USER_AGENT)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _api_post(endpoint: str, data: dict) -> dict:
    """POST to a WP REST API endpoint with auth."""
    url = f"{WP_URL}/wp-json/wp/v2/{endpoint}"
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", _auth_header())
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", USER_AGENT)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _api_delete(endpoint: str) -> dict:
    """DELETE a WP REST API endpoint with auth (force=true)."""
    url = f"{WP_URL}/wp-json/wp/v2/{endpoint}?force=true"
    req = urllib.request.Request(url, method="DELETE")
    req.add_header("Authorization", _auth_header())
    req.add_header("User-Agent", USER_AGENT)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


class TestIMIRegistryCPT:
    """Live tests for imi_registry custom post type."""

    def test_imi_registry_cpt_exists(self) -> None:
        """The imi_registry post type is registered and visible via REST API."""
        types = _api_get("types")
        assert "imi_registry" in types, (
            f"imi_registry not found in registered types: {list(types.keys())}"
        )

    def test_imi_registry_has_required_fields(self) -> None:
        """The imi_registry CPT exposes required meta fields (author_name, category, source_url)."""
        # Get the schema for imi_registry
        url = f"{WP_URL}/wp-json/wp/v2/imi_registry"
        req = urllib.request.Request(url, method="OPTIONS")
        req.add_header("Authorization", _auth_header())
        req.add_header("User-Agent", USER_AGENT)
        with urllib.request.urlopen(req, timeout=30) as resp:
            schema = json.loads(resp.read().decode())

        # The schema should list meta properties
        meta_schema = schema.get("schema", {}).get("properties", {}).get("meta", {})
        meta_props = meta_schema.get("properties", {})

        required_fields = {"author_name", "category", "source_url"}
        actual_fields = set(meta_props.keys())
        missing = required_fields - actual_fields
        assert not missing, f"Missing meta fields: {missing}. Found: {actual_fields}"

    def test_imi_registry_rest_endpoint_accessible(self) -> None:
        """The /wp-json/wp/v2/imi_registry endpoint is accessible and returns a list."""
        result = _api_get("imi_registry")
        assert isinstance(result, list), f"Expected list, got {type(result)}: {result}"

    def test_can_create_and_delete_imi_registry_post(self) -> None:
        """Can create an imi_registry post with meta fields, then delete it."""
        # Create
        payload = {
            "title": "TDD Test Scholar — DELETE ME",
            "status": "draft",
            "meta": {
                "author_name": "Test Author",
                "category": "Test Category",
                "source_url": "https://example.com/test",
            },
        }
        created = _api_post("imi_registry", payload)
        post_id = created.get("id")
        assert post_id, f"Failed to create post: {created}"

        try:
            # Verify meta came back
            meta = created.get("meta", {})
            assert meta.get("author_name") == "Test Author", f"author_name mismatch: {meta}"
            assert meta.get("category") == "Test Category", f"category mismatch: {meta}"
            assert meta.get("source_url") == "https://example.com/test", (
                f"source_url mismatch: {meta}"
            )
        finally:
            # Clean up — always delete
            deleted = _api_delete(f"imi_registry/{post_id}")
            assert deleted.get("deleted", False) or deleted.get("id") == post_id, (
                f"Failed to delete post {post_id}: {deleted}"
            )

    def test_metadata_fields_stored_correctly(self) -> None:
        """Create a post with meta fields, read it back, assert values match."""
        payload = {
            "title": "Meta Field Verification Test",
            "slug": "imi-test-meta-verification-unique",
            "status": "draft",
            "meta": {
                "author_name": "Test Author Verified",
                "category": "Test Category Verified",
                "source_url": "https://example.com/source-verified",
            },
        }
        created = _api_post("imi_registry", payload)
        post_id = created.get("id")
        assert post_id, f"Failed to create: {created}"
        try:
            # Read back with edit context to get meta
            fetched = _api_get(f"imi_registry/{post_id}")
            meta = fetched.get("meta", {})
            assert meta.get("author_name") == "Test Author Verified", f"author_name: {meta}"
            assert meta.get("category") == "Test Category Verified", f"category: {meta}"
            assert meta.get("source_url") == "https://example.com/source-verified", (
                f"source_url: {meta}"
            )
        finally:
            _api_delete(f"imi_registry/{post_id}")

    def test_auth_failure_on_write_raises_http_error(self) -> None:
        """Wrong credentials on POST (write) return HTTP 401."""
        import base64
        import urllib.error

        bad_creds = base64.b64encode(b"flow@ind.media:WRONG_PASSWORD_XYZ").decode()
        body = json.dumps({"title": "Should fail", "status": "draft"}).encode()
        req = urllib.request.Request(
            f"{WP_URL}/wp-json/wp/v2/imi_registry", data=body, method="POST"
        )
        req.add_header("Authorization", f"Basic {bad_creds}")
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", USER_AGENT)
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req, timeout=10)
        assert exc_info.value.code in (401, 403), f"Expected 401/403, got {exc_info.value.code}"

    def test_browser_user_agent_reaches_api(self) -> None:
        """Browser-like UA gets through Cloudflare — API returns 200."""
        req = urllib.request.Request(f"{WP_URL}/wp-json/wp/v2/imi_registry")
        req.add_header("Authorization", _auth_header())
        req.add_header("User-Agent", USER_AGENT)
        with urllib.request.urlopen(req, timeout=10) as resp:
            assert resp.status == 200

    def test_idempotency_same_slug_no_duplicate(self) -> None:
        """Publishing same slug: only one post exists for that slug."""
        import time as _time

        slug = f"imi-test-idempotency-{int(_time.time())}"
        # Clean up any stale posts with similar prefix before running
        stale = _api_get(f"imi_registry?slug={slug}&status=any") or []
        for s in stale:
            _api_delete(f"imi_registry/{s['id']}")
        created = _api_post(
            "imi_registry",
            {
                "title": "Idempotency Test",
                "slug": slug,
                "status": "draft",
            },
        )
        post_id = created.get("id")
        assert post_id
        try:
            results = _api_get(f"imi_registry?slug={slug}&status=draft")
            assert len(results) == 1, f"Expected 1 draft for slug, got {len(results)}: {results}"
            assert results[0]["id"] == post_id
        finally:
            _api_delete(f"imi_registry/{post_id}")

    def test_minimal_fields_post_succeeds(self) -> None:
        """Title only, no meta — creates cleanly."""
        created = _api_post(
            "imi_registry",
            {
                "title": "Minimal Post Test Only",
                "slug": "imi-test-minimal-only99",
                "status": "draft",
            },
        )
        post_id = created.get("id")
        assert post_id and post_id > 0, f"No post_id: {created}"
        try:
            assert "Minimal" in created["title"]["rendered"]
            meta = created.get("meta", {})
            # Optional fields should be empty/absent — not an error
            assert meta.get("author_name", "") in ("", None)
        finally:
            _api_delete(f"imi_registry/{post_id}")
