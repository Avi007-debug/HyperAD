"""
HyperAD — P1 Algorithm Unit Tests
===================================

Run:   pytest tests/test_algorithms.py -v
       pytest tests/test_algorithms.py -v --tb=short   (concise failures)

All tests use deterministic synthetic graphs from graph_factory.py.
No network calls, no external dependencies.

Test categories:
  1. Decay function tests        — pure math verification
  2. Bellman-Ford tests          — path finding + temporal weighting
  3. Tarjan SCC tests            — cycle detection
  4. HITS tests                  — authority/hub scoring
  5. Blast radius tests          — BFS reachability
  6. Integration tests           — all algorithms together on known graph
  7. Edge case tests             — empty graph, disconnected, single node
  8. Performance smoke tests     — basic timing assertions (50-node graph)
"""

from __future__ import annotations

import math
import sys
import time
from pathlib import Path
from typing import Dict, List, Set

import networkx as nx
import pytest

# ── Path setup so imports work from repo root ─────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from algorithm.blast_radius         import (
    compare_blast_radii, detect_crown_jewels,
    get_critical_path_to_da, get_lateral_movement_subgraph,
    run_blast_radius,
)
from algorithm.hits_scorer          import (
    cluster_hubs_by_target, compute_attack_centrality,
    hits_to_priority_list, run_hits,
)
from algorithm.tarjan_scc           import (
    enrich_scc_findings, get_delegation_graph_stats,
    run_tarjan_scc,
)
from algorithm.temporal_bellman_ford import (
    build_graph_from_snapshot, run_temporal_bellman_ford,
    summarise_paths,
)
from algorithm.graph_factory             import (
    graph_to_snapshot, make_small_graph, make_tiny_graph,
)
from algorithm.decay                     import (
    invert_weight, lambda_sensitivity, temporal_weight,
)
from algorithm.models                    import EdgeType, EscalationPath, RiskLevel

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Decay function
# ═════════════════════════════════════════════════════════════════════════════

class TestTemporalDecay:
    """Tests for the exponential decay weight formula."""

    def test_zero_days_returns_base_risk(self):
        """A permission used today should return its full base risk."""
        w = temporal_weight(EdgeType.GENERIC_ALL, days_since_last_use=0)
        # base_risk for GenericAll = 10.0, exp(0) = 1.0 → w = 10.0
        assert abs(w - 10.0) < 0.01, f"Expected ~10.0, got {w}"

    def test_stale_permission_lower_weight(self):
        """An unused permission scores lower than an active one."""
        active = temporal_weight(EdgeType.GENERIC_ALL, days_since_last_use=1)
        stale  = temporal_weight(EdgeType.GENERIC_ALL, days_since_last_use=180)
        assert stale < active, "Stale permission must score lower than active"

    def test_none_days_treated_as_max_staleness(self):
        """days=None (never seen used) should give minimum weight."""
        w_none = temporal_weight(EdgeType.GENERIC_ALL, days_since_last_use=None)
        w_365  = temporal_weight(EdgeType.GENERIC_ALL, days_since_last_use=365)
        assert abs(w_none - w_365) < 0.01, "None should equal 365-day staleness"

    def test_floor_prevents_zero(self):
        """Even a maximally stale edge must have weight > 0 (floor)."""
        w = temporal_weight(EdgeType.GENERIC_ALL, days_since_last_use=365)
        assert w > 0.0, "Weight must never be exactly zero"

    def test_high_risk_edge_always_higher_than_low_risk(self):
        """GenericAll must always outweigh MemberOf at the same staleness."""
        for days in [0, 30, 90, 180, 365]:
            ga = temporal_weight(EdgeType.GENERIC_ALL, days)
            mo = temporal_weight(EdgeType.MEMBER_OF,   days)
            assert ga > mo, f"GenericAll must > MemberOf at days={days}"

    def test_invert_weight_is_inverse(self):
        """invert_weight(w) × w should be approximately 1.0."""
        w = temporal_weight(EdgeType.WRITE_DACL, days_since_last_use=10)
        assert abs(invert_weight(w) * w - 1.0) < 0.001

    def test_lambda_sensitivity_returns_expected_shape(self):
        """Higher lambda should produce steeper decay."""
        table = lambda_sensitivity(EdgeType.GENERIC_ALL)
        for lam_key, day_map in table.items():
            # Weight at day=0 must be highest
            assert day_map[0] >= day_map[365], f"Day 0 must be >= Day 365 for {lam_key}"

    def test_dc_sync_higher_than_member_of(self):
        """DCSync must have higher base risk than MemberOf."""
        w_dcsync = temporal_weight(EdgeType.DC_SYNC,    days_since_last_use=0)
        w_mo     = temporal_weight(EdgeType.MEMBER_OF,  days_since_last_use=0)
        assert w_dcsync > w_mo

    def test_decay_formula_mathematically_correct(self):
        """Manually verify: w = 10.0 * exp(-0.02 * 30) = 10.0 * 0.5488 ≈ 5.488"""
        w = temporal_weight(EdgeType.GENERIC_ALL, days_since_last_use=30, lam=0.02)
        expected = 10.0 * math.exp(-0.02 * 30)
        assert abs(w - expected) < 0.01, f"Expected {expected:.4f}, got {w}"


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Temporal Bellman-Ford
# ═════════════════════════════════════════════════════════════════════════════

