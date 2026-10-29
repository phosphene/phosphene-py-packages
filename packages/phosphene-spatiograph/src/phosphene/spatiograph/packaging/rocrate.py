"""RO-Crate 1.1 Preservation Packaging Adapter (T-611).

Conforms to:
- RO-Crate 1.1 Specification (https://www.researchobject.org/ro-crate/1.1/)
- RFC 8493 BagIt convergence: directly consumes verified BagIt bags and LFS trees
  inheriting payload fixity without digest recomputation.
- Phosphene architecture: InvariantStatic models, pure transformations, no inline regex.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
from pydantic import Field
from phosphene.core.models import InvariantStatic


# ---------------------------------------------------------------------------
# RO-Crate 1.1 Schema Models (JSON-LD Entities)
# ---------------------------------------------------------------------------

class ROCrateEntity(InvariantStatic):
    """Generic JSON-LD entity in an RO-Crate graph."""

    id: str = Field(alias="@id")
    type: Any = Field(alias="@type")
    name: Optional[str] = None
    description: Optional[str] = None

    model_config = {
        "populate_by_name": True,
        "serialize_by_alias": True,
    }


class ROCrateFile(ROCrateEntity):
    """File item inside an RO-Crate payload."""

    type: str = Field(default="File", alias="@type")
    contentSize: Optional[int] = None
    encodingFormat: Optional[str] = None
    sha256: Optional[str] = None
    sha512: Optional[str] = None


class ROCrateDataset(ROCrateEntity):
    """Root dataset or sub-collection inside an RO-Crate."""

    type: str = Field(default="Dataset", alias="@type")
    datePublished: Optional[str] = None
    hasPart: List[Dict[str, str]] = Field(default_factory=list)
    license: Optional[str] = None
    author: Optional[Any] = None


class ROCrateMetadata(InvariantStatic):
    """Top-level ro-crate-metadata.json descriptor."""

    context: str = Field(
        default="https://w3id.org/ro/crate/1.1/context",
        alias="@context",
    )
    graph: List[Dict[str, Any]] = Field(
        default_factory=list,
        alias="@graph",
    )

    model_config = {
        "populate_by_name": True,
        "serialize_by_alias": True,
    }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to compliant JSON-LD text."""
        return json.dumps(self.model_dump(by_alias=True, exclude_none=True), indent=indent)


# ---------------------------------------------------------------------------
# BagIt Parser & Manifest Consuming Functions (Pure / Disk Inspection)
# ---------------------------------------------------------------------------

def parse_bagit_manifest(manifest_path: Path) -> Dict[str, str]:
    """Parse a BagIt manifest file (manifest-sha256.txt or manifest-sha512.txt).

    Returns mapping: relative payload path -> digest string.
    """
    if not manifest_path.is_file():
        return {}

    mapping: Dict[str, str] = {}
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(maxsplit=1)
        if len(parts) == 2:
            digest, file_path = parts[0], parts[1].strip()
            # Normalize leading asterisks or slashes
            file_path = file_path.lstrip("*")
            mapping[file_path] = digest
    return mapping


def parse_bagit_info(bag_info_path: Path) -> Dict[str, str]:
    """Parse bag-info.txt key-value metadata tags per RFC 8493."""
    if not bag_info_path.is_file():
        return {}

    tags: Dict[str, str] = {}
    current_key: Optional[str] = None
    for line in bag_info_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        if line.startswith((" ", "\t")) and current_key:
            # Continuation line
            tags[current_key] += " " + line.strip()
        elif ":" in line:
            key, val = line.split(":", 1)
            current_key = key.strip()
            tags[current_key] = val.strip()
    return tags


# ---------------------------------------------------------------------------
# Packaging Builders
# ---------------------------------------------------------------------------

def build_rocrate_from_bagit(
    bag_dir: str | Path,
    dataset_name: str,
    dataset_description: str,
    root_id: str = "./",
    license_uri: Optional[str] = None,
) -> ROCrateMetadata:
    """Construct an RO-Crate 1.1 metadata graph from a verified RFC 8493 BagIt bag.

    Inherits pre-computed fixity digests directly from manifest-sha256.txt
    and manifest-sha512.txt without recomputing digests.
    """
    bag_path = Path(bag_dir)
    data_dir = bag_path / "data"

    sha256_map = parse_bagit_manifest(bag_path / "manifest-sha256.txt")
    sha512_map = parse_bagit_manifest(bag_path / "manifest-sha512.txt")
    bag_info = parse_bagit_info(bag_path / "bag-info.txt")

    date_published = bag_info.get("Bagging-Date")
    contact_name = bag_info.get("Contact-Name")
    source_org = bag_info.get("Source-Organization")

    has_parts: List[Dict[str, str]] = []
    file_entities: List[Dict[str, Any]] = []

    # Map files under data/
    if data_dir.is_dir():
        for item in sorted(data_dir.rglob("*")):
            if not item.is_file():
                continue
            # Path relative to bag root (starts with data/...)
            rel_to_bag = item.relative_to(bag_path).as_posix()
            has_parts.append({"@id": rel_to_bag})

            sha256 = sha256_map.get(rel_to_bag) or sha256_map.get(item.relative_to(data_dir).as_posix())
            sha512 = sha512_map.get(rel_to_bag) or sha512_map.get(item.relative_to(data_dir).as_posix())

            file_entity = {
                "@id": rel_to_bag,
                "@type": "File",
                "name": item.name,
                "contentSize": item.stat().st_size,
            }
            if sha256:
                file_entity["sha256"] = sha256
            if sha512:
                file_entity["sha512"] = sha512

            file_entities.append(file_entity)

    # Top-level descriptor
    descriptor = {
        "@id": "ro-crate-metadata.json",
        "@type": "CreativeWork",
        "about": {"@id": root_id},
        "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
    }

    # Root dataset
    root_dataset: Dict[str, Any] = {
        "@id": root_id,
        "@type": "Dataset",
        "name": dataset_name,
        "description": dataset_description,
        "hasPart": has_parts,
    }
    if date_published:
        root_dataset["datePublished"] = date_published
    if license_uri:
        root_dataset["license"] = license_uri
    if contact_name or source_org:
        author_entity: Dict[str, str] = {
            "@type": "Organization" if source_org and not contact_name else "Person",
            "name": contact_name or source_org or "Unknown",
        }
        if source_org and contact_name:
            author_entity["affiliation"] = source_org
        root_dataset["author"] = author_entity

    graph: List[Dict[str, Any]] = [descriptor, root_dataset]
    graph.extend(file_entities)

    return ROCrateMetadata.model_validate({"@context": "https://w3id.org/ro/crate/1.1/context", "@graph": graph})


def assemble_rocrate_archive(
    source_bag: str | Path,
    out_dir: str | Path,
    dataset_name: str,
    dataset_description: str,
    license_uri: Optional[str] = None,
) -> Path:
    """Assemble an RO-Crate directory with ro-crate-metadata.json alongside payload files."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    metadata = build_rocrate_from_bagit(
        bag_dir=source_bag,
        dataset_name=dataset_name,
        dataset_description=dataset_description,
        license_uri=license_uri,
    )

    meta_file = out_path / "ro-crate-metadata.json"
    meta_file.write_text(metadata.to_json(), encoding="utf-8")
    return meta_file
