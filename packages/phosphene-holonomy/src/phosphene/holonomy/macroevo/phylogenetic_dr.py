"""Pure Newick tree parsing and Jetz et al. (2012) Tip DR diagnostics.

Genealogy:
    Rung: 0/1 pure structural parsing and Tip DR reduction (zero disk I/O).
    Literature: Jetz et al. (2012) Nature 491:444–448; Redding & Mooers (2006).

Contract:
    ``newick_tip_paths`` returns branch lengths strictly in **tip-to-root** order
    (index 0 = terminal pendant branch), matching ``TipBranchPath`` and ``tip_dr``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from phosphene.holonomy.macroevo.primitives import (
    TipDRDiagnostic,
    tip_dr_diagnostic,
)


@dataclass
class _PhyloNode:
    name: Optional[str] = None
    branch_length: float = 0.0
    children: List[_PhyloNode] = field(default_factory=list)
    parent: Optional[_PhyloNode] = None


def _parse_newick_nodes(newick_str: str) -> _PhyloNode:
    s = newick_str.strip()
    if s.endswith(";"):
        s = s[:-1]
    if not s:
        raise ValueError("Newick string must be non-empty")

    tokens: list[str] = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c in "(),:;":
            tokens.append(c)
            i += 1
        elif c.isspace():
            i += 1
        else:
            j = i
            while j < n and s[j] not in "(),:; \t\r\n":
                j += 1
            tokens.append(s[i:j])
            i = j

    curr = _PhyloNode()
    root = curr
    idx, num_tokens = 0, len(tokens)
    while idx < num_tokens:
        tok = tokens[idx]
        if tok == ";":
            break
        elif tok == "(":
            child = _PhyloNode(parent=curr)
            curr.children.append(child)
            curr = child
            idx += 1
        elif tok == ",":
            if curr.parent is None:
                raise ValueError("Malformed Newick: unexpected ',' at root")
            curr = curr.parent
            child = _PhyloNode(parent=curr)
            curr.children.append(child)
            curr = child
            idx += 1
        elif tok == ")":
            if curr.parent is None:
                raise ValueError("Malformed Newick: unmatched ')'")
            curr = curr.parent
            idx += 1
            if idx < num_tokens and tokens[idx] not in "(),:;":
                curr.name = tokens[idx].strip("'\"")
                idx += 1
            if idx < num_tokens and tokens[idx] == ":":
                idx += 1
                curr.branch_length = float(tokens[idx])
                idx += 1
        elif tok == ":":
            idx += 1
            curr.branch_length = float(tokens[idx])
            idx += 1
        else:
            curr.name = tok.strip("'\"")
            idx += 1

    return root


def newick_tip_paths(newick_str: str) -> Dict[str, tuple[float, ...]]:
    """Parse a Newick string into tip-to-root branch length tuples per leaf taxon.

    Genealogy:
        Rung: 0 pure string-to-value transformation (zero disk I/O).

    Objective:
        For each leaf taxon i, extracts (l_1, l_2, ..., l_N) where l_1 is the
        terminal pendant branch and l_N is the deepest internal edge below root.

    Dimensions:
        newick_str: Standard Newick text with branch lengths in [T].
        Returns: Mapping ``taxon_name -> tuple[float, ...]`` in tip-to-root order [T].

    Boundary & Falsification Semantics:
        - Empty or malformed Newick string -> raises ValueError.
    """
    root = _parse_newick_nodes(newick_str)
    paths: Dict[str, tuple[float, ...]] = {}

    def _walk(node: _PhyloNode, ancestor_path: list[float]) -> None:
        if not node.children:
            if node.name:
                paths[node.name] = tuple([node.branch_length] + ancestor_path)
            return
        next_anc = [node.branch_length] + ancestor_path if node.parent is not None else []
        for child in node.children:
            _walk(child, next_anc)

    _walk(root, [])
    return paths


@dataclass(frozen=True)
class TreeTipDRRecord:
    """Per-taxon Jetz et al. (2012) Tip DR diagnostic record."""

    taxon: str
    tip_to_root_lengths: tuple[float, ...]
    diagnostic: TipDRDiagnostic

    @property
    def equal_splits(self) -> float:
        return self.diagnostic.equal_splits

    @property
    def diversification_rate(self) -> float:
        return self.diagnostic.diversification_rate

    @property
    def min_branch_length(self) -> float:
        return self.diagnostic.min_branch_length

    @property
    def terminal_branch_length(self) -> float:
        return self.diagnostic.terminal_branch_length

    @property
    def has_singularity(self) -> bool:
        return self.diagnostic.has_singularity


def tree_tip_dr_diagnostics(
    tip_paths: Dict[str, Sequence[float]],
    min_branch_length: float = 1e-4,
    singularity_threshold: float = 1e-6,
    exclude_taxa: Sequence[str] = (),
) -> List[TreeTipDRRecord]:
    """Compute Tip DR and polytomy singularity diagnostics across all included tree tips.

    Genealogy:
        Rung: 0 map over ``tip_dr_diagnostic`` (zero disk I/O).
        Literature: Jetz et al. (2012) Nature 491:444–448.

    Dimensions:
        tip_paths: Mapping ``taxon -> tip-to-root branch lengths`` [T].
        min_branch_length: [T] Regularization floor (> 0).
        singularity_threshold: [T] Polytomy artifact flag threshold (> 0).
        Returns: List of ``TreeTipDRRecord`` sorted by taxon name.
    """
    excluded = set(exclude_taxa)
    records: List[TreeTipDRRecord] = []
    for taxon, lengths in sorted(tip_paths.items()):
        if taxon in excluded:
            continue
        diag = tip_dr_diagnostic(
            lengths,
            min_branch_length=min_branch_length,
            singularity_threshold=singularity_threshold,
        )
        records.append(
            TreeTipDRRecord(
                taxon=taxon,
                tip_to_root_lengths=tuple(float(l) for l in lengths),
                diagnostic=diag,
            )
        )
    return records


# Backward-compatibility aliases
parse_simple_newick = newick_tip_paths
TipDRAudit = TreeTipDRRecord
audit_tree_diversification_rates = tree_tip_dr_diagnostics

__all__ = [
    "newick_tip_paths",
    "TreeTipDRRecord",
    "tree_tip_dr_diagnostics",
    "parse_simple_newick",
    "TipDRAudit",
    "audit_tree_diversification_rates",
]