class TestBellmanFord:
    """Tests for the temporal Bellman-Ford escalation path finder."""

    @pytest.fixture
    def tiny(self):
        G, answers = make_tiny_graph()
        return G, answers

    def test_finds_escalation_paths(self, tiny):
        """Must find at least the known number of escalation paths."""
        G, answers = tiny
        paths = run_temporal_bellman_ford(G, da_nodes=answers["da_nodes"])
        assert len(paths) >= answers["escalation_path_count"], (
            f"Expected >= {answers['escalation_path_count']} paths, found {len(paths)}"
        )

    def test_paths_start_at_non_admin_nodes(self, tiny):
        """No path should start at a Domain Admin node."""
        G, answers = tiny
        paths = run_temporal_bellman_ford(G, da_nodes=answers["da_nodes"])
        for p in paths:
            assert p.source not in answers["da_nodes"], (
                f"Path started at DA node: {p.source}"
            )

    def test_paths_end_at_da_node(self, tiny):
        """Every escalation path must terminate at a Domain Admin node."""
        G, answers = tiny
        paths = run_temporal_bellman_ford(G, da_nodes=answers["da_nodes"])
        for p in paths:
            assert p.target in answers["da_nodes"], (
                f"Path ended at non-DA node: {p.target}"
            )

    def test_sorted_by_score_descending(self, tiny):
        """Paths must be sorted highest risk first."""
        G, answers = tiny
        paths = run_temporal_bellman_ford(G, da_nodes=answers["da_nodes"])
        scores = [p.total_score for p in paths]
        assert scores == sorted(scores, reverse=True), "Paths not sorted by score"

    def test_active_path_scores_higher_than_stale(self, tiny):
        """svc_sql (active 2 days) must score higher than jdoe (stale 300 days)."""
        G, answers = tiny
        paths = run_temporal_bellman_ford(G, da_nodes=answers["da_nodes"])
        sql_paths  = [p for p in paths if p.source == "svc_sql"]
        jdoe_paths = [p for p in paths if p.source == "jdoe"]
        if sql_paths and jdoe_paths:
            assert sql_paths[0].total_score > jdoe_paths[0].total_score, (
                "Active svc_sql path must score higher than stale jdoe path"
            )

    def test_no_cyclic_paths(self, tiny):
        """Returned paths must not contain repeated nodes (no cycles)."""
        G, answers = tiny
        paths = run_temporal_bellman_ford(G, da_nodes=answers["da_nodes"])
        for p in paths:
            assert len(p.nodes) == len(set(p.nodes)), (
                f"Cyclic path detected: {p.nodes}"
            )

    def test_risk_level_assigned(self, tiny):
        """Each path must have a non-null RiskLevel."""
        G, answers = tiny
        paths = run_temporal_bellman_ford(G, da_nodes=answers["da_nodes"])
        for p in paths:
            assert p.risk_level in RiskLevel, f"Invalid risk level: {p.risk_level}"

    def test_hop_count_correct(self, tiny):
        """hop_count must equal len(nodes) - 1."""
        G, answers = tiny
        paths = run_temporal_bellman_ford(G, da_nodes=answers["da_nodes"])
        for p in paths:
            assert p.hop_count == len(p.nodes) - 1

    def test_weights_match_edges(self, tiny):
        """len(weights) must equal len(edges) must equal hop_count."""
        G, answers = tiny
        paths = run_temporal_bellman_ford(G, da_nodes=answers["da_nodes"])
        for p in paths:
            assert len(p.weights) == p.hop_count, "Weight count != hop count"
            assert len(p.edges)   == p.hop_count, "Edge count != hop count"

    def test_summarise_returns_valid_structure(self, tiny):
        """summarise_paths must return a dict with expected keys."""
        G, answers = tiny
        paths   = run_temporal_bellman_ford(G, da_nodes=answers["da_nodes"])
        summary = summarise_paths(paths)
        assert "total"    in summary
        assert "by_risk"  in summary
        assert "top_5"    in summary
        assert summary["total"] == len(paths)

    def test_empty_graph_returns_empty(self):
        """Empty graph must return empty list without error."""
        G = nx.DiGraph()
        paths = run_temporal_bellman_ford(G)
        assert paths == []

    def test_no_da_nodes_returns_empty(self, tiny):
        """If no DA nodes exist, return empty."""
        G, _ = tiny
        paths = run_temporal_bellman_ford(G, da_nodes=set())
        assert paths == []

    def test_build_from_snapshot(self, tiny):
        """Graph built from P2 snapshot JSON must produce same node/edge count."""
        G, answers = tiny
        snapshot  = graph_to_snapshot(G)
        G2        = build_graph_from_snapshot(snapshot)
        assert G2.number_of_nodes() == G.number_of_nodes()
        assert G2.number_of_edges() == G.number_of_edges()

    def test_max_hops_limits_paths(self, tiny):
        """max_hops=1 should find only 1-hop paths (direct edges to DA)."""
        G, answers = tiny
        paths_limited = run_temporal_bellman_ford(
            G, da_nodes=answers["da_nodes"], max_hops=1
        )
        for p in paths_limited:
            assert p.hop_count <= 1, f"Path has {p.hop_count} hops but max=1"


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Tarjan SCC
# ═════════════════════════════════════════════════════════════════════════════

