# phosphene-myths

Unified Myth & Cross-Domain Evidence Engine.

Part of the [Phosphene](https://github.com/phosphene) ecosystem.

## Overview

`phosphene-myths` provides cryptographic provenance, relational systems of record, and mdrag-conformant Markdown projections for comparative mythology and cross-domain anthropology.

- **Cryptographic Provenance Envelopes (`SourceRecord`)**: Enforces sha256 checksums, capture dates, and time horizons on all ingested datasets.
- **Relational Storage (`MythStore`)**: Embedded SQLite store with foreign-key constraints and WAL mode for motifs, taxa, occurrences, and character matrices.
- **mdrag Projections**: Lossless markdown export with Coordinate Index and Hickey coordinates (`<!-- :coord | ... -->`).
- **Cross-Domain Identity Bridge**: Unifies cultural identifiers across TRAMES, Berezkin, D-PLACE, Glottolog, Pulotu, and Reich ancient DNA.
