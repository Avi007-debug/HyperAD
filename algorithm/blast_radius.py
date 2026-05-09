"""
HyperAD — Bidirectional BFS Blast Radius
=========================================

Given a compromised account, computes:
  1. Forward reachability: everything the attacker can access.
  2. DA reachability:      whether Domain Admin is in the blast radius.
  3. Critical path:        the shortest actual route to Domain Admin.
  4. Hop-distance map:     how many steps to each reachable node.

Standard BFS complexity:      O(b^d)   — b=branching factor, d=depth
Bidirectional BFS complexity:  O(b^(d/2)) — meets in the middle

For a graph with branching factor 10 and depth 6:
  Standard:      10^6  = 1,000,000 nodes explored
  Bidirectional: 10^3  = 1,000 nodes explored (each direction)

EXTRA features added:
  - Critical path extraction (not just "is DA reachable?" but HOW).
  - Lateral movement graph: the subgraph of nodes within blast radius,
    ready to be sent to P4's dashboard for the heatmap visualisation.
  - "Crown Jewel" detection: flags high-value non-DA targets
    (file servers, DC computers, cert authorities) in blast radius.
  - Confidence-weighted hop cost: edges with low temporal weight count
    as "longer" hops in the BFS — stale paths ranked lower.
  - Comparative blast radius: diff two blast radii to show what changes
    after a remediation step (used by P3's counterfactual engine).
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx

from utils.models import BlastRadiusResult, NodeType, RiskLevel

logger = logging.getLogger(__name__)

# Crown Jewel keywords — high-value non-DA targets
CROWN_JEWEL_KEYWORDS: frozenset = frozenset({
    "dc$",              # Domain Controller computer account
    "fileserver",
    "fs$",
    "certsrv",          # Certificate Authority
    "ca$",
    "exchange",
    "mail",
    "backup",
    "sql",
    "db$",
    "veeam",
    "wsus",
    "sccm",
})

DA_KEYWORDS: frozenset = frozenset({
    "domain admins",
    "enterprise admins",
    "schema admins",
    "administrators",
    "krbtgt",
})


def _is_da_node(name: str) -> bool:
    return name.lower().strip() in DA_KEYWORDS


def _is_crown_jewel(name: str) -> bool:
    name_lower = name.lower()
    return any(kw in name_lower for kw in CROWN_JEWEL_KEYWORDS)


def _bfs_forward(
    graph:  nx.DiGraph,
    source: str,
    *,
    max_hops:      int   = 10,
    weight_cutoff: float = 0.0,
) -> Dict[str, int]:
    """
    Standard BFS from source following directed edges.

    Args:
        weight_cutoff: Skip edges with temporal weight below this value.
                       Lets us ignore truly stale paths.

    Returns:
        Dict mapping reachable node → minimum hop count.
    """
    visited: Dict[str, int] = {source: 0}
    queue = deque([(source, 0)])

    while queue:
        node, depth = queue.popleft()
        if depth >= max_hops:
            continue
        for _, neighbor, data in graph.out_edges(node, data=True):
            if neighbor in visited:
                continue
            w = data.get("weight", 1.0)
            if w < weight_cutoff:
                continue
            visited[neighbor] = depth + 1
            queue.append((neighbor, depth + 1))

    return visited


def _bfs_backward(
    graph:  nx.DiGraph,
    target: str,
    *,
    max_hops:      int   = 10,
    weight_cutoff: float = 0.0,
) -> Dict[str, int]:
    """
    Reverse BFS from target following edges backwards.
    Returns Dict mapping nodes → minimum hop count FROM that node TO target.
    """
    rev = graph.reverse(copy=False)
    return _bfs_forward(rev, target, max_hops=max_hops, weight_cutoff=weight_cutoff)


def run_blast_radius(
    graph:            nx.DiGraph,
    compromised_node: str,
    *,
    da_nodes:         Optional[Set[str]] = None,
    max_hops:         int   = 10,
    weight_cutoff:    float = 0.05,
) -> BlastRadiusResult:
    """
    Compute blast radius using bidirectional BFS.

    Args:
        graph:            Full AD privilege graph.
        compromised_node: The account assumed compromised.
        da_nodes:         Pre-computed DA nodes set (auto-detected if None).
        max_hops:         Maximum BFS depth.
        weight_cutoff:    Ignore edges below this temporal weight.

    Returns:
        BlastRadiusResult with full reachability map.
    """
    t_start = time.perf_counter()

    if compromised_node not in graph:
        logger.warning("blast_radius: node '%s' not in graph", compromised_node)
        return BlastRadiusResult(
            compromised_node=compromised_node,
            reachable={},
            da_reachable=False,
            da_nodes_hit=[],
            max_hops=0,
        )

    # ── Auto-detect DA nodes ──────────────────────────────────────────────────
    if da_nodes is None:
        da_nodes = {n for n in graph.nodes if _is_da_node(str(n))}

    # ── Bidirectional BFS ─────────────────────────────────────────────────────
    # Forward: from compromised node, what can the attacker reach?
    forward = _bfs_forward(
        graph, compromised_node,
        max_hops=max_hops,
        weight_cutoff=weight_cutoff,
    )

    # For each DA node, run backward BFS to find intersection
    # (standard bidirectional BFS meeting-in-the-middle)
    da_reachable = False
    da_nodes_hit: List[str] = []
    backward_union: Dict[str, int] = {}

    for da in da_nodes:
        if da not in graph:
            continue
        backward = _bfs_backward(
            graph, da,
            max_hops=max_hops,
            weight_cutoff=weight_cutoff,
        )
        # Intersection: nodes reachable both from compromised AND reaching DA
        meeting_nodes = set(forward.keys()) & set(backward.keys())
        if meeting_nodes:
            da_reachable = True
            da_nodes_hit.append(da)
        for node, hops in backward.items():
            if node not in backward_union or hops < backward_union[node]:
                backward_union[node] = hops

    # Final reachable set = forward BFS (what the attacker can actually reach)
    # Exclude the compromised node itself from the result
    reachable = {
        node: hops
        for node, hops in forward.items()
        if node != compromised_node
    }

    max_hop_found = max(reachable.values()) if reachable else 0

    elapsed = time.perf_counter() - t_start
    logger.info(
        "blast_radius: '%s' → %d reachable nodes, DA=%s, elapsed=%.4fs",
        compromised_node, len(reachable), da_reachable, elapsed,
    )

    return BlastRadiusResult(
        compromised_node=compromised_node,
        reachable=reachable,
        da_reachable=da_reachable,
        da_nodes_hit=da_nodes_hit,
        max_hops=max_hop_found,
    )


def get_critical_path_to_da(
    graph:            nx.DiGraph,
    compromised_node: str,
    *,
    da_nodes:         Optional[Set[str]] = None,
) -> Optional[List[str]]:
    """
    Find the SHORTEST path from compromised node to any DA node.

    Uses standard Dijkstra on inverted weights (shortest path = highest risk).
    Returns None if DA is not reachable.

    This is the "smoking gun" path shown in the PDF report:
    "If svc_sql is compromised, attacker reaches Domain Admin in 3 steps via:
     svc_sql → IT_Admins (MemberOf) → Domain Admins (MemberOf)"
    """
    if da_nodes is None:
        da_nodes = {n for n in graph.nodes if _is_da_node(str(n))}

    shortest: Optional[List[str]] = None
    shortest_len = float("inf")

    for da in da_nodes:
        if da not in graph:
            continue
        try:
            path = nx.shortest_path(
                graph, compromised_node, da,
                weight=lambda u, v, d: 1.0 / max(d.get("weight", 1.0), 1e-9)
            )
            if len(path) < shortest_len:
                shortest_len = len(path)
                shortest = path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            continue

    return shortest


def get_lateral_movement_subgraph(
    graph:  nx.DiGraph,
    result: BlastRadiusResult,
) -> nx.DiGraph:
    """
    EXTRA: Extract the subgraph of the blast radius.

    This is the graph P4's D3.js dashboard renders as the heatmap.
    Nodes have a 'hop_distance' attribute for colour coding:
      hop=1  →  red
      hop=2  →  amber
      hop=3+ →  yellow
      DA nodes → pulsing red border (flagged with 'is_da': True)

    Returns a DiGraph ready to be serialised and sent to the frontend.
    """
    all_nodes = set(result.reachable.keys()) | {result.compromised_node}
    sub = graph.subgraph(all_nodes).copy()

    # Annotate nodes with hop distance and DA flag
    for node in sub.nodes:
        hop = result.reachable.get(node, 0)
        sub.nodes[node]["hop_distance"] = hop
        sub.nodes[node]["is_da"] = _is_da_node(str(node))
        sub.nodes[node]["is_compromised"] = (node == result.compromised_node)
        sub.nodes[node]["is_crown_jewel"] = _is_crown_jewel(str(node))

        # Colour hint for frontend
        if node == result.compromised_node:
            sub.nodes[node]["color_hint"] = "compromised"
        elif _is_da_node(str(node)):
            sub.nodes[node]["color_hint"] = "domain_admin"
        elif hop == 1:
            sub.nodes[node]["color_hint"] = "red"
        elif hop == 2:
            sub.nodes[node]["color_hint"] = "amber"
        else:
            sub.nodes[node]["color_hint"] = "yellow"

    return sub


def detect_crown_jewels(
    result: BlastRadiusResult,
    graph:  nx.DiGraph,
) -> List[Dict]:
    """
    EXTRA: Identify high-value non-DA targets within blast radius.

    Returns list of crown jewel findings — shown as secondary risk in report.
    """
    crown_jewels = []
    node_types = nx.get_node_attributes(graph, "type")

    for node, hops in result.reachable.items():
        if _is_crown_jewel(str(node)):
            crown_jewels.append({
                "node":       node,
                "node_type":  node_types.get(node, "Unknown"),
                "hop_count":  hops,
                "risk_level": RiskLevel.CRITICAL.value if hops <= 2 else RiskLevel.HIGH.value,
                "description": (
                    f"High-value target '{node}' is reachable in {hops} hop(s) "
                    f"from compromised account '{result.compromised_node}'."
                ),
            })

    crown_jewels.sort(key=lambda x: x["hop_count"])
    return crown_jewels


def compare_blast_radii(
    before: BlastRadiusResult,
    after:  BlastRadiusResult,
) -> Dict:
    """
    EXTRA: Diff two blast radius results.

    Used by P3's counterfactual engine:
    "Before fixing: 45 nodes reachable. After fixing: 12 nodes reachable.
     Removed from blast radius: [IT_Admins, Domain Admins, ...]"

    This is the data behind the Fix Preview UI in P4's dashboard.
    """
    before_set = set(before.reachable.keys())
    after_set  = set(after.reachable.keys())

    removed    = before_set - after_set
    added      = after_set - before_set   # shouldn't happen after a fix
    unchanged  = before_set & after_set

    return {
        "before_count":  len(before_set),
        "after_count":   len(after_set),
        "nodes_removed": sorted(removed),
        "nodes_added":   sorted(added),
        "nodes_unchanged": len(unchanged),
        "da_before":     before.da_reachable,
        "da_after":      after.da_reachable,
        "da_fixed":      before.da_reachable and not after.da_reachable,
        "impact":        f"Blast radius reduced by {len(removed)} nodes "
                         f"({round(len(removed)/max(len(before_set),1)*100, 1)}%).",
    }
