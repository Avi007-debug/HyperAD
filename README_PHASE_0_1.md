# HyperAD Project — Phase 0 & 1 Complete ✅

**Status:** Ready for testing and Sync 1 integration  
**Date:** May 10, 2026  
**Team:** P4 (Frontend + API)

---

## 📋 Executive Summary

HyperAD is a **real-time Active Directory privilege graph analyzer** for detecting attack paths and privilege escalation chains.

**Phase 0–1 (Weeks 1–6)** is now complete:
- ✅ FastAPI backend with mock data
- ✅ React frontend with D3.js graph visualization
- ✅ Findings panel with MITRE tactic mapping
- ✅ Blast radius calculator (interactive)
- ✅ JSON contracts locked with P1 and P3
- ✅ Integration guides for all teams

---

## 🚀 Quick Start

### Start the Frontend

```bash
cd frontend
npm run dev
# Runs on http://localhost:5173
```

### Start the Backend

```bash
cd api
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
# Runs on http://localhost:8000
# Auto-reload on file changes
```

### Test the API

```bash
# In a new terminal
python test_api.py
# Tests all 5 endpoints and validates data shapes
```

---

## 📚 Documentation

| Document | Purpose | Audience |
|---|---|---|
| [CONTRACTS.md](CONTRACTS.md) | **Locked JSON schemas** for all API responses | All teams |
| [PHASE_0_1_SETUP.md](PHASE_0_1_SETUP.md) | **Complete setup & testing guide** | All teams |
| [P1_INTEGRATION_GUIDE.md](P1_INTEGRATION_GUIDE.md) | Algorithm team integration checklist | P1 (Algorithm) |
| [P3_INTEGRATION_GUIDE.md](P3_INTEGRATION_GUIDE.md) | AI Agent team integration checklist | P3 (AI Agent) |

---

## 🏗️ Project Structure

```
HyperAD/
├── api/                         # FastAPI backend
│   ├── main.py                 # All 4 route endpoints
│   ├── __init__.py
│   └── requirements.txt         # pip dependencies
│
├── frontend/                    # React + Vite + D3.js
│   ├── src/app/
│   │   ├── App.tsx            # Main layout
│   │   └── components/
│   │       ├── GraphExplorer.tsx    # D3 force graph (interactive)
│   │       ├── FindingsList.tsx     # Findings panel (sortable)
│   │       ├── BlastRadius.tsx      # Reachability overlay
│   │       ├── NodeDetail.tsx       # Selected node info
│   │       └── LandingPage.tsx      # Splash screen
│   ├── package.json
│   └── vite.config.ts
│
├── algorithm/                   # P1: Attack path algorithms
│   ├── blast_radius.py
│   ├── temporal_bellman_ford.py
│   ├── models.py               # Shared data types
│   ├── test_algorithms.py
│   └── requirements.txt
│
├── agent_and_report/            # P3: AI Agent & Reporting
│   ├── ai_agent/
│   │   ├── agent_core.py       # Findings generator
│   │   └── counterfactual.py   # Remediation simulator
│   ├── reporting/
│   │   └── report_gen.py       # PDF/DOCX export
│   └── requirements.txt
│
├── CONTRACTS.md                # **Locked API schemas**
├── PHASE_0_1_SETUP.md         # **Setup & testing guide**
├── P1_INTEGRATION_GUIDE.md    # **Algorithm team checklist**
├── P3_INTEGRATION_GUIDE.md    # **AI Agent team checklist**
├── test_api.py                 # Test suite for API validation
└── README.md                   # This file
```

---

## 🔌 API Endpoints

All endpoints return JSON and support CORS from `localhost:3000` and `localhost:5173`.

### 1. `GET /health`
**Health check liveness probe**
```bash
curl http://localhost:8000/health
# Response: { "status": "ok" }
```

### 2. `GET /findings`
**List all security findings**
```bash
curl http://localhost:8000/findings
# Returns: { "findings": [...] }
```
- **Frontend:** FindingsList component fetches this
- **Sort by:** Confidence (descending default)
- **Columns:** Title, MITRE tactic, confidence %, severity

### 3. `GET /graph`
**Full AD privilege graph**
```bash
curl http://localhost:8000/graph
# Returns: { "nodes": [...], "edges": [...] }
```
- **Frontend:** GraphExplorer D3 component renders this
- **Nodes:** user, group, computer, service (+ isDomainAdmin flag)
- **Edges:** Weighted by risk (0–10)

### 4. `POST /blast-radius/{node}`
**Reachability from compromised node**
```bash
curl -X POST http://localhost:8000/blast-radius/user1
# Returns: { "node": "user1", "reachable": { "1hop": [...], "2hop": [...], ... } }
```
- **Frontend:** Triggered by GraphExplorer node click
- **Shows:** Which nodes can be reached in 1, 2, 3 hops
- **Use case:** "If this user is compromised, what gets hit?"

### 5. `POST /counterfactual/{finding_id}`
**"What if we fix this finding?"**
```bash
curl -X POST http://localhost:8000/counterfactual/f1
# Returns: { "finding_id": "f1", "paths_before": 14, "paths_after": 2, "delta": -12 }
```
- **Frontend:** Phase 2 (FixPreview component)
- **Shows:** Attack path count before and after remediation
- **Use case:** Quantify the impact of fixing a vulnerability

---

## 🎨 Frontend Components

### GraphExplorer (D3.js Force Graph)
- **Interactive:** Drag nodes, zoom, pan
- **Colors:** User (blue) → Group (purple) → Computer (grey) → Service (amber) → DA (red)
- **Interactivity:** Click node → shows blast radius overlay
- **Size:** Node size scales by authority score
- **Edges:** Thickness scales by risk weight

