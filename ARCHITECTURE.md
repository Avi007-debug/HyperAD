# HyperAD System Architecture

## High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    ACTIVE DIRECTORY                             │
│              (Customer Environment)                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │  AD Graph Parser / Data Ingestion       │
        │  (Converts AD to NetworkX DiGraph)      │
        └─────────────────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        │                                           │
        ▼                                           ▼
    ┌────────────────────┐               ┌──────────────────────┐
    │  P1: ALGORITHMS    │               │   P3: AI AGENT       │
    ├────────────────────┤               ├──────────────────────┤
    │ • blast_radius()   │               │ • get_findings()     │
    │ • temporal_bf()    │               │ • counterfactual()   │
    │ • hits()           │               │ • mitre_mapper()     │
    │ • tarjan_scc()     │               │ • delta_reporter()   │
    └────────────────────┘               └──────────────────────┘
        │                                       │
        │  (Dict/JSON)                          │  (List[Finding])
        │                                       │
        └─────────────────┬─────────────────────┘
                          ▼
            ┌──────────────────────────────┐
            │   P4: FASTAPI BACKEND        │
            ├──────────────────────────────┤
            │ GET /findings                │
            │ GET /graph                   │
            │ POST /blast-radius/{node}    │
            │ POST /counterfactual/{id}    │
            │ + CORS + WebSocket (Phase 2) │
            └──────────────────────────────┘
                   ▲         ▲
         HTTP/JSON │         │ JSON
                   │         │
    ┌──────────────┴────┬────┴─────────────┐
    │                   │                  │
    ▼                   ▼                  ▼
┌─────────────┐   ┌──────────────┐   ┌─────────────┐
│  React Dev  │   │ GraphExplorer│   │FindingsList │
│  Server     │   │ (D3.js)      │   │  (API-driven)
│ :5173       │   │              │   │             │
└─────────────┘   └──────────────┘   └─────────────┘
    │                   │                  │
    └───────────────────┴──────────────────┘
           Browser Tab (localhost:5173)
```

---

## Component Hierarchy

```
App.tsx
├── Header (HyperAD title, Last scan, Run Scan button)
├── Main Layout (flex row)
│   ├── FindingsList
│   │   └── Finding Card (expandable)
│   │       ├── Title + Severity pill
│   │       ├── MITRE badge (clickable)
│   │       └── Evidence + Remediation (expanded)
│   │
│   ├── GraphExplorer (D3.js Force Simulation)
│   │   ├── SVG Canvas
│   │   ├── Nodes (circles, colored by type)
│   │   ├── Edges (lines, weighted)
│   │   ├── Zoom + Pan
│   │   └── Legend
│   │
│   ├── BlastRadius (Overlay, triggered by node click)
│   │   ├── Hop stats (1-hop, 2-hop, 3-hop counts)
│   │   └── Node lists by hop distance
│   │
│   └── NodeDetail (Right sidebar, optional)
│       └── Selected node information
```

---

## API Routes & Responsibility

```
FastAPI (api/main.py)
│
├── GET /health
│   └── Native endpoint (P4)
│
├── GET /findings
│   ├── P3 Integration: calls get_findings()
│   └── Returns: { findings: [...] }
│
├── GET /graph
│   ├── P1 Integration: calls run_temporal_bellman_ford()
│   ├── Serializes: graph → nodes + edges
│   └── Returns: { nodes: [...], edges: [...] }
│
├── POST /blast-radius/{node}
│   ├── P1 Integration: calls run_blast_radius()
│   └── Returns: { node, reachable: { 1hop, 2hop, 3hop } }
│
├── POST /counterfactual/{finding_id}
│   ├── P3 Integration: calls run_counterfactual()
│   └── Returns: { finding_id, paths_before, paths_after, delta }
│
└── (Phase 2) WebSocket /ws/alerts
    ├── P3 Integration: calls delta_reporter.alert_stream()
    └── Streams: alerts in real-time
```

---

## Data Flow Examples

### Example 1: User Views Findings

```
1. Browser loads app → React calls GET /findings
2. FastAPI routes to api/main.py:get_findings()
3. Mock returns: [ { id: "f1", title: "...", ... } ]
4. Frontend renders FindingsList with 4 findings
5. User clicks card → expands evidence + remediation
```

### Example 2: User Clicks a Node

```
1. GraphExplorer (D3) detects mouse click on node
2. React calls POST /blast-radius/{node_id}
3. FastAPI routes to api/main.py:blast_radius_endpoint()
4. API calls (Week 6) P1's run_blast_radius(graph, node_id)
5. P1 returns: { compromised_node, reachable: { 1hop, 2hop, 3hop } }
6. API returns JSON response
7. React updates BlastRadius overlay with results
8. Frontend highlights nodes by hop distance (red → amber → yellow)
```

### Example 3: User Checks Remediation Impact

```
1. Frontend shows "What if we fix this?" button (Phase 2)
2. User clicks → calls POST /counterfactual/f1
3. FastAPI routes to api/main.py:counterfactual()
4. API calls (Week 6) P3's run_counterfactual("f1")
5. P3 logic:
   - Load graph
   - Identify edge for finding f1
   - Create copy, remove edge
   - Re-run P1's algorithms on both versions
   - Count paths before & after
   - Return: { paths_before: 14, paths_after: 2, delta: -12 }
6. Frontend displays: "Fixing this could eliminate 12 attack paths"
```

---

## Network Topology

```
┌─────────────────────────────────────────────────────┐
│            Developer Laptop                         │
│                                                     │
│  ┌──────────────┐            ┌──────────────┐      │
│  │ Frontend Dev │  HTTP/JSON │ FastAPI Svr  │      │
│  │ http://      │◄──────────►│ http://      │      │
│  │ :5173        │            │ :8000        │      │
│  └──────────────┘            └──────────────┘      │
│       │                             ▲               │
│       │ Browser                     │ Python        │
│       ▼                             ▼               │
│    React                      P1 + P3 + Utils      │
│    (Vite dev)                 (Algorithms)         │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Note:** In production, both frontend and backend would be deployed separately or to containers. For development, they both run locally.

---

## Database / State Management

**Current (MVP):**
- ✅ All data is in-memory (no persistence)
- ✅ Frontend state managed by React hooks
- ✅ Backend state: None (stateless API)
- ✅ Mock data hardcoded in api/main.py

**Phase 2:**
- 🔜 Add PostgreSQL for findings history
- 🔜 Store graph snapshots over time
- 🔜 Track when findings are resolved
- 🔜 Audit log for all changes

---

## Security Considerations (Phase 2+)

- [ ] Add authentication (JWT tokens)
- [ ] Add authorization (RBAC)
- [ ] Sanitize all inputs
- [ ] Rate limiting on API routes
- [ ] HTTPS for production
- [ ] Database encryption at rest
- [ ] Audit logging

---

## Performance Notes

- **Graph rendering:** D3.js force simulation handles ~5,000 nodes
- **API response time:** <100ms for mock data, <1s for real algorithms
- **Frontend load:** ~2-3s for initial bundle (Vite optimized)
- **Scalability:** With caching, can handle 100+ concurrent users

---

**Diagram Version:** 1.0  
**Last Updated:** May 10, 2026
