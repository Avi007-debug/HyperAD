# P3 Integration Guide (AI Agent & Reporting → API)

**Target:** Weeks 1–6  
**Handoff:** End of Week 6 for Sync 1

---

## Your Role

You (P3) provide:
1. **Findings generation** — security issues discovered in AD environment
2. **Counterfactual analysis** — "what if we fix this finding?" simulations
3. **Reporting & alerts** — (Phase 2) real-time updates when findings change

P4 exposes your outputs via FastAPI so the frontend can display findings and test remediation impact.

---

## What P4 Needs From You

### 1. `get_findings()` Function

**Location:** `ai_agent/agent_core.py`

**Your Task:** Return findings in the exact schema below.

```python
def get_findings() -> List[Finding]:
    """
    Returns all discovered security findings in the AD environment.
    
    Should internally call:
      - run_temporal_bellman_ford() [from P1]
      - run_hits() [from P1]
      - run_tarjan_scc() [from P1]
    
    And generate findings from the results.
    
    Returns:
        List of Finding objects
    """
    ...
```

**Output Shape (Finding):**

Each finding must have this exact structure:

```python
{
    "id": "f1",                                    # Unique identifier
    "title": "Kerberoastable SPN on Critical...",  # Human-readable title
    "mitreTactic": "T1558.003",                    # MITRE ATT&CK technique
    "confidence": 0.94,                            # 0.0–1.0 (1.0 = 100% confident)
    "severity": "Critical",                        # Critical|High|Medium|Low
    "evidence": [                                  # Proof points
        "Service account SVC_DB_PROD has...",
        "Account has SPN registered...",
    ],
    "remediation": "Remove SPN from service...",   # How to fix it
}
```

**Enum Values (Locked Contracts):**

```python
severity ∈ {"Critical", "High", "Medium", "Low"}

mitreTactic examples:
  "T1558.003"    # Kerberoasting
  "T1078.002"    # Valid Accounts (default domain credentials)
  "T1003.006"    # OS Credential Dumping (DCSync)
  "T1134.001"    # Process Injection (Token Impersonation)
  "T1059.001"    # Command and Scripting Interpreter (PowerShell)
  ... (use actual MITRE ATT&CK IDs)
```

**P4 Wiring** (in `api/main.py`):

```python
@app.get("/findings", response_model=FindingsResponse)
def get_findings():
    from ai_agent.agent_core import get_findings as get_real_findings
    findings = get_real_findings()
    return FindingsResponse(findings=findings)
```

### 2. `run_counterfactual()` Function

**Location:** `ai_agent/counterfactual.py`

**Your Task:** Simulate removing a finding's edge, recompute paths, return delta.

```python
def run_counterfactual(finding_id: str) -> CounterfactualResult:
    """
    Simulate: "What if we remediate finding X?"
    
    Algorithm:
      1. Load the current AD graph
      2. Identify which edge(s) the finding represents
      3. Create a copy, remove that edge
      4. Re-run temporal_bellman_ford() on both graphs
      5. Count attack paths in each
      6. Return before/after counts
    
    Args:
        finding_id: The finding to simulate fixing
    
    Returns:
        CounterfactualResult with paths_before, paths_after, delta
    """
    ...
```

**Input:**
```python
# finding_id → lookup in findings dict to know which edge to remove
# E.g., "f1" = remove SVC_DB_PROD → DOMAIN_ADMINS edge
```

**Output Shape:**

```python
{
    "finding_id": "f1",       # Echo back the finding ID
    "paths_before": 14,       # Total attack paths before remediation
    "paths_after": 2,         # Total attack paths after remediation
    "delta": -12,             # Change (always ≤ 0, improvement)
}
```

**Math:**
```
delta = paths_after - paths_before

E.g.,
  14 - 2 = -12  ✓ Good (fixed 12 paths)
  14 - 14 = 0   ✓ OK (finding doesn't help attackers)
  14 - 16 = 2   ✗ Bad (remediation makes things worse — unlikely)
```

**P4 Wiring** (in `api/main.py`):

