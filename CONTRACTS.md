# HyperAD JSON Contracts (P1 ↔ P3 ↔ P4)

This document defines the exact JSON schemas that all teams must agree on. Lock these shapes in Week 1 — sync is successful only if these contracts are honored.

---

## Contract 1: Graph Nodes & Edges (P1 → P4)

### Node Shape
```json
{
  "id": "string (unique identifier)",
  "type": "user|group|computer|service",
  "label": "string (display name)",
  "authorityScore": "number (0.0–1.0, importance/risk)",
  "isDomainAdmin": "boolean (optional)"
}
```

### Edge Shape
```json
{
  "source": "string (node id)",
  "target": "string (node id)",
  "weight": "number (0.0–10.0, risk weight)"
}
```

### Graph Response (`GET /graph`)
```json
{
  "nodes": [
    { "id": "user1", "type": "user", "label": "alice", "authorityScore": 0.6 },
    { "id": "da", "type": "group", "label": "Domain Admins", "authorityScore": 1.0, "isDomainAdmin": true }
  ],
  "edges": [
    { "source": "user1", "target": "da", "weight": 8.5 }
  ]
}
```

---

## Contract 2: Findings (P3 → P4)

### Finding Shape
```json
{
  "id": "string (unique finding id)",
  "title": "string (human-readable title)",
  "mitreTactic": "string (e.g., 'T1558.003')",
  "confidence": "number (0.0–1.0 or 0–100, TBD with P3)",
  "severity": "Critical|High|Medium|Low",
  "evidence": "string[] (array of evidence strings)",
  "remediation": "string (how to fix this)"
}
```

### Findings Response (`GET /findings`)
```json
{
  "findings": [
    {
      "id": "f1",
      "title": "Kerberoastable SPN",
      "mitreTactic": "T1558.003",
      "confidence": 0.91,
      "severity": "Critical",
      "evidence": [
        "svc_sql has unconstrained delegation flag",
        "SPN registered for SQL service"
      ],
      "remediation": "Remove SPN or enforce AES encryption"
    }
  ]
}
```

---

## Contract 3: Blast Radius (P1 → P4)

### Response Shape (`POST /blast-radius/{node}`)
```json
{
  "node": "string (the compromised node id)",
  "reachable": {
    "1hop": ["string id 1", "string id 2"],
    "2hop": ["string id 3"],
    "3hop": []
  }
}
```

### Example
```json
{
  "node": "user1",
  "reachable": {
    "1hop": ["svc_sql", "IT_Admins"],
    "2hop": ["dc01", "Domain Admins"],
    "3hop": []
  }
}
```

---

## Contract 4: Counterfactual (P3 → P4)

### Response Shape (`POST /counterfactual/{finding_id}`)
```json
{
  "finding_id": "string",
  "paths_before": "number (count of attack paths before fix)",
  "paths_after": "number (count of attack paths after fix)",
  "delta": "number (paths_after - paths_before, always ≤ 0)"
}
```

### Example
```json
{
  "finding_id": "f1",
  "paths_before": 14,
  "paths_after": 2,
  "delta": -12
}
```

---

## Contract 5: Alert Payload (P3 → P4, for Phase 2 WebSocket)

### Shape (`/ws/alerts`)
```json
{
  "finding_id": "string",
  "timestamp": "string (ISO 8601)",
  "title": "string",
  "severity": "Critical|High|Medium|Low",
  "delta_type": "new|resolved|risk_increased"
}
```

---

## Node Color Mapping (Frontend)

All teams must use this for consistency:

| Type | Color | Hex |
|---|---|---|
| `user` | Blue | `#4A90D9` |
| `group` | Purple | `#7B68EE` |
| `computer` | Grey | `#888888` |
| `service` | Amber | `#F5A623` |
| `domainAdmin` | Red | `#C0392B` (pulsing) |

---

## Severity Color Mapping (Frontend)

| Severity | Color | Hex |
|---|---|---|
| Critical | Red | `#C0392B` |
| High | Orange | `#E07B39` |
| Medium | Yellow | `#C9A84C` |
| Low | Green | `#4A7C59` |

---

## Acceptance Criteria for Sync 1

- [ ] All 4 contracts match exactly (JSON shapes must be identical)
- [ ] P1 delivers `run_blast_radius()` and `run_temporal_bellman_ford()` compatible with these shapes
- [ ] P3 delivers findings with exact mitreTactic and confidence values
- [ ] P4 can parse and render without schema changes
- [ ] CORS middleware allows React ↔ FastAPI communication on ports 3000 ↔ 8000
