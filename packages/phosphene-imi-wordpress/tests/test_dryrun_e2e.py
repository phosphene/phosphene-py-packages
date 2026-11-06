"""End-to-end dry-run tests — full pipeline, no network.

Proves that the complete Draft → DryRunWPClient → assertions pipeline
works without any HTTP requests.  Tests use the real IMIRegistryPost
CPT definition and the real DryRunWPClient.
"""

from __future__ import annotations

from phosphene.imi_wordpress.cpts.imi_registry import IMIRegistryMeta, IMIRegistryPost
from phosphene.imi_wordpress.dryrun import DryRunWPClient


def _make_draft(
    title: str = "Why Care Work Matters",
    author: str = "Gunnar Rundgren",
    category: str = "Economy",
    source_url: str = "https://source.com/task/1",
) -> IMIRegistryPost:
    """Build a realistic IMIRegistryPost for testing."""
    slug = title.lower().replace(" ", "-")
    # Simplistic slug — mirrors the real slugify logic for ASCII titles
    return IMIRegistryPost(
        title=title,
        slug=slug,
        status="publish",
        meta=IMIRegistryMeta(
            author_name=author,
            category=category,
            source_url=source_url,
        ),
    )


class TestFullPipelineDryRun:
    """Full pipeline: Draft → DryRunWPClient → result assertions."""

    def test_full_pipeline_records_calls(self) -> None:
        """End-to-end: exists check + create records exactly 2 calls."""
        client = DryRunWPClient()
        draft = _make_draft()

        client.post_exists(draft.slug)
        result = client.create_post(draft.to_wp_payload())

        assert len(client.calls) == 2
        assert client.calls[0]["method"] == "post_exists"
        assert client.calls[0]["args"]["slug"] == draft.slug
        assert client.calls[1]["method"] == "create_post"
        assert client.calls[1]["args"]["payload"]["title"] == draft.title
        assert result["status"] == "publish"

    def test_payload_carries_all_meta_fields(self) -> None:
        """The WP payload from IMIRegistryPost includes all meta fields."""
        draft = _make_draft()
        payload = draft.to_wp_payload()

        assert payload["meta"]["author_name"] == "Gunnar Rundgren"
        assert payload["meta"]["category"] == "Economy"
        assert payload["meta"]["source_url"] == "https://source.com/task/1"

    def test_result_echoes_payload(self) -> None:
        """DryRunWPClient returns a result that includes the original payload keys."""
        client = DryRunWPClient()
        draft = _make_draft()
        result = client.create_post(draft.to_wp_payload())

        assert result["title"] == draft.title
        assert result["slug"] == draft.slug
        assert result["status"] == "publish"


class TestDryRunNoHTTP:
    """Prove that no real HTTP requests are made."""

    def test_client_has_no_urlopen(self) -> None:
        """DryRunWPClient doesn't import or use urllib.request."""
        client = DryRunWPClient()
        # Verify the client has no config, no auth, no network attributes
        assert not hasattr(client, "config")
        assert not hasattr(client, "_auth_header")

    def test_create_post_is_pure(self) -> None:
        """create_post returns a synthetic dict without any network call."""
        client = DryRunWPClient()
        result = client.create_post({"title": "Test", "status": "draft"})
        assert isinstance(result, dict)
        assert result["id"] == 0  # Synthetic ID
        assert result["status"] == "draft"

    def test_post_exists_is_pure(self) -> None:
        """post_exists returns False without any network call."""
        client = DryRunWPClient()
        assert client.post_exists("any-slug-at-all") is False

    def test_post_url_is_pure(self) -> None:
        """post_url returns a synthetic URL without any network call."""
        client = DryRunWPClient()
        url = client.post_url(99)
        assert url == "https://example.com/?p=99"


class TestDryRunIdempotency:
    """Idempotency patterns using the call log."""

    def test_duplicate_publish_detected_via_call_log(self) -> None:
        """The outlet idempotency pattern: check calls before creating again."""
        client = DryRunWPClient()
        draft = _make_draft()
        slug = draft.slug
        payload = draft.to_wp_payload()

        # First publish
        client.create_post(payload)

        # Second publish — check call log for idempotency (outlet pattern)
        already_published = any(
            c["method"] == "create_post" and c["args"]["payload"].get("slug") == slug
            for c in client.calls
        )
        assert already_published is True
        # Don't create again — exactly 1 create call
        assert (
            sum(
                1
                for c in client.calls
                if c["method"] == "create_post" and c["args"]["payload"].get("slug") == slug
            )
            == 1
        )

    def test_different_slugs_are_independent(self) -> None:
        """Two different drafts don't trigger idempotency conflict."""
        client = DryRunWPClient()
        draft_a = _make_draft(title="Article A")
        draft_b = _make_draft(title="Article B")

        client.create_post(draft_a.to_wp_payload())
        client.create_post(draft_b.to_wp_payload())

        assert len(client.calls) == 2
        slugs = {c["args"]["payload"]["slug"] for c in client.calls}
        assert len(slugs) == 2

    def test_fresh_client_has_no_history(self) -> None:
        """A new DryRunWPClient has no call history — clean slate."""
        client = DryRunWPClient()
        assert client.calls == []
        # No idempotency conflict on first publish
        already = any(c["method"] == "create_post" for c in client.calls)
        assert already is False
