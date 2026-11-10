---
uri: phosphene.tooling/refverify
owner: edphos
status: active
license: MIT
updated: 2026-11-10
---

# `refverify` — Scholarly Reference Verification & Quality-Control Gate

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)
[![Architecture: Hexagonal](https://img.shields.io/badge/architecture-hexagonal-success)](README.md#architecture)

`refverify` validates bibliographic entries and citations from academic manuscripts (Markdown, DOCX, plain text) and wikitext, resolving citations against primary metadata registries (Crossref, OpenAlex, arXiv) with an offline-first caching layer.

---

## 1. Architecture

`refverify` implements strict logic and I/O separation via a hexagonal architecture:

```
  ┌─────────────────────────────────────────────────────────────┐
  │         Intake Readers & Markdown Orchestration             │
  │     - phosphene-mdrag AST parser (Open World Assumption)    │
  │     - phosphene-frontmatters Shadow Patch Sync Engine       │
  │     - Word Document (.docx) & Wikitext (.wiki) Adapters     │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │                  Pure Domain Core (DFT)                     │
  │     - Reference Extraction & Normalization                  │
  │     - Pure Scoring Algorithm (Title, Author, Year)          │
  │     - Intra-Manuscript Duplicate & Discrepancy Detection    │
  │     - Tripartite Gate Decision (PASS / WARN / BLOCK)        │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │                   Ports & Infrastructure                    │
  │     - Protocol Port: LookupClient                           │
  │     - Local Disk Cache Adapter (FileCache, TTL)             │
  │     - Upstream Registry Adapters: Crossref, OpenAlex, arXiv │
  └─────────────────────────────────────────────────────────────┘
```

- **Pure Domain & Core Invariants:** Pure verification, scoring, deduplication, and gate decisions. Value objects (`Reference`, `CandidateRecord`, `VerdictResult`) inherit from `phosphene.core.models.InvariantStatic`, guaranteeing immutability, mathematical hashability, and zero tolerance for schema drift (`extra='forbid'`).
- **Ports & Adapters:** Defines an abstract `LookupClient` protocol satisfied by HTTP adapters (`CrossrefClient`, `OpenAlexClient`, `ArxivClient`) and a local disk cache (`FileCache`).
- **Specification:** Formal Gherkin feature specifications in `features/reference_verification.feature`.

---

## 2. Installation

Install via `pip`:

```bash
pip install .
```

Or run via `uv`:

```bash
uv pip install -e .
```

---

## 3. Usage

### Verify Manuscripts & Bibliographies
`refverify` automatically detects input format by file extension:

```bash
# Academic Markdown manuscript
refverify manuscript.md

# Word document
refverify draft.docx

# Raw bibliography text
refverify references.txt
```

### Verify Wikitext Pages
Pass the `--wiki` flag to extract and verify the `|Bibliography=` field from MediaWiki templates:

```bash
refverify --wiki article.wiki
```

### Markdown Frontmatter Synchronization
When evaluating academic manuscripts with frontmatter headers, `refverify` integrates with `phosphene-frontmatters` to project verification audit results directly into the document's YAML metadata without altering human-authored comments, indentation, or document styling:

```yaml
---
title: Empirical Dynamics of Valence
author: Lead Researcher # Primary author note
references_verified: true
verification_score: 96.5
verification_gate: pass
verification_summary:
  total: 42
  verified: 42
  mismatch: 0
  unresolved: 0
---
```

---
### Cache Management & Direct Verification
By default, query results are cached locally in `~/.cache/refverify/cache-v2.json` with a 30-day TTL.

```bash
# Direct upstream verification (bypassing cache)
refverify manuscript.md --no-cache

# Custom cache time-to-live (in seconds)
refverify manuscript.md --ttl-seconds 86400
```

---

## 4. Gate Decisions & Verification Scoring

Each reference receives an empirical composite match score $[0, 100]$ based on weighted heuristic components:
- **Title Similarity (60%):** Sequence matching ratio over normalized letter-digit strings.
- **Author Match (25%):** Primary surname agreement.
- **Publication Year (15%):** Exact year agreement (15 pts) or $\pm 1$ year divergence (10 pts).

The publication gate evaluates composite verdicts across the bibliography:

| Verdict | Criteria | Gate Action |
|---|---|---|
| **PASS** | All citations resolve with high metadata confidence ($\ge 85$ composite score, exact DOI verification, or verified arXiv identity). | Publication approved |
| **WARN** | Low-confidence matches ($45 \le \text{score} < 85$) or unindexed entries requiring human editorial review. | Editorial review flagged |
| **BLOCK** | Metadata mismatch (divergent title/year under cited DOI), duplicate citations of identical works, or unresolvable references. | Publication blocked |

---

## 5. License

MIT
