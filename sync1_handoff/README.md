# HyperAD Sync1 Handoff (P1 → P3/P4)

This folder contains the **pre-Sync1 integration package** for the algorithm stream.

## Goal
Enable P3 (AI Agent) and P4 (Frontend/API) to integrate immediately with stable algorithm interfaces.

## Delivered in this handoff
- Stable algorithm package: `algorithm/`
- Local setup instructions (Python 3.13 compatible)
- Interface contract examples (`contracts.json`)
- P3 integration guide (`p3_ai_handoff.md`)
- P4 integration guide (`p4_api_handoff.md`)

## Quick validation
From repo root:

```powershell
cd algorithm
.\.venv\Scripts\Activate.ps1
python -m pytest test_algorithms.py -q
```

Expected:

```text
64 passed
```
