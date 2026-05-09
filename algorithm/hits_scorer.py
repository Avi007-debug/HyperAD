"""
HyperAD — HITS Algorithm for AD Account Authority Scoring
==========================================================

Kleinberg's Hyperlink-Induced Topic Search (HITS, 1999) computes two
scores per node:

  hub score:       "I point to many important things"
                   → accounts that have many high-value outbound permissions
                   → attacker's *entry points* worth monitoring

  authority score: "Many important things point to me"
                   → accounts that many hubs can reach
                   → attacker's *targets* — Domain Admin pathway nodes

In web search, high-authority = important page.
In AD security, high-authority = most-wanted account.

Domain Admin groups naturally converge to authority ≈ 1.0.
Service accounts with wide delegation converge to high hub scores.

Complexity: O(k × E) where k = iterations until convergence.

EXTRA features:
  - Weighted HITS: uses temporal weights instead of binary edges
    so stale permissions contribute less to hub/authority scores.
  - DA-path flag: marks nodes that have at least one path to DA.
  - Cluster analysis: groups high-hub nodes by the DA targets they share.
  - "attack centrality" score: combined hub+authority metric that
    identifies nodes that are BOTH entry points AND targets — these
    are the most dangerous accounts in the environment.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx
import numpy as np

from algorithm.models import HITSResult, RiskLevel

logger = logging.getLogger(__name__)

# HITS convergence parameters
DEFAULT_MAX_ITER  = 200
DEFAULT_TOLERANCE = 1.0e-8
DEFAULT_TOP_N     = 20


def _build_weighted_adjacency(
    graph: nx.DiGraph,
) -> Tuple[np.ndarray, List[str]]:
    """
    Build a weighted adjacency matrix for HITS computation.

    Standard HITS uses binary adjacency (edge exists = 1).
    Weighted HITS uses the temporal weight on each edge.
    This means stale permissions have less influence on scoring.

    Returns:
        (matrix, node_list): numpy array and ordered node list.
    """
    nodes    = list(graph.nodes())
    n        = len(nodes)
    idx      = {node: i for i, node in enumerate(nodes)}
    matrix   = np.zeros((n, n), dtype=np.float64)

    for u, v, data in graph.edges(data=True):
        if u in idx and v in idx:
            w = data.get("weight", 1.0)
            matrix[idx[u], idx[v]] = w

    return matrix, nodes


def run_hits(
    graph:    nx.DiGraph,
    *,
    max_iter: int   = DEFAULT_MAX_ITER,
    tol:      float = DEFAULT_TOLERANCE,
    top_n:    int   = DEFAULT_TOP_N,
    weighted: bool  = True,
    da_nodes: Optional[Set[str]] = None,
) -> Tuple[List[HITSResult], Dict]:
    """
    Run weighted HITS on the AD privilege graph.

    Args:
        graph:    Full AD graph with temporal weights.
        max_iter: Maximum HITS iterations.
        tol:      Convergence tolerance (L2 norm of score delta).
        top_n:    Return top-n results each for hub and authority.
        weighted: If True, use temporal weights. If False, binary edges.
        da_nodes: Known Domain Admin node names for DA-path flagging.

    Returns:
        (results_list, metadata_dict)
        results_list: Top-n HITSResult objects sorted by authority score.
        metadata_dict: Convergence info, iteration count, etc.
    """
    t_start = time.perf_counter()

    if graph.number_of_nodes() == 0:
        return [], {"error": "empty graph"}

    # ── Build adjacency matrix ────────────────────────────────────────────────
    if weighted:
        matrix, nodes = _build_weighted_adjacency(graph)
    else:
        # Binary adjacency — standard HITS
        nodes  = list(graph.nodes())
        matrix = nx.to_numpy_array(graph, nodelist=nodes, weight=None)

    n   = len(nodes)
    idx = {node: i for i, node in enumerate(nodes)}

    # ── Initialise hub and authority vectors ──────────────────────────────────
    hub  = np.ones(n, dtype=np.float64)
    auth = np.ones(n, dtype=np.float64)

    converged   = False
    iterations  = 0

    # ── HITS update loop ──────────────────────────────────────────────────────
    # auth[i] = sum of hub[j] for all j that point to i  →  A^T × hub
    # hub[i]  = sum of auth[j] for all j that i points to → A × auth
    for it in range(max_iter):
        new_auth = matrix.T @ hub        # column of incoming hub scores
        new_hub  = matrix   @ new_auth   # row of outgoing auth scores

        # Normalise by L2 norm to keep values in [0, 1]
        auth_norm = np.linalg.norm(new_auth)
        hub_norm  = np.linalg.norm(new_hub)

        if auth_norm > 0:
            new_auth /= auth_norm
        if hub_norm > 0:
            new_hub  /= hub_norm

        # Check convergence
        delta = np.linalg.norm(new_auth - auth) + np.linalg.norm(new_hub - hub)
        auth  = new_auth
        hub   = new_hub
        iterations += 1

        if delta < tol:
            converged = True
            break

    # ── Build result objects ──────────────────────────────────────────────────
    # Pre-compute DA-path set if not given
    if da_nodes is None:
        from algorithm.temporal_bellman_ford import _is_da_node
        da_nodes = {n for n in nodes if _is_da_node(str(n))}

    # BFS from each DA node in the REVERSED graph to find which nodes
    # can reach DA (i.e. are on a path to Domain Admin)
    rev   = graph.reverse(copy=False)
    da_ancestors: Set[str] = set()
    for da in da_nodes:
        if da in graph:
            da_ancestors.update(nx.descendants(rev, da))
    da_ancestors.update(da_nodes)

    results: List[HITSResult] = []
    node_types = nx.get_node_attributes(graph, "type")

    for i, node in enumerate(nodes):
        results.append(HITSResult(
            node=node,
            authority=float(auth[i]),
            hub=float(hub[i]),
            node_type=node_types.get(node, "Unknown"),
            is_da_path=(node in da_ancestors),
        ))

    # Sort by authority descending — these are the priority targets
    results.sort(key=lambda r: r.authority, reverse=True)

    elapsed = time.perf_counter() - t_start
    metadata = {
        "iterations":    iterations,
        "converged":     converged,
        "tolerance":     tol,
        "weighted":      weighted,
        "nodes_scored":  n,
        "elapsed_sec":   round(elapsed, 4),
        "da_path_count": len(da_ancestors),
    }

    logger.info(
        "run_hits: %d nodes, %d iterations, converged=%s, elapsed=%.4fs",
        n, iterations, converged, elapsed,
    )

    return results[:top_n], metadata


def compute_attack_centrality(results: List[HITSResult]) -> List[Dict]:
    """
    EXTRA: Attack centrality score = hub × authority.

    Nodes with HIGH hub AND HIGH authority are the most dangerous:
    - They can reach many important targets (high hub)
    - Many attackers would want to compromise them (high authority)

    These are the accounts where a single phishing email = game over.

    Returns enriched dicts with attack_centrality field, sorted descending.
    """
    enriched = []
    for r in results:
        d = r.to_dict()
        d["attack_centrality"] = round(r.hub * r.authority, 6)
        d["interpretation"] = (
            "Entry point AND target — highest priority"
            if r.hub > 0.3 and r.authority > 0.3
            else "Primary target" if r.authority > 0.5
            else "Entry point" if r.hub > 0.5
            else "Supporting role"
        )
        enriched.append(d)

    enriched.sort(key=lambda x: x["attack_centrality"], reverse=True)
    return enriched


def cluster_hubs_by_target(
    results:  List[HITSResult],
    graph:    nx.DiGraph,
    da_nodes: Optional[Set[str]] = None,
) -> Dict[str, List[str]]:
    """
    EXTRA: Group high-hub nodes by which DA targets they share a path to.

    This lets the AI agent say:
    "svc_sql and svc_backup both reach 'Domain Admins' via IT_Admins —
    fixing the IT_Admins GenericAll permission kills both attack paths."

    Returns: { da_node_name: [list of hub nodes that can reach it] }
    """
    if da_nodes is None:
        from algorithm.temporal_bellman_ford import _is_da_node
        da_nodes = {n for n in graph.nodes if _is_da_node(str(n))}

    high_hubs = {r.node for r in results if r.hub > 0.2}
    clusters: Dict[str, List[str]] = defaultdict(list)

    for da in da_nodes:
        if da not in graph:
            continue
        rev  = graph.reverse(copy=False)
        reachable_from_da = nx.descendants(rev, da)
        reachable_from_da.add(da)

        for hub_node in high_hubs:
            if hub_node in reachable_from_da:
                clusters[da].append(hub_node)

    return dict(clusters)


def hits_to_priority_list(results: List[HITSResult], top_n: int = 20) -> List[Dict]:
    """
    Format top-n HITS results as a clean priority list for the PDF report.
    """
    enriched = compute_attack_centrality(results)
    return [
        {
            "rank":             i + 1,
            "account":          r["node"],
            "authority_score":  r["authority"],
            "hub_score":        r["hub"],
            "attack_centrality":r["attack_centrality"],
            "on_da_path":       r["is_da_path"],
            "priority":         r["priority"],
            "interpretation":   r["interpretation"],
            "node_type":        r["node_type"],
        }
        for i, r in enumerate(enriched[:top_n])
    ]
