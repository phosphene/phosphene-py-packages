"""Unit tests for Unified Myth Engine core modules (T-561..T-564)."""

import sqlite3
from pathlib import Path
import pytest
from phosphene.myths.identity import IdentityBridgeManager, IdentityBridgeRecord
from phosphene.myths.projections import project_motifs_to_markdown, project_taxa_to_markdown
from phosphene.myths.provenance import SourceRecord, TimeHorizon
from phosphene.myths.store import MythStore


def test_source_record_provenance(tmp_path: Path) -> None:
    test_file = tmp_path / "raw_berezkin.json"
    test_file.write_text('{"sample": "data"}', encoding="utf-8")

    rec = SourceRecord.from_file(
        file_path=test_file,
        source_id="src.berezkin.2026",
        title="Berezkin Electronic Folklore Database",
        doi_or_url="http://ruthenia.ru/folklore/berezkin",
        time_horizon=TimeHorizon.ETHNOGRAPHIC_OBSERVATION,
        description="Core Berezkin motifs snapshot",
    )

    assert rec.source_id == "src.berezkin.2026"
    assert len(rec.sha256) == 64
    assert rec.time_horizon == TimeHorizon.ETHNOGRAPHIC_OBSERVATION


def test_myth_store_crud(tmp_path: Path) -> None:
    db_file = tmp_path / "myths_test.db"
    store = MythStore(db_file)

    source = SourceRecord(
        source_id="src.trames.2018",
        title="TRAMES 2018 Matrix",
        doi_or_url="https://doi.org/10.3176/tr.2018.4.01",
        sha256="a" * 64,
        time_horizon=TimeHorizon.ETHNOGRAPHIC_OBSERVATION,
    )
    store.insert_source(source)
    assert store.get_source("src.trames.2018") is not None

    store.insert_taxon(
        taxon_id="T001",
        name="San (Bushmen)",
        canonical_slug="san-bushmen",
        region="Southern Africa",
        lifestyle_mode="forager",
    )
    assert store.count_taxa() == 1

    store.insert_motif(
        motif_id="M0042",
        short_name="Cosmic Hunt",
        description="Hunters pursuing celestial game",
        berezkin_ref="B23",
    )
    assert store.count_motifs() == 1

    store.insert_occurrence(
        taxon_id="T001",
        motif_id="M0042",
        source_id="src.trames.2018",
        confidence=1.0,
        verbatim_evidence="Three hunters chase the eland into the stars.",
    )
    assert store.count_occurrences() == 1


def test_projections_to_markdown(tmp_path: Path) -> None:
    db_file = tmp_path / "myths_proj.db"
    store = MythStore(db_file)

    source = SourceRecord(
        source_id="src.test",
        title="Test Source",
        doi_or_url="https://example.org",
        sha256="b" * 64,
        time_horizon=TimeHorizon.ETHNOGRAPHIC_OBSERVATION,
    )
    store.insert_source(source)
    store.insert_taxon(taxon_id="T100", name="Hadza", canonical_slug="hadza", region="East Africa")
    store.insert_motif(motif_id="M001", short_name="Origin of Fire", berezkin_ref="A1")

    motifs_md = tmp_path / "motifs.md"
    taxa_md = tmp_path / "taxa.md"

    m_count = project_motifs_to_markdown(db_file, motifs_md)
    t_count = project_taxa_to_markdown(db_file, taxa_md)

    assert m_count == 1
    assert t_count == 1

    m_text = motifs_md.read_text(encoding="utf-8")
    assert "<!-- :coord | M001 | motif -->" in m_text
    assert "Origin of Fire" in m_text

    t_text = taxa_md.read_text(encoding="utf-8")
    assert "<!-- :coord | T100 | taxon -->" in t_text
    assert "Hadza" in t_text


def test_identity_bridge(tmp_path: Path) -> None:
    db_file = tmp_path / "myths_bridge.db"
    store = MythStore(db_file)
    bridge = IdentityBridgeManager(db_file)

    store.insert_taxon(taxon_id="T005", name="Yoruba", canonical_slug="yoruba")

    rec = IdentityBridgeRecord(
        taxon_id="T005",
        trames_region_id=42,
        berezkin_tradition_id=105,
        dplace_society_id="EA001",
        glottocode="yoru1245",
        confidence=1.0,
    )
    bridge.link_entity(rec)

    assert bridge.count_mappings() == 1
    fetched = bridge.get_by_taxon_id("T005")
    assert fetched is not None
    assert fetched.glottocode == "yoru1245"
    assert fetched.trames_region_id == 42
