"""Parsed URN models (CTS, CITE-2, CITE-ROI, External Identifiers).

Conforms strictly to Phosphene Pydantic Standards:
- Extends InvariantStatic (frozen=True, extra='forbid')
- Zero inline regex strings; validation delegated to pure function units in utils.py
- Small, focused value-object classes with pure serialization and parsing methods
"""

from __future__ import annotations

from typing import Literal
from pydantic import Field, field_validator, model_validator
from phosphene.core.models import InvariantStatic
from phosphene.spatiograph.utils import (
    classify_external_identifier,
    format_cite2_urn_string,
    format_cite_roi_fragment,
    format_cts_urn_string,
    parse_cite2_urn_string,
    parse_cite_roi_fragment,
    parse_cts_urn_string,
    validate_identifier_segment,
)


class CiteRoi(InvariantStatic):
    """Parsed CITE-2 / W3C Media Fragment Planar Region of Interest (ROI)."""

    unit: Literal["pixel", "percent"] = "pixel"
    x: float
    y: float
    w: float
    h: float

    @model_validator(mode="after")
    def _validate_roi(self) -> CiteRoi:
        if self.w < 0 or self.h < 0:
            raise ValueError(f"Width and height must be non-negative: w={self.w}, h={self.h}")
        if self.unit == "percent":
            if not (0 <= self.x <= 100 and 0 <= self.y <= 100 and self.x + self.w <= 100 and self.y + self.h <= 100):
                raise ValueError(
                    f"Percent ROI out of [0, 100] bounds: x={self.x}, y={self.y}, w={self.w}, h={self.h}"
                )
        return self

    def as_fragment(self) -> str:
        """Pure serialization to standard W3C Media Fragment format."""
        return format_cite_roi_fragment(self.unit, self.x, self.y, self.w, self.h)

    def __str__(self) -> str:
        return self.as_fragment()

    @classmethod
    def parse(cls, fragment: str) -> CiteRoi:
        """Parse fragment using pure parser function."""
        unit, x, y, w, h = parse_cite_roi_fragment(fragment)
        return cls(unit=unit, x=x, y=y, w=w, h=h)


class CtsUrnModel(InvariantStatic):
    """Parsed Canonical Text Services (CTS) URN."""

    namespace: str
    textgroup: str
    work: str | None = None
    version: str | None = None
    exemplar: str | None = None
    passage: str | None = None
    token: str | None = None

    @field_validator("namespace", "textgroup")
    @classmethod
    def _validate_required_identifiers(cls, v: str) -> str:
        return validate_identifier_segment(v)

    @field_validator("work", "version", "exemplar")
    @classmethod
    def _validate_optional_identifiers(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_identifier_segment(v)
        return None

    @property
    def work_hierarchy(self) -> str:
        parts = [self.textgroup]
        if self.work:
            parts.append(self.work)
            if self.version:
                parts.append(self.version)
                if self.exemplar:
                    parts.append(self.exemplar)
        return ".".join(parts)

    @property
    def passage_component(self) -> str | None:
        if not self.passage and not self.token:
            return None
        res = self.passage or ""
        if self.token:
            res = f"{res}@{self.token}" if res else f"@{self.token}"
        return res

    def as_urn(self) -> str:
        """Pure serialization to CTS URN string."""
        return format_cts_urn_string(
            namespace=self.namespace,
            textgroup=self.textgroup,
            work=self.work,
            version=self.version,
            exemplar=self.exemplar,
            passage=self.passage,
            token=self.token,
        )

    def __str__(self) -> str:
        return self.as_urn()

    @classmethod
    def parse(cls, urn_str: str) -> CtsUrnModel:
        """Parse CTS URN using pure parser function."""
        ns, tg, wk, ver, ex, psg, tok = parse_cts_urn_string(urn_str)
        return cls(
            namespace=ns,
            textgroup=tg,
            work=wk,
            version=ver,
            exemplar=ex,
            passage=psg,
            token=tok,
        )


class Cite2UrnModel(InvariantStatic):
    """Parsed Collection, Image, Text, Extension (CITE-2) URN."""

    namespace: str
    collection: str
    object_id: str
    subreference: str | None = None
    roi: CiteRoi | None = None

    @field_validator("namespace", "collection", "object_id")
    @classmethod
    def _validate_identifiers(cls, v: str) -> str:
        return validate_identifier_segment(v)

    @model_validator(mode="after")
    def _sync_subreference_roi(self) -> Cite2UrnModel:
        if self.roi is not None and not self.subreference:
            object.__setattr__(self, "subreference", f"#{self.roi.as_fragment()}")
        elif self.subreference and self.roi is None:
            sub = self.subreference.lstrip(":#")
            if sub.startswith("xywh="):
                try:
                    parsed_roi = CiteRoi.parse(sub)
                    object.__setattr__(self, "roi", parsed_roi)
                except Exception:
                    pass
        return self

    def as_urn(self) -> str:
        """Pure serialization to CITE-2 URN string."""
        return format_cite2_urn_string(
            namespace=self.namespace,
            collection=self.collection,
            object_id=self.object_id,
            subreference=self.subreference,
        )

    def __str__(self) -> str:
        return self.as_urn()

    @classmethod
    def parse(cls, urn_str: str) -> Cite2UrnModel:
        """Parse CITE-2 URN using pure parser function."""
        ns, coll, obj, subref = parse_cite2_urn_string(urn_str)
        roi: CiteRoi | None = None
        if subref and "xywh=" in subref:
            try:
                roi = CiteRoi.parse(subref)
            except Exception:
                pass
        return cls(
            namespace=ns,
            collection=coll,
            object_id=obj,
            subreference=subref,
            roi=roi,
        )


class ExternalIdentifierModel(InvariantStatic):
    """Normalized external scholarly authority identifier (DOI, ARK, Wikidata, etc.)."""

    scheme: Literal["doi", "ark", "wikidata", "isbn", "url"]
    value: str

    @classmethod
    def parse(cls, raw: str) -> ExternalIdentifierModel:
        scheme, value = classify_external_identifier(raw)
        return cls(scheme=scheme, value=value)

    def as_canonical(self) -> str:
        if self.scheme == "doi":
            return f"doi:{self.value}"
        elif self.scheme == "ark":
            return self.value if self.value.startswith("ark:") else f"ark:{self.value}"
        elif self.scheme == "wikidata":
            return f"wikidata:{self.value}"
        elif self.scheme == "isbn":
            return f"isbn:{self.value}"
        return self.value

    def __str__(self) -> str:
        return self.as_canonical()
