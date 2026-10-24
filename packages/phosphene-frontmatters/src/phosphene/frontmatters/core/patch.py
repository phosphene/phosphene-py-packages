"""Shadow Patch Engine for phosphene-frontmatters.

Implements the recursive synchronization logic that projects an 'Ideal'
model (OpenRecord or Pydantic) onto a 'Shadow' ruamel.yaml object. This
ensures that modifications are performed in-place, preserving human-authored
comments, custom indentation, and formatting.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, get_args, get_origin

from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.scalarstring import (
    DoubleQuotedScalarString,
    LiteralScalarString,
    SingleQuotedScalarString,
)

from ..annotations import YamlStyle

if TYPE_CHECKING:
    pass


def apply_shadow_patch(ruamel_obj: Any, model: Any) -> None:
    """Recursively patches a ruamel.yaml object from an Ideal model.

    Updates the ruamel.yaml structures (CommentedMap, CommentedSeq) with values
    from the model while preserving comments and applying defined styles.

    Args:
        ruamel_obj: The ruamel.yaml object to update in-place.
        model: The Ideal model (OpenRecord or BaseModel) serving as the state.
    """
    _patch_recursive(ruamel_obj, model.model_dump(exclude_unset=True), model.__class__)


def _patch_recursive(target: Any, source_data: dict[str, Any], model_cls: Any) -> None:
    """Internal recursive walker for the patch engine.

    Args:
        target: The ruamel.yaml target object (CommentedMap or CommentedSeq).
        source_data: The data dictionary from the Ideal model or OpenRecord.
        model_cls: The model class used for metadata lookup.
    """
    if not isinstance(target, (CommentedMap, dict)):
        return

    fields = getattr(model_cls, "model_fields", {})

    for key, value in source_data.items():
        field_info = fields.get(key)

        if field_info is None:
            # Open world / OpenRecord: dynamically injected fields without schema
            if isinstance(value, dict):
                if key not in target:
                    target[key] = CommentedMap()
                _patch_recursive(target[key], value, dict)
                continue
            if isinstance(value, list):
                target[key] = _patch_list(target.get(key), value)
                continue
            target[key] = value
            continue

        # Extract YamlStyle metadata from Annotated (if present)
        style = _get_yaml_style(field_info.annotation)

        # 1. Handle Nested Models
        if isinstance(value, dict) and hasattr(field_info.annotation, "model_fields"):
            if key not in target:
                target[key] = CommentedMap()
            _patch_recursive(target[key], value, field_info.annotation)
            continue

        # 2. Handle Lists
        if isinstance(value, list):
            target[key] = _patch_list(target.get(key), value)
            continue

        # 3. Handle Scalars with Style
        final_value = _apply_style(value, style)
        target[key] = final_value


def _get_yaml_style(annotation: Any) -> YamlStyle | None:
    """Extracts YamlStyle from an Annotated type hint."""
    if get_origin(annotation) is not None:
        for arg in get_args(annotation):
            if isinstance(arg, YamlStyle):
                return arg
    return None


def _apply_style(value: Any, style: YamlStyle | None) -> Any:
    """Applies ruamel.yaml scalar styles based on YamlStyle metadata."""
    if style is None or not isinstance(value, str):
        return value

    if style.scalar_style == "|":
        return LiteralScalarString(value)
    if style.scalar_style == ">":
        # ruamel doesn't have a direct FoldedScalarString but
        # LiteralScalarString is often sufficient for block intent.
        return LiteralScalarString(value)
    if style.scalar_style == '"':
        return DoubleQuotedScalarString(value)
    if style.scalar_style == "'":
        return SingleQuotedScalarString(value)

    return value


def _patch_list(target_seq: Any, source_list: list[Any]) -> CommentedSeq:
    """Updates a CommentedSeq while preserving top-level comments from the target.

    Constructs a new CommentedSeq from source_list and copies comment items
    from the existing target when present. Comments are copied via ca.items
    rather than direct ca assignment, which is a read-only property.

    Args:
        target_seq: The existing ruamel.yaml sequence (may be None).
        source_list: The new list data to populate the sequence with.

    Returns:
        A new CommentedSeq populated with source_list data and preserved comments.
    """
    new_seq = CommentedSeq(source_list)
    if isinstance(target_seq, CommentedSeq):
        # ca is a read-only property — copy items dict directly to preserve
        # any existing top-level comments without triggering the property setter
        existing_items = getattr(target_seq.ca, "items", {})
        if existing_items:
            for k, v in existing_items.items():
                new_seq.ca.items[k] = v
    return new_seq
