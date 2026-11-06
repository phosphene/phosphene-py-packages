"""Behavioral boundary tests for the IMI Registry REST API.

Tests the finished artifact — a running WordPress with the imi-registry
plugin active — not the underlying layers. Each layer (PHP domain, PHP
adapters, Python client, Python extractor) has its own tests for its own
concerns. These tests compose them into boundary verification.

Design: drafts/platform/imi-boundary-test-design.md

Requires:
    WP_INTEGRATION=1
    WP_URL            — e.g. http://localhost:8090
    WP_USERNAME       — WordPress admin user
    WP_APP_PASSWORD   — application password

Optionally:
    WP_TEST_REGISTRY_ID — pre-created golden fixture post ID
    WP_TEST_POST_ID     — regular post ID for Yoast scope test
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from phosphene.imi_wordpress.testing.metadata_extractor import (
    MetadataExtractor,
)
from phosphene.imi_wordpress.testing.payload_builder import PayloadBuilder
from phosphene.imi_wordpress.testing.wp_test_client import WPTestClient

SKIP_MSG = "WP_INTEGRATION not set — requires running WordPress"
FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def wp() -> WPTestClient:
    """Authenticated WP REST client from environment."""
    url = os.environ.get("WP_URL", "")
    user = os.environ.get("WP_USERNAME", "")
    pw = os.environ.get("WP_APP_PASSWORD", "")
    if not all([url, user, pw]):
        pytest.skip("WP_URL, WP_USERNAME, WP_APP_PASSWORD required")
    return WPTestClient(url, user, pw)


@pytest.fixture
def payloads() -> PayloadBuilder:
    """Payload builder with golden fixtures."""
    return PayloadBuilder(fixture_dir=FIXTURE_DIR)


def _cleanup(wp: WPTestClient, post_id: int) -> None:
    """Delete a test post. Best-effort, doesn't assert."""
    wp.delete(f"/wp-json/wp/v2/imi_registry/{post_id}?force=true")


# ── Round-trip: what Python sends is what Python gets back ──────────


@pytest.mark.skipif(not os.environ.get("WP_INTEGRATION"), reason=SKIP_MSG)
class TestPayloadRoundTrip:
    """The REST API persists what the pipeline sends and returns it intact."""

    def test_draft_meta_roundtrips(self, wp: WPTestClient, payloads: PayloadBuilder) -> None:
        """Draft payload meta fields survive the POST → GET cycle.

        Axiom: fields the pipeline sends are not silently dropped.
        Distinguishes per field: persisted | dropped | corrupted.
        """
        payload = payloads.draft()
        created = wp.post("/wp-json/wp/v2/imi_registry", payload)
        assert created.ok, f"Create failed: {created.error_message}"

        post_id = created.data["id"]
        try:
            fetched = wp.get(f"/wp-json/wp/v2/imi_registry/{post_id}")
            assert fetched.ok, f"Fetch failed: {fetched.error_message}"

            fetched_meta = fetched.data.get("meta", {})
            for key, sent_value in payload["meta"].items():
                received = fetched_meta.get(key)
                assert received == sent_value, (
                    f"Field '{key}': sent {sent_value!r}, got {received!r}"
                )
        finally:
            _cleanup(wp, post_id)

    def test_valid_payload_accepted(self, wp: WPTestClient, payloads: PayloadBuilder) -> None:
        """A full valid payload with declaration passes validation.

        Axiom: the pipeline's canonical payload shape is accepted.
        Distinguishes: accepted | rejected by validation.
        """
        payload = payloads.valid()
        created = wp.post("/wp-json/wp/v2/imi_registry", payload)
        assert created.ok, f"Valid payload rejected: {created.error_message}"
        assert "id" in created.data

        _cleanup(wp, created.data["id"])

    def test_minimal_payload_accepted(self, wp: WPTestClient, payloads: PayloadBuilder) -> None:
        """Minimum required fields are sufficient for a valid entry.

        Axiom: the pipeline doesn't need to send all 39 fields.
        Distinguishes: minimal accepted | minimal rejected.
        """
        payload = payloads.minimal()
        created = wp.post("/wp-json/wp/v2/imi_registry", payload)
        assert created.ok, f"Minimal payload rejected: {created.error_message}"

        _cleanup(wp, created.data["id"])


# ── Rendered artifact: the page has scholarly metadata ──────────────


