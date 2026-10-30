"""mdrag-conformant Markdown Projections for Myth Engine (T-563).

Generates coordinate-indexed, git-addressable markdown formulations of
canonical motifs and taxa with Hickey coordinates (<!-- :coord | ... -->).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List


def project_motifs_to_markdown(db_path: str | Path, out_path: str | Path) -> int:
    """Project canonical motifs from SQLite to mdrag markdown with Hickey coordinates."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    rows = c.execute("SELECT motif_id, short_name, description, berezkin_ref, atu_type, tmi_code FROM motifs ORDER BY motif_id").fetchall()
    conn.close()

    lines: List[str] = [
        "---",
        "uri: myths.registries/motifs",
        "title: Canonical Myth Motifs Registry",
        "status: living",
        "---",
        "",
        "# Canonical Myth Motifs Registry",
        "",
        "<!-- :coordinate-index -->",
    ]

    for r in rows:
        m_id = r["motif_id"]
        lines.append(f"- [{m_id}](#{m_id.lower()}): {r['short_name']}")

    lines.extend(["", "---", ""])

    for r in rows:
        m_id = r["motif_id"]
        lines.append(f"## {m_id}")
        lines.append(f"<!-- :coord | {m_id} | motif -->")
        lines.append(f"- **Title:** {r['short_name']}")
        if r["berezkin_ref"]:
            lines.append(f"- **Berezkin Ref:** `{r['berezkin_ref']}`")
        if r["atu_type"]:
            lines.append(f"- **ATU:** `{r['atu_type']}`")
        if r["tmi_code"]:
            lines.append(f"- **TMI:** `{r['tmi_code']}`")
        if r["description"]:
            lines.append(f"- **Description:** {r['description']}")
        lines.append("")

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    return len(rows)


def project_taxa_to_markdown(db_path: str | Path, out_path: str | Path) -> int:
    """Project taxa traditions from SQLite to mdrag markdown with Hickey coordinates."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    rows = c.execute("SELECT taxon_id, name, region, lifestyle_mode, language_family FROM taxa ORDER BY taxon_id").fetchall()
    conn.close()

    lines: List[str] = [
        "---",
        "uri: myths.registries/taxa",
        "title: Canonical Cultural Taxa Registry",
        "status: living",
        "---",
        "",
        "# Canonical Cultural Taxa Registry",
        "",
        "<!-- :coordinate-index -->",
    ]

    for r in rows:
        t_id = r["taxon_id"]
        lines.append(f"- [{t_id}](#{t_id.lower()}): {r['name']}")

    lines.extend(["", "---", ""])

    for r in rows:
        t_id = r["taxon_id"]
        lines.append(f"## {t_id}")
        lines.append(f"<!-- :coord | {t_id} | taxon -->")
        lines.append(f"- **Name:** {r['name']}")
        if r["region"]:
            lines.append(f"- **Region:** {r['region']}")
        if r["lifestyle_mode"]:
            lines.append(f"- **Lifestyle:** {r['lifestyle_mode']}")
        if r["language_family"]:
            lines.append(f"- **Family:** {r['language_family']}")
        lines.append("")

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    return len(rows)
