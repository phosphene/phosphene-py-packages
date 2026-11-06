"""Tests for PayloadBuilder — REST API fixture factory."""

from __future__ import annotations

from pathlib import Path

import pytest

from phosphene.imi_wordpress.testing.payload_builder import PayloadBuilder

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def builder() -> PayloadBuilder:
    """Provide a PayloadBuilder wired to test fixtures."""
    return PayloadBuilder(fixture_dir=FIXTURE_DIR)


# ---------------------------------------------------------------------------
# valid()
# ---------------------------------------------------------------------------


class TestValid:
    """Tests for PayloadBuilder.valid()."""

    def test_valid_has_title(self, builder: PayloadBuilder) -> None:
        p = builder.valid()
        assert p["title"] == "On the Origins of Tool Use in Early Hominins"

    def test_valid_has_publish_status(self, builder: PayloadBuilder) -> None:
        assert builder.valid()["status"] == "publish"

    def test_valid_declaration_is_boolean(self, builder: PayloadBuilder) -> None:
        assert builder.valid()["meta"]["reg_declaration"] is True

    def test_valid_has_meta_fields(self, builder: PayloadBuilder) -> None:
        meta = builder.valid()["meta"]
        assert "reg_author_name" in meta
        assert "reg_abstract" in meta
        assert "reg_methodology" in meta

    def test_valid_abstract_at_least_150_words(self, builder: PayloadBuilder) -> None:
        abstract = builder.valid()["meta"]["reg_abstract"]
        word_count = len(abstract.split())
        assert word_count >= 150, f"Abstract only {word_count} words"

    def test_valid_returns_deep_copy(self, builder: PayloadBuilder) -> None:
        p1 = builder.valid()
        p2 = builder.valid()
        p1["meta"]["reg_author_name"] = "Mutated"
        assert p2["meta"]["reg_author_name"] != "Mutated"


# ---------------------------------------------------------------------------
# minimal()
# ---------------------------------------------------------------------------


class TestMinimal:
    """Tests for PayloadBuilder.minimal()."""

    def test_minimal_has_title(self, builder: PayloadBuilder) -> None:
        assert builder.minimal()["title"] == "Minimal Valid Registry Entry"

    def test_minimal_has_publish_status(self, builder: PayloadBuilder) -> None:
        assert builder.minimal()["status"] == "publish"

    def test_minimal_declaration_is_boolean(self, builder: PayloadBuilder) -> None:
        assert builder.minimal()["meta"]["reg_declaration"] is True

    def test_minimal_has_only_required_meta(self, builder: PayloadBuilder) -> None:
        meta = builder.minimal()["meta"]
        assert "reg_author_name" in meta
        assert "reg_abstract" in meta
        assert "reg_methodology" in meta
        assert "reg_license" in meta

    def test_minimal_returns_deep_copy(self, builder: PayloadBuilder) -> None:
        p1 = builder.minimal()
        p2 = builder.minimal()
        p1["title"] = "Mutated"
        assert p2["title"] != "Mutated"


# ---------------------------------------------------------------------------
# draft()
# ---------------------------------------------------------------------------


class TestDraft:
    """Tests for PayloadBuilder.draft()."""

    def test_draft_status_is_draft(self, builder: PayloadBuilder) -> None:
        assert builder.draft()["status"] == "draft"

    def test_draft_has_no_declaration(self, builder: PayloadBuilder) -> None:
        assert "reg_declaration" not in builder.draft()["meta"]

    def test_draft_preserves_other_fields(self, builder: PayloadBuilder) -> None:
        d = builder.draft()
        assert d["title"] == "On the Origins of Tool Use in Early Hominins"
        assert "reg_author_name" in d["meta"]


# ---------------------------------------------------------------------------
# without_field()
# ---------------------------------------------------------------------------


class TestWithoutField:
    """Tests for PayloadBuilder.without_field()."""

    def test_removes_specified_field(self, builder: PayloadBuilder) -> None:
        p = builder.without_field("reg_orcid")
        assert "reg_orcid" not in p["meta"]

    def test_preserves_other_fields(self, builder: PayloadBuilder) -> None:
        p = builder.without_field("reg_orcid")
        assert "reg_author_name" in p["meta"]
        assert "reg_abstract" in p["meta"]

    def test_nonexistent_field_no_error(self, builder: PayloadBuilder) -> None:
        p = builder.without_field("reg_nonexistent_field")
        assert "reg_nonexistent_field" not in p["meta"]


# ---------------------------------------------------------------------------
# with_override() / with_meta_override() / with_empty_required()
# ---------------------------------------------------------------------------


class TestOverrides:
    """Tests for override and mutation methods."""

    def test_with_override_top_level(self, builder: PayloadBuilder) -> None:
        p = builder.with_override("status", "pending")
        assert p["status"] == "pending"

    def test_with_meta_override(self, builder: PayloadBuilder) -> None:
        p = builder.with_meta_override("reg_methodology", "theoretical")
        assert p["meta"]["reg_methodology"] == "theoretical"

    def test_with_empty_required(self, builder: PayloadBuilder) -> None:
        p = builder.with_empty_required("reg_author_name")
        assert p["meta"]["reg_author_name"] == ""

    def test_override_returns_deep_copy(self, builder: PayloadBuilder) -> None:
        builder.with_override("title", "Changed")
        p2 = builder.valid()
        assert p2["title"] != "Changed"

    def test_meta_override_returns_deep_copy(self, builder: PayloadBuilder) -> None:
        builder.with_meta_override("reg_country", "France")
        p2 = builder.valid()
        assert p2["meta"]["reg_country"] != "France"
