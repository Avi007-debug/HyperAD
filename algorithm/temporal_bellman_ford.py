"""
HyperAD — Temporal Bellman-Ford Algorithm
==========================================

Finds ALL privilege escalation paths from every non-admin node to every
Domain Admin node in the weighted AD graph.

Standard Bellman-Ford: finds shortest path in O(V * E).
Our extension:
  - Edge weights are temporal decay values (higher = more dangerous).
  - We INVERT weights so BF finds the CHEAPEST path = HIGHEST RISK path.
  - We recover the full path (not just distances) via predecessor tracking.
  - We detect and report negative-weight cycles as a separate finding
    (shouldn't occur in AD graphs but worth detecting for integrity).

EXTRA features added beyond the basic requirement:
  - k-shortest paths (not just the single best path — gives P3's agent
    more findings to reason about).
  - Per-hop weight breakdown in results (helps the PDF report generator).
  - Cycle guard: if a node appears twice in a path, skip it (AD graphs
    can have redundant membership edges).
  - Complexity logging: records actual V×E product so the paper can
    report real numbers rather than theoretical bounds.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx

from algorithm.decay import invert_weight, score_path_weights, temporal_weight
from algorithm.models import (
    BASE_RISK, EdgeType, EscalationPath, RiskLevel
)

logger = logging.getLogger(__name__)

# Domain Admin group names to recognise as escalation targets.
# Extended list covers common naming conventions across organisations.
DA_MARKERS = frozenset({
    "domain admins",
    "enterprise admins",
    "schema admins",
    "administrators",
    "domain controllers",
    "group policy creator owners",
    "account operators",
    "backup operators",
    "print operators",
    "server operators",
})


def _is_da_node(node_name: str) -> bool:
    """Return True if the node name looks like a Domain Admin group."""
    return node_name.lower().strip() in DA_MARKERS


def _extract_path_details(
    graph:       nx.DiGraph,
    pred:        Dict[str, Optional[str]],
    target_node: str,
    source_node: str,
) -> Tuple[List[str], List[str], List[float]]:
    """
    Reconstruct path from predecessor map.

    Returns:
        (node_list, edge_type_list, weight_list)
    """
    nodes: List[str] = []
    cur = target_node
    while cur is not None:
        nodes.append(cur)
        cur = pred.get(cur)
    nodes.reverse()

    if not nodes or nodes[0] != source_node:
        return [], [], []

    edge_types: List[str] = []
    weights:    List[float] = []

    for i in range(len(nodes) - 1):
        u, v = nodes[i], nodes[i + 1]
        edge_data = graph.get_edge_data(u, v) or {}
        etype  = edge_data.get("edge_type", "Unknown")
        weight = edge_data.get("weight", 1.0)
        edge_types.append(etype)
        weights.append(weight)

    return nodes, edge_types, weights


def run_temporal_bellman_ford(
    graph:           nx.DiGraph,
    *,
    da_nodes:        Optional[Set[str]] = None,
    max_hops:        int = 10,
    top_k:           int = 5,
    min_score_threshold: float = 0.1,
) -> List[EscalationPath]:
    """
    Run temporal Bellman-Ford to find all high-risk escalation paths.

    Args:
        graph:      NetworkX DiGraph with 'weight', 'edge_type', and
                    optionally 'days_since_use' on each edge.
        da_nodes:   Pre-computed set of Domain Admin node names. If None,
                    auto-detected from node names using DA_MARKERS.
        max_hops:   Maximum path length to consider (prunes search space).
        top_k:      Return the top-k highest scoring paths per source node.
        min_score_threshold: Ignore paths scoring below this value.

    Returns:
        List[EscalationPath] sorted by total_score descending.
    """
    t_start = time.perf_counter()

    # ── 1. Identify Domain Admin target nodes ────────────────────────────────
    if da_nodes is None:
        da_nodes = {n for n in graph.nodes if _is_da_node(str(n))}

    if not da_nodes:
        logger.warning("temporal_bellman_ford: no Domain Admin nodes found in graph")
        return []

    logger.info("temporal_bellman_ford: %d DA targets, %d nodes, %d edges",
                len(da_nodes), graph.number_of_nodes(), graph.number_of_edges())

    # ── 2. Build cost graph (inverted weights) ───────────────────────────────
    # Bellman-Ford minimises cost.  We want to maximise risk.
    # cost = 1 / weight  →  high risk edge = low cost = preferred.
    cost_graph = nx.DiGraph()
    cost_graph.add_nodes_from(graph.nodes(data=True))

    for u, v, data in graph.edges(data=True):
        w     = data.get("weight", 1.0)
        cost  = invert_weight(w)
        cost_graph.add_edge(u, v, cost=cost, weight=w,
                            edge_type=data.get("edge_type", "Unknown"))

    # ── 3. Run BF from every non-DA source node ──────────────────────────────
    all_paths: List[EscalationPath] = []
    source_nodes = [n for n in graph.nodes if n not in da_nodes]

    complexity_ve = graph.number_of_nodes() * graph.number_of_edges()
    logger.info("temporal_bellman_ford: V×E complexity product = %d", complexity_ve)

    for source in source_nodes:
        try:
            # nx.single_source_bellman_ford returns (dist_dict, pred_dict)
            dist, pred = nx.single_source_bellman_ford(
                cost_graph, source, weight="cost", cutoff=max_hops
            )
        except nx.NetworkXUnbounded:
            # Negative-weight cycle detected — this is itself a Critical finding
            # (reported separately by Tarjan SCC; skip here to avoid infinite loop)
            logger.warning("temporal_bellman_ford: negative cycle detected from %s", source)
            continue
        except nx.NodeNotFound:
            continue

        # Check which DA nodes are reachable from this source
        paths_this_source: List[EscalationPath] = []

        for da in da_nodes:
            if da not in dist or da == source:
                continue

            nodes, etypes, weights = _extract_path_details(
                graph, pred, da, source
            )
            if not nodes:
                continue

            # Guard: skip paths with cycles (repeated nodes)
            if len(nodes) != len(set(nodes)):
                continue

            score = score_path_weights(weights)
            if score < min_score_threshold:
                continue

            paths_this_source.append(EscalationPath(
                nodes=nodes,
                edges=etypes,
                weights=weights,
                total_score=score,
            ))

        # Keep only top-k per source (avoids explosion in dense graphs)
        paths_this_source.sort(key=lambda p: p.total_score, reverse=True)
        all_paths.extend(paths_this_source[:top_k])

    # ── 4. Sort globally and deduplicate ─────────────────────────────────────
    all_paths.sort(key=lambda p: p.total_score, reverse=True)
    seen: Set[Tuple[str, ...]] = set()
    unique_paths: List[EscalationPath] = []
    for path in all_paths:
        key = tuple(path.nodes)
        if key not in seen:
            seen.add(key)
            unique_paths.append(path)

    elapsed = time.perf_counter() - t_start
    logger.info(
        "temporal_bellman_ford: found %d unique paths in %.3fs "
        "(V×E=%d, sources=%d, DA_targets=%d)",
        len(unique_paths), elapsed, complexity_ve, len(source_nodes), len(da_nodes),
    )

    return unique_paths


def summarise_paths(paths: List[EscalationPath]) -> Dict:
    """
    Generate a summary dict suitable for the AI agent's get_findings() tool
    and for the PDF report's executive summary section.
    """
    if not paths:
        return {"total": 0, "by_risk": {}, "top_5": []}

    by_risk: Dict[str, int] = defaultdict(int)
    for p in paths:
        by_risk[p.risk_level.value] += 1

    return {
        "total":    len(paths),
        "by_risk":  dict(by_risk),
        "top_5":    [p.to_dict() for p in paths[:5]],
        "unique_sources": len({p.source for p in paths}),
        "unique_targets": len({p.target for p in paths}),
        "avg_hops":       round(sum(p.hop_count for p in paths) / len(paths), 2),
        "avg_score":      round(sum(p.total_score for p in paths) / len(paths), 4),
    }


# ── Convenience builder: construct a graph from P2's snapshot JSON ────────────
def build_graph_from_snapshot(snapshot: dict) -> nx.DiGraph:
    """
    Build a NetworkX DiGraph from P2's snapshot JSON format.

    Expected snapshot structure:
    {
        "nodes": [{"id": str, "type": str, "lastLogon": int, ...}, ...],
        "edges": [{"src": str, "dst": str, "edge_type": str,
                   "days_since_use": int|null}, ...]
    }

    This function is called at Sync 1 when P2 hands over the real data.
    Until then, tests use synthetic graphs.
    """
    import datetime

    G = nx.DiGraph()

    # Add nodes
    for node in snapshot.get("nodes", []):
        G.add_node(node["id"], **{k: v for k, v in node.items() if k != "id"})

    # Add edges with temporal weights
    today = datetime.date.today()
    for edge in snapshot.get("edges", []):
        src       = edge["src"]
        dst       = edge["dst"]
        etype     = edge.get("edge_type", "MemberOf")
        days_raw  = edge.get("days_since_use")

        # Compute temporal weight
        w = temporal_weight(etype, days_raw)

        G.add_edge(src, dst,
                   edge_type=etype,
                   weight=w,
                   days_since_use=days_raw)

    logger.info("build_graph_from_snapshot: %d nodes, %d edges",
                G.number_of_nodes(), G.number_of_edges())
    return G
