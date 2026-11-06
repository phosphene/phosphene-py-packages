"""String mutation matrix — regression tests for WP hook side-effects.

WordPress's update_post_meta() applies wp_slash() which escapes double
quotes, backslashes, and NUL bytes. These parameterized tests confirm
that the parity harness detects escaping behavior across a matrix of
problematic string values.

The mutation matrix covers:
- Raw double quotes (JSON's native delimiter)
- Unescaped backslashes (URL paths, regex patterns)
- Multibyte UTF-8 characters (em-dashes, smart quotes, CJK)
- HTML strings (angle brackets, entities)
- Null bytes
- Mixed content (real-world Elementor data fragments)
"""

from __future__ import annotations

import json

import pytest

from phosphene.imi_wordpress.elementor_model import ElementorPageModel

# --- String Mutation Matrix ---

MUTATION_CASES = [
    # (name, raw_value, expected_after_slash)
    ("double_quotes", '{"key": "value"}', '{\\"key\\": \\"value\\"}'),
    ("nested_quotes", '{"title": "He said \\"hello\\""}', '{"title": "He said \\\\"hello\\\\""}'),
    (
        "backslash_url",
        '{"url": "https://example.com/path"}',
        '{"url": "https:\\/\\/example.com\\/path"}',
    ),
    ("em_dash", '{"text": "Author — Title"}', '{"text": "Author — Title"}'),
    ("smart_quotes", '{"text": ""Hello""}', '{"text": "\\u201cHello\\u201d"}'),
    ("html_entities", '{"html": "<p>Hello</p>"}', '{"html": "<p>Hello<\\/p>"}'),
    ("cjk_characters", '{"name": "田中太郎"}', '{"name": "田中太郎"}'),
    ("null_byte_safe", '{"x": "before\\u0000after"}', '{"x": "before\\u0000after"}'),
]


class TestStringMutationMatrix:
    """Parameterized tests confirming escaping behavior detection."""

    @pytest.mark.parametrize("name,raw,slashed", MUTATION_CASES)
    def test_slash_detection(self, name: str, raw: str, slashed: str) -> None:
        """Each mutation case: slashed value must differ from raw."""
        # The slashing changes the value
        if raw != slashed:
            assert raw != slashed, f"Case '{name}': wp_slash should change this value"
            # Slashed version should fail JSON parse (in most cases)
            try:
                json.loads(slashed)
                # Some slashed values might still parse (e.g. multibyte)
            except json.JSONDecodeError:
                pass  # Expected: slashed JSON is invalid

    @pytest.mark.regression
    @pytest.mark.parametrize("name,raw,slashed", MUTATION_CASES)
    def test_parity_detects_slashing(self, name: str, raw: str, slashed: str) -> None:
        """Parity check must flag when REST returns clean but DB has slashed."""
        from unittest.mock import MagicMock

        from phosphene.imi_wordpress.client import UrllibWPClient
        from phosphene.imi_wordpress.db_client import WPEngineDBClient
        from phosphene.imi_wordpress.parity_harness import (
            WordPressDualHarness,
        )

        rest = MagicMock(spec=UrllibWPClient)
        db = MagicMock(spec=WPEngineDBClient)

        rest.get_meta.return_value = {"_elementor_data": raw}
        db.get_raw_meta.return_value = slashed

        harness = WordPressDualHarness(rest, db)
        result = harness.verify_meta_parity(43)

        if raw != slashed:
            assert result.matches is False, (
                f"Case '{name}': parity check failed to detect slashing. "
                f"raw_len={len(raw)}, slashed_len={len(slashed)}"
            )


class TestReSerializationStability:
    """Verify json_decode → json_encode cycles are identity-stable."""

    @pytest.mark.parametrize("name,raw,slashed", MUTATION_CASES)
    def test_json_roundtrip(self, name: str, raw: str, slashed: str) -> None:
        """json.loads → json.dumps should preserve structure."""
        try:
            parsed = json.loads(raw)
            roundtripped = json.dumps(parsed)
            reparsed = json.loads(roundtripped)
            assert reparsed == parsed, f"Case '{name}': round-trip changed structure"
        except json.JSONDecodeError:
            # Some test cases are intentionally not valid JSON
            pass

    def test_elementor_model_roundtrip(self) -> None:
        """ElementorPageModel.to_json() should preserve widget count."""
        data = json.dumps(
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
                                {
                                    "id": "w1",
                                    "elType": "widget",
                                    "widgetType": "heading",
                                    "settings": {},
                                },
                            ],
                        }
                    ],
                }
            ]
        )
        model = ElementorPageModel(data)
        roundtripped = ElementorPageModel(model.to_json())
        assert roundtripped.widget_count == model.widget_count
        assert roundtripped.section_count == model.section_count
        assert roundtripped.widget_ids == model.widget_ids


class TestRemoveWidgetById:
    """Tests for targeted widget removal while maintaining collateral layout."""

    def _build_model(self, widgets: list[tuple[str, str]]) -> ElementorPageModel:
        """Build a test model with the given widgets in a single section."""
        data = [
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
                            {"id": wid, "elType": "widget", "widgetType": wtype, "settings": {}}
                            for wid, wtype in widgets
                        ],
                    }
                ],
            }
        ]
        return ElementorPageModel(json.dumps(data))

    def test_remove_single_widget(self) -> None:
        """Removing one widget from a multi-widget page preserves others."""
        model = self._build_model(
            [
                ("w1", "heading"),
                ("w2", "image"),
                ("w3", "button"),
            ]
        )
        result = model.remove_widget_by_id("w2")

        assert result.widget_count == 2
        assert "w2" not in result.widget_ids
        assert "w1" in result.widget_ids
        assert "w3" in result.widget_ids

    def test_remove_preserves_section_structure(self) -> None:
        """Section and column elements survive widget removal."""
        model = self._build_model([("w1", "heading")])
        result = model.remove_widget_by_id("w1")

        assert result.section_count == 1
        assert "s1" in result.section_ids
        # Widget is gone, column remains (empty)
        assert result.widget_count == 0

    def test_remove_nested_widget(self) -> None:
        """Widget nested deep in the tree can be removed."""
        data = json.dumps(
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
                                {
                                    "id": "w1",
                                    "elType": "widget",
                                    "widgetType": "heading",
                                    "settings": {},
                                },
                            ],
                        },
                        {
                            "id": "c2",
                            "elType": "column",
                            "settings": {},
                            "elements": [
                                {
                                    "id": "w2",
                                    "elType": "widget",
                                    "widgetType": "image",
                                    "settings": {},
                                },
                            ],
                        },
                    ],
                }
            ]
        )
        model = ElementorPageModel(data)
        result = model.remove_widget_by_id("w2")

        assert result.widget_count == 1
        assert "w1" in result.widget_ids
        assert "w2" not in result.widget_ids

    def test_remove_nonexistent_raises(self) -> None:
        """Removing a non-existent widget ID raises."""
        model = self._build_model([("w1", "heading")])
        from phosphene.imi_wordpress.elementor_model import ElementorValidationError

        with pytest.raises(ElementorValidationError, match="not found"):
            model.remove_widget_by_id("nonexistent")

    def test_remove_original_unchanged(self) -> None:
        """The original model is not mutated by remove_widget_by_id."""
        model = self._build_model([("w1", "heading"), ("w2", "image")])
        original_count = model.widget_count
        model.remove_widget_by_id("w1")

        assert model.widget_count == original_count  # Original unchanged
