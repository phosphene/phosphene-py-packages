"""Unit tests for pure URN utility functions."""

import pytest
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


def test_validate_identifier_segment() -> None:
    assert validate_identifier_segment("valid_segment_123") == "valid_segment_123"
    with pytest.raises(ValueError, match="Must match pattern"):
        validate_identifier_segment("Invalid-With-Dashes")
    with pytest.raises(ValueError, match="Must match pattern"):
        validate_identifier_segment("has spaces")


def test_cts_pure_parser_and_formatter() -> None:
    raw = "urn:cts:phosphene:pendell.pharmako_gnosis:p133@on_circles"
    ns, tg, wk, ver, ex, psg, tok = parse_cts_urn_string(raw)
    assert ns == "phosphene"
    assert tg == "pendell"
    assert wk == "pharmako_gnosis"
    assert ver is None
    assert ex is None
    assert psg == "p133"
    assert tok == "on_circles"

    rebuilt = format_cts_urn_string(ns, tg, wk, ver, ex, psg, tok)
    assert rebuilt == raw


def test_cite_roi_pure_parser_and_formatter() -> None:
    frag = "xywh=pixel:150,200,450,600"
    unit, x, y, w, h = parse_cite_roi_fragment(frag)
    assert unit == "pixel"
    assert (x, y, w, h) == (150.0, 200.0, 450.0, 600.0)

    rebuilt = format_cite_roi_fragment(unit, x, y, w, h)
    assert rebuilt == frag


def test_cite2_pure_parser_and_formatter() -> None:
    raw = "urn:cite2:poetarch:visuals.diagram_084#xywh=pixel:10,20,30,40"
    ns, coll, obj, sub = parse_cite2_urn_string(raw)
    assert ns == "poetarch"
    assert coll == "visuals"
    assert obj == "diagram_084"
    assert sub == "#xywh=pixel:10,20,30,40"

    rebuilt = format_cite2_urn_string(ns, coll, obj, sub)
    assert rebuilt == raw


def test_classify_external_identifier() -> None:
    assert classify_external_identifier("doi:10.1093/mind/f.1.1") == ("doi", "10.1093/mind/f.1.1")
    assert classify_external_identifier("10.1093/mind/f.1.1") == ("doi", "10.1093/mind/f.1.1")
    assert classify_external_identifier("ark:/12148/bpt6k1234567") == ("ark", "ark:/12148/bpt6k1234567")
    assert classify_external_identifier("Q42") == ("wikidata", "Q42")
    assert classify_external_identifier("isbn:9780879030544") == ("isbn", "9780879030544")
    assert classify_external_identifier("https://doi.org/10.1000/182") == ("url", "https://doi.org/10.1000/182")

    with pytest.raises(ValueError, match="Unrecognized external authority"):
        classify_external_identifier("unrecognized_gibberish")