```python
@app.post("/counterfactual/{finding_id}", response_model=CounterfactualResponse)
def counterfactual(finding_id: str):
    from ai_agent.counterfactual import run_counterfactual
    result = run_counterfactual(finding_id)
    return CounterfactualResponse(
        finding_id=finding_id,
        paths_before=result.paths_before,
        paths_after=result.paths_after,
        delta=result.delta,
    )
```

### 3. `delta_reporter.py` (Phase 2 Prep)

**Location:** `ai_agent/delta_reporter.py`

**Your Task:** Generate alert events when findings change (new, resolved, increased risk).

**Output Shape (for Phase 2 WebSocket):**

```python
{
    "finding_id": "f1",
    "timestamp": "2026-05-10T14:32:00Z",    # ISO 8601
    "title": "Kerberoastable SPN...",
    "severity": "Critical",
    "delta_type": "new|resolved|risk_increased",
}
```

**Phase 2 Wiring** (not yet):

```python
# Will be added in Phase 2
@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    from ai_agent.delta_reporter import alert_stream
    async for alert in alert_stream():
        await websocket.send_json(alert)
```

---

## Data Shapes (Locked Contracts)

### MITRE ATT&CK Tactics

Use official MITRE IDs. Reference: https://attack.mitre.org/

Common examples:
```
Reconnaissance:
  T1592  — Gather Victim Identity Information
  
Initial Access:
  T1133  — External Remote Services

Persistence:
  T1098.003  — Account Manipulation (Add Office 365 Global Admin Role)

Privilege Escalation:
  T1078.002  — Valid Accounts (Domain Accounts)
  T1548.002  — Abuse Elevation Control Mechanism (Bypass UAC)

Defense Evasion:
  T1564.011  — Hide Artifacts (NTFS File Attributes)

Credential Access:
  T1110.004  — Brute Force (Credential Stuffing)
  T1187     — Forced Authentication

Lateral Movement:
  T1570  — Lateral Tool Transfer
  T1021  — Remote Services (incl. WMI, RDP, SMB)

Collection:
  T1005  — Data from Local System

Command & Control:
  T1071  — Application Layer Protocol

Exfiltration:
  T1041  — Exfiltration Over C2 Channel

Impact:
  T1531  — Account Access Removal
```

### Severity → Risk Score Mapping

```python
severity ↔ confidence range:

Critical: 0.80–1.00   (extremely high confidence)
High:     0.60–0.79  (high confidence)
Medium:   0.40–0.59  (moderate confidence)
Low:      0.00–0.39  (low confidence / informational)
```

### Finding Evidence

Each finding should have 2–5 evidence strings, e.g.:

```python
evidence = [
    "Service account SVC_DB_PROD has TRUSTED_FOR_DELEGATION flag",
    "Account has SPN registered for MSSQL service",
    "No selective authentication constraints configured",
]
```

These are shown to security teams to justify the finding.

### Remediation Steps

Clear, actionable guidance, e.g.:

```python
remediation = "Remove SPN from service account via 'setspn -d' or enforce AES encryption on Kerberos tickets"
```

---

## Integration Timeline

### Week 1
- [ ] Review this guide with P4 and P1
- [ ] Lock MITRE tactic list (use subset of ~10 key tactics)
- [ ] Define which findings your agent will generate

