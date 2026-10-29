# phosphene-spatiograph

Canonical Spatio-Graphic Archival Engine, RO-Crate 1.1 Packaging, and CTS/CITE-2 Projection.

Part of the [Phosphene](https://github.com/phosphene) ecosystem.

## Overview

`phosphene-spatiograph` is a self-contained Python package designed for archivists, curators, and researchers working with complex historical corpora, manuscript materials, and visual artifacts. It decouples high-integrity archival storage from web presentation and scholarly dissemination.

It provides:
- **CTS / CITE-2 Geometric Data Models**: Structured immutable representations (`InvariantStatic`) of canvases, spatial selector frames, diplomatic graphemes, and scholarly assertions.
- **Embedded Canonical Store**: SQLite-backed zero-server storage with R*Tree 2D spatial indexing and recursive ANSI CTE influence-graph traversal.
- **RFC 8493 BagIt Intake & Verification**: Dual-digest fixity verification (`sha256`, `sha512`) and bag authoring with zero heavy dependencies.
- **RO-Crate 1.1 Preservation Packaging Adapter**: Direct assembly of RFC 8493 bags and custodial drops into standard `ro-crate-metadata.json` graphs inheriting payload checksums without re-computation.
- **IIIF Presentation 3.0 & W3C Web Annotation Exporter**: Dynamic projection of internal spatial entities out to standard W3C Web Annotations (Media Fragments & SVG selectors) and IIIF 3.0 Manifests for Mirador, Universal Viewer, and web dissemination.

## Installation

```bash
pip install phosphene-spatiograph
```

## Quickstart

### 1. Ingesting & Verifying a Custodial BagIt Drop

```python
from phosphene.spatiograph.intake import verify_bag

# Verify payload fixity and RFC 8493 structure
result = verify_bag("path/to/custodial_drop")
if result.valid:
    print(f"Verified {result.verified_files} files using {result.algorithms}")
else:
    print("Verification failed:", result.errors)
```

### 2. Packaging as an RO-Crate 1.1 Dataset

```python
from phosphene.spatiograph.packaging import assemble_rocrate_archive

assemble_rocrate_archive(
    source_bag="path/to/verified_bag",
    out_dir="path/to/ro_crate_export",
    dataset_name="Botanikos Slivovitz Curated Archive",
    dataset_description="Archival labels, woodcuts, and lineage sheets",
    license_uri="https://creativecommons.org/licenses/by-nc/4.0/",
)
```

### 3. Projecting Canvases to IIIF 3.0 Manifests

```python
from phosphene.spatiograph.exporters.iiif import (
    IIIFCanvas,
    IIIFLabel,
    build_iiif_manifest,
)

canvas = IIIFCanvas(
    id="https://example.org/canvases/plate_01",
    label=IIIFLabel.from_string("Plate 1: Molecular lineage"),
    width=2400,
    height=3200,
)

manifest = build_iiif_manifest(
    manifest_id="https://example.org/manifests/pharmako",
    label="Pharmako Archival Plates",
    summary="Curated high-resolution scans",
    canvases=[canvas],
)

print(manifest.to_json())
```
