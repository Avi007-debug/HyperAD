# HyperAD Phase 0 & Phase 1 Setup Guide

**Date:** May 10, 2026  
**Scope:** Complete environment setup and Phase 1 deliverables  
**Status:** ✅ Ready for testing

---

## Phase 0 — Environment Verification

### System Requirements

| Component | Version | Status |
|---|---|---|
| Node.js | v22.19.0 ✅ | ✓ Verified |
| Python | 3.14.0 ✓ | ✓ Verified |
| npm | 10.5.2+ ✓ | ✓ Verified |

### Frontend Dependencies Installed

```bash
✅ d3 — D3.js force graph visualization
✅ axios — HTTP client for API calls
✅ react — UI framework (v18.3.1)
✅ react-dom — React DOM renderer
✅ recharts — Chart components (already present)
```

All other shadcn/ui components pre-installed from initial scaffold.

### Backend Environment

**Python packages to install before running API:**

```bash
cd api
pip install -r requirements.txt
# installs: fastapi, uvicorn, pydantic, python-multipart, networkx, numpy
```

---

## Phase 1 Deliverables

### 1. ✅ FastAPI Skeleton (`api/main.py`)

**Location:** [api/main.py](api/main.py)

**Routes Implemented:**

| Route | Method | Purpose | Integrates |
|---|---|---|---|
| `/health` | GET | Liveness probe | Native ✅ |
| `/findings` | GET | Returns security findings | P3 (Week 6) |
| `/graph` | GET | AD privilege graph | P1 (Week 6) |
| `/blast-radius/{node}` | POST | Reachability from node | P1 (Week 6) |
| `/counterfactual/{finding_id}` | POST | Before/after path count | P3 (Week 6) |

**CORS Configuration:**
- ✅ Allows `http://localhost:3000` (React dev)
- ✅ Allows `http://localhost:5173` (Vite alt)
- ✅ Supports all HTTP methods and headers

**Mock Data:** Full realistic dataset included for testing

### 2. ✅ GraphExplorer Component (`frontend/src/app/components/GraphExplorer.tsx`)

**Features:**
- ✅ D3.js force simulation (not canvas)
- ✅ Dynamic node sizing by authority score
- ✅ Color-coded nodes (user/group/computer/service/DA)
- ✅ Edge width scales with risk weight
- ✅ Zoom + pan controls
- ✅ Click node → triggers `/blast-radius/{node}`
- ✅ Blast radius highlighting (1/2/3-hop with color gradient)
- ✅ Interactive legend
- ✅ API-driven (fetches from `GET /graph`)

**Colors:**
```
user     → #4A90D9 (blue)
group    → #7B68EE (purple)
computer → #888888 (grey)
service  → #F5A623 (amber)
DA       → #C0392B (red, pulsing)
```

### 3. ✅ FindingsList Component (`frontend/src/app/components/FindingsList.tsx`)

**Features:**
- ✅ API-driven (fetches from `GET /findings`)
- ✅ Sorted by confidence score (descending by default)
- ✅ Expandable cards showing evidence + remediation
- ✅ Severity pill (Critical/High/Medium/Low)
- ✅ MITRE tactic badge (clickable → attack.mitre.org)
- ✅ Confidence percentage display
- ✅ Color-coded severity borders
- ✅ Loading + error states

**Sort Options:**
- Risk Score ↓ (default)
- Risk Score ↑

### 4. ✅ BlastRadius Component (`frontend/src/app/components/BlastRadius.tsx`)

**Features:**
- ✅ Displays reachability from selected node
- ✅ Hop-by-hop breakdown (1-hop, 2-hop, 3-hop)
- ✅ Total reachable count
- ✅ Dismissible modal
- ✅ Color-coded hop levels
- ✅ Triggered by GraphExplorer node click

### 5. ✅ JSON Contracts (`CONTRACTS.md`)

**Defined & locked:**
- ✅ Graph node shape
- ✅ Graph edge shape
- ✅ Findings shape
- ✅ Blast radius shape
- ✅ Counterfactual shape
- ✅ Alert payload shape (Phase 2)
- ✅ Color mappings (node types + severity)

---

## Quick Start

### Start Frontend (React + Vite)

```bash
cd frontend
npm run dev
# Runs on http://localhost:5173
```

### Start Backend (FastAPI)

```bash
cd api
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
# Runs on http://localhost:8000
# Auto-reload on file changes
```

### Test Health Check

```bash
curl http://localhost:8000/health
# Expected response: { "status": "ok" }
```

### Test Mock Endpoints

```bash
# Findings
curl http://localhost:8000/findings

# Graph
curl http://localhost:8000/graph

# Blast radius
curl -X POST http://localhost:8000/blast-radius/user1

# Counterfactual
curl -X POST http://localhost:8000/counterfactual/f1
```

---

## API Response Examples

### GET /findings

```json
{
  "findings": [
    {
      "id": "f1",
      "title": "Kerberoastable SPN on Critical Service Account",
      "mitreTactic": "T1558.003",
      "confidence": 0.94,
      "severity": "Critical",
      "evidence": [
        "Service account SVC_DB_PROD has TRUSTED_FOR_DELEGATION flag",
        "Account has SPN registered for MSSQL service",
        "No selective authentication constraints configured"
      ],
      "remediation": "Remove SPN from service account or enforce AES encryption on Kerberos tickets"
    }
  ]
}
```

### GET /graph