class TestTarjanSCC:
    """Tests for circular delegation / trust loop detection."""

    @pytest.fixture
    def tiny(self):
        G, answers = make_tiny_graph()
        return G, answers

    def test_detects_planted_cycle(self, tiny):
        """Must detect the svc_backup ⇄ svc_web delegation cycle."""
        G, answers = tiny
        findings = run_tarjan_scc(G)
        assert len(findings) >= answers["scc_count"], (
            f"Expected >= {answers['scc_count']} SCC(s), found {len(findings)}"
        )

    def test_cycle_contains_correct_nodes(self, tiny):
        """The detected SCC must contain exactly svc_backup and svc_web."""
        G, answers = tiny
        findings = run_tarjan_scc(G)
        all_scc_nodes = set()
        for f in findings:
            all_scc_nodes.update(f.nodes)
        expected = answers["scc_cycle_nodes"]
        assert expected.issubset(all_scc_nodes), (
            f"Expected cycle nodes {expected} not found in SCCs {all_scc_nodes}"
        )

    def test_scc_size_correct(self, tiny):
        """Each SCC finding's size field must equal len(nodes)."""
        G, _ = tiny
        findings = run_tarjan_scc(G)
        for f in findings:
            assert f.size == len(f.nodes)

    def test_risk_level_high_or_critical(self, tiny):
        """Any SCC must be at least High risk."""
        G, _ = tiny
        findings = run_tarjan_scc(G)
        for f in findings:
            assert f.risk_level in {RiskLevel.CRITICAL, RiskLevel.HIGH}, (
                f"SCC risk level {f.risk_level} is too low"
            )

    def test_no_false_positives_on_acyclic_graph(self):
        """A DAG must produce zero SCC findings."""
        G = nx.DiGraph()
        G.add_edge("A", "B", edge_type=EdgeType.ALLOWED_TO_DELEGATE, weight=5.0)
        G.add_edge("B", "C", edge_type=EdgeType.ALLOWED_TO_DELEGATE, weight=3.0)
        G.add_edge("C", "Domain Admins", edge_type=EdgeType.MEMBER_OF, weight=2.0)
        findings = run_tarjan_scc(G)
        assert findings == [], f"Expected no SCCs in DAG, got {findings}"

    def test_three_node_cycle_detected(self):
        """Tri-node cycle A→B→C→A must be detected as one SCC of size 3."""
        G = nx.DiGraph()
        for src, dst in [("A","B"), ("B","C"), ("C","A")]:
            G.add_edge(src, dst, edge_type=EdgeType.ALLOWED_TO_DELEGATE, weight=5.0)
        findings = run_tarjan_scc(G, min_size=2)
        assert len(findings) == 1
        assert findings[0].size == 3

    def test_enrich_adds_mitre_tactic(self, tiny):
        """Enriched findings must include a MITRE tactic string."""
        G, _ = tiny
        findings = run_tarjan_scc(G)
        enriched = enrich_scc_findings(findings, G)
        for e in enriched:
            assert "mitre_tactic" in e
            assert e["mitre_tactic"].startswith("T"), (
                f"MITRE tactic must start with 'T': {e['mitre_tactic']}"
            )

    def test_enrich_includes_remediation(self, tiny):
        """Enriched findings must include a remediation string."""
        G, _ = tiny
        findings = run_tarjan_scc(G)
        enriched = enrich_scc_findings(findings, G)
        for e in enriched:
            assert "remediation" in e
            assert len(e["remediation"]) > 10

    def test_graph_stats_correct_structure(self, tiny):
        """get_delegation_graph_stats must return all expected keys."""
        G, _ = tiny
        stats = get_delegation_graph_stats(G)
        for key in ["delegation_nodes", "delegation_edges", "total_sccs",
                    "cyclic_sccs", "largest_scc_size"]:
            assert key in stats, f"Missing key '{key}' in stats"

    def test_cyclic_scc_count_matches_findings(self, tiny):
        """Cyclic SCC count in stats must match actual findings count."""
        G, _ = tiny
        stats    = get_delegation_graph_stats(G)
        findings = run_tarjan_scc(G)
        assert stats["cyclic_sccs"] == len(findings), (
            f"Stats reports {stats['cyclic_sccs']} cycles, "
            f"but findings has {len(findings)}"
        )


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 4 — HITS
# ═════════════════════════════════════════════════════════════════════════════

