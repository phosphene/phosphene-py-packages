# phosphene.mdrag

**Extensible Scientific Markdown Orchestration**

`phosphene.mdrag` (Markdown-Structured RAG) is a deterministic, AST-aware document parsing and manipulation engine. It transitions markdown workflows from fragile text-based manipulation to a robust, model-driven architecture.

## Key Features

- **Open World Assumption (The Innovation Bucket)**: Leverages the `OpenRecord` primitive and deterministic fallback rendering (`mistune.MarkdownRenderer`) to ingest, serialize, and preserve unknown metadata and undefined functional markdown chunks (e.g., bespoke tables, custom blocks). Researcher innovation is never discarded.
- **High-Fidelity Serialization**: Leverages `phosphene.frontmatters` for high-fidelity frontmatter synchronization, preserving comments and formatting during round-trips.
- **AST-Aware Parsing**: Uses `mistune` to generate a structural Abstract Syntax Tree (AST).
- **Axiomatic Integrity**: Enforces structural invariants (Identity Parity, URI resolution) while remaining open to un-schemaed data.
- **Identity Parity**: Axiomatically ensures that a document's internal `metadata.id` matches its filesystem location.
- **Multi-Stage URI Extraction**:
  - Canonical YAML front matter support.
  - Legacy one-line header parsing (`uri: ns/slug`).
  - Embedded paragraph marker support.
  - Filesystem-derived fallback.
- **Deterministic Rendering**: Round-trip safety ensures that documents can be read, modified, and written back to disk with consistent formatting.
- **Graduated Discovery**: Implements the three-stage knowledge graph protocol (Registry → Interface → Implementation) to enable efficient, low-cost information navigation.
- **Axiomatic JSON Serialization**: Standardizes on `orjson` for high-performance, high-fidelity serialization of structural data, including native support for NumPy, UUIDs, and ISO timestamps.

## Installation

```bash
# Using uv (recommended)
uv add phosphene-mdrag

# Using pip
pip install phosphene-mdrag
```

## Quick Start

### Parsing a Document

```python
from phosphene.mdrag.engine import MarkdownEngine

engine = MarkdownEngine()

# Read from string
text = """---
uri: sci.bio/levin-v1
title: Bioelectric Cognition
---
# Introduction
Michael Levin's research...
"""
ast = engine.read(text)

print(ast.uri)  # sci.bio/levin-v1
print(ast.blocks[0].text)  # Introduction
```

### Modifying and Writing

```python
# The AST is frozen (immutable) for safety
new_metadata = ast.metadata.model_copy(update={"status": "reviewed"})
new_ast = ast.model_copy(update={"metadata": new_metadata})

# Render back to Markdown
markdown_text = engine.write(new_ast)
```

## Graduated Discovery

`phosphene.mdrag` implements the three-stage knowledge graph protocol defined by the platform team:

1.  **Stage 1: Registry**: A lightweight URI-to-Path map containing only coordinates.
2.  **Stage 2: Interface**: Metadata-rich summaries and section headers. Enables "Interface-level" reasoning without loading document bodies.
3.  **Stage 3: Implementation**: Full AST ingestion and block-level manipulation.

### Using the Discovery Engine

The `DiscoveryEngine` provides a query surface over the tiered registry. It supports lazy ingestion, loading only the namespace required for a specific query.

```python
from phosphene.mdrag.discovery import DiscoveryEngine

# Automatically finds meta/WORKSPACE_REGISTRY.md (Stage 1)
discovery = DiscoveryEngine()

# Query: Lazily loads specific namespace registries as needed
results = discovery.query(ns="biol", relevant_when="research-mode")

for interface in results:
    print(f"[{interface.uri}] {interface.summary}")
    # interface.capabilities contains detect lenses (T-045)
```

## Data Models

`phosphene.mdrag` is built on three primary pillars:

1.  **MarkdownAST**: The root Model-as-Source-of-Truth.
2.  **Metadata**: Validated YAML front matter (URI, ID, Namespace, etc.). Hardened with **Architectural Authority** fields (`layers`, `direction`) and dedicated **reasoning** space for agentic intent (Phosphene 1.5).
3.  **Blocks**: Structural components (Heading, Paragraph, List, Coordinate).

## Block Schema Registry (T-050)

`phosphene.mdrag` includes a formal registry system for validating document-level structural blocks. The registry defines axiomatic contracts for specific block types (e.g., the "Five-Block" Wiki format).

### The "Five-Block" Wiki Schema
The system enforces formal contracts for the following wiki blocks:
- **Wit**: Aphorisms and axiomatic statements.
- **Analogy**: Cross-domain mappings via Hickey coordinates.
- **Nuance**: Precise contextual qualifiers.
- **Genealogy**: Lineage and derivation tracking.
- **Claim**: Epistemic statements with formal status enums (`established`, `contested`, etc.).

## Discovery DSL & Selector Engine

`phosphene.mdrag` includes a formal **Discovery DSL** for robust, non-heuristic data extraction. This replaces fragile regex-based string scraping with a registry-driven query system.

### Block Queries
The `BlockQuery` model allows for precise filtering of the AST:
```python
from phosphene.mdrag.query import BlockQuery

# Find all level 2 headings containing "OKR"
query = BlockQuery(type="heading", attrs={"level": 2}, text_regex="OKR")
blocks = ast.find_blocks(query)
```

### Selector DSL
The `select` method provides a unified API for field extraction, supporting both metadata and block-level traversal:
```python
# Extract metadata
title = ast.select("metadata.title")

# Extract block content by type and position
first_p = ast.select("paragraph.1.content")

# Extract specific block attributes
header_text = ast.select("heading.text")
```

The Selector engine supports legacy `type.N.field` formats while ensuring structural integrity through formal `BlockQuery` matching.

## Identity System

The engine enforces **ID-Path Parity**. When reading a file from disk:
- The `metadata.id` must match the relative path.
- Example: A file at `sci/bio/levin.md` must have an ID of `sci/bio/levin`.

This prevents "identity drift" in large research corpora.

## Custom Extraction Rules

`phosphene.mdrag` supports extensible extraction rules to pull structured data from document blocks.

### OKR Mapping
The `OkrMappingExtractor` (in `block_rules.py`) parses specialized coordinate blocks to define deterministic BDD mapping:
```markdown
{:okr/mapping: id=O1, patterns=['woodchipper', 'monster']}
```
These values are extracted into a structured registry during engine execution.

## Development

### Running Tests

Execute tests from the project root using `uv` or `pytest`:

```bash
PYTHONPATH=src uv run pytest
```

## License

MIT © 2026 Edward Phillips (phosphene.com)