```json
{
  "nodes": [
    {
      "id": "user1",
      "type": "user",
      "label": "JSMITH",
      "authorityScore": 0.6
    },
    {
      "id": "da",
      "type": "group",
      "label": "Domain Admins",
      "authorityScore": 1.0,
      "isDomainAdmin": true
    }
  ],
  "edges": [
    {
      "source": "user1",
      "target": "da",
      "weight": 8.5
    }
  ]
}
```

### POST /blast-radius/{node}

```json
{
  "node": "user1",
  "reachable": {
    "1hop": ["it_admins", "svc_sql"],
    "2hop": ["da", "dc01"],
    "3hop": []
  }
}
```

### POST /counterfactual/{finding_id}

```json
{
  "finding_id": "f1",
  "paths_before": 14,
  "paths_after": 2,
  "delta": -12
}
```

---

## Phase 1 Sync 1 Checklist (End of Week 6)

### Frontend Components
- [x] GraphExplorer fully implemented with D3.js
- [x] FindingsList with sorting & expansion
- [x] BlastRadius overlay component
- [x] NodeDetail integration ready
- [x] All components fetch from API endpoints

### Backend API
- [x] FastAPI skeleton with all 4 core routes
- [x] CORS middleware configured
- [x] Mock data for full integration testing
- [x] Pydantic models for type safety
- [x] Health check endpoint
- [x] Logging configured

### Contracts & Documentation
- [x] JSON contracts locked (CONTRACTS.md)
- [x] All shapes match API responses
- [x] Color mappings defined
- [x] Integration hooks documented in api/main.py

### Integration Points (P1 & P3)

**P1 (Algorithm Team) must deliver by Sync 1:**

1. **`run_blast_radius(graph, compromised_node, ...)`**
   - Location: `algorithm/blast_radius.py`
   - Must return data matching `BlastRadiusResult.to_dict()`
   - P4 wires to: `POST /blast-radius/{node}` route

2. **`run_temporal_bellman_ford(graph, ...)`**
   - Location: `algorithm/temporal_bellman_ford.py`
   - Must serialize to nodes/edges format
   - P4 wires to: `GET /graph` route

**P3 (AI Agent Team) must deliver by Sync 1:**

1. **`get_findings()`**
   - Location: `ai_agent/agent_core.py`
   - Must return list of findings matching `Finding` model
   - P4 wires to: `GET /findings` route

2. **`run_counterfactual(finding_id)`**
   - Location: `ai_agent/counterfactual.py`
   - Must return before/after path counts
   - P4 wires to: `POST /counterfactual/{finding_id}` route

3. **`delta_reporter.py` (Phase 2 prep)**
   - Must produce alert payloads matching schema
   - P4 will wire to WebSocket `/ws/alerts` in Phase 2

---

## Deployment Checklist

Before declaring Sync 1 complete:

- [ ] `npm run dev` starts frontend without errors
- [ ] `uvicorn api.main:app --reload` starts backend without errors
- [ ] Frontend can reach backend on `http://localhost:8000`
- [ ] `/health` returns 200 OK
- [ ] `/findings` returns mock findings (no API errors)
- [ ] `/graph` returns mock graph (no API errors)
- [ ] `/blast-radius/user1` returns mock blast radius (no API errors)
- [ ] `/counterfactual/f1` returns mock counterfactual (no API errors)
- [ ] GraphExplorer renders without console errors
- [ ] FindingsList loads findings and sorts by confidence
- [ ] Clicking a node triggers blast radius overlay
- [ ] Expanding finding cards shows evidence + remediation
- [ ] MITRE tactic badges are clickable

---

## Troubleshooting

### Frontend won't load

```bash
# Clear node_modules and reinstall
cd frontend
rm -rf node_modules
npm install
npm run dev
```

### Backend won't start

```bash
# Check Python version
python --version  # Must be 3.10+

# Reinstall dependencies
cd api
rm -rf .venv
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\Activate on Windows
pip install -r requirements.txt
```

### CORS errors in console

- ✓ FastAPI CORS middleware is configured for `localhost:3000` and `localhost:5173`
- Verify React runs on one of these URLs
- Check Network tab in DevTools for response headers

### Graph not rendering

- Check browser console for D3 errors
- Verify `/graph` endpoint returns valid JSON
- Ensure nodes and edges arrays are not empty

---

## Phase 2 Preparation

After Sync 1, the following will be wired:

1. **WebSocket `/ws/alerts`**
   - Real-time finding alerts from P3's `delta_reporter.py`
   - UI will update findings list when new findings appear

2. **FixPreview component** (counterfactual visualization)
   - Shows impact graph when user clicks "What if we fix this?"
   - Uses `/counterfactual/{finding_id}` endpoint

3. **Export reports**
   - PDF/DOCX generation via P3's reporting module
   - Hooked into `POST /export` endpoint

---

## Team Handoff Notes

**For P1 (Algorithm):**
- Check [CONTRACTS.md](CONTRACTS.md) for exact data shapes
- Your `run_blast_radius()` and `run_temporal_bellman_ford()` functions are already imported in comments in [api/main.py](api/main.py)
- Mock data in the API can serve as a reference for your output format

**For P3 (AI Agent):**
- Check [CONTRACTS.md](CONTRACTS.md) for findings shape
- Your `get_findings()` and `run_counterfactual()` functions are hooked to specific routes in [api/main.py](api/main.py)
- Frontend expects `remediation` field in each finding (new addition from spec)

---

**Last Updated:** May 10, 2026  
**Phase:** 0–1 Complete ✅  
**Next:** Sync 1 Integration (Week 6)
