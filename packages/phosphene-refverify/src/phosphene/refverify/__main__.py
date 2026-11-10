"""CLI: bibliography and manuscript reference verification gate.

Modes:
    refverify document.md [--no-cache] [--ttl-seconds N]
    refverify document.docx [--no-cache] [--ttl-seconds N]
    refverify bibliography.txt [--no-cache] [--ttl-seconds N]
    refverify --wiki page.wiki [page2.wiki ...] [--no-cache] [--ttl-seconds N]

Exit codes:
    0: pass or warn
    1: invocation error or no input
    2: gate BLOCK (severe mismatch, duplication, or unresolvable load-bearing citation)
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from phosphene.refverify.adapters.cache import FileCache
from phosphene.refverify.adapters.providers import (
    ArxivAdapter,
    CrossrefAdapter,
    OpenAlexAdapter,
    SemanticScholarAdapter,
)
from phosphene.refverify.domain.readers import extract_bibliography
from phosphene.refverify.domain.verdict import GateDecision
from phosphene.refverify.domain.verify import verify_bibliography
from phosphene.refverify.domain.wikitext import extract_article_field

EXIT_OK = 0
EXIT_USAGE = 1
EXIT_BLOCK = 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="refverify",
        description="Scholarly reference verification and quality-control gate.",
    )
    p.add_argument(
        "files",
        nargs="*",
        help="Path(s) to manuscript (.md), document (.docx), bibliography (.txt), or wikitext (.wiki).",
    )
    p.add_argument(
        "--wiki",
        action="store_true",
        help="Treat input as Observatory/Wikipedia {{Article}} template files and extract |Bibliography= field.",
    )
    p.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass on-disk HTTP response cache.",
    )
    p.add_argument(
        "--ttl-seconds",
        type=int,
        default=604800,
        help="Cache time-to-live in seconds (default: 7 days).",
    )
    return p


def _build_cache(no_cache: bool, ttl_seconds: int) -> FileCache:
    if no_cache:
        return FileCache.in_memory(ttl_seconds=0, enabled=False)
    cache_dir = Path.home() / ".cache" / "refverify"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return FileCache(cache_dir, ttl_seconds=ttl_seconds)


def _verify_text(text: str, cache: FileCache, label: str) -> tuple[GateDecision, int]:
    if not text.strip():
        print(f"{label}: [EMPTY] no references found.")
        return "pass", 0

    lookup = CrossrefAdapter(
        cache,
        fallback=OpenAlexAdapter(
            cache,
            fallback=SemanticScholarAdapter(cache, fallback=ArxivAdapter(cache)),
        ),
    )
    result = verify_bibliography(text, lookup)

    print(f"
=== {label} ===")
    print(f"Decision: {result.decision.upper()} ({result.total_blocking} blocking issue(s))")
    print(
        f"Total: {len(result.references)} | "
        f"Verified: {len(result.verified)} | "
        f"Mismatches: {len(result.mismatches)} | "
        f"Duplicates: {len(result.duplicates)} | "
        f"Unresolved: {len(result.unresolved)}"
    )

    for v in result.verified:
        print(f"  [PASS] {v.reference.raw[:75]}... (score: {v.score:.2f})")
    for m in result.mismatches:
        print(f"  [WARN/MISMATCH] {m.reference.raw[:75]}... -> best match: {m.candidate_title[:50]} (score: {m.score:.2f})")
    for d in result.duplicates:
        print(f"  [BLOCK/DUP] {d.reference.raw[:75]}...")
    for u in result.unresolved:
        print(f"  [UNRESOLVED] {u.reference.raw[:75]}...")

    return result.decision, result.total_blocking


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.files:
        parser.print_help()
        return EXIT_USAGE

    cache = _build_cache(args.no_cache, args.ttl_seconds)
    worst: GateDecision = "pass"
    blocking_total = 0

    for file_str in args.files:
        path = Path(file_str)
        if not path.exists():
            print(f"File not found: {path}", file=sys.stderr)
            return EXIT_USAGE

        if args.wiki:
            raw_text = path.read_text(encoding="utf-8", errors="replace")
            bib_text = extract_article_field(raw_text, "Bibliography")
            if not bib_text:
                print(f"no |Bibliography= field, skipped: {path}")
                continue
        else:
            bib_text = extract_bibliography(path)

        decision, blocking = _verify_text(bib_text, cache, str(path))
        if decision == "block":
            worst = "block"
        elif decision == "warn" and worst != "block":
            worst = "warn"
        blocking_total += blocking

    if worst == "block":
        return EXIT_BLOCK
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
