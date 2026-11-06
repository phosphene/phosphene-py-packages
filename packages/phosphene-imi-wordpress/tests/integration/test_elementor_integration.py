"""Integration tests for the dual-layer parity harness against Docker WordPress.

Tests run against a real WordPress + MySQL + Elementor stack started via
``compose.test.yml``. Environment setup is handled programmatically by the
session-scoped ``wp_env`` fixture in ``conftest.py`` — no shell scripts.

Requires:
    WP_INTEGRATION=1 (or any truthy value)
"""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

import pytest

from phosphene.imi_wordpress.client import UrllibWPClient
from phosphene.imi_wordpress.db_client import WPEngineDBClient
from phosphene.imi_wordpress.parity_harness import WordPressDualHarness
from phosphene.imi_wordpress.test_setup import WPTestEnvironment

pytestmark = pytest.mark.skipif(
    not os.environ.get("WP_INTEGRATION"),
    reason="WP_INTEGRATION not set — requires running WordPress Docker stack",
)

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


# --- Fixtures (rest_client, db_client, harness, wp_env from conftest.py) ---


@pytest.fixture
def fixture_page_id(wp_env: WPTestEnvironment) -> int:
    """Create a fixture page with known Elementor data via the mu-plugin gateway."""
    fixture_path = FIXTURE_DIR / "elementor-fixture-page.json"
    with open(fixture_path) as f:
        fixture = json.load(f)

    body = json.dumps(
        {
            "title": "Parity Test Fixture",
            "_elementor_data": fixture["_elementor_data"],
        }
    ).encode()

    req = urllib.request.Request(
        f"{wp_env.url}/?imi_diag=1&action=create_fixture_page&token={wp_env.db_token}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        page_id = data["page_id"]

    yield page_id


# --- Tests: REST API ---


class TestRestApiReads:
    """Verify REST API reads work against Docker WordPress."""

    def test_get_page_returns_valid_response(
        self, rest_client: UrllibWPClient, fixture_page_id: int
    ) -> None:
        page = rest_client.get_page(fixture_page_id, context="edit")
        assert "error" not in page, f"REST error: {page}"
        assert page["id"] == fixture_page_id
        assert "meta" in page
        assert "_elementor_data" in page["meta"]

    def test_get_meta_returns_elementor_data(
        self, rest_client: UrllibWPClient, fixture_page_id: int
    ) -> None:
        meta = rest_client.get_meta(fixture_page_id, context="edit")
        assert "_elementor_data" in meta
        ed = meta["_elementor_data"]
        assert len(ed) > 100
        parsed = json.loads(ed)
        assert isinstance(parsed, list)


# --- Tests: DB Gateway ---


class TestDBGateway:
    """Verify the mu-plugin DB gateway works against Docker WordPress."""

    def test_status(self, wp_env: WPTestEnvironment) -> None:
        req = urllib.request.Request(
            f"{wp_env.url}/?imi_diag=1&action=status&token={wp_env.db_token}",
            headers={"User-Agent": "test"},
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
        assert data["status"] == "ok"

    def test_get_raw_meta(self, db_client: WPEngineDBClient, fixture_page_id: int) -> None:
        val = db_client.get_raw_meta(fixture_page_id, "_elementor_data")
        assert len(val) > 100
        json.loads(val)

    def test_backup_page(self, db_client: WPEngineDBClient, fixture_page_id: int) -> None:
        backup = db_client.backup_page(fixture_page_id)
        assert backup["page"]["ID"] == fixture_page_id
        assert "_elementor_data" in backup["meta"]


# --- Tests: Parity Harness ---


class TestParityHarnessDocker:
    """Dual-layer parity verification against real WordPress."""

    def test_meta_parity_after_create(
        self,
        harness: WordPressDualHarness,
        fixture_page_id: int,
    ) -> None:
        result = harness.verify_meta_parity(fixture_page_id)
        assert result.matches, (
            f"Parity failure: REST len={result.rest_length}, DB len={result.db_length}"
        )
        assert result.rest_json_valid
        assert result.db_json_valid

    def test_elementor_structure_valid(
        self,
        harness: WordPressDualHarness,
        fixture_page_id: int,
    ) -> None:
        model = harness.verify_elementor_structure(fixture_page_id)
        assert model.section_count >= 1
        assert model.widget_count >= 5

    def test_widget_extraction(
        self,
        harness: WordPressDualHarness,
        fixture_page_id: int,
    ) -> None:
        model = harness.verify_elementor_structure(fixture_page_id)
        widgets = model.widgets()
        assert len(widgets) == 6
        widget_types = [w.widget_type for w in widgets]
        assert "heading" in widget_types
        assert "text-editor" in widget_types
        assert "image" in widget_types
        assert "button" in widget_types


# --- Tests: Safe Write Pipeline ---


class TestSafeWritePipelineDocker:
    """Full safe_write_elementor against real WordPress."""

    def test_safe_write_with_no_changes(
        self,
        harness: WordPressDualHarness,
        fixture_page_id: int,
    ) -> None:
        model = harness.verify_elementor_structure(fixture_page_id)
        result = harness.safe_write_elementor(fixture_page_id, model.to_json())
        assert result["verified"], f"Write failed: {result}"
        assert result["post_parity"]["matches"]

    def test_safe_write_after_widget_removal(
        self,
        harness: WordPressDualHarness,
        fixture_page_id: int,
    ) -> None:
        model = harness.verify_elementor_structure(fixture_page_id)
        original_count = model.widget_count

        widget_to_remove = model.widgets()[0].id
        mutated = model.remove_widget_by_id(widget_to_remove)

        assert mutated.widget_count == original_count - 1

        result = harness.safe_write_elementor(fixture_page_id, mutated.to_json())

        assert result["verified"], f"Write failed: {result}"
        assert result["elementor"]["widget_count"] == original_count - 1

        post_model = harness.verify_elementor_structure(fixture_page_id)
        assert post_model.widget_count == original_count - 1
        assert widget_to_remove not in post_model.widget_ids


# --- Tests: wp_slash Regression ---


class TestWPSlashRegressionDocker:
    """Regression: verify wp_slash corruption is detectable in Docker."""

    def test_rest_vs_db_after_raw_write(
        self,
        harness: WordPressDualHarness,
        fixture_page_id: int,
    ) -> None:
        model = harness.verify_elementor_structure(fixture_page_id)
        result = harness.safe_write_elementor(fixture_page_id, model.to_json())
        assert result["post_parity"]["matches"]
        assert result["post_parity"]["json_valid"]
