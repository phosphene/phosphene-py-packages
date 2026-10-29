"""Pure utility functions for parsing, decomposing, and formatting URN components.

Every function is a pure, side-effect-free, deterministic transformation unit.
"""

from __future__ import annotations

from typing import Literal
from phosphene.spatiograph.patterns import (
    CITE2_URN_RE,
    CTS_URN_RE,
    DOI_PREFIX_RE,
    IDENTIFIER_RE,
    WIKIDATA_ID_RE,
)


def validate_identifier_segment(val: str, field_name: str = "identifier") -> str:
    """Validate that a string segment satisfies lowercase alphanumeric/underscore syntax."""
    if not IDENTIFIER_RE.match(val):
        raise ValueError(
            f"Invalid {field_name} format: '{val}'. Must match pattern '^[a-z0-9_]+$'"
        )
    return val


def parse_cts_urn_string(urn_str: str) -> tuple[str, str, str | None, str | None, str | None, str | None, str | None]:
    """Pure parsing function for Canonical Text Services (CTS) URN.

    Returns:
        (namespace, textgroup, work, version, exemplar, passage, token)
    """
    if not urn_str.startswith("urn:cts:"):
        raise ValueError(f"Invalid CTS URN scheme prefix: '{urn_str}'")
    if not CTS_URN_RE.match(urn_str):
        raise ValueError(f"Malformed CTS URN syntax: '{urn_str}'")

    parts = urn_str.split(":")
    namespace = parts[2]
    work_str = parts[3]
    passage_str = parts[4] if len(parts) == 5 else None

    work_parts = work_str.split(".")
    textgroup = work_parts[0]
    work = work_parts[1] if len(work_parts) > 1 else None
    version = work_parts[2] if len(work_parts) > 2 else None
    exemplar = work_parts[3] if len(work_parts) > 3 else None

    passage: str | None = None
    token: str | None = None
    if passage_str:
        if "@" in passage_str:
            psg_part, tok_part = passage_str.split("@", 1)
            passage = psg_part if psg_part else None
            token = tok_part if tok_part else None
        else:
            passage = passage_str

    return namespace, textgroup, work, version, exemplar, passage, token


def format_cts_urn_string(
    namespace: str,
    textgroup: str,
    work: str | None = None,
    version: str | None = None,
    exemplar: str | None = None,
    passage: str | None = None,
    token: str | None = None,
) -> str:
    """Pure formatting function to assemble a CTS URN string."""
    work_parts = [textgroup]
    if work:
        work_parts.append(work)
        if version:
            work_parts.append(version)
            if exemplar:
                work_parts.append(exemplar)
    work_hierarchy = ".".join(work_parts)
    base = f"urn:cts:{namespace}:{work_hierarchy}"

    if passage or token:
        psg = passage or ""
        if token:
            psg = f"{psg}@{token}" if psg else f"@{token}"
        return f"{base}:{psg}"
    return base


def parse_cite_roi_fragment(fragment: str) -> tuple[Literal["pixel", "percent"], float, float, float, float]:
    """Pure parsing function for W3C Media Fragment / CITE-ROI strings.

    Returns:
        (unit, x, y, w, h)
    """
    cleaned = fragment.lstrip("#").strip()
    if not cleaned.startswith("xywh="):
        raise ValueError(f"Invalid CITE-ROI fragment, must start with xywh=: '{fragment}'")
    val = cleaned[len("xywh="):]
    unit: Literal["pixel", "percent"] = "pixel"
    if val.startswith("pixel:"):
        unit = "pixel"
        val = val[len("pixel:"):]
    elif val.startswith("percent:"):
        unit = "percent"
        val = val[len("percent:"):]

    parts = val.split(",")
    if len(parts) != 4:
        raise ValueError(f"CITE-ROI requires 4 coordinates (x,y,w,h): '{fragment}'")
    try:
        x, y, w, h = (float(p.strip()) for p in parts)
    except ValueError as e:
        raise ValueError(f"Non-numeric coordinates in CITE-ROI: '{fragment}'") from e

    return unit, x, y, w, h


def format_cite_roi_fragment(unit: Literal["pixel", "percent"], x: float, y: float, w: float, h: float) -> str:
    """Pure formatting function for CITE-ROI fragment strings."""
    fx = f"{int(x)}" if x.is_integer() else f"{x}"
    fy = f"{int(y)}" if y.is_integer() else f"{y}"
    fw = f"{int(w)}" if w.is_integer() else f"{w}"
    fh = f"{int(h)}" if h.is_integer() else f"{h}"
    return f"xywh={unit}:{fx},{fy},{fw},{fh}"


def parse_cite2_urn_string(urn_str: str) -> tuple[str, str, str, str | None]:
    """Pure parsing function for CITE-2 URN.

    Returns:
        (namespace, collection, object_id, subreference)
    """
    if not urn_str.startswith("urn:cite2:"):
        raise ValueError(f"Invalid CITE-2 URN scheme prefix: '{urn_str}'")

    fragment: str | None = None
    main_part = urn_str
    if "#" in urn_str:
        main_part, fragment = urn_str.split("#", 1)

    parts = main_part.split(":")
    if len(parts) < 4 or len(parts) > 5:
        raise ValueError(f"Malformed CITE-2 URN structure: '{urn_str}'")

    namespace = parts[2]
    coll_obj = parts[3]
    subref_from_colon = parts[4] if len(parts) == 5 else None

    if "." not in coll_obj:
        raise ValueError(f"CITE-2 record identifier must have collection.object format: '{coll_obj}'")
    collection, object_id = coll_obj.split(".", 1)

    subreference: str | None = None
    if fragment:
        subreference = f"#{fragment}"
    elif subref_from_colon:
        subreference = subref_from_colon

    return namespace, collection, object_id, subreference


def format_cite2_urn_string(
    namespace: str,
    collection: str,
    object_id: str,
    subreference: str | None = None,
) -> str:
    """Pure formatting function to assemble a CITE-2 URN string."""
    base = f"urn:cite2:{namespace}:{collection}.{object_id}"
    if subreference:
        if subreference.startswith("#") or subreference.startswith(":"):
            return f"{base}{subreference}"
        return f"{base}:{subreference}"
    return base


def classify_external_identifier(raw: str) -> tuple[Literal["doi", "ark", "wikidata", "isbn", "url"], str]:
    """Pure function classifying and normalizing external scholarly identifiers."""
    raw_clean = raw.strip()
    if raw_clean.lower().startswith("doi:"):
        val = raw_clean[4:].strip()
        return "doi", val
    if DOI_PREFIX_RE.match(raw_clean):
        return "doi", raw_clean
    if raw_clean.lower().startswith("ark:"):
        return "ark", raw_clean
    if WIKIDATA_ID_RE.match(raw_clean.upper()):
        return "wikidata", raw_clean.upper()
    if raw_clean.lower().startswith("isbn:"):
        return "isbn", raw_clean[5:].strip()
    if raw_clean.startswith("http://") or raw_clean.startswith("https://"):
        return "url", raw_clean
    raise ValueError(f"Unrecognized external authority identifier format: '{raw}'")
