"""P1 Research Pipeline contract — Woodchipper.

Defines what the woodchipper pipeline requires from the documents it
processes: grading, structuring, and ingestion into the research wiki.

This is not a global schema. It applies only to documents submitted to
the research pipeline. A SPEC_LOG entry, a memory file, a skill file —
these all live in the namespace graph (registry contract: ``id`` only)
without ever needing to satisfy these requirements.

Usage::

    from phosphene.frontmatters.contracts.woodchipper import WoodchipperContract
    from phosphene.frontmatters import read

    # Gate a document at the pipeline boundary
    result = read(path, model_cls=WoodchipperContract)

    # Or validate an already-parsed result
    WoodchipperContract.model_validate(result.fields)

The contract extends ``InvariantDynamic`` (frozen + open world), so
all extra frontmatter keys are preserved and unknown fields pass silently.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import field_validator

from phosphene.mdrag.core import InvariantDynamic

#: Valid epistemic tiers for research documents.
SourceQuality = Literal["primary", "secondary", "mixed", "speculative"]

#: ISO 8601 date pattern (YYYY-MM-DD, no time component).
_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class WoodchipperContract(InvariantDynamic):
    """P1 Research Pipeline contract.

    The woodchipper requires these fields beyond the registry contract (``id``).
    All other frontmatter fields are open-world: present, preserved, not policed.

    Attributes:
        id: The stable Hickey coordinate — ``namespace/slug`` format.
            Ground truth for registry and pipeline contracts. Required.
        title: Human-readable document identity. Required.
            The pipeline produces structured output that includes the title;
            without it, the output is unaddressable by humans.
        date: Provenance date in ISO 8601 format (``YYYY-MM-DD``). Required.
            Scientific knowledge is dated. A document without a date cannot
            be placed in the timeline of a research field.
        source_quality: Epistemic tier. Required.
            One of ``primary``, ``secondary``, ``mixed``, ``speculative``.
            The woodchipper grades documents; source quality is a required
            input for grading. Free-form values are rejected.

    Note:
        This contract is local to the woodchipper pipeline.
        It does not apply to documents that do not enter the research pipeline.
        Use ``validateForRegistry`` (TypeScript) or check for ``id`` only
        (Python) for the universal registry-level gate.

    Example::

        from phosphene.frontmatters.contracts.woodchipper import WoodchipperContract
        from pydantic import ValidationError

        try:
            doc = WoodchipperContract.model_validate({
                "id": "biol/sapolsky-robert",
                "title": "Robert Sapolsky",
                "date": "2026-04-05",
                "source_quality": "mixed",
                "uri": "biol/sapolsky-robert",          # extra — preserved
                "tags": ["stress", "primatology"],       # extra — preserved
            })
        except ValidationError as e:
            # Document cannot enter the woodchipper pipeline
            print(e)
    """

    id: str
    title: str
    date: str
    source_quality: SourceQuality

    @field_validator("date", mode="before")
    @classmethod
    def validate_date_format(cls, v: object) -> str:
        """Enforce ISO 8601 date format: YYYY-MM-DD.

        Args:
            v: The raw date string from frontmatter.

        Returns:
            The validated date string, unchanged.

        Raises:
            ValueError: If the date does not match ``YYYY-MM-DD``.
        """
        import datetime

        # YAML parsers (ruamel.yaml, PyYAML) coerce bare dates like `2026-04-05`
        # to Python datetime.date objects. Coerce back to ISO string here so
        # documents with standard YAML date fields work without frontmatter changes.
        if isinstance(v, (datetime.date, datetime.datetime)):
            v = v.isoformat()[:10]
        v = str(v)
        if not _DATE_PATTERN.match(v):
            raise ValueError(
                f'"date" must be YYYY-MM-DD (no time component, no partial dates), '
                f"got: {v!r}"
            )
        return v
