"""Tests for ElementorPageModel — structural AST validation."""

from __future__ import annotations

import json

import pytest

from phosphene.imi_wordpress.elementor_model import (
    ElementorPageModel,
    ElementorValidationError,
)

# --- Fixtures ---

SIMPLE_PAGE = json.dumps(
    [
        {
            "id": "abc123",
            "elType": "section",
            "settings": {"padding": {"top": "50"}},
            "elements": [
                {
                    "id": "col1",
                    "elType": "column",
                    "settings": {"_column_size": 100},
                    "elements": [
                        {
                            "id": "w1",
                            "elType": "widget",
                            "widgetType": "heading",
                            "settings": {"title": "Hello World"},
                        },
                        {
                            "id": "w2",
                            "elType": "widget",
                            "widgetType": "image",
                            "settings": {"image": {"url": "https://example.com/img.jpg"}},
                        },
                    ],
                },
            ],
        }
    ]
)

MULTI_SECTION_PAGE = json.dumps(
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
                    ],
                },
            ],
        },
        {
            "id": "s2",
            "elType": "section",
            "settings": {},
            "elements": [
                {
                    "id": "c2",
                    "elType": "column",
                    "settings": {},
                    "elements": [
                        {
                            "id": "w2",
                            "elType": "widget",
                            "widgetType": "text-editor",
                            "settings": {},
                        },
                        {"id": "w3", "elType": "widget", "widgetType": "button", "settings": {}},
                    ],
                },
            ],
        },
    ]
)


class TestElementorPageModelParsing:
    """Tests for JSON parsing and schema validation."""

    def test_valid_json_parses(self) -> None:
        """A valid Elementor JSON should parse without error."""
        model = ElementorPageModel(SIMPLE_PAGE)
        assert model.section_count == 1
        assert model.widget_count == 2

    def test_invalid_json_raises(self) -> None:
        """Invalid JSON should raise ElementorValidationError."""
        with pytest.raises(ElementorValidationError, match="Invalid JSON"):
            ElementorPageModel("{not valid json")

    def test_root_must_be_list(self) -> None:
        """Root must be a JSON array, not an object."""
        with pytest.raises(ElementorValidationError, match="must be a list"):
            ElementorPageModel('{"id": "x", "elType": "section"}')

    def test_empty_array_valid(self) -> None:
        """An empty array is a valid (empty) Elementor page."""
        model = ElementorPageModel("[]")
        assert model.section_count == 0
        assert model.widget_count == 0


class TestElementorPageModelSchema:
    """Tests for element schema validation."""

    def test_unknown_eltype_raises(self) -> None:
        """Unknown elType should fail validation."""
        bad = json.dumps([{"id": "x", "elType": "container", "settings": {}}])
        with pytest.raises(ElementorValidationError, match="Unknown elType"):
            ElementorPageModel(bad)

    def test_missing_id_raises(self) -> None:
        """Missing id field should fail validation."""
        bad = json.dumps([{"elType": "section", "settings": {}, "elements": []}])
        with pytest.raises(ElementorValidationError, match="missing 'id'"):
            ElementorPageModel(bad)

    def test_elements_must_be_list(self) -> None:
        """Non-list elements field should fail validation."""
        bad = json.dumps(
            [{"id": "x", "elType": "section", "settings": {}, "elements": "not a list"}]
        )
        with pytest.raises(ElementorValidationError, match="must be a list"):
            ElementorPageModel(bad)

    def test_nested_validation(self) -> None:
        """Validation should recurse into nested elements."""
        # Column with invalid child
        bad = json.dumps(
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
                            "elements": [{"id": "w1", "elType": "widget", "settings": {}}],
                        }
                    ],
                }
            ]
        )
        model = ElementorPageModel(bad)
        assert model.widget_count == 1

    def test_multi_section_count(self) -> None:
        """Multi-section page should count sections and widgets correctly."""
        model = ElementorPageModel(MULTI_SECTION_PAGE)
        assert model.section_count == 2
        assert model.widget_count == 3


class TestElementorPageModelWidgets:
    """Tests for widget extraction and search."""

    def test_extract_widgets(self) -> None:
        """widgets() should return all widgets in document order."""
        model = ElementorPageModel(SIMPLE_PAGE)
        widgets = model.widgets()
        assert len(widgets) == 2
        assert widgets[0].widget_type == "heading"
        assert widgets[1].widget_type == "image"

    def test_find_widget_by_id(self) -> None:
        """find_widget should locate an element by ID."""
        model = ElementorPageModel(SIMPLE_PAGE)
        found = model.find_widget("w1")
        assert found is not None
        assert found["widgetType"] == "heading"

    def test_find_widget_not_found(self) -> None:
        """find_widget should return None for non-existent ID."""
        model = ElementorPageModel(SIMPLE_PAGE)
        assert model.find_widget("nonexistent") is None

    def test_contains_text(self) -> None:
        """contains_text should search widget settings case-insensitively."""
        model = ElementorPageModel(SIMPLE_PAGE)
        assert model.contains_text("Hello World") is True
        assert model.contains_text("hello world") is True
        assert model.contains_text("Goodbye") is False


class TestElementorPageModelDiff:
    """Tests for structural diff between models."""

    def test_diff_no_change(self) -> None:
        """Diffing a model against itself should show zero deltas."""
        model = ElementorPageModel(SIMPLE_PAGE)
        diff = model.diff(model)
        assert diff["widget_delta"] == 0
        assert diff["added_widgets"] == []
        assert diff["removed_widgets"] == []

    def test_diff_added_widget(self) -> None:
        """Diff should detect added widgets."""
        model_a = ElementorPageModel(SIMPLE_PAGE)
        model_b = ElementorPageModel(MULTI_SECTION_PAGE)
        diff = model_a.diff(model_b)
        assert diff["widget_delta"] == 1  # 3 - 2 = 1
        assert "w2" in diff["added_widgets"] or "w3" in diff["added_widgets"]

    def test_to_json_roundtrip(self) -> None:
        """to_json should produce equivalent JSON."""
        model = ElementorPageModel(SIMPLE_PAGE)
        roundtripped = ElementorPageModel(model.to_json())
        assert roundtripped.widget_count == model.widget_count
        assert roundtripped.section_count == model.section_count