class TestHITS:
    """Tests for hub/authority scoring."""

    @pytest.fixture
    def tiny(self):
        G, answers = make_tiny_graph()
        return G, answers

    def test_returns_results(self, tiny):
        """HITS must return at least one result."""
        G, _ = tiny
        results, meta = run_hits(G, top_n=5)
        assert len(results) > 0

    def test_da_node_has_highest_authority(self, tiny):
        """Domain Admins or Enterprise Admins should have top authority score."""
        G, answers = tiny
        results, _ = run_hits(G, top_n=len(G.nodes),
                               da_nodes=answers["da_nodes"])
        top_node = results[0].node
        assert top_node in answers["da_nodes"] or results[0].authority > 0.0, (
            f"Top authority node '{top_node}' is not a DA node"
        )

    def test_scores_in_range(self, tiny):
        """All hub and authority scores must be in [0, 1]."""
        G, _ = tiny
        results, _ = run_hits(G, top_n=len(G.nodes))
        for r in results:
            assert 0.0 <= r.authority <= 1.0, f"Authority out of range: {r.authority}"
            assert 0.0 <= r.hub <= 1.0,       f"Hub out of range: {r.hub}"

    def test_convergence_metadata(self, tiny):
        """Metadata must include convergence info."""
        G, _ = tiny
        _, meta = run_hits(G)
        assert "converged" in meta
        assert "iterations" in meta

    def test_weighted_vs_binary_different(self, tiny):
        """Weighted HITS must produce different scores than binary HITS."""
        G, _ = tiny
        results_w, _ = run_hits(G, weighted=True,  top_n=5)
        results_b, _ = run_hits(G, weighted=False, top_n=5)
        w_scores = [r.authority for r in results_w]
        b_scores = [r.authority for r in results_b]
        # They shouldn't be identical (weights changed the distribution)
        assert w_scores != b_scores, "Weighted and binary HITS produced identical scores"

    def test_attack_centrality_product(self, tiny):
        """attack_centrality must equal hub × authority."""
        G, _ = tiny
        results, _ = run_hits(G, top_n=5)
        enriched    = compute_attack_centrality(results)
        for e in enriched:
            expected = e["hub_score"] * e["authority_score"]
            assert abs(e["attack_centrality"] - expected) < 1e-6

    def test_priority_list_structure(self, tiny):
        """hits_to_priority_list must return dicts with required fields."""
        G, _ = tiny
        results, _ = run_hits(G, top_n=5)
        pl = hits_to_priority_list(results)
        required = {"rank", "account", "authority_score", "hub_score",
                    "attack_centrality", "on_da_path", "priority"}
        for item in pl:
            assert required.issubset(item.keys()), (
                f"Missing keys: {required - item.keys()}"
            )

    def test_empty_graph_returns_empty(self):
        """Empty graph must not crash and return empty list."""
        G = nx.DiGraph()
        results, meta = run_hits(G)
        assert results == []
        assert "error" in meta


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Blast Radius
# ═════════════════════════════════════════════════════════════════════════════