### Weeks 2–6
- [ ] Implement `get_findings()` using P1's outputs
- [ ] Implement `run_counterfactual()` (calls P1's algorithms)
- [ ] Test locally with mock data
- [ ] Validate JSON schema matches contracts

### Week 6 (Sync 1)
- [ ] Run test: `python test_ai_agent.py` (P4 provides template)
- [ ] Verify all findings have required fields
- [ ] Verify counterfactual delta values are sensible
- [ ] P4 wires functions into API routes
- [ ] Joint test: API returns findings → Frontend renders list + sorts

### After Sync 1 (Phase 2)
- [ ] Implement `delta_reporter.py` for real-time alerts
- [ ] P4 wires WebSocket handler
- [ ] Frontend subscribes and updates findings list live

---

## Checklist Before Handing Off (Sync 1)

### Findings
- [ ] `get_findings()` returns `List[Finding]` (not wrapped in response object)
- [ ] Each finding has: `id`, `title`, `mitreTactic`, `confidence`, `severity`, `evidence`, `remediation`
- [ ] `confidence` is float 0.0–1.0 (not 0–100)
- [ ] `severity` is one of: Critical, High, Medium, Low
- [ ] `mitreTactic` is valid MITRE ATT&CK ID (e.g., "T1558.003")
- [ ] `evidence` array has 2–5 strings
- [ ] `remediation` is 1–2 sentences, actionable
- [ ] Findings are sorted by confidence (descending) or severity

### Counterfactual
- [ ] `run_counterfactual(finding_id)` accepts finding ID as string
- [ ] Returns object with: `finding_id`, `paths_before`, `paths_after`, `delta`
- [ ] `paths_before` and `paths_after` are non-negative integers
- [ ] `delta = paths_after - paths_before` (verified)
- [ ] `delta` is always ≤ 0 (unless bug in algorithm, which is OK for mock)
- [ ] Handles unknown finding_id gracefully (return 404 via API)

### Code Quality
- [ ] No hardcoded test data in production functions
- [ ] All imports use `from ai_agent import ...` or `from algorithm import ...`
- [ ] Functions are deterministic (same input → same output)
- [ ] Error handling for missing graph data, missing nodes, etc.

---

## Testing Locally

Before handing off to P4:

```python
# Test findings generation
from ai_agent.agent_core import get_findings
findings = get_findings()
print(f"Generated {len(findings)} findings")
print(f"Sample: {findings[0]}")
# Expected: 4+ findings with all required fields

# Test counterfactual
from ai_agent.counterfactual import run_counterfactual
result = run_counterfactual("f1")
print(result)
# Expected: {finding_id, paths_before, paths_after, delta}

# Validate JSON serialization
import json
json.dumps({
    "id": f.id,
    "title": f.title,
    "mitreTactic": f.mitreTactic,
    "confidence": f.confidence,
    "severity": f.severity,
    "evidence": f.evidence,
    "remediation": f.remediation,
})
# Expected: valid JSON with no encoding errors
```

---

## FAQ

**Q: Should I rank findings by confidence or severity?**  
A: P4's frontend defaults to sorting by confidence (descending). You can return in any order; frontend will sort.

**Q: What if a finding involves multiple edges?**  
A: For MVP, assume 1 finding = 1 edge. In Phase 2, we can support multi-edge findings.

**Q: How do I know which edges to count for `counterfactual`?**  
A: Create a mapping in your code: `finding_id → (from_node, to_node)`. Store in a dict or config file.

**Q: Should counterfactual re-run the full AI agent or just P1's algorithms?**  
A: For MVP, just re-run P1's algorithms on the modified graph. The AI agent's findings won't change (they're static until next scan).

**Q: Can findings have the same MITRE tactic?**  
A: Yes, multiple findings can be for the same tactic. Frontend handles this.

**Q: What if `paths_before` and `paths_after` are both 0?**  
A: That's OK! It means the finding doesn't contribute to any attack path (low-risk). Delta will be 0.

---

## Phase 2 Preview

After Sync 1, you'll implement:

1. **Real-time delta detection**
   - When findings are re-scanned, detect what changed (new, resolved, increased risk)
   - Generate alert events

2. **Alert stream**
   - `delta_reporter.py` yields alert events
   - P4 connects WebSocket → frontend subscribes
   - Findings list updates live without page refresh

3. **Historical tracking**
   - Store finding history (finding appeared on 2026-05-10, resolved on 2026-05-12)
   - Frontend can show timeline

---

## Appendix: Sample Finding Data

```python
findings_sample = [
    {
        "id": "f1",
        "title": "Kerberoastable SPN on Critical Service Account",
        "mitreTactic": "T1558.003",
        "confidence": 0.94,
        "severity": "Critical",
        "evidence": [
            "Service account SVC_DB_PROD has TRUSTED_FOR_DELEGATION flag set",
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
            "IT_ADMINS is nested in DOMAIN_ADMINS",
            "2-hop escalation path detected",
        ],
        "remediation": "Remove GenericAll permission from JSMITH or remove IT_ADMINS from Domain Admins",
    },
]
```

---

**Contact P4:** See [PHASE_0_1_SETUP.md](../PHASE_0_1_SETUP.md) for integration contact & timeline.
