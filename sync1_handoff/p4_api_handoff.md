# P4 FastAPI/UI Integration Handoff

## Minimal API route mapping

- `GET /findings`
  - Internally calls:
    - `run_temporal_bellman_ford`
    - `run_tarjan_scc` + `enrich_scc_findings`
    - `run_hits`
- `POST /blast-radius/{node}`
  - Calls `run_blast_radius`
- `POST /counterfactual/{finding_id}`
  - Build graph copy, remove edge, compare with `compare_blast_radii`

## Serialization note
- Convert dataclass objects with `.to_dict()`.
- For NetworkX subgraphs, serialize nodes/edges explicitly for frontend.

## Sync1 acceptance checks
1. API imports from `algorithm.*` only (no `utils.*`/`algorithms.*`).
2. `/blast-radius/{node}` returns reachable nodes and DA reachability.
3. GraphExplorer + Findings panel can render using returned JSON.
