"""Tests for DryRunWPClient."""

from __future__ import annotations

from phosphene.imi_wordpress.dryrun import DryRunWPClient


class TestDryRunWPClient:
    """DryRunWPClient behavior tests."""

    def test_calls_list_starts_empty(self, dry_run_client: DryRunWPClient) -> None:
        """Fresh client has no recorded calls."""
        assert dry_run_client.calls == []

    def test_create_post_records_call(self, dry_run_client: DryRunWPClient) -> None:
        """create_post appends to the calls list."""
        payload = {"title": "Test Post", "status": "draft"}
        dry_run_client.create_post(payload)

        assert len(dry_run_client.calls) == 1
        assert dry_run_client.calls[0]["method"] == "create_post"
        assert dry_run_client.calls[0]["args"]["payload"] == payload

    def test_post_exists_returns_false(self, dry_run_client: DryRunWPClient) -> None:
        """post_exists always returns False in dry-run mode."""
        assert dry_run_client.post_exists("any-slug") is False

    def test_post_exists_records_call(self, dry_run_client: DryRunWPClient) -> None:
        """post_exists records the lookup call."""
        dry_run_client.post_exists("test-slug")

        assert len(dry_run_client.calls) == 1
        assert dry_run_client.calls[0]["method"] == "post_exists"

    def test_post_url_returns_synthetic(self, dry_run_client: DryRunWPClient) -> None:
        """post_url returns a synthetic URL."""
        url = dry_run_client.post_url(42)
        assert "42" in url

    def test_multiple_calls_accumulate(self, dry_run_client: DryRunWPClient) -> None:
        """Multiple method calls all accumulate in the calls list."""
        dry_run_client.create_post({"title": "A"})
        dry_run_client.post_exists("b")
        dry_run_client.post_url(1)

        assert len(dry_run_client.calls) == 3
