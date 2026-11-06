"""TDD tests for IMIPipeline runner.

Tests written FIRST (red phase) — the pipeline module does not yet exist.
Each test exercises one discrete behavior of the pipeline runner:
fan-out to outlets, result aggregation, failure isolation, dry-run mode.
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Inline fixture — lightweight Draft stand-in
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Draft:
    """Minimal draft fixture for pipeline tests."""

    title: str = "Test Article"
    body: str = "<p>Hello world</p>"


@pytest.fixture()
def draft() -> Draft:
    """Return a simple Draft fixture."""
    return Draft()


def _make_outlet(name: str, *, succeed: bool = True, artifact: str | None = None) -> MagicMock:
    """Build a mock outlet with a controllable publish method.

    Args:
        name: Outlet name (e.g. ``"wordpress"``, ``"salesforce"``).
        succeed: If True, publish returns a success dict; if False, raises.
        artifact: Optional artifact string returned on success.
    """
    outlet = MagicMock()
    outlet.name = name
    if succeed:
        outlet.publish.return_value = {"ok": True, "artifact": artifact}
    else:
        outlet.publish.side_effect = RuntimeError(f"{name} outlet failed")
    return outlet


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestIMIPipeline:
    """Pipeline runner test suite — 6 tests, all must fail initially (red)."""

    def test_pipeline_publishes_to_all_outlets(self, draft: Draft) -> None:
        """Pipeline calls publish on every registered outlet."""
        from phosphene.imi_wordpress.pipeline import IMIPipeline

        wp = _make_outlet("wordpress", artifact="https://example.com/post/1")
        sf = _make_outlet("salesforce", artifact="sf-id-123")

        pipeline = IMIPipeline(outlets=[wp, sf])
        pipeline.run(draft)

        wp.publish.assert_called_once_with(draft)
        sf.publish.assert_called_once_with(draft)

    def test_pipeline_returns_report_with_all_results(self, draft: Draft) -> None:
        """Pipeline result contains one OutletCallResult per outlet, all_succeeded=True."""
        from phosphene.imi_wordpress.pipeline import IMIPipeline

        wp = _make_outlet("wordpress", artifact="https://example.com/post/1")
        sf = _make_outlet("salesforce", artifact="sf-id-123")

        pipeline = IMIPipeline(outlets=[wp, sf])
        result = pipeline.run(draft)

        assert len(result.outlet_results) == 2
        assert result.all_succeeded is True

    def test_pipeline_continues_on_outlet_failure(self, draft: Draft) -> None:
        """When one outlet fails, the pipeline still calls subsequent outlets."""
        from phosphene.imi_wordpress.pipeline import IMIPipeline

        wp = _make_outlet("wordpress", succeed=False)
        sf = _make_outlet("salesforce", artifact="sf-id-123")

        pipeline = IMIPipeline(outlets=[wp, sf])
        result = pipeline.run(draft)

        # SF was still called even though WP failed
        sf.publish.assert_called_once_with(draft)
        assert result.all_succeeded is False

    def test_pipeline_dry_run_mode(self, draft: Draft) -> None:
        """In dry-run mode, outlets are NOT called and result.dry_run=True."""
        from phosphene.imi_wordpress.pipeline import IMIPipeline

        wp = _make_outlet("wordpress")
        sf = _make_outlet("salesforce")

        pipeline = IMIPipeline(outlets=[wp, sf], dry_run=True)
        result = pipeline.run(draft)

        wp.publish.assert_not_called()
        sf.publish.assert_not_called()
        assert result.dry_run is True

    def test_pipeline_result_wordpress_url(self, draft: Draft) -> None:
        """result.wordpress_url extracts the artifact from the wordpress outlet."""
        from phosphene.imi_wordpress.pipeline import IMIPipeline

        wp = _make_outlet("wordpress", artifact="https://example.com/post/42")
        sf = _make_outlet("salesforce", artifact="sf-id-999")

        pipeline = IMIPipeline(outlets=[wp, sf])
        result = pipeline.run(draft)

        assert result.wordpress_url == "https://example.com/post/42"

    def test_pipeline_with_no_outlets_returns_empty_report(self) -> None:
        """Empty outlet list → all_succeeded=True, no outlet results."""
        from phosphene.imi_wordpress.pipeline import IMIPipeline

        pipeline = IMIPipeline(outlets=[])
        result = pipeline.run(Draft())

        assert result.outlet_results == []
        assert result.all_succeeded is True