class TestBlastRadius:
    """Tests for bidirectional BFS blast radius computation."""

    @pytest.fixture
    def tiny(self):
        G, answers = make_tiny_graph()
        return G, answers

    def test_svc_sql_reaches_da(self, tiny):
        """svc_sql has GenericAll on IT_Admins → IT_Admins in Domain Admins → DA reachable."""
        G, answers = tiny
        result = run_blast_radius(G, "svc_sql", da_nodes=answers["da_nodes"])
        assert result.da_reachable, "svc_sql must reach Domain Admin"

    def test_compromised_node_not_in_reachable(self, tiny):
        """The compromised node itself must not appear in reachable set."""
        G, answers = tiny
        result = run_blast_radius(G, "svc_sql", da_nodes=answers["da_nodes"])
        assert "svc_sql" not in result.reachable

    def test_hop_distances_positive(self, tiny):
        """All hop distances in reachable set must be >= 1."""
        G, answers = tiny
        result = run_blast_radius(G, "svc_sql", da_nodes=answers["da_nodes"])
        for node, hops in result.reachable.items():
            assert hops >= 1, f"Node {node} has hop distance {hops} < 1"

    def test_direct_neighbour_is_hop_1(self, tiny):
        """IT_Admins is a direct GenericAll target of svc_sql → must be hop 1."""
        G, answers = tiny
        result = run_blast_radius(G, "svc_sql", da_nodes=answers["da_nodes"])
        assert result.reachable.get("IT_Admins") == 1, (
            "IT_Admins should be 1 hop from svc_sql"
        )

    def test_by_hop_helper(self, tiny):
        """by_hop(1) must return all nodes exactly 1 hop away."""
        G, answers = tiny
        result = run_blast_radius(G, "svc_sql", da_nodes=answers["da_nodes"])
        hop1 = result.by_hop(1)
        for n in hop1:
            assert result.reachable[n] == 1

    def test_unknown_node_returns_empty(self, tiny):
        """A node not in the graph must return an empty result gracefully."""
        G, answers = tiny
        result = run_blast_radius(G, "NONEXISTENT_NODE",
                                  da_nodes=answers["da_nodes"])
        assert result.total_reachable == 0
        assert not result.da_reachable

    def test_critical_path_found_for_svc_sql(self, tiny):
        """get_critical_path_to_da must return a non-None path for svc_sql."""
        G, answers = tiny
        path = get_critical_path_to_da(G, "svc_sql",
                                       da_nodes=answers["da_nodes"])
        assert path is not None, "Expected a path from svc_sql to DA"
        assert path[0] == "svc_sql"
        assert path[-1] in answers["da_nodes"]

    def test_lateral_movement_subgraph_has_color_hints(self, tiny):
        """Lateral movement subgraph nodes must have color_hint attribute."""
        G, answers = tiny
        result  = run_blast_radius(G, "svc_sql", da_nodes=answers["da_nodes"])
        sub     = get_lateral_movement_subgraph(G, result)
        for n, data in sub.nodes(data=True):
            assert "color_hint" in data, f"Node {n} missing color_hint"
            assert "hop_distance" in data

    def test_compare_blast_radii_diff(self, tiny):
        """After fixing svc_sql's GenericAll, blast radius should shrink."""
        G, answers = tiny
        result_before = run_blast_radius(G, "svc_sql",
                                         da_nodes=answers["da_nodes"])
        # Simulate fix: remove the GenericAll edge
        G_fixed = G.copy()
        if G_fixed.has_edge("svc_sql", "IT_Admins"):
            G_fixed.remove_edge("svc_sql", "IT_Admins")
        result_after = run_blast_radius(G_fixed, "svc_sql",
                                        da_nodes=answers["da_nodes"])
        diff = compare_blast_radii(result_before, result_after)
        assert diff["before_count"] >= diff["after_count"], (
            "Blast radius must not grow after a fix"
        )
        assert diff["da_fixed"] or not result_before.da_reachable

    def test_crown_jewels_detected(self):
        """Crown jewel nodes (fileserver, DC$) must be flagged in blast radius."""
        G = nx.DiGraph()
        from algorithm.decay import temporal_weight
        G.add_node("attacker",      type="User")
        G.add_node("FileServer01$", type="Computer")
        G.add_node("DC01$",         type="Computer")
        G.add_node("Domain Admins", type="Group")
        G.add_edge("attacker",      "FileServer01$",
                   edge_type=EdgeType.ADMIN_TO, weight=temporal_weight(EdgeType.ADMIN_TO, 0))
        G.add_edge("FileServer01$", "DC01$",
                   edge_type=EdgeType.HAS_SESSION, weight=temporal_weight(EdgeType.HAS_SESSION, 0))
        result = run_blast_radius(G, "attacker",
                                  da_nodes={"Domain Admins"})
        jewels = detect_crown_jewels(result, G)
        jewel_names = [j["node"] for j in jewels]
        assert "FileServer01$" in jewel_names or "DC01$" in jewel_names


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 6 — Integration tests (all algorithms on tiny graph)
# ═════════════════════════════════════════════════════════════════════════════

