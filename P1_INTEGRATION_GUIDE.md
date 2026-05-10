# P1 Integration Guide (Algorithm → API)

**Target:** Weeks 1–6  
**Handoff:** End of Week 6 for Sync 1

---

## Your Role

You (P1) provide the algorithm engine. P4 takes your outputs and exposes them via FastAPI so the frontend can visualize attack paths and blast radius.

---

## What P4 Needs From You

### 1. `run_blast_radius()` Function

**Current Location:** `algorithm/blast_radius.py` ✓ Already exists  
**Your Task:** Ensure it matches this exact interface.

```python
def run_blast_radius(
    graph: nx.DiGraph,
    compromised_node: str,
    *,
    da_nodes: Optional[Set[str]] = None,
    max_hops: int = 10,
    weight_cutoff: float = 0.0,
) -> BlastRadiusResult:
    """
    Args:
        graph: Active Directory privilege graph
        compromised_node: Node ID to compute reachability from
        da_nodes: Set of Domain Admin node IDs (auto-detected if None)
        max_hops: Maximum hop distance to compute
        weight_cutoff: Ignore edges below this weight (0.0 = all edges)
    
    Returns:
        BlastRadiusResult with reachable nodes by hop distance
    """
    ...
```

**Input Shape (Graph):**
```python
# NetworkX DiGraph with nodes and edges
# Each node should have metadata:
node_data = {
    'type': 'user|group|computer|service',  # node type
    'criticality': float,                    # 0.0-1.0 importance
}

# Each edge should have:
edge_data = {
    'weight': float,  # 0.0-10.0 risk score
}
```

**Output Shape (BlastRadiusResult):**

Your `BlastRadiusResult.to_dict()` must return:

```python
{
    "compromised_node": "str",       # the input node
    "da_reachable": bool,            # True if any DA is reachable
    "da_nodes_hit": ["str"],         # list of DA node IDs hit
    "total_reachable": int,          # count of all reachable nodes
    "max_hops": int,                 # maximum hop distance
    "by_hop": {
        "1": ["node_id_1", ...],     # 1-hop reachable nodes
        "2": ["node_id_2", ...],     # 2-hop reachable nodes
        "3": [...],
    },
    "risk_level": "Critical|High|Medium"
}
```

**P4 Wiring** (in `api/main.py`):

```python
@app.post("/blast-radius/{node}", response_model=BlastRadiusResponse)
def blast_radius_endpoint(node: str):
    from algorithm.blast_radius import run_blast_radius
    # 1. Load graph (from GraphFactory or your store)
    # 2. Call run_blast_radius(graph, compromised_node=node, ...)
    # 3. Return result.to_dict() (already matches response schema)
    ...
```

### 2. `run_temporal_bellman_ford()` Function

**Current Location:** `algorithm/temporal_bellman_ford.py` ✓ Already exists

**Your Task:** Ensure it serializes to the graph format below.

```python
def run_temporal_bellman_ford(
    graph: nx.DiGraph,
    da_nodes: Optional[Set[str]] = None,
    max_hops: int = 10,
    top_k: int = 5,
    min_score_threshold: float = 0.1,
) -> List[EscalationPath]:
    """
    Args:
        graph: AD privilege graph
        da_nodes: Domain Admin node IDs
        max_hops: Maximum path length
        top_k: Return top-K most dangerous paths
        min_score_threshold: Skip paths below this risk score
    
    Returns:
        Sorted list of EscalationPath objects (most dangerous first)
    """
    ...
```

**Output → Serialization:**

P4 needs to convert your output to JSON for the frontend:

```python
# Frontend expects this shape from GET /graph:
{
    "nodes": [
        {
            "id": "node_uuid",
            "type": "user|group|computer|service",
            "label": "DISPLAY_NAME",
            "authorityScore": 0.0-1.0,
            "isDomainAdmin": bool (optional)
        },
        ...
    ],
    "edges": [
        {
            "source": "from_node_id",
            "target": "to_node_id",
            "weight": 0.0-10.0  # risk score
        },
        ...
    ]
}
```

**P4 Wiring** (in `api/main.py`):

