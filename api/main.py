"""
HyperAD FastAPI Backend — Phase 1 Skeleton
===========================================

This API bridges React frontend (port 3000) with Python algorithms (P1)
and AI agent (P3). It starts with mock data, then integrates real functions
at Sync 1 (end of Week 6).

Routes:
  - GET /findings       → Security findings list (P3 integration point)
  - GET /graph          → AD graph nodes + edges (P1 integration point)
  - POST /blast-radius/{node}     → Blast radius for compromised node (P1)
  - POST /counterfactual/{finding_id}  → "What if we fix this?" (P3)

CORS enabled for React on localhost:3000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import logging

# ──────────────────────────────────────────────────────────────────────────
# Logging setup
# ──────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────
# Pydantic Models (Request/Response DTOs)
# ──────────────────────────────────────────────────────────────────────────

class GraphNode(BaseModel):
    """AD object node in the privilege graph."""
    id: str
    type: str  # user|group|computer|service
    label: str
    authorityScore: float
    isDomainAdmin: Optional[bool] = False


class GraphEdge(BaseModel):
    """Privilege escalation edge between nodes."""
    source: str
    target: str
    weight: float


class GraphResponse(BaseModel):
    """Full graph response."""
    nodes: List[GraphNode]
    edges: List[GraphEdge]


class Finding(BaseModel):
    """Security finding / vulnerability."""
    id: str
    title: str
    mitreTactic: str  # e.g., "T1558.003"
    confidence: float  # 0.0–1.0
    severity: str  # Critical|High|Medium|Low
    evidence: List[str]
    remediation: str


class FindingsResponse(BaseModel):
    """Findings list response."""
    findings: List[Finding]


class BlastRadiusResponse(BaseModel):
    """Reachability from a compromised node."""
    node: str
    reachable: Dict[str, List[str]]  # {"1hop": [...], "2hop": [...], "3hop": [...]}


class CounterfactualResponse(BaseModel):
    """Before/after path count when a finding is remediated."""
    finding_id: str
    paths_before: int
    paths_after: int
    delta: int


# ──────────────────────────────────────────────────────────────────────────
# Mock Data (Week 1–6: Replace with real P1/P3 logic at Sync 1)
# ──────────────────────────────────────────────────────────────────────────

MOCK_FINDINGS = [
    {
        "id": "f1",
        "title": "Kerberoastable SPN on Critical Service Account",
        "mitreTactic": "T1558.003",
        "confidence": 0.94,
        "severity": "Critical",
        "evidence": [
            "Service account SVC_DB_PROD has TRUSTED_FOR_DELEGATION flag",
            "Account has SPN registered for MSSQL service",
            "No selective authentication constraints configured",
        ],
        "remediation": "Remove SPN from service account or enforce AES encryption on Kerberos tickets",
    },
    {
        "id": "f2",
        "title": "Generic All Rights Path to Domain Admin",
        "mitreTactic": "T1078.002",
        "confidence": 0.87,
        "severity": "Critical",
        "evidence": [
            "User JSMITH has GenericAll on group IT_ADMINS",
            "IT_ADMINS nested in DOMAIN_ADMINS",
            "2-hop escalation path detected via group membership",
        ],
        "remediation": "Remove GenericAll permissions from JSMITH or remove IT_ADMINS from Domain Admins",
    },
    {
        "id": "f3",
        "title": "DCSync Rights on Standard User Account",
        "mitreTactic": "T1003.006",
        "confidence": 0.91,
        "severity": "High",
        "evidence": [
            "User BACKUP_OPERATOR has DS-Replication-Get-Changes-All",
            "Account is active, last logon 2 days ago",
            "No MFA enrolled on account",
        ],
        "remediation": "Remove replication rights or enforce MFA on BACKUP_OPERATOR",
    },
    {
        "id": "f4",
        "title": "Weak Kerberos Encryption on Computer Object",
        "mitreTactic": "T1558.003",
        "confidence": 0.76,
        "severity": "Medium",
        "evidence": [
            "Computer WKS-042 supports RC4_HMAC only",
            "AES encryption not configured",
            "Legacy protocol enabled",
        ],
        "remediation": "Update WKS-042 to support AES-256 Kerberos encryption",
    },
]

MOCK_GRAPH_NODES = [
    {"id": "user1", "type": "user", "label": "JSMITH", "authorityScore": 0.6},
    {"id": "user2", "type": "user", "label": "BACKUP_OPERATOR", "authorityScore": 0.7},
    {"id": "svc_sql", "type": "service", "label": "SVC_DB_PROD", "authorityScore": 0.75},
    {"id": "it_admins", "type": "group", "label": "IT_ADMINS", "authorityScore": 0.85},
    {"id": "da", "type": "group", "label": "Domain Admins", "authorityScore": 1.0, "isDomainAdmin": True},
    {"id": "dc01", "type": "computer", "label": "DC01", "authorityScore": 0.95, "isDomainAdmin": True},
    {"id": "wks042", "type": "computer", "label": "WKS-042", "authorityScore": 0.4},
]

MOCK_GRAPH_EDGES = [
    {"source": "user1", "target": "it_admins", "weight": 8.5},
    {"source": "it_admins", "target": "da", "weight": 9.2},
    {"source": "svc_sql", "target": "da", "weight": 9.4},
    {"source": "user2", "target": "da", "weight": 7.8},
    {"source": "wks042", "target": "it_admins", "weight": 5.2},
    {"source": "user1", "target": "svc_sql", "weight": 6.0},
]

MOCK_BLAST_RADII = {
    "user1": {
        "node": "user1",
        "reachable": {
            "1hop": ["it_admins", "svc_sql"],
            "2hop": ["da", "dc01"],
            "3hop": [],
        },
    },
    "user2": {
        "node": "user2",
        "reachable": {
            "1hop": ["da", "dc01"],
            "2hop": [],
            "3hop": [],
        },
    },
    "svc_sql": {
        "node": "svc_sql",
        "reachable": {
            "1hop": ["da", "dc01"],
            "2hop": [],
            "3hop": [],
        },
    },
    "it_admins": {
        "node": "it_admins",
        "reachable": {
            "1hop": ["da", "dc01"],
            "2hop": [],
            "3hop": [],
        },
    },
    "da": {
        "node": "da",
        "reachable": {
            "1hop": [],
            "2hop": [],
            "3hop": [],
        },
    },
    "dc01": {
        "node": "dc01",
        "reachable": {
            "1hop": [],
            "2hop": [],
            "3hop": [],
        },
    },
    "wks042": {
        "node": "wks042",
        "reachable": {
            "1hop": ["it_admins"],
            "2hop": ["da", "dc01"],
            "3hop": [],
        },
    },
}

# ──────────────────────────────────────────────────────────────────────────
# FastAPI Application
# ──────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="HyperAD API",
    description="AD privilege graph analysis backend",
    version="0.1.0",
)

# ──────────────────────────────────────────────────────────────────────────
# CORS Middleware (Critical for React ↔ FastAPI communication)
# ──────────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",      # React dev server
        "http://localhost:5173",      # Vite dev server (alternative)
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────────────────


@app.get("/health")
def health_check():
    """Liveness probe."""
    return {"status": "ok"}


@app.get("/findings", response_model=FindingsResponse)
def get_findings():
    """
    Returns list of security findings.
    
    **At Sync 1 (Week 6):** Replace with:
    ```python
    from ai_agent.agent_core import get_findings as get_real_findings
    findings = get_real_findings()
    return FindingsResponse(findings=findings)
    ```
    """
    logger.info("GET /findings — returning %d findings", len(MOCK_FINDINGS))
    return FindingsResponse(findings=MOCK_FINDINGS)


@app.get("/graph", response_model=GraphResponse)
def get_graph():
    """
    Returns full AD privilege graph (nodes + edges).
    
    **At Sync 1 (Week 6):** Replace with:
    ```python
    from algorithm.temporal_bellman_ford import run_temporal_bellman_ford
    # Get real graph from P1's algorithm
    paths = run_temporal_bellman_ford(graph, da_nodes=...)
    # Serialize to nodes/edges format
    ```
    """
    logger.info("GET /graph — returning graph with %d nodes, %d edges",
                len(MOCK_GRAPH_NODES), len(MOCK_GRAPH_EDGES))
    return GraphResponse(
        nodes=MOCK_GRAPH_NODES,
        edges=MOCK_GRAPH_EDGES,
    )


@app.post("/blast-radius/{node}", response_model=BlastRadiusResponse)
def blast_radius_endpoint(node: str):
    """
    Compute blast radius (reachability) from a compromised node.
    
    Returns nodes reachable at each hop distance (1, 2, 3, ...).
    
    **At Sync 1 (Week 6):** Replace with:
    ```python
    from algorithm.blast_radius import run_blast_radius
    # Load graph and DA nodes
    result = run_blast_radius(graph, compromised_node=node, da_nodes=...)
    return BlastRadiusResponse(
        node=node,
        reachable=result.by_hop_dict()  # or whatever P1 exposes
    )
    ```
    """
    if node not in MOCK_BLAST_RADII:
        logger.warning("POST /blast-radius/%s — node not found", node)
        raise HTTPException(status_code=404, detail=f"Node '{node}' not found")
    
    logger.info("POST /blast-radius/%s — computing blast radius", node)
    return MOCK_BLAST_RADII[node]


@app.post("/counterfactual/{finding_id}", response_model=CounterfactualResponse)
def counterfactual_endpoint(finding_id: str):
    """
    Simulate removing a finding's vulnerability and recompute attack paths.
    
    Returns: before/after path counts and delta.
    
    **At Sync 1 (Week 6):** Replace with:
    ```python
    from ai_agent.counterfactual import run_counterfactual
    result = run_counterfactual(finding_id)
    return CounterfactualResponse(
        finding_id=finding_id,
        paths_before=result.paths_before,
        paths_after=result.paths_after,
        delta=result.delta
    )
    ```
    """
    # Mock: always return a reasonable counterfactual result
    mock_results = {
        "f1": {"before": 14, "after": 2, "delta": -12},
        "f2": {"before": 18, "after": 5, "delta": -13},
        "f3": {"before": 12, "after": 7, "delta": -5},
        "f4": {"before": 8, "after": 6, "delta": -2},
    }
    
    if finding_id not in mock_results:
        logger.warning("POST /counterfactual/%s — finding not found", finding_id)
        raise HTTPException(status_code=404, detail=f"Finding '{finding_id}' not found")
    
    result = mock_results[finding_id]
    logger.info("POST /counterfactual/%s — paths: %d → %d (Δ %d)",
                finding_id, result["before"], result["after"], result["delta"])
    
    return CounterfactualResponse(
        finding_id=finding_id,
        paths_before=result["before"],
        paths_after=result["after"],
        delta=result["delta"],
    )


# ──────────────────────────────────────────────────────────────────────────
# Integration Hooks (To be populated at Sync 1)
# ──────────────────────────────────────────────────────────────────────────

"""
### P1 Integration (Algorithm Team)

Import after Sync 1:
```python
from algorithm.blast_radius import run_blast_radius
from algorithm.temporal_bellman_ford import run_temporal_bellman_ford
from algorithm.graph_factory import GraphFactory

# Wire into routes:
#   1. get_graph() → calls run_temporal_bellman_ford()
#   2. blast_radius_endpoint() → calls run_blast_radius()
```

### P3 Integration (AI Agent & Reporting Team)

Import after Sync 1:
```python
from ai_agent.agent_core import get_findings
from ai_agent.counterfactual import run_counterfactual

# Wire into routes:
#   1. get_findings() → calls get_findings()
#   2. counterfactual_endpoint() → calls run_counterfactual()
```

### Phase 2 (WebSocket for Real-Time Alerts)

After Sync 1, add WebSocket endpoint:
```python
from fastapi import WebSocket

@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    await websocket.accept()
    # Stream alert events from P3's delta_reporter
    # Each alert: { "finding_id", "timestamp", "title", "severity", "delta_type" }
```
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
