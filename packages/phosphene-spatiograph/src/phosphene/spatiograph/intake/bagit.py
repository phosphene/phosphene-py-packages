"""Forensic BagIt Intake & Custodial Fixity Verification (T-608 / T-611).

Pure, standalone Python implementation of RFC 8493 BagIt verification and creation.
Has zero external dependencies beyond standard library hashlib and phosphene.core.
Ensures external archivists and researchers can verify and create BagIt packages
without access to internal infrastructure or private repos.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from pydantic import Field
from phosphene.core.models import InvariantStatic


class ChecksumMismatchError(Exception):
    """Raised when an ingested file digest fails fixity verification."""


class MissingPayloadFileError(Exception):
    """Raised when a manifest specifies a file that does not exist in payload."""


class BagValidationResult(InvariantStatic):
    """Summary of RFC 8493 bag verification."""

    valid: bool
    verified_files: int
    algorithms: List[str]
    errors: List[str] = Field(default_factory=list)


def compute_file_digest(file_path: Path, algorithm: str = "sha256", chunk_size: int = 65536) -> str:
    """Compute hex digest of a file using specified algorithm (sha256, sha512, md5)."""
    h = hashlib.new(algorithm)
    with file_path.open("rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def verify_bag(bag_dir: str | Path, fast: bool = False) -> BagValidationResult:
    """Verify an RFC 8493 BagIt directory structure and payload fixity.

    Args:
        bag_dir: Path to directory containing bagit.txt and payload data/.
        fast: If True, only verify file existence and bag declaration, skip hashes.
    """
    root = Path(bag_dir)
    errors: List[str] = []

    bagit_txt = root / "bagit.txt"
    if not bagit_txt.is_file():
        return BagValidationResult(
            valid=False,
            verified_files=0,
            algorithms=[],
            errors=["Missing bagit.txt declaration file"],
        )

    data_dir = root / "data"
    if not data_dir.is_dir():
        return BagValidationResult(
            valid=False,
            verified_files=0,
            algorithms=[],
            errors=["Missing data/ payload directory"],
        )

    # Locate all manifest-*.txt files
    manifest_files = list(root.glob("manifest-*.txt"))
    if not manifest_files:
        return BagValidationResult(
            valid=False,
            verified_files=0,
            algorithms=[],
            errors=["No manifest-<alg>.txt files found in bag root"],
        )

    algorithms: List[str] = []
    verified_files_set = set()

    for mf in sorted(manifest_files):
        # Filename format: manifest-<alg>.txt
        alg = mf.stem.replace("manifest-", "").lower()
        algorithms.append(alg)

        try:
            hashlib.new(alg)
        except ValueError:
            errors.append(f"Unsupported hash algorithm '{alg}' in manifest {mf.name}")
            continue

        for line in mf.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                continue
            expected_digest, rel_str = parts[0], parts[1].strip().lstrip("*")
            target_path = root / rel_str

            if not target_path.is_file():
                errors.append(f"Payload file missing on disk: {rel_str}")
                continue

            if not fast:
                actual_digest = compute_file_digest(target_path, algorithm=alg)
                if actual_digest.lower() != expected_digest.lower():
                    errors.append(
                        f"Checksum mismatch for {rel_str} ({alg}): expected {expected_digest}, got {actual_digest}"
                    )
            verified_files_set.add(rel_str)

    # Check for unmanifested oxum/payload files in data/
    for disk_file in data_dir.rglob("*"):
        if disk_file.is_file():
            rel_disk = disk_file.relative_to(root).as_posix()
            if rel_disk not in verified_files_set:
                errors.append(f"Payload file exists on disk but is not in manifest: {rel_disk}")

    is_valid = len(errors) == 0
    return BagValidationResult(
        valid=is_valid,
        verified_files=len(verified_files_set),
        algorithms=algorithms,
        errors=errors,
    )


def create_bag(
    target_dir: str | Path,
    metadata_tags: Optional[Dict[str, str]] = None,
    algorithms: Tuple[str, ...] = ("sha256", "sha512"),
) -> Path:
    """Turn an existing directory containing files into an RFC 8493 Bag.

    Moves existing non-bag files into data/, computes manifests, and writes bagit.txt + bag-info.txt.
    """
    root = Path(target_dir)
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Move any non-bag root files into data/
    for item in list(root.iterdir()):
        if item.name in ("data", "bagit.txt", "bag-info.txt") or item.name.startswith("manifest-"):
            continue
        dest = data_dir / item.name
        if not dest.exists():
            item.rename(dest)

    # Write bagit.txt
    (root / "bagit.txt").write_text(
        "BagIt-Version: 1.0\nTag-File-Character-Encoding: UTF-8\n",
        encoding="utf-8",
    )

    # Write bag-info.txt
    tags = metadata_tags or {}
    bag_info_lines = [f"{k}: {v}\n" for k, v in tags.items()]
    (root / "bag-info.txt").write_text("".join(bag_info_lines), encoding="utf-8")

    # Compute manifests
    payload_files = sorted([f for f in data_dir.rglob("*") if f.is_file()])
    for alg in algorithms:
        manifest_lines = []
        for pf in payload_files:
            rel = pf.relative_to(root).as_posix()
            digest = compute_file_digest(pf, algorithm=alg)
            manifest_lines.append(f"{digest}  {rel}\n")
        (root / f"manifest-{alg}.txt").write_text("".join(manifest_lines), encoding="utf-8")

    return root