```python
@app.get("/graph", response_model=GraphResponse)
def get_graph():
    from algorithm.temporal_bellman_ford import run_temporal_bellman_ford
    from algorithm.graph_factory import GraphFactory
    
    # 1. Load graph
    graph = GraphFactory.load_graph(...)
    
    # 2. Run your algorithm
    paths = run_temporal_bellman_ford(graph, da_nodes=...)
    
    # 3. Serialize graph → nodes/edges
    nodes = [
        {
            "id": n,
            "type": graph.nodes[n].get("type", "unknown"),
            "label": graph.nodes[n].get("name", n),
            "authorityScore": graph.nodes[n].get("criticality", 0.5),
            "isDomainAdmin": _is_da_node(n),
        }
        for n in graph.nodes()
    ]
    
    edges = [
        {
            "source": u,
            "target": v,
            "weight": graph[u][v].get("weight", 1.0),
        }
        for u, v in graph.edges()
    ]
    
    return GraphResponse(nodes=nodes, edges=edges)
```

---

## Data Shapes (Locked Contracts)

### Node Type Values

```python
node_type ∈ {"user", "group", "computer", "service"}

# Examples:
- User account: "user"
- Security group: "group"
- AD computer: "computer"
- Service account: "service"
```

### Edge Weight / Risk Levels

```
weight = 0.0  - 10.0

Interpretation:
  0.0 - 1.0   → Low risk (e.g., basic read permissions)
  1.1 - 3.0   → Medium risk (e.g., group membership)
  3.1 - 6.0   → High risk (e.g., generic write permissions)
  6.1 - 10.0  → Critical risk (e.g., DCSync, admin rights)
```

### Authority / Criticality Score

```
authorityScore = 0.0 - 1.0

Interpretation:
  0.0 - 0.2   → Low (user workstation)
  0.2 - 0.5   → Medium (standard user)
  0.5 - 0.8   → High (service account, admin)
  0.8 - 1.0   → Critical (Domain Admin, Domain Controller)
```

---

## Integration Timeline

### Week 1
- [ ] Review this guide with P4
- [ ] Lock data shapes in `algorithm/models.py`
- [ ] Agree on graph loading / initialization

### Weeks 2–6
- [ ] Implement and test `run_blast_radius()` locally
- [ ] Implement and test `run_temporal_bellman_ford()` locally
- [ ] Ensure `.to_dict()` methods match serialization format
- [ ] Test with mock graphs in `test_algorithms.py`

### Week 6 (Sync 1)
- [ ] Run test suite: `python -m pytest test_algorithms.py -v`
- [ ] Export your functions as public API (no underscore prefix)
- [ ] Verify they can be imported: `from algorithm.blast_radius import run_blast_radius`
- [ ] P4 creates integration branch, wires your functions
- [ ] Joint test: API returns data → Frontend renders correctly

---

## Checklist Before Handing Off

- [ ] `run_blast_radius()` accepts `(graph, compromised_node, da_nodes, max_hops, weight_cutoff)`
- [ ] `run_temporal_bellman_ford()` returns sorted list of `EscalationPath`
- [ ] `.to_dict()` methods on result objects match serialization format
- [ ] All node IDs are string UUIDs (not integers)
- [ ] All weights are floats (0.0–10.0)
- [ ] Authority scores are floats (0.0–1.0)
- [ ] Functions handle edge cases (missing nodes, empty graphs, etc.)
- [ ] No hardcoded test data in production code
- [ ] All imports use `from algorithm import ...` (not relative paths)

---

## Testing Your Output

Before handing off to P4, validate locally:

```python
# Load a test graph
from algorithm.graph_factory import GraphFactory
graph = GraphFactory.load_sample_ad_graph()

# Test blast radius
from algorithm.blast_radius import run_blast_radius
result = run_blast_radius(graph, "user1", max_hops=3)
print(result.to_dict())
# Expected: dict with keys: compromised_node, da_reachable, total_reachable, by_hop, risk_level

# Test temporal bellman ford
from algorithm.temporal_bellman_ford import run_temporal_bellman_ford
paths = run_temporal_bellman_ford(graph, top_k=5)
print([p.to_dict() for p in paths[:2]])
# Expected: list of dicts with keys: source, target, nodes, total_score, hop_count, risk_level
```

---

## FAQ

**Q: What if the graph is empty or node doesn't exist?**  
A: Your function should return gracefully (empty result, not crash). P4 will handle HTTP 404 errors.

**Q: Should I filter by weight?**  
A: P4 may pass `weight_cutoff=0.0` (use all edges). Support the parameter but don't require it.

**Q: How do I know if a node is Domain Admin?**  
A: Check if node type is `"group"` AND label contains "Domain Admin" (case-insensitive). P4 will help with DA node detection.

**Q: What about performance?**  
A: For now, focus on correctness. Mock graphs in tests will be small (<1000 nodes). P4 will benchmark and optimize later.

---

**Contact P4:** See [PHASE_0_1_SETUP.md](../PHASE_0_1_SETUP.md) for integration contact & timeline.
