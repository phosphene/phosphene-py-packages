"""Unit tests for RO-Crate 1.1 packaging adapter (T-611)."""

import json
from pathlib import Path
import pytest
from phosphene.spatiograph.packaging.rocrate import (
    ROCrateMetadata,
    assemble_rocrate_archive,
    build_rocrate_from_bagit,
    parse_bagit_info,
    parse_bagit_manifest,
)


def test_parse_bagit_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest-sha256.txt"
    manifest.write_text(
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  data/empty.txt\n"
        "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824 *data/hello.txt\n"
    )

    mapping = parse_bagit_manifest(manifest)
    assert mapping["data/empty.txt"] == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert mapping["data/hello.txt"] == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"


def test_parse_bagit_info(tmp_path: Path) -> None:
    info = tmp_path / "bag-info.txt"
    info.write_text(
        "Bagging-Date: 2026-10-29\n"
        "Contact-Name: Jacob Nasim\n"
        "Source-Organization: HUSH estate custody chain\n"
        "External-Description: multi-line description\n"
        " continued here\n"
    )

    tags = parse_bagit_info(info)
    assert tags["Bagging-Date"] == "2026-10-29"
    assert tags["Contact-Name"] == "Jacob Nasim"
    assert tags["Source-Organization"] == "HUSH estate custody chain"
    assert tags["External-Description"] == "multi-line description continued here"


def test_build_rocrate_from_bagit_fixture(tmp_path: Path) -> None:
    bag = tmp_path / "mock_bag"
    data = bag / "data"
    data.mkdir(parents=True)
    file1 = data / "plate1.tif"
    file1.write_bytes(b"mock tiff data")

    (bag / "manifest-sha256.txt").write_text("dummy256  data/plate1.tif\n")
    (bag / "manifest-sha512.txt").write_text("dummy512  data/plate1.tif\n")
    (bag / "bag-info.txt").write_text(
        "Bagging-Date: 2026-10-29\n"
        "Contact-Name: Jacob Nasim\n"
        "Source-Organization: Phosphene\n"
    )

    rocrate = build_rocrate_from_bagit(
        bag_dir=bag,
        dataset_name="Botanikos Study Subset",
        dataset_description="Curated plates from Botanikos",
        license_uri="https://creativecommons.org/licenses/by-nc/4.0/",
    )

    assert rocrate.context == "https://w3id.org/ro/crate/1.1/context"
    graph = {item["@id"]: item for item in rocrate.graph}

    # Descriptor check
    assert "ro-crate-metadata.json" in graph
    assert graph["ro-crate-metadata.json"]["@type"] == "CreativeWork"
    assert graph["ro-crate-metadata.json"]["conformsTo"]["@id"] == "https://w3id.org/ro/crate/1.1"

    # Root dataset check
    assert "./" in graph
    assert graph["./"]["@type"] == "Dataset"
    assert graph["./"]["name"] == "Botanikos Study Subset"
    assert graph["./"]["license"] == "https://creativecommons.org/licenses/by-nc/4.0/"
    assert graph["./"]["datePublished"] == "2026-10-29"
    assert graph["./"]["author"]["name"] == "Jacob Nasim"

    # File check
    assert "data/plate1.tif" in graph
    f_node = graph["data/plate1.tif"]
    assert f_node["@type"] == "File"
    assert f_node["sha256"] == "dummy256"
    assert f_node["sha512"] == "dummy512"
    assert f_node["contentSize"] == len(b"mock tiff data")


def test_assemble_rocrate_archive(tmp_path: Path) -> None:
    bag = tmp_path / "source_bag"
    data = bag / "data"
    data.mkdir(parents=True)
    (data / "sample.txt").write_text("hello world")

    (bag / "manifest-sha256.txt").write_text("abc  data/sample.txt\n")
    out_dir = tmp_path / "crate_out"

    meta_file = assemble_rocrate_archive(
        source_bag=bag,
        out_dir=out_dir,
        dataset_name="Sample Archive",
        dataset_description="An assembled test crate",
    )

    assert meta_file.exists()
    content = json.loads(meta_file.read_text())
    assert content["@context"] == "https://w3id.org/ro/crate/1.1/context"
    assert len(content["@graph"]) >= 3