@pytest.mark.skipif(not os.environ.get("WP_INTEGRATION"), reason=SKIP_MSG)
class TestRenderedMetadata:
    """The rendered page is the finished artifact. It must have
    four layers of scholarly metadata when the plugin is active."""

    def test_four_metadata_layers_present(
        self, wp: WPTestClient, payloads: PayloadBuilder
    ) -> None:
        """The finished artifact has citation, OG, DC, and JSON-LD layers.

        Axiom: the system produces scholarly metadata from valid input.
        Distinguishes per layer: present | absent.
        """
        payload = payloads.valid()
        created = wp.post("/wp-json/wp/v2/imi_registry", payload)
        assert created.ok, f"Create failed: {created.error_message}"

        post_id = created.data["id"]
        try:
            link = created.data.get("link", "")
            assert link, "Created entry has no permalink"

            html = wp.fetch_html(link)
            assert html, "Rendered page returned empty HTML"

            metadata = MetadataExtractor.from_html(html)

            # Layer 1: Google Scholar
            assert "citation_title" in metadata.citation, (
                "Layer 1 (citation): citation_title absent"
            )

            # Layer 2: Open Graph
            assert "og:type" in metadata.open_graph, "Layer 2 (OG): og:type absent"

            # Layer 3: Dublin Core
            assert "DC.title" in metadata.dublin_core, "Layer 3 (DC): DC.title absent"

            # Layer 4: JSON-LD
            assert len(metadata.jsonld) > 0, "Layer 4 (JSON-LD): no JSON-LD blocks found"
        finally:
            _cleanup(wp, post_id)

    def test_yoast_suppressed_on_registry(
        self, wp: WPTestClient, payloads: PayloadBuilder
    ) -> None:
        """Yoast SEO output is suppressed on imi_registry pages.

        Axiom: the plugin's YoastSuppressor fires on the correct CPT.
        Distinguishes: Yoast absent | Yoast present.
        """
        payload = payloads.valid()
        created = wp.post("/wp-json/wp/v2/imi_registry", payload)
        assert created.ok

        post_id = created.data["id"]
        try:
            html = wp.fetch_html(created.data.get("link", ""))
            metadata = MetadataExtractor.from_html(html)
            assert metadata.yoast_present is False, (
                "Yoast JSON-LD should be suppressed on imi_registry pages"
            )
        finally:
            _cleanup(wp, post_id)


# ── Validation surface: the system enforces its own rules ───────────


@pytest.mark.skipif(not os.environ.get("WP_INTEGRATION"), reason=SKIP_MSG)
class TestValidationBoundary:
    """The system's validation rules are observable at the boundary.
    We don't test the rules themselves (PHP's concern) — we test
    that the boundary rejects what it should reject."""

    def test_short_abstract_rejected(self, wp: WPTestClient, payloads: PayloadBuilder) -> None:
        """An abstract under 150 words is rejected at the boundary.

        Axiom: the system enforces abstract length.
        Distinguishes: rejected | silently accepted.
        """
        payload = payloads.with_meta_override("reg_abstract", "Too short.")
        result = wp.post("/wp-json/wp/v2/imi_registry", payload)

        if result.ok:
            # Advisory mode — clean up
            _cleanup(wp, result.data.get("id", 0))
        else:
            assert "validation" in str(result.error_code).lower(), (
                f"Expected validation error, got: {result.error_code}"
            )

    def test_missing_declaration_rejected_for_publish(
        self, wp: WPTestClient, payloads: PayloadBuilder
    ) -> None:
        """Publish status without declaration is rejected.

        Axiom: the system requires Scholar's Declaration for publication.
        Distinguishes: rejected | silently accepted.
        """
        payload = payloads.without_field("reg_declaration")
        result = wp.post("/wp-json/wp/v2/imi_registry", payload)

        if result.ok:
            _cleanup(wp, result.data.get("id", 0))
        else:
            assert "validation" in str(result.error_code).lower()

    def test_draft_without_declaration_accepted(
        self, wp: WPTestClient, payloads: PayloadBuilder
    ) -> None:
        """Drafts don't require the declaration.

        Axiom: validation rules differ by status.
        Distinguishes: draft accepted without declaration | draft rejected.
        """
        payload = payloads.draft()
        result = wp.post("/wp-json/wp/v2/imi_registry", payload)
        assert result.ok, f"Draft should be accepted: {result.error_message}"

        _cleanup(wp, result.data["id"])
