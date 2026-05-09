"""
HyperAD — Synthetic Graph Factory for Tests
============================================

Builds deterministic, annotated NetworkX graphs that simulate
real Active Directory environments with known misconfigurations.

These graphs are used by:
  - All unit tests (pytest)
  - Integration tests before Sync 1
  - P3's AI agent tests (mock tool calls)
  - P4's dashboard dev (mock API responses)

Three sizes are provided to match the paper's evaluation scenarios:
  - tiny():    12 nodes, 3 known misconfigs  (unit tests)
  - small():   50 nodes, 5 misconfigs        (evaluation scenario 1)
  - medium():  200 nodes, 15 misconfigs      (evaluation scenario 2)
"""

from __future__ import annotations

import random
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx

from utils.models import EdgeType, NodeType
from utils.decay  import temporal_weight


# ── Shared helpers ────────────────────────────────────────────────────────────

def _add_node(G: nx.DiGraph, name: str, ntype: str, **kwargs) -> None:
    G.add_node(name, type=ntype, **kwargs)


def _add_edge(
    G:          nx.DiGraph,
    src:        str,
    dst:        str,
    etype:      str,
    days:       Optional[int] = 1,
) -> None:
    w = temporal_weight(etype, days)
    G.add_edge(src, dst, edge_type=etype, weight=w, days_since_use=days)


# ── TINY graph (12 nodes) ─────────────────────────────────────────────────────

def make_tiny_graph() -> Tuple[nx.DiGraph, Dict]:
    """
    12-node graph with 3 planted misconfigurations:
      1. svc_sql → IT_Admins (GenericAll)  →  Domain Admins
         - Kerberoastable service account with direct path to DA
      2. svc_backup ⇄ svc_web  (circular delegation)
         - Tarjan SCC should detect this cycle
      3. jdoe → Domain Admins (MemberOf, stale 300 days)
         - Very low temporal weight — should rank LOW

    Known correct answers (used in assertions):
      - Bellman-Ford: at least 2 escalation paths to Domain Admins
      - Tarjan SCC:   1 SCC of size 2 {svc_backup, svc_web}
      - HITS:         IT_Admins should have highest authority score
      - Blast radius from svc_sql:  DA reachable = True
      - Blast radius from jdoe:     DA reachable = True (stale path exists)
    """
    G = nx.DiGraph()

    # ── Nodes ─────────────────────────────────────────────────────────────────
    _add_node(G, "jdoe",          NodeType.USER,           lastLogon=300)
    _add_node(G, "bsmith",        NodeType.USER,           lastLogon=5)
    _add_node(G, "svc_sql",       NodeType.SERVICE_ACCOUNT,lastLogon=2)
    _add_node(G, "svc_backup",    NodeType.SERVICE_ACCOUNT,lastLogon=10)
    _add_node(G, "svc_web",       NodeType.SERVICE_ACCOUNT,lastLogon=8)
    _add_node(G, "IT_Help",       NodeType.GROUP,          lastLogon=None)
    _add_node(G, "IT_Admins",     NodeType.GROUP,          lastLogon=None)
    _add_node(G, "Backup_Ops",    NodeType.GROUP,          lastLogon=None)
    _add_node(G, "Workstation01", NodeType.COMPUTER,       lastLogon=1)
    _add_node(G, "DC01",          NodeType.COMPUTER,       lastLogon=0)
    _add_node(G, "Domain Admins", NodeType.GROUP,          lastLogon=None)
    _add_node(G, "Enterprise Admins", NodeType.GROUP,      lastLogon=None)

    # ── Edges — normal membership ─────────────────────────────────────────────
    _add_edge(G, "jdoe",    "IT_Help",        EdgeType.MEMBER_OF, days=300)  # stale
    _add_edge(G, "bsmith",  "IT_Help",        EdgeType.MEMBER_OF, days=5)
    _add_edge(G, "IT_Help", "IT_Admins",      EdgeType.MEMBER_OF, days=None)

    # ── Misconfig 1: svc_sql → GenericAll → IT_Admins → Domain Admins ─────────
    _add_edge(G, "svc_sql",    "IT_Admins",   EdgeType.GENERIC_ALL, days=2)
    _add_edge(G, "IT_Admins",  "Domain Admins", EdgeType.MEMBER_OF, days=None)

    # ── Misconfig 2: circular delegation svc_backup ⇄ svc_web ────────────────
    _add_edge(G, "svc_backup", "svc_web",  EdgeType.ALLOWED_TO_DELEGATE, days=10)
    _add_edge(G, "svc_web",    "svc_backup",EdgeType.ALLOWED_TO_DELEGATE, days=8)

    # ── Misconfig 3: jdoe stale path via IT_Help → IT_Admins → Domain Admins ──
    # (covered by MemberOf edges above — jdoe → IT_Help stale 300 days)

    # ── Additional edges for HITS to have meaningful scores ───────────────────
    _add_edge(G, "svc_backup", "Backup_Ops",   EdgeType.MEMBER_OF, days=10)
    _add_edge(G, "Backup_Ops", "Domain Admins",EdgeType.MEMBER_OF, days=None)
    _add_edge(G, "bsmith",     "Workstation01",EdgeType.ADMIN_TO,  days=5)
    _add_edge(G, "DC01",       "Domain Admins",EdgeType.HAS_SESSION, days=0)
    _add_edge(G, "Domain Admins", "Enterprise Admins", EdgeType.MEMBER_OF, days=None)

    known_answers = {
        "da_nodes":              {"Domain Admins", "Enterprise Admins"},
        "escalation_path_count": 2,           # at minimum
        "scc_cycle_nodes":       {"svc_backup", "svc_web"},
        "scc_count":             1,
        "blast_radius_svc_sql_da": True,
        "blast_radius_bsmith_da":  True,
        "hits_top_authority":    "Domain Admins",
    }

    return G, known_answers


