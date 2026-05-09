"""
HyperAD — Tarjan's SCC for Circular Delegation Detection
=========================================================

Finds circular delegation chains in the AD delegation subgraph.

A Strongly Connected Component (SCC) with size > 1 in the delegation
subgraph means:
    Account A can impersonate Account B
    AND Account B can impersonate Account A (directly or transitively)

This is a Critical misconfiguration — compromising ANY account in the
cycle gives the attacker full control over ALL accounts in the cycle.

Standard Tarjan SCC complexity: O(V + E)  — optimal, single DFS pass.

EXTRA features:
  - Delegation subgraph extraction with edge-type filtering
  - Risk scoring per SCC based on the privilege level of members
  - MITRE ATT&CK pre-labelling (T1134 — Access Token Manipulation)
  - "explosion score": if any SCC member is a Domain Admin or high-value
    service account, the finding is auto-escalated to CRITICAL
  - Full SCC metadata: which edges connect the cycle members
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Set, Tuple

import networkx as nx

from algorithm.models import EdgeType, NodeType, RiskLevel, SCCFinding

logger = logging.getLogger(__name__)

# Edge types that represent delegation relationships
DELEGATION_EDGE_TYPES: frozenset = frozenset({
    EdgeType.ALLOWED_TO_DELEGATE,
    EdgeType.ALLOWED_TO_ACT,
    EdgeType.GENERIC_ALL,        # GenericAll implies delegation capability
    EdgeType.WRITE_DACL,         # WriteDACL can be used to grant delegation
})

# High-value node keywords — if present in an SCC, escalate to Critical
HIGH_VALUE_KEYWORDS: frozenset = frozenset({
    "domain admin",
    "enterprise admin",
    "schema admin",
    "dc$",
    "krbtgt",
    "administrator",
    "svc_",
    "service",
})

# MITRE ATT&CK mapping for circular delegation
MITRE_TACTIC = "T1134.001"   # Access Token Manipulation: Token Impersonation/Theft
MITRE_NAME   = "Token Impersonation/Theft via Circular Delegation"


def _extract_delegation_subgraph(graph: nx.DiGraph) -> nx.DiGraph:
    """
    Extract the subgraph containing only delegation-type edges.

    This reduces noise: membership edges don't create delegation cycles,
    only actual delegation / permission-grant edges do.
    """
    sub = nx.DiGraph()
    sub.add_nodes_from(graph.nodes(data=True))

    for u, v, data in graph.edges(data=True):
        etype = data.get("edge_type", "")
        if etype in DELEGATION_EDGE_TYPES:
            sub.add_edge(u, v, **data)

    removed_nodes = [n for n in sub.nodes if sub.degree(n) == 0]
    sub.remove_nodes_from(removed_nodes)

    logger.info(
        "_extract_delegation_subgraph: %d nodes, %d edges "
        "(from original %d nodes, %d edges)",
        sub.number_of_nodes(), sub.number_of_edges(),
        graph.number_of_nodes(), graph.number_of_edges(),
    )
    return sub


def _node_is_high_value(node_name: str) -> bool:
    """Check if a node name suggests a high-value target."""
    name_lower = node_name.lower()
    return any(kw in name_lower for kw in HIGH_VALUE_KEYWORDS)


def _scc_has_high_value(scc_nodes: List[str]) -> bool:
    """Return True if any node in the SCC is a high-value target."""
    return any(_node_is_high_value(n) for n in scc_nodes)


def _get_cycle_edges(
    subgraph: nx.DiGraph,
    scc_nodes: List[str],
) -> List[Dict]:
    """
    Return the edges that form the cycle within an SCC.
    These are the edges an attacker would exploit.
    """
    scc_set = set(scc_nodes)
    cycle_edges = []
    for u, v, data in subgraph.edges(data=True):
        if u in scc_set and v in scc_set:
            cycle_edges.append({
                "from":      u,
                "to":        v,
                "edge_type": data.get("edge_type", "Unknown"),
                "weight":    round(data.get("weight", 0.0), 4),
            })
    return cycle_edges


def run_tarjan_scc(
    graph: nx.DiGraph,
    *,
    min_size:          int  = 2,
    include_all_edges: bool = False,
) -> List[SCCFinding]:
    """
    Run Tarjan's SCC on the delegation subgraph.

    Args:
        graph:             Full AD graph (delegation edges will be extracted).
        min_size:          Minimum SCC size to report. Default 2 (any cycle).
        include_all_edges: If True, run on the full graph instead of just
                           delegation edges. Useful for comprehensive sweep.

    Returns:
        List[SCCFinding] sorted by size descending (largest cycles first).
    """
    t_start = time.perf_counter()

    subgraph = graph if include_all_edges else _extract_delegation_subgraph(graph)

    if subgraph.number_of_edges() == 0:
        logger.info("run_tarjan_scc: no delegation edges found — no cycles possible")
        return []

    # NetworkX uses Tarjan's algorithm internally for strongly_connected_components
    # This runs in O(V + E) — optimal
    raw_sccs = list(nx.strongly_connected_components(subgraph))

    findings: List[SCCFinding] = []

    for scc_nodes_set in raw_sccs:
        if len(scc_nodes_set) < min_size:
            continue

        scc_nodes = sorted(scc_nodes_set)  # deterministic ordering
        cycle_edges = _get_cycle_edges(subgraph, scc_nodes)
        edge_types  = list({e["edge_type"] for e in cycle_edges})

        finding = SCCFinding(nodes=scc_nodes, edge_types=edge_types)

        # Escalate to Critical if any high-value account is in the cycle
        if _scc_has_high_value(scc_nodes):
            finding.risk_level = RiskLevel.CRITICAL

        findings.append(finding)

    findings.sort(key=lambda f: f.size, reverse=True)

    elapsed = time.perf_counter() - t_start
    logger.info(
        "run_tarjan_scc: found %d SCCs (size >= %d) in %.4fs",
        len(findings), min_size, elapsed,
    )

    return findings


def enrich_scc_findings(
    findings:   List[SCCFinding],
    graph:      nx.DiGraph,
) -> List[Dict]:
    """
    Enrich raw SCC findings with:
      - MITRE tactic labelling
      - Blast-radius estimate (how many non-cycle nodes each SCC member connects to)
      - Remediation recommendation
      - Explosion score (how bad is it if the cycle is compromised)

    Returns enriched dicts ready for the AI agent and PDF report.
    """
    enriched = []

    for f in findings:
        base = f.to_dict()

        # Estimate outbound reach of SCC members (rough blast radius)
        scc_set = set(f.nodes)
        outbound: Set[str] = set()
        for node in f.nodes:
            if node in graph:
                outbound.update(nx.descendants(graph, node))
        outbound -= scc_set  # exclude cycle members themselves

        # Explosion score = size × outbound reach (higher = more dangerous)
        explosion_score = f.size * len(outbound)

        base.update({
            "mitre_tactic":    MITRE_TACTIC,
            "mitre_name":      MITRE_NAME,
            "outbound_reach":  len(outbound),
            "explosion_score": explosion_score,
            "remediation": (
                f"1. Immediately audit delegation settings for: {', '.join(f.nodes[:3])}{'...' if len(f.nodes) > 3 else ''}. "
                f"2. Remove unconstrained delegation from all service accounts. "
                f"3. Replace with Resource-Based Constrained Delegation (RBCD) where required. "
                f"4. Enable Protected Users security group for all members of this cycle."
            ),
        })
        enriched.append(base)

    return enriched


def get_delegation_graph_stats(graph: nx.DiGraph) -> Dict:
    """
    Extra analysis: stats about the delegation subgraph.
    Useful for the paper's dataset characterisation section.
    """
    sub = _extract_delegation_subgraph(graph)
    sccs = list(nx.strongly_connected_components(sub))

    return {
        "delegation_nodes":    sub.number_of_nodes(),
        "delegation_edges":    sub.number_of_edges(),
        "total_sccs":          len(sccs),
        "cyclic_sccs":         sum(1 for s in sccs if len(s) > 1),
        "largest_scc_size":    max((len(s) for s in sccs), default=0),
        "is_dag":              nx.is_directed_acyclic_graph(sub),
    }