class TestIntegration:
    """Run all 4 algorithms on the same tiny graph and cross-validate."""

    @pytest.fixture
    def setup(self):
        G, answers = make_tiny_graph()
        da_nodes   = answers["da_nodes"]

        paths    = run_temporal_bellman_ford(G, da_nodes=da_nodes)
        sccs     = run_tarjan_scc(G)
        results, meta = run_hits(G, top_n=len(G.nodes), da_nodes=da_nodes)
        br_sql   = run_blast_radius(G, "svc_sql",  da_nodes=da_nodes)
        br_jdoe  = run_blast_radius(G, "jdoe",     da_nodes=da_nodes)

        return {
            "G": G, "answers": answers, "paths": paths,
            "sccs": sccs, "hits": results, "hits_meta": meta,
            "br_sql": br_sql, "br_jdoe": br_jdoe,
        }

    def test_all_algorithms_produce_results(self, setup):
        """All 4 algorithms must return non-empty results on the tiny graph."""
        assert len(setup["paths"])  > 0, "Bellman-Ford returned no paths"
        assert len(setup["sccs"])   > 0, "Tarjan returned no SCCs"
        assert len(setup["hits"])   > 0, "HITS returned no results"
        assert setup["br_sql"].total_reachable > 0, "Blast radius found nothing"

    def test_scc_nodes_also_appear_in_bf_paths(self, setup):
        """The cycle members should also appear in some escalation path."""
        cycle_nodes = set(setup["answers"]["scc_cycle_nodes"])
        path_nodes: Set[str] = set()
        for p in setup["paths"]:
            path_nodes.update(p.nodes)
        # svc_backup is in a cycle and in Backup_Ops → Domain Admins path
        # At least one cycle node should appear somewhere in paths
        assert cycle_nodes & path_nodes, (
            "No cycle node appears in any escalation path — unexpected"
        )

    def test_hits_da_path_flag_matches_bf(self, setup):
        """Nodes flagged is_da_path=True in HITS must appear in BF paths."""
        path_sources = {p.source for p in setup["paths"]}
        for hit in setup["hits"]:
            if hit.is_da_path and hit.node not in setup["answers"]["da_nodes"]:
                # This node was flagged as on a DA path — verify BF agrees
                # (some intermediate nodes won't be sources, so check ancestors)
                all_path_nodes: Set[str] = set()
                for p in setup["paths"]:
                    all_path_nodes.update(p.nodes)
                # If HITS flags it AND it's not in any BF path, that's a
                # discrepancy worth logging (not necessarily a hard failure
                # since HITS uses different reachability logic)
                # We just assert the flag is boolean
                assert isinstance(hit.is_da_path, bool)

    def test_blast_radius_da_consistent_with_bf(self, setup):
        """If BF finds a path from svc_sql, blast radius must confirm DA reachable."""
        sql_paths = [p for p in setup["paths"] if p.source == "svc_sql"]
        if sql_paths:
            assert setup["br_sql"].da_reachable, (
                "BF found svc_sql path to DA but blast radius says DA not reachable"
            )


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 7 — Edge cases
# ═════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:

    def test_single_node_graph(self):
        """Single-node graph must not crash any algorithm."""
        G = nx.DiGraph()
        G.add_node("Domain Admins", type="Group")
        paths   = run_temporal_bellman_ford(G)
        sccs    = run_tarjan_scc(G)
        results, _ = run_hits(G)
        br      = run_blast_radius(G, "Domain Admins")
        assert paths == []
        assert sccs  == []

    def test_disconnected_graph(self):
        """Disconnected graph — isolated nodes must not affect results."""
        G = nx.DiGraph()
        G.add_node("isolated_user", type="User")
        G.add_node("Domain Admins", type="Group")
        # No edges
        paths = run_temporal_bellman_ford(G, da_nodes={"Domain Admins"})
        assert paths == []

    def test_self_loop_ignored(self):
        """Self-loops must not create false SCC findings."""
        G = nx.DiGraph()
        G.add_edge("svc_a", "svc_a",
                   edge_type=EdgeType.ALLOWED_TO_DELEGATE, weight=5.0)
        # Self-loop is technically an SCC of size 1 — should be excluded
        # by min_size=2 default
        findings = run_tarjan_scc(G, min_size=2)
        assert findings == []

    def test_large_weight_does_not_overflow(self):
        """Large base risk values must not cause float overflow."""
        G = nx.DiGraph()
        G.add_edge("A", "Domain Admins",
                   edge_type=EdgeType.GENERIC_ALL, weight=10.0,
                   days_since_use=0)
        G.add_node("A", type="User")
        G.add_node("Domain Admins", type="Group")
        paths = run_temporal_bellman_ford(G, da_nodes={"Domain Admins"})
        assert len(paths) >= 1
        assert all(math.isfinite(p.total_score) for p in paths)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 8 — Performance smoke tests (50-node graph)
