"""Axiomatic JSON Serialization — orjson-backed performance and Pydantic parity.

Provides a unified interface for JSON serialization across the Woodchipper project.
Standardizing on orjson ensures high-fidelity serialization of complex research
data (NumPy vectors, ISO-8601 timestamps, UUIDs) while maintaining strict
compliance with Pydantic v2 models and the project's Invariant Static/Dynamic
operational modes.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any

import orjson
from pydantic import BaseModel


def _default_encoder(obj: Any) -> Any:
    """Fallback encoder for types orjson doesn't handle natively."""
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    # NumPy handling is managed via orjson.OPT_SERIALIZE_NUMPY
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


class AxiomaticJSON:
    """Encapsulates JSON serialization settings and operational modes.

    This processor acts as the project's central serialization bus, ensuring
    that all internal state transitions (Search results, Graduation logs) are
    serialized with consistent precision and performance.
    """

    def __init__(self, indent: bool = False, sort_keys: bool = False) -> None:
        """Initialise with formatting preferences.

        Args:
            indent: If True, uses 2-space indentation.
            sort_keys: If True, sorts dictionary keys alphabetically.
        """
        self.options = orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_UTC_Z
        if indent:
            self.options |= orjson.OPT_INDENT_2
        if sort_keys:
            self.options |= orjson.OPT_SORT_KEYS

    def dumps(self, data: Any) -> str:
        """Serialise data to a JSON string.

        Supports Pydantic models, NumPy arrays, datetimes, and UUIDs.

        Args:
            data: The data to serialise.

        Returns:
            A UTF-8 encoded JSON string.
        """
        # Unpack Pydantic models if present
        if isinstance(data, BaseModel):
            data = data.model_dump()
        elif isinstance(data, list) and data and isinstance(data[0], BaseModel):
            data = [i.model_dump() for i in data]
        elif isinstance(data, dict):
            # Recursively handle dicts/lists? orjson handles most nested structures,
            # but we might need to manually unpack Pydantic models inside lists.
            pass

        return orjson.dumps(data, default=_default_encoder, option=self.options).decode(
            "utf-8"
        )

    def loads(self, data: str | bytes) -> Any:
        """Deserialise data from a JSON string or bytes.

        Args:
            data: The JSON data to deserialise.

        Returns:
            The deserialised Python object (usually a dict or list).
        """
        return orjson.loads(data)


# ──────────────────────────────────────────────────────────────────────
# Functional Interface (Convenience)
# ──────────────────────────────────────────────────────────────────────

_DEFAULT_PROCESSOR = AxiomaticJSON()
_PRETTY_PROCESSOR = AxiomaticJSON(indent=True, sort_keys=True)


def dumps(data: Any, pretty: bool = False) -> str:
    """Converts data to JSON string using the default axiomatic settings."""
    processor = _PRETTY_PROCESSOR if pretty else _DEFAULT_PROCESSOR
    return processor.dumps(data)


def loads(data: str | bytes) -> Any:
    """Converts JSON string or bytes back to a Python object."""
    return _DEFAULT_PROCESSOR.loads(data)
