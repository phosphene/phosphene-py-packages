"""Wikitext field extraction — pure.

Observatory articles are `{{Article ...}}` template pages with pipe-separated
fields, one per line:

    {{Article
    |Title=...
    |Bibliography=Author, A. (2020) [https://doi.org/10.1/x Title]. ''Venue''.
    Author, B. (2021) ...
    |Sources=...
    }}

Multi-line field values (like Bibliography) continue until the next `|Field=`
line or the closing `}}`. No regex — line scanning only.
"""

from __future__ import annotations

import re


def extract_article_field(wikitext: str, field: str) -> str:
    """Extract a template field's value from `{{Article ...}}` wikitext.

    Returns '' when the field is absent or empty. Continuation lines are
    joined with newlines, in order.
    """
    header = re.compile(rf"^\|{re.escape(field)}\s*=")
    value_lines: list[str] = []
    capturing = False
    for raw in wikitext.splitlines():
        line = raw.strip()
        if header.match(line):
            capturing = True
            rest = line.split("=", 1)[1].strip()
            if rest:
                value_lines.append(rest)
            continue
        if capturing:
            if line.startswith("|") or line.startswith("}}"):
                break  # next field or template close
            if line:
                value_lines.append(line)
    return "\n".join(value_lines)


def has_article_template(wikitext: str) -> bool:
    """True when the page opens with an {{Article template."""
    return wikitext.lstrip().startswith("{{Article")
