"""Tests for the in-process fakes (FakeWPClient, FakeDBClient).

These tests verify the fakes execute real behavior (A5 mock-doubles),
not just record calls. A fake that doesn't store/return data correctly
is useless as a test double.

@dft
- A1 (pure-io-separation): tests are pure — fakes are in-process, no network.
- A5 (mock-doubles): tests the fakes themselves (real behavior, not mocks).
- A6 (check-result): fakes return real data structures (the proof).
"""

from __future__ import annotations

import json

import pytest

from phosphene.imi_wordpress.config import WPConfig
from phosphene.imi_wordpress.fakes import FakeDBClient, FakeWPClient


@pytest.fixture
def wp_config() -> WPConfig:
    return WPConfig(url="https://example.com", username="test", app_password="test-pass")


@pytest.fixture
def wp_client(wp_config: WPConfig) -> FakeWPClient:
    return FakeWPClient(config=wp_config)


@pytest.fixture
def db_client() -> FakeDBClient:
    return FakeDBClient()


class TestFakeWPClient:
    """FakeWPClient executes real REST-client behavior in-process."""

    def test_get_page_returns_seeded_page(self, wp_client: FakeWPClient) -> None:
        wp_client.seed_page(43, {"id": 43, "title": "Who We Are"})
        result = wp_client.get_page(43)
        assert result["id"] == 43
        assert result["title"] == "Who We Are"

    def test_get_page_returns_error_for_missing(self, wp_client: FakeWPClient) -> None:
        result = wp_client.get_page(999)
        assert result["error"] is True

    def test_get_meta_returns_seeded_meta(self, wp_client: FakeWPClient) -> None:
        wp_client.seed_page(43, {"id": 43}, meta={"_elementor_data": '{"key":"val"}'})
        meta = wp_client.get_meta(43)
        assert meta["_elementor_data"] == '{"key":"val"}'

    def test_update_page_modifies_seeded_page(self, wp_client: FakeWPClient) -> None:
        wp_client.seed_page(43, {"id": 43, "title": "Old"})
        wp_client.update_page(43, {"title": "New"})
        assert wp_client.pages[43]["title"] == "New"

    def test_create_post_assigns_incrementing_id(self, wp_client: FakeWPClient) -> None:
        post1 = wp_client.create_post("imi_registry", {"title": "First"})
        post2 = wp_client.create_post("imi_registry", {"title": "Second"})
        assert post1["id"] == 1
        assert post2["id"] == 2

    def test_post_exists_finds_created_post(self, wp_client: FakeWPClient) -> None:
        wp_client.create_post("imi_registry", {"title": "Test", "slug": "test-slug"})
        assert wp_client.post_exists("imi_registry", "test-slug") is True
        assert wp_client.post_exists("imi_registry", "missing") is False

    def test_calls_are_recorded(self, wp_client: FakeWPClient) -> None:
        wp_client.get_page(43)
        wp_client.get_meta(43)
        assert len(wp_client.calls) == 2
        assert wp_client.calls[0]["method"] == "get_page"
        assert wp_client.calls[1]["method"] == "get_meta"


class TestFakeDBClient:
    """FakeDBClient executes real DB-client behavior in-process."""

    def test_set_then_get_roundtrip(self, db_client: FakeDBClient) -> None:
        db_client.set_elementor_data(43, '{"key":"val"}')
        assert db_client.get_raw_meta(43) == '{"key":"val"}'

    def test_set_returns_verified_result(self, db_client: FakeDBClient) -> None:
        result = db_client.set_elementor_data(43, '{"key":"val"}')
        assert result["status"] == "updated"
        assert result["verify_json_valid"] is True
        assert result["verify_length"] == len('{"key":"val"}')

    def test_set_invalid_json_reports_invalid(self, db_client: FakeDBClient) -> None:
        result = db_client.set_elementor_data(43, "{not json")
        assert result["verify_json_valid"] is False

    def test_simulate_slashing_corrupts_data(self, db_client: FakeDBClient) -> None:
        """The slashing simulation is the core regression test enabler."""
        db_client.simulate_slashing(True)
        original = '{"key": "val"}'
        db_client.set_elementor_data(43, original)
        stored = db_client.get_raw_meta(43)
        assert stored != original  # Corruption!
        assert '\\"' in stored  # Double quotes escaped

    def test_slashing_makes_json_invalid(self, db_client: FakeDBClient) -> None:
        db_client.simulate_slashing(True)
        db_client.set_elementor_data(43, '{"key": "val"}')
        stored = db_client.get_raw_meta(43)
        with pytest.raises(json.JSONDecodeError):
            json.loads(stored)

    def test_backup_captures_meta(self, db_client: FakeDBClient) -> None:
        db_client.seed_meta(43, "_elementor_data", '{"key":"val"}')
        backup = db_client.backup_page(43)
        assert backup["page_id"] == 43
        assert backup["meta"]["_elementor_data"] == '{"key":"val"}'

    def test_write_log_records_writes(self, db_client: FakeDBClient) -> None:
        db_client.set_elementor_data(43, '{"key":"val"}')
        assert len(db_client.write_log) == 1
        assert db_client.write_log[0]["post_id"] == 43
