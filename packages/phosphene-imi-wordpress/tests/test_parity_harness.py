"""Tests for WordPressDualHarness — REST vs DB parity verification.

These tests use mocks to simulate the REST and DB clients, including
the critical regression test for the wp_slash() corruption bug.

The slashing bug: WordPress's update_post_meta() applies wp_slash()
which escapes double quotes in JSON values. When raw JSON is passed
through update_post_meta(), the stored value has all double quotes
escaped (\"), making the JSON longer and invalid. The parity harness
detects this by comparing the REST API read (which unslashes) against
the raw DB read (which doesn't).
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from phosphene.imi_wordpress.client import UrllibWPClient
from phosphene.imi_wordpress.db_client import WPEngineDBClient
from phosphene.imi_wordpress.elementor_model import ElementorPageModel
from phosphene.imi_wordpress.parity_harness import (
    WordPressDualHarness,
)

# --- Fixtures ---

VALID_ELEMENTOR = json.dumps(
    [
        {
            "id": "s1",
            "elType": "section",
            "settings": {"padding": {"top": "50"}},
            "elements": [
                {
                    "id": "c1",
                    "elType": "column",
                    "settings": {"_column_size": 100},
                    "elements": [
                        {
                            "id": "w1",
                            "elType": "widget",
                            "widgetType": "heading",
                            "settings": {"title": "Who We Are"},
                        },
                    ],
                },
            ],
        }
    ]
)

# What update_post_meta() would produce after wp_slash() —
# double quotes are escaped with backslashes, corrupting the JSON.
SLASHED_ELEMENTOR = VALID_ELEMENTOR.replace('"', '\\"')


@pytest.fixture
def mock_rest_client() -> MagicMock:
    """Mock REST client."""
    client = MagicMock(spec=UrllibWPClient)
    return client


@pytest.fixture
def mock_db_client() -> MagicMock:
    """Mock DB client."""
    return MagicMock(spec=WPEngineDBClient)


@pytest.fixture
def harness(mock_rest_client: MagicMock, mock_db_client: MagicMock) -> WordPressDualHarness:
    """Parity harness with mock clients."""
    return WordPressDualHarness(mock_rest_client, mock_db_client)


class TestVerifyMetaParity:
    """Tests for REST vs DB meta parity verification."""

    def test_parity_when_values_match(
        self,
        harness: WordPressDualHarness,
        mock_rest_client: MagicMock,
        mock_db_client: MagicMock,
    ) -> None:
        """When REST and DB return identical values, parity matches."""
        mock_rest_client.get_meta.return_value = {"_elementor_data": VALID_ELEMENTOR}
        mock_db_client.get_raw_meta.return_value = VALID_ELEMENTOR

        result = harness.verify_meta_parity(43)

        assert result.matches is True
        assert result.rest_length == result.db_length
        assert result.rest_json_valid is True
        assert result.db_json_valid is True

    def test_parity_fails_on_length_mismatch(
        self,
        harness: WordPressDualHarness,
        mock_rest_client: MagicMock,
        mock_db_client: MagicMock,
    ) -> None:
        """When REST and DB return different-length values, parity fails."""
        mock_rest_client.get_meta.return_value = {"_elementor_data": VALID_ELEMENTOR}
        # Simulate the slashing corruption: DB has slashed (longer) value
        mock_db_client.get_raw_meta.return_value = SLASHED_ELEMENTOR

        result = harness.verify_meta_parity(43)

        assert result.matches is False
        assert result.rest_length != result.db_length
        assert result.rest_json_valid is True
        # Slashed JSON is not valid JSON
        assert result.db_json_valid is False

    def test_parity_fails_on_content_mismatch_same_length(
        self,
        harness: WordPressDualHarness,
        mock_rest_client: MagicMock,
        mock_db_client: MagicMock,
    ) -> None:
        """Parity fails even when lengths match but content differs."""
        mock_rest_client.get_meta.return_value = {"_elementor_data": '{"a": 1}'}
        mock_db_client.get_raw_meta.return_value = '{"b": 1}'

        result = harness.verify_meta_parity(43)

        assert result.matches is False
        assert result.rest_length == result.db_length  # Same length!

    def test_parity_detects_invalid_json(
        self,
        harness: WordPressDualHarness,
        mock_rest_client: MagicMock,
        mock_db_client: MagicMock,
    ) -> None:
        """Parity check reports JSON validity separately from match."""
        mock_rest_client.get_meta.return_value = {"_elementor_data": "{not json"}
        mock_db_client.get_raw_meta.return_value = "{not json"

        result = harness.verify_meta_parity(43)

        assert result.matches is True  # They match, but...
        assert result.rest_json_valid is False
        assert result.db_json_valid is False

    @pytest.mark.regression
    def test_slashing_bug_regression(
        self,
        harness: WordPressDualHarness,
        mock_rest_client: MagicMock,
        mock_db_client: MagicMock,
    ) -> None:
        """Regression test: detect wp_slash() corruption.

        This is the bug that corrupted the Who We Are page on Aug 6 2026.
        WordPress's update_post_meta() applies wp_slash() which escapes
        double quotes in JSON values. When a raw JSON string is read from
        the DB and written back via update_post_meta(), the stored value
        gets double-escaped.

        The parity harness must detect this mismatch.
        """
        # REST API unslashes on read → returns clean JSON
        mock_rest_client.get_meta.return_value = {"_elementor_data": VALID_ELEMENTOR}
        # DB has the slashed (corrupted) value
        mock_db_client.get_raw_meta.return_value = SLASHED_ELEMENTOR

        result = harness.verify_meta_parity(43)

        # The harness MUST detect the corruption
        assert result.matches is False, (
            "Parity harness failed to detect wp_slash() corruption! "
            "REST returns clean JSON but DB has slashed (corrupted) value."
        )
        assert result.db_json_valid is False, "Slashed JSON should not parse as valid JSON"
        assert result.rest_json_valid is True, "REST API should return valid (unslashed) JSON"


class TestVerifyElementorStructure:
    """Tests for Elementor AST validation via the harness."""

    def test_valid_elementor_returns_model(
        self,
        harness: WordPressDualHarness,
        mock_db_client: MagicMock,
    ) -> None:
        """Valid Elementor data returns a validated model."""
        mock_db_client.get_raw_meta.return_value = VALID_ELEMENTOR

        model = harness.verify_elementor_structure(43)

        assert isinstance(model, ElementorPageModel)
        assert model.section_count == 1
        assert model.widget_count == 1
        assert "w1" in model.widget_ids

    def test_invalid_elementor_raises(
        self,
        harness: WordPressDualHarness,
        mock_db_client: MagicMock,
    ) -> None:
        """Invalid Elementor data raises ElementorValidationError."""
        from phosphene.imi_wordpress.elementor_model import ElementorValidationError

        mock_db_client.get_raw_meta.return_value = "{not valid json"

        with pytest.raises(ElementorValidationError):
            harness.verify_elementor_structure(43)


class TestSafeWriteElementor:
    """Tests for the safe write pipeline."""

    def test_successful_write(
        self,
        harness: WordPressDualHarness,
        mock_rest_client: MagicMock,
        mock_db_client: MagicMock,
    ) -> None:
        """A successful safe write returns verified=True."""
        # Pre-write parity: both layers return same clean value
        mock_rest_client.get_meta.return_value = {"_elementor_data": VALID_ELEMENTOR}
        mock_db_client.get_raw_meta.return_value = VALID_ELEMENTOR

        # Write succeeds
        mock_db_client.set_elementor_data.return_value = {
            "status": "updated",
            "verify_length": len(VALID_ELEMENTOR),
            "verify_json_valid": True,
        }
        mock_db_client.backup_page.return_value = {"page_id": 43}

        result = harness.safe_write_elementor(43, VALID_ELEMENTOR)

        assert result["verified"] is True
        assert result["write_result"]["status"] == "updated"
        assert result["elementor"]["widget_count"] == 1

    def test_write_fails_on_invalid_json(
        self,
        harness: WordPressDualHarness,
        mock_db_client: MagicMock,
    ) -> None:
        """Invalid JSON should raise before any write attempt."""
        mock_db_client.get_raw_meta.return_value = VALID_ELEMENTOR
        mock_rest_client = MagicMock(spec=UrllibWPClient)
        mock_rest_client.get_meta.return_value = {"_elementor_data": VALID_ELEMENTOR}
        harness.rest = mock_rest_client

        from phosphene.imi_wordpress.elementor_model import ElementorValidationError

        with pytest.raises(ElementorValidationError):
            harness.safe_write_elementor(43, "{invalid json")

    def test_write_fails_on_db_error(
        self,
        harness: WordPressDualHarness,
        mock_rest_client: MagicMock,
        mock_db_client: MagicMock,
    ) -> None:
        """A DB write failure should raise RuntimeError."""
        mock_rest_client.get_meta.return_value = {"_elementor_data": VALID_ELEMENTOR}
        mock_db_client.get_raw_meta.return_value = VALID_ELEMENTOR
        mock_db_client.set_elementor_data.return_value = {"status": "failed"}
        mock_db_client.backup_page.return_value = {"page_id": 43}

        with pytest.raises(RuntimeError, match="Write failed"):
            harness.safe_write_elementor(43, VALID_ELEMENTOR)

    def test_write_detects_post_write_parity_failure(
        self,
        harness: WordPressDualHarness,
        mock_rest_client: MagicMock,
        mock_db_client: MagicMock,
    ) -> None:
        """Post-write parity failure should not verify."""
        # Pre-write: both layers match
        mock_rest_client.get_meta.return_value = {"_elementor_data": VALID_ELEMENTOR}
        mock_db_client.get_raw_meta.return_value = VALID_ELEMENTOR
        mock_db_client.backup_page.return_value = {"page_id": 43}

        # Write succeeds
        mock_db_client.set_elementor_data.return_value = {
            "status": "updated",
            "verify_length": len(VALID_ELEMENTOR),
            "verify_json_valid": True,
        }

        # Post-write: REST returns clean, DB has slashed (corruption!)
        # Simulate by changing the DB response after the write call
        call_count = {"db": 0}

        def db_side_effect(post_id, meta_key="_elementor_data"):
            call_count["db"] += 1
            if call_count["db"] <= 1:  # Pre-write read
                return VALID_ELEMENTOR
            else:  # Post-write read — simulate corruption
                return SLASHED_ELEMENTOR

        mock_db_client.get_raw_meta.side_effect = db_side_effect

        result = harness.safe_write_elementor(43, VALID_ELEMENTOR)

        assert result["verified"] is False
        assert result["post_parity"]["matches"] is False