# ── SMALL graph (50 nodes) ────────────────────────────────────────────────────

def make_small_graph(seed: int = 42) -> Tuple[nx.DiGraph, Dict]:
    """
    50-node graph simulating a small company AD.
    5 planted misconfigurations.
    """
    rng = random.Random(seed)
    G   = nx.DiGraph()

    # Infrastructure
    _add_node(G, "Domain Admins",     NodeType.GROUP)
    _add_node(G, "Enterprise Admins", NodeType.GROUP)
    _add_node(G, "DC01$",             NodeType.COMPUTER, lastLogon=0)
    _add_node(G, "DC02$",             NodeType.COMPUTER, lastLogon=0)

    _add_edge(G, "Domain Admins", "Enterprise Admins", EdgeType.MEMBER_OF)
    _add_edge(G, "DC01$", "Domain Admins", EdgeType.HAS_SESSION, days=0)

    # Departments
    departments = ["IT", "Finance", "HR", "Dev", "Security"]
    dept_groups: List[str] = []
    for dept in departments:
        grp = f"{dept}_Team"
        adm = f"{dept}_Admins"
        _add_node(G, grp, NodeType.GROUP)
        _add_node(G, adm, NodeType.GROUP)
        _add_edge(G, grp, adm, EdgeType.MEMBER_OF, days=None)
        dept_groups.append(grp)

    _add_edge(G, "IT_Admins",       "Domain Admins", EdgeType.MEMBER_OF, days=None)
    _add_edge(G, "Security_Admins", "Domain Admins", EdgeType.MEMBER_OF, days=None)

    # Users (20)
    users = [f"user{i:02d}" for i in range(1, 21)]
    for u in users:
        days = rng.randint(0, 180)
        _add_node(G, u, NodeType.USER, lastLogon=days)
        dept = rng.choice(dept_groups)
        _add_edge(G, u, dept, EdgeType.MEMBER_OF, days=days)

    # Service accounts (8)
    svc_accounts = [f"svc_{name}" for name in
                    ["sql", "backup", "web", "mail", "monitor", "deploy", "print", "scan"]]
    for svc in svc_accounts:
        days = rng.randint(0, 30)
        _add_node(G, svc, NodeType.SERVICE_ACCOUNT, lastLogon=days)

    # Computers (10)
    computers = [f"WS{i:02d}$" for i in range(1, 11)]
    for c in computers:
        _add_node(G, c, NodeType.COMPUTER, lastLogon=rng.randint(0, 7))

    # ── Misconfig 1: svc_sql Kerberoastable + GenericAll on IT_Admins ─────────
    _add_edge(G, "svc_sql",    "IT_Admins",    EdgeType.GENERIC_ALL, days=1)

    # ── Misconfig 2: svc_backup unconstrained delegation ──────────────────────
    _add_edge(G, "svc_backup", "svc_web",      EdgeType.ALLOWED_TO_DELEGATE, days=5)
    _add_edge(G, "svc_web",    "svc_backup",   EdgeType.ALLOWED_TO_DELEGATE, days=3)

    # ── Misconfig 3: user01 WriteDACL on Domain Admins ────────────────────────
    _add_edge(G, "user01",     "Domain Admins",EdgeType.WRITE_DACL, days=0)

    # ── Misconfig 4: svc_deploy DCSync rights ────────────────────────────────
    _add_edge(G, "svc_deploy", "DC01$",        EdgeType.DC_SYNC, days=2)

    # ── Misconfig 5: stale admin account (user15 in IT_Admins, 160 days) ─────
    _add_edge(G, "user15",     "IT_Admins",    EdgeType.MEMBER_OF, days=160)

    known_answers = {
        "da_nodes":          {"Domain Admins", "Enterprise Admins"},
        "misconfig_count":   5,
        "scc_count":         1,
        "scc_nodes":         {"svc_backup", "svc_web"},
        "critical_accounts": {"svc_sql", "user01", "svc_deploy"},
    }

    return G, known_answers


# ── Graph → JSON snapshot (for P2 handoff simulation) ────────────────────────

def graph_to_snapshot(G: nx.DiGraph) -> Dict:
    """
    Serialise a NetworkX graph to the JSON snapshot format P2 will deliver.
    Used for integration testing before real P2 data is available.
    """
    nodes = []
    for name, data in G.nodes(data=True):
        nodes.append({"id": name, **data})

    edges = []
    for u, v, data in G.edges(data=True):
        edges.append({
            "src":          u,
            "dst":          v,
            "edge_type":    data.get("edge_type", "MemberOf"),
            "days_since_use": data.get("days_since_use"),
            "weight":       data.get("weight", 1.0),
        })

    return {"nodes": nodes, "edges": edges}
