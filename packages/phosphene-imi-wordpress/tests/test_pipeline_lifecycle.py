"""Pipeline lifecycle phase matrix — end-to-end mutation pipeline tests.

The pipeline has 5 phases:
1. Backup — snapshot current page state
2. AST Dry-Run — validate mutated model and diff
3. Direct DB Write — raw SQL, bypass wp_slash
4. Dual-Read Parity — REST vs DB byte-for-byte
5. Render & Cache Validation — purge caches, check live HTML

These tests use mocks to simulate the full pipeline without touching prod.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from phosphene.imi_wordpress.client import UrllibWPClient
from phosphene.imi_wordpress.config import WPConfig
from phosphene.imi_wordpress.db_client import WPEngineDBClient
from phosphene.imi_wordpress.elementor_model import ElementorPageModel
from phosphene.imi_wordpress.parity_harness import WordPressDualHarness

# --- Fixtures ---

ORIGINAL_DATA = json.dumps(
    [
        {
            "id": "s1",
            "elType": "section",
            "settings": {},
            "elements": [
                {
                    "id": "c1",
                    "elType": "column",
                    "settings": {},
                    "elements": [
                        {"id": "w1", "elType": "widget", "widgetType": "heading", "settings": {}},
                        {"id": "w2", "elType": "widget", "widgetType": "image", "settings": {}},
                        {"id": "w3", "elType": "widget", "widgetType": "button", "settings": {}},
                    ],
                }
            ],
        }
    ]
)

MUTATED_DATA = json.dumps(
    [
        {
            "id": "s1",
            "elType": "section",
            "settings": {},
            "elements": [
                {
                    "id": "c1",
                    "elType": "column",
                    "settings": {},
                    "elements": [
                        {"id": "w1", "elType": "widget", "widgetType": "heading", "settings": {}},
                        {"id": "w3", "elType": "widget", "widgetType": "button", "settings": {}},
                    ],
                }
            ],
        }
    ]
)


@pytest.fixture
def mock_harness() -> WordPressDualHarness:
    """Harness with mock clients for pipeline testing."""
    rest = MagicMock(spec=UrllibWPClient)
    rest.config = WPConfig(
        url="https://example.com",
        username="test",
        app_password="test-pass",
    )
    db = MagicMock(spec=WPEngineDBClient)
    return WordPressDualHarness(rest, db)


class TestPipelineBackup:
    """Phase 1: Backup — snapshot current page state."""

    def test_backup_captures_page_state(self, mock_harness: WordPressDualHarness) -> None:
        mock_harness.db.backup_page.return_value = {
            "backup_time": "2026-08-07 00:00:00",
            "page": {"content_length": 5000, "ID": 43},
            "meta": {"_elementor_data": ORIGINAL_DATA},
        }
        mock_harness.db.get_raw_meta.return_value = ORIGINAL_DATA
        mock_harness.db.set_elementor_data.return_value = {
            "status": "updated",
            "verify_length": len(MUTATED_DATA),
            "verify_json_valid": True,
        }
        mock_harness.rest.get_meta.return_value = {"_elementor_data": MUTATED_DATA}

        mutation = ElementorPageModel(MUTATED_DATA)
        result = mock_harness.run_pipeline(43, mutation)

        phase = result["phases"]["1_backup"]
        assert phase["status"] == "done"
        assert phase["content_length"] == 5000


class TestPipelineDryRun:
    """Phase 2: AST Dry-Run — validate and diff."""

    def test_dry_run_shows_widget_delta(self, mock_harness: WordPressDualHarness) -> None:
        mock_harness.db.backup_page.return_value = {"page": {}}
        mock_harness.db.get_raw_meta.return_value = ORIGINAL_DATA

        mutation = ElementorPageModel(MUTATED_DATA)
        result = mock_harness.run_pipeline(43, mutation)

        phase = result["phases"]["2_dry_run"]
        assert phase["status"] == "done"
        assert phase["current_widgets"] == 3
        assert phase["target_widgets"] == 2
        assert phase["widget_delta"] == -1
        assert "w2" in phase["removed_widgets"]

    def test_dry_run_fails_on_invalid_current(self, mock_harness: WordPressDualHarness) -> None:
        mock_harness.db.backup_page.return_value = {"page": {}}
        mock_harness.db.get_raw_meta.return_value = "{invalid json"

        mutation = ElementorPageModel(MUTATED_DATA)
        result = mock_harness.run_pipeline(43, mutation)

        assert result["phases"]["2_dry_run"]["status"] == "failed"
        assert result["verified"] is False


class TestPipelineDBWrite:
    """Phase 3: Direct DB Write — raw SQL."""

    def test_write_succeeds(self, mock_harness: WordPressDualHarness) -> None:
        mock_harness.db.backup_page.return_value = {"page": {}}
        mock_harness.db.get_raw_meta.return_value = ORIGINAL_DATA
        mock_harness.db.set_elementor_data.return_value = {
            "status": "updated",
            "verify_length": len(MUTATED_DATA),
            "verify_json_valid": True,
        }
        mock_harness.rest.get_meta.return_value = {"_elementor_data": MUTATED_DATA}

        mutation = ElementorPageModel(MUTATED_DATA)
        result = mock_harness.run_pipeline(43, mutation)

        assert result["phases"]["3_db_write"]["status"] == "updated"
        assert result["phases"]["3_db_write"]["verify_json_valid"] is True

    def test_write_failure_aborts_pipeline(self, mock_harness: WordPressDualHarness) -> None:
        mock_harness.db.backup_page.return_value = {"page": {}}
        mock_harness.db.get_raw_meta.return_value = ORIGINAL_DATA
        mock_harness.db.set_elementor_data.return_value = {"status": "failed"}

        mutation = ElementorPageModel(MUTATED_DATA)
        result = mock_harness.run_pipeline(43, mutation)

        assert result["phases"]["3_db_write"]["status"] == "failed"
        assert result["verified"] is False
        # Phase 4 and 5 should not have run
        assert "4_parity" not in result["phases"]


class TestPipelineParity:
    """Phase 4: Dual-Read Parity — REST vs DB."""

    def test_parity_passes_on_match(self, mock_harness: WordPressDualHarness) -> None:
        mock_harness.db.backup_page.return_value = {"page": {}}
        # First call returns original (for dry-run), then returns mutated (after write)
        mock_harness.db.get_raw_meta.side_effect = [ORIGINAL_DATA, MUTATED_DATA]
        mock_harness.db.set_elementor_data.return_value = {
            "status": "updated",
            "verify_length": len(MUTATED_DATA),
            "verify_json_valid": True,
        }
        mock_harness.rest.get_meta.return_value = {"_elementor_data": MUTATED_DATA}

        mutation = ElementorPageModel(MUTATED_DATA)
        result = mock_harness.run_pipeline(43, mutation)

        phase = result["phases"]["4_parity"]
        assert phase["matches"] is True
        assert phase["json_valid"] is True
        assert result["verified"] is True

    def test_parity_fails_on_mismatch(self, mock_harness: WordPressDualHarness) -> None:
        mock_harness.db.backup_page.return_value = {"page": {}}
        # First call returns original (for dry-run), then returns original again (simulating write failure)
        mock_harness.db.get_raw_meta.side_effect = [ORIGINAL_DATA, ORIGINAL_DATA]
        mock_harness.db.set_elementor_data.return_value = {
            "status": "updated",
            "verify_length": len(MUTATED_DATA),
            "verify_json_valid": True,
        }
        # REST returns mutated, but DB still has original → mismatch
        mock_harness.rest.get_meta.return_value = {"_elementor_data": MUTATED_DATA}

        mutation = ElementorPageModel(MUTATED_DATA)
        result = mock_harness.run_pipeline(43, mutation)

        phase = result["phases"]["4_parity"]
        assert phase["matches"] is False
        assert result["verified"] is False


class TestPipelineRenderValidation:
    """Phase 5: Render & Cache Validation."""

    @patch("urllib.request.urlopen")
    def test_render_verification(
        self, mock_urlopen: MagicMock, mock_harness: WordPressDualHarness
    ) -> None:
        mock_harness.db.backup_page.return_value = {"page": {}}
        mock_harness.db.get_raw_meta.side_effect = [ORIGINAL_DATA, MUTATED_DATA]
        mock_harness.db.set_elementor_data.return_value = {
            "status": "updated",
            "verify_length": len(MUTATED_DATA),
            "verify_json_valid": True,
        }
        mock_harness.rest.get_meta.return_value = {"_elementor_data": MUTATED_DATA}
        mock_harness.rest.get_page.return_value = {"link": "https://example.com/who-we-are/"}

        # Mock HTML response with elementor-widget
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'<div class="elementor-widget">Hello</div>'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        mutation = ElementorPageModel(MUTATED_DATA)
        result = mock_harness.run_pipeline(43, mutation, purge_caches=False)

        assert result["phases"]["5_render"]["render_verified"] is True
