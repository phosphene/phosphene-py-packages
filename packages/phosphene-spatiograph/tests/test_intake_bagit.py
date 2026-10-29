"""Unit tests for standalone BagIt intake & fixity verification."""

from pathlib import Path
import pytest
from phosphene.spatiograph.intake.bagit import (
    compute_file_digest,
    create_bag,
    verify_bag,
)


def test_create_and_verify_bag(tmp_path: Path) -> None:
    source_dir = tmp_path / "archive_drop"
    source_dir.mkdir()
    (source_dir / "sample1.txt").write_text("Plate 1: Amanita muscaria")
    (source_dir / "sample2.txt").write_text("Plate 2: Claviceps purpurea")

    bag_path = create_bag(
        source_dir,
        metadata_tags={"Source-Organization": "Pendell Archive", "Contact-Name": "Jacob Nasim"},
        algorithms=("sha256", "sha512"),
    )

    assert (bag_path / "bagit.txt").exists()
    assert (bag_path / "bag-info.txt").exists()
    assert (bag_path / "manifest-sha256.txt").exists()
    assert (bag_path / "manifest-sha512.txt").exists()
    assert (bag_path / "data" / "sample1.txt").exists()

    result = verify_bag(bag_path)
    assert result.valid is True
    assert result.verified_files == 2
    assert "sha256" in result.algorithms
    assert "sha512" in result.algorithms
    assert len(result.errors) == 0


def test_corrupt_bag_detection(tmp_path: Path) -> None:
    drop = tmp_path / "corrupt_drop"
    drop.mkdir()
    f = drop / "data.bin"
    f.write_bytes(b"\x00\x01\x02\x03")

    create_bag(drop, algorithms=("sha256",))

    # Tamper with file
    (drop / "data" / "data.bin").write_bytes(b"\xff\xff\xff\xff")

    res = verify_bag(drop)
    assert res.valid is False
    assert any("Checksum mismatch" in err for err in res.errors)
