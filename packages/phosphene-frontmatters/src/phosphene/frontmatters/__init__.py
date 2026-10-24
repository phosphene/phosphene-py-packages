"""phosphene.frontmatters — Graduated discovery registry for platform markdown assets.

Implements Stage 1 (registry) of the T-043 graduated discovery framework.
Core primitive: frontmatter parsing as an open-world, schema-free operation.

Public API:
    frontmatter.parse(text)  → FrontmatterResult
    frontmatter.read(path)   → FrontmatterResult
"""