### FindingsList
- **Sortable:** By confidence score
- **Expandable:** Click card to see evidence + remediation steps
- **MITRE badges:** Clickable link to attack.mitre.org
- **Severity pills:** Color-coded (Critical/High/Medium/Low)

### BlastRadius Overlay
- **Shows:** Hop-by-hop breakdown from compromised node
- **Color gradient:** 1-hop (red) → 2-hop (amber) → 3-hop (yellow)
- **Dismissible:** "Clear" button to hide

---

## 📊 Data Contracts (Locked)

### Finding Shape

```json
{
  "id": "f1",
  "title": "Kerberoastable SPN...",
  "mitreTactic": "T1558.003",
  "confidence": 0.94,
  "severity": "Critical",
  "evidence": ["..."],
  "remediation": "..."
}
```

### Node Shape

```json
{
  "id": "user1",
  "type": "user|group|computer|service",
  "label": "JSMITH",
  "authorityScore": 0.6,
  "isDomainAdmin": false
}
```

### Edge Shape

```json
{
  "source": "user1",
  "target": "domain_admins",
  "weight": 8.5
}
```

**👉 See [CONTRACTS.md](CONTRACTS.md) for complete schemas & color mappings**

---

## ✅ Sync 1 Checklist (End of Week 6)

Before declaring ready for integration with P1 and P3:

- [ ] Frontend dev server starts: `npm run dev`
- [ ] Backend server starts: `uvicorn api.main:app --reload`
- [ ] `test_api.py` passes all 5 tests
- [ ] `/health` returns 200 OK
- [ ] `/findings` returns mock findings
- [ ] `/graph` returns mock graph with nodes and edges
- [ ] `/blast-radius/user1` returns reachability
- [ ] `/counterfactual/f1` returns paths before/after
- [ ] GraphExplorer renders without console errors
- [ ] FindingsList loads and sorts findings
- [ ] Clicking a node shows BlastRadius overlay
- [ ] Expanding finding card shows evidence + remediation
- [ ] MITRE badges link to attack.mitre.org
- [ ] No CORS errors in browser console
- [ ] All Pydantic models serialize to JSON correctly

---

## 🔗 Integration Roadmap

### Week 6 (Sync 1) — Algorithm Integration (P1)

P1 delivers:
1. `run_blast_radius()` → P4 wires to `POST /blast-radius/{node}`
2. `run_temporal_bellman_ford()` → P4 wires to `GET /graph`

P4 actions:
- [ ] Import P1 functions in `api/main.py`
- [ ] Replace mock data calls with real algorithm calls
- [ ] Run integration tests
- [ ] Demo to P1 that frontend renders their data correctly

**See:** [P1_INTEGRATION_GUIDE.md](P1_INTEGRATION_GUIDE.md)

### Week 6 (Sync 1) — AI Agent Integration (P3)

P3 delivers:
1. `get_findings()` → P4 wires to `GET /findings`
2. `run_counterfactual()` → P4 wires to `POST /counterfactual/{finding_id}`

P4 actions:
- [ ] Import P3 functions in `api/main.py`
- [ ] Replace mock findings with real agent findings
- [ ] Replace mock counterfactual with real analysis
- [ ] Run integration tests
- [ ] Demo to P3 that frontend displays findings correctly

**See:** [P3_INTEGRATION_GUIDE.md](P3_INTEGRATION_GUIDE.md)

### Phase 2 (Weeks 7–10) — Real-Time Alerts

1. P3 implements `delta_reporter.py` (detects finding changes)
2. P4 adds WebSocket `/ws/alerts` endpoint
3. Frontend subscribes → findings list updates live

---

## 🚨 Known Limitations (MVP)

- **No persistence:** Data is in-memory, not saved to database
- **No authentication:** Anyone can access the API
- **Single scan:** Graph is static, not updated incrementally
- **Mock data:** Findings are hardcoded, not generated from real AD

These will be addressed in Phase 2 & beyond.

---

## 📞 Support & Questions

**For P4 (Frontend + API):**
- Contact: See project leads in [PHASE_0_1_SETUP.md](PHASE_0_1_SETUP.md)

**For P1 (Algorithm):**
- See: [P1_INTEGRATION_GUIDE.md](P1_INTEGRATION_GUIDE.md)
- Review: `algorithm/models.py` for data types
- Test: `python -m pytest algorithm/test_algorithms.py -v`

**For P3 (AI Agent):**
- See: [P3_INTEGRATION_GUIDE.md](P3_INTEGRATION_GUIDE.md)
- Review: `ai_agent/agent_core.py` for function signatures
- Test: `python test_api.py` to validate your outputs

---

## 📈 Development Tips

### Frontend Development

```bash
cd frontend

# Start dev server with hot reload
npm run dev

# Build for production
npm run build

# Type check (TypeScript)
npx tsc --noEmit
```

### Backend Development

```bash
cd api

# Auto-reload server on file changes
python -m uvicorn main:app --reload --port 8000

# Test a single endpoint
curl http://localhost:8000/findings | python -m json.tool

# Enable debug logging
export PYTHONUNBUFFERED=1
```

### Debugging Tips

- **Frontend:** Use browser DevTools (F12) → Network tab to inspect API calls
- **Backend:** Check terminal output for logs (auto-printed via FastAPI)
- **CORS errors:** Verify `add_middleware(CORSMiddleware, ...)` in `api/main.py`

---

## 📝 License

See [LICENSE](LICENSE)

---

**Status:** ✅ **Phase 0–1 Complete** — Ready for Week 6 Sync 1  
**Last Updated:** May 10, 2026  
**Next:** P1 & P3 Integration (Weeks 6–7)
