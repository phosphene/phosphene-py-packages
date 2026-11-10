"""Tests verifying mdrag AST extraction and frontmatters shadow patching."""

from __future__ import annotations

from phosphene.refverify.domain.readers import (
    DocumentVerificationAudit,
    extract_from_markdown,
    patch_document_frontmatter,
)


def test_extract_from_markdown_ast_references_block():
    md = """---
uri: papers/sample-study
title: Sample Study
---

# Introduction
Discussion of earlier findings.

## References
* Author, A. (2020). Primary Groundwork. Nature, 500: 10-15.
* Collaborator, B. (2021). Follow-up Analysis. Science, 300: 20-25.

## Discussion
Further notes.
"""
    bib = extract_from_markdown(md)
    assert "Author, A. (2020)" in bib
    assert "Collaborator, B. (2021)" in bib
    assert "Further notes" not in bib


def test_patch_document_frontmatter_preserves_comments():
    md = """---
uri: papers/sample-study
title: Sample Study # Critical human-authored comment
author: Lead Researcher
---

# Introduction
Text here.
"""
    audit = DocumentVerificationAudit(
        verified=True,
        score=94.5,
        gate="pass",
        total_references=2,
        verified_count=2,
        mismatch_count=0,
        unresolved_count=0,
    )

    patched = patch_document_frontmatter(md, audit)

    assert "# Critical human-authored comment" in patched
    assert "references_verified: true" in patched
    assert "verification_score: 94.5" in patched
    assert "verification_gate: pass" in patched
    assert "# Introduction\nText here." in patched
