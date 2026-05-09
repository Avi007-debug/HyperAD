# P3 AI Agent Integration Handoff

## Use these imports

```python
from algorithm.temporal_bellman_ford import run_temporal_bellman_ford, summarise_paths
from algorithm.tarjan_scc import run_tarjan_scc, enrich_scc_findings
from algorithm.hits_scorer import run_hits, hits_to_priority_list
from algorithm.blast_radius import run_blast_radius, compare_blast_radii
```

## Recommended tool wrappers (LangChain)
- `get_paths()` → `run_temporal_bellman_ford`
- `get_findings()` → combined output:
  - bellman-ford summary
  - enriched SCC findings
  - HITS priority list
- `blast_radius(node)` → `run_blast_radius`

## Output shaping
- Convert dataclass outputs via `.to_dict()` before returning to LLM.
- For executive summary use `summarise_paths(paths)`.

## Sync1 acceptance checks
1. Agent can call all 4 tools without import errors.
2. Agent returns at least one DA-path finding on tiny graph.
3. SCC findings include MITRE tactic and remediation fields.