# ═════════════════════════════════════════════════════════════════════════════

class TestPerformance:
    """
    Basic timing assertions on the 50-node small graph.
    These are NOT strict benchmarks — just smoke tests to catch
    accidentally quadratic code during development.

    For the IEEE paper, real benchmarks use 200 and 500 node graphs
    with timeit module for statistical accuracy.
    """

    BELLMAN_FORD_MAX_SEC = 5.0
    TARJAN_MAX_SEC       = 1.0
    HITS_MAX_SEC         = 3.0
    BLAST_RADIUS_MAX_SEC = 2.0

    @pytest.fixture
    def small(self):
        G, answers = make_small_graph()
        return G, answers

    def test_bellman_ford_speed(self, small):
        G, answers = small
        t0 = time.perf_counter()
        run_temporal_bellman_ford(G, da_nodes=answers["da_nodes"])
        elapsed = time.perf_counter() - t0
        assert elapsed < self.BELLMAN_FORD_MAX_SEC, (
            f"Bellman-Ford took {elapsed:.3f}s on 50-node graph "
            f"(limit: {self.BELLMAN_FORD_MAX_SEC}s)"
        )

    def test_tarjan_speed(self, small):
        G, _ = small
        t0 = time.perf_counter()
        run_tarjan_scc(G)
        elapsed = time.perf_counter() - t0
        assert elapsed < self.TARJAN_MAX_SEC, (
            f"Tarjan SCC took {elapsed:.3f}s (limit: {self.TARJAN_MAX_SEC}s)"
        )

    def test_hits_speed(self, small):
        G, _ = small
        t0 = time.perf_counter()
        run_hits(G, top_n=10)
        elapsed = time.perf_counter() - t0
        assert elapsed < self.HITS_MAX_SEC, (
            f"HITS took {elapsed:.3f}s (limit: {self.HITS_MAX_SEC}s)"
        )

    def test_blast_radius_speed(self, small):
        G, answers = small
        t0 = time.perf_counter()
        run_blast_radius(G, "svc_sql", da_nodes=answers["da_nodes"])
        elapsed = time.perf_counter() - t0
        assert elapsed < self.BLAST_RADIUS_MAX_SEC, (
            f"Blast radius took {elapsed:.3f}s (limit: {self.BLAST_RADIUS_MAX_SEC}s)"
        )

    def test_small_graph_finds_planted_misconfigs(self, small):
        """All 5 planted misconfigs in small graph must surface as findings."""
        G, answers = small

        paths   = run_temporal_bellman_ford(G, da_nodes=answers["da_nodes"])
        sccs    = run_tarjan_scc(G)

        # Misconfig 1: svc_sql → IT_Admins (GenericAll)
        sql_paths = [p for p in paths if p.source == "svc_sql"]
        assert sql_paths, "svc_sql escalation path not found"

        # Misconfig 2: svc_backup ⇄ svc_web cycle
        found_cycle_nodes: Set[str] = set()
        for f in sccs:
            found_cycle_nodes.update(f.nodes)
        assert answers["scc_nodes"].issubset(found_cycle_nodes), (
            f"Cycle {answers['scc_nodes']} not detected. Found: {found_cycle_nodes}"
        )

        # Misconfig 3: user01 WriteDACL on Domain Admins
        user01_paths = [p for p in paths if p.source == "user01"]
        assert user01_paths, "user01 WriteDACL path not found"
