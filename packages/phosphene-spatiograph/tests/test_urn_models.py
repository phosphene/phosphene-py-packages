"""Unit and property tests for parsed URN models (CTS, CITE-2, CITE-ROI, External)."""

import pytest
from pydantic import ValidationError
from phosphene.spatiograph.urns import (
    Cite2UrnModel,
    CiteRoi,
    CtsUrnModel,
    ExternalIdentifierModel,
)


# ---------------------------------------------------------------------------
# CTS URN Tests
# ---------------------------------------------------------------------------

def test_cts_urn_parse_and_serialize() -> None:
    raw = "urn:cts:poetarch:metaphysics.hegel_cycle:v1.3.12@thesis"
    parsed = CtsUrnModel.parse(raw)
    assert parsed.namespace == "poetarch"
    assert parsed.textgroup == "metaphysics"
    assert parsed.work == "hegel_cycle"
    assert parsed.passage == "v1.3.12"
    assert parsed.token == "thesis"
    assert parsed.as_urn() == raw
    assert str(parsed) == raw


def test_cts_urn_construction() -> None:
    cts = CtsUrnModel(
        namespace="phosphene",
        textgroup="pendell",
        work="pharmako_gnosis",
        passage="p133",
        token="on_circles",
    )
    assert cts.as_urn() == "urn:cts:phosphene:pendell.pharmako_gnosis:p133@on_circles"


def test_cts_urn_invalid_prefix() -> None:
    with pytest.raises(ValueError, match="Invalid CTS URN scheme prefix"):
        CtsUrnModel.parse("urn:cite2:phosphene:work.1:p1")


# ---------------------------------------------------------------------------
# CITE-2 & CITE-ROI Tests
# ---------------------------------------------------------------------------

def test_cite_roi_pixel_parse() -> None:
    frag = "xywh=pixel:120,450,300,200"
    roi = CiteRoi.parse(frag)
    assert roi.unit == "pixel"
    assert roi.x == 120.0
    assert roi.y == 450.0
    assert roi.w == 300.0
    assert roi.h == 200.0
    assert roi.as_fragment() == frag


def test_cite_roi_percent_parse() -> None:
    frag = "xywh=percent:10,20,50,40"
    roi = CiteRoi.parse(frag)
    assert roi.unit == "percent"
    assert roi.w == 50.0
    assert roi.as_fragment() == frag


def test_cite2_urn_with_roi_fragment() -> None:
    raw = "urn:cite2:poetarch:diagrams.schema_042#xywh=pixel:120,450,300,200"
    parsed = Cite2UrnModel.parse(raw)
    assert parsed.namespace == "poetarch"
    assert parsed.collection == "diagrams"
    assert parsed.object_id == "schema_042"
    assert parsed.roi is not None
    assert parsed.roi.x == 120.0
    assert parsed.as_urn() == raw


def test_cite2_urn_with_element_subreference() -> None:
    raw = "urn:cite2:poetarch:diag_nodes.schema_042:node_dialectic_apex"
    parsed = Cite2UrnModel.parse(raw)
    assert parsed.namespace == "poetarch"
    assert parsed.collection == "diag_nodes"
    assert parsed.object_id == "schema_042"
    assert parsed.subreference == "node_dialectic_apex"
    assert parsed.as_urn() == raw


def test_cite2_urn_construct_with_roi_auto_subreference() -> None:
    roi = CiteRoi(unit="pixel", x=10, y=20, w=100, h=50)
    cite = Cite2UrnModel(
        namespace="phosphene",
        collection="selectors",
        object_id="sel_001",
        roi=roi,
    )
    assert cite.subreference == "#xywh=pixel:10,20,100,50"
    assert cite.as_urn() == "urn:cite2:phosphene:selectors.sel_001#xywh=pixel:10,20,100,50"


# ---------------------------------------------------------------------------
# External Identifier Tests
# ---------------------------------------------------------------------------

def test_external_identifier_doi() -> None:
    ext = ExternalIdentifierModel.parse("doi:10.1093/mind/f.1.1")
    assert ext.scheme == "doi"
    assert ext.value == "10.1093/mind/f.1.1"
    assert ext.as_canonical() == "doi:10.1093/mind/f.1.1"


def test_external_identifier_ark() -> None:
    ext = ExternalIdentifierModel.parse("ark:/12148/bpt6k1234567")
    assert ext.scheme == "ark"
    assert ext.as_canonical() == "ark:/12148/bpt6k1234567"


def test_external_identifier_wikidata() -> None:
    ext = ExternalIdentifierModel.parse("Q42")
    assert ext.scheme == "wikidata"
    assert ext.as_canonical() == "wikidata:Q42"
