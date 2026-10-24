"""Open-World modeling primitives for flexible document ingestion.

Provides `OpenRecord`, an alternative to Pydantic's `InvariantDynamic` that
prioritizes testability, transparent attribute resolution, and field-level
freezing for "partial open-world models".
"""

from __future__ import annotations

from typing import Any


class OpenRecord:
    """An open-world model that supports flexible field-level freezing.

    Unlike standard immutable structs or rigid schemas, OpenRecord merges
    the dictionary __contains__ API with standard attribute access, providing
    the flexibility needed for axiomatic or un-schemaed frontmatters. It
    implements the 'Open World Assumption'—preserving unknown fields during
    ingestion and serialization.
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialises the record with arbitrary keyword arguments."""
        # Using __dict__ directly prevents __setattr__ intercept
        self.__dict__["_data"] = {}
        self.__dict__["_frozen_fields"] = set()
        self.__dict__["_fully_frozen"] = False

        for k, v in kwargs.items():
            self._data[k] = v

    @classmethod
    def model_validate(cls, data: Any) -> OpenRecord:
        """Compatibility method for standard ingestion bridges.

        Args:
            data: A dictionary of attributes to ingest. If not a dict
                  (e.g., None or bare string legacy), an empty or partial
                  record is generated.
        """
        if not isinstance(data, dict):
            # Fallback for completely malformed frontmatters
            return cls()
        return cls(**data)

    def __getattr__(self, name: str) -> Any:
        """Return dynamic field by name, raising AttributeError if absent."""
        try:
            return self._data[name]
        except KeyError:
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{name}'"
            )

    def __setattr__(self, name: str, value: Any) -> None:
        """Set a dynamic field, enforcing frozen-field and fully-frozen guards."""
        # Protect internal state fields
        if name in ("_data", "_frozen_fields", "_fully_frozen"):
            super().__setattr__(name, value)
            return

        if self._fully_frozen:
            raise AttributeError(f"Cannot mutate fully frozen record (field: '{name}')")

        if name in self._frozen_fields:
            raise AttributeError(f"Cannot mutate frozen attribute '{name}'")

        self._data[name] = value

    def __contains__(self, name: str) -> bool:
        """Return True if the dynamic field exists in this record."""
        return name in self._data

    def get(self, name: str, default: Any = None) -> Any:
        """Dictionary-like accessor for dynamic fields."""
        return self._data.get(name, default)

    def freeze_field(self, name: str) -> None:
        """Locks a specific field from future modification."""
        if name not in self._data:
            # We can allow freezing a future field, or restrict it.
            # Usually better to protect existing fields.
            self._data[name] = None

        self._frozen_fields.add(name)

    def model_freeze(self) -> None:
        """Locks the entire record against modification (Pydantic compat)."""
        self.__dict__["_fully_frozen"] = True

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Serializes the record back to a native python dictionary.
        Ignores kwargs like 'exclude_unset' for Pydantic compatibility.
        """
        return dict(self._data)
