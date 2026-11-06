"""Unit tests for IMIRegistryPost and IMIRegistryMeta — Draft→WP payload mapping."""

from __future__ import annotations

from phosphene.imi_wordpress.cpts.imi_registry import IMIRegistryMeta, IMIRegistryPost


class TestIMIRegistryMeta:
    def test_defaults_are_empty_strings(self):
        meta = IMIRegistryMeta()
        assert meta.author_name == ""
        assert meta.category == ""
        assert meta.source_url == ""

    def test_fields_set_correctly(self):
        meta = IMIRegistryMeta(
            author_name="Jane Smith",
            category="Economy",
            source_url="https://example.com",
        )
        assert meta.author_name == "Jane Smith"
        assert meta.category == "Economy"
        assert meta.source_url == "https://example.com"


class TestIMIRegistryPost:
    def test_title_required(self):
        post = IMIRegistryPost(title="Why Care Work Matters")
        assert post.title == "Why Care Work Matters"

    def test_default_status_is_draft(self):
        assert IMIRegistryPost(title="T").status == "draft"

    def test_slug_defaults_empty(self):
        assert IMIRegistryPost(title="T").slug == ""


class TestToWpPayload:
    """Draft→WP payload mapping — the critical integration contract."""

    def test_title_maps_to_title(self):
        payload = IMIRegistryPost(title="Why Care Work Matters").to_wp_payload()
        assert payload["title"] == "Why Care Work Matters"

    def test_status_maps_to_status(self):
        assert IMIRegistryPost(title="T", status="publish").to_wp_payload()["status"] == "publish"

    def test_author_name_maps_to_meta_author_name(self):
        """THE critical mapping: author_name lands in meta.author_name."""
        post = IMIRegistryPost(title="T", meta=IMIRegistryMeta(author_name="Jane Smith"))
        assert post.to_wp_payload()["meta"]["author_name"] == "Jane Smith"

    def test_category_maps_to_meta_category(self):
        post = IMIRegistryPost(title="T", meta=IMIRegistryMeta(category="Economy"))
        assert post.to_wp_payload()["meta"]["category"] == "Economy"

    def test_source_url_maps_to_meta_source_url(self):
        post = IMIRegistryPost(title="T", meta=IMIRegistryMeta(source_url="https://example.com"))
        assert post.to_wp_payload()["meta"]["source_url"] == "https://example.com"

    def test_slug_included_when_set(self):
        post = IMIRegistryPost(title="T", slug="why-care-work-matters")
        assert post.to_wp_payload()["slug"] == "why-care-work-matters"

    def test_slug_excluded_when_empty(self):
        assert "slug" not in IMIRegistryPost(title="T", slug="").to_wp_payload()

    def test_meta_key_present_in_payload(self):
        assert "meta" in IMIRegistryPost(title="T").to_wp_payload()

    def test_all_meta_fields_present(self):
        meta = IMIRegistryPost(title="T").to_wp_payload()["meta"]
        assert "author_name" in meta
        assert "category" in meta
        assert "source_url" in meta

    def test_empty_meta_yields_empty_strings(self):
        meta = IMIRegistryPost(title="T").to_wp_payload()["meta"]
        assert meta["author_name"] == ""
        assert meta["category"] == ""
        assert meta["source_url"] == ""

    def test_payload_is_dict(self):
        assert isinstance(IMIRegistryPost(title="T").to_wp_payload(), dict)
