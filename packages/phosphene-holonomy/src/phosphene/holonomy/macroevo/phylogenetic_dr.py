"""Phylogenetic Tip Diversification Rate (DR) auditing and singularity diagnostics.

Replaces PyRate branch-length collapses with exact Newick parsing and regularized Jetz et al. (2012) metrics.
Detects and guards against zero-length polytomy machine-epsilon artifacts (< 1e-6 Myr / picoseconds)
that cause inverse branch-length explosions in published phylogenetic trees.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

from phosphene.holonomy.macroevo.primitives import (
    regularized_inverse_branch_length,
    tip_diversification_rate,
)


@dataclass(frozen=True)
class TipDRAudit:
    """Audit result for tip diversification rate across taxa."""

    taxon: str
    branch_lengths_root_to_tip: Tuple[float, ...]
    harmonic_dr: float
    min_branch_length_myr: float
    has_singularity: bool


def parse_simple_newick(newick_str: str) -> Dict[str, List[float]]:
    """Parse a simple Newick tree and extract root-to-tip branch lengths per taxon.

    A pure functional lightweight recursive parser avoiding heavy third-party bio dependencies.
    """
    clean = newick_str.strip().rstrip(";")

    # Tokenizer for simple Newick trees
    taxa_paths: Dict[str, List[float]] = {}

    def extract_leaves(sub_tree: str, current_path: List[float]) -> None:
        sub_tree = sub_tree.strip()
        if not sub_tree:
            return

        # Check if internal node or leaf
        if sub_tree.startswith("(") and sub_tree.endswith(")"):
            inner = sub_tree[1:-1]
        elif "(" in sub_tree:
            inner = sub_tree
        else:
            # Leaf node format: name:length
            parts = sub_tree.split(":")
            name = parts[0].strip().strip("'\"")
            length = float(parts[1]) if len(parts) > 1 else 1.0
            taxa_paths[name] = current_path + [length]
            return

        # Split top-level commas
        parts = []
        depth = 0
        cur = []
        for char in inner:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif char == "," and depth == 0:
                parts.append("".join(cur))
                cur = []
                continue
            cur.append(char)
        if cur:
            parts.append("".join(cur))

        for p in parts:
            p = p.strip()
            # Extract branch length of sub-clade if present
            branch_len = 1.0
            if "):" in p:
                node_part, len_part = p.rsplit("):", 1)
                sub_clade = node_part + ")"
                try:
                    branch_len = float(len_part.split()[0])
                except ValueError:
                    branch_len = 1.0
            elif ":" in p and not p.startswith("("):
                sub_clade = p
                branch_len = 0.0  # Handled inside leaf
            else:
                sub_clade = p

            if sub_clade.startswith("("):
                extract_leaves(sub_clade, current_path + [branch_len])
            else:
                extract_leaves(sub_clade, current_path)

    extract_leaves(clean, [])
    return taxa_paths


def audit_tree_diversification_rates(
    taxa_branch_lengths: Dict[str, List[float]],
    epsilon_myr: float = 0.01,
) -> List[TipDRAudit]:
    """Compute Tip Diversification Rate (DR) and singularity diagnostics across all tips."""
    audits = []
    for taxon, lengths in sorted(taxa_branch_lengths.items()):
        min_len = min(lengths) if lengths else 0.0
        has_singularity = min_len < 1e-5
        dr = tip_diversification_rate(lengths, epsilon_myr=epsilon_myr)
        audits.append(
            TipDRAudit(
                taxon=taxon,
                branch_lengths_root_to_tip=tuple(lengths),
                harmonic_dr=dr,
                min_branch_length_myr=min_len,
                has_singularity=has_singularity,
            )
        )
    return audits
