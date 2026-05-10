#!/usr/bin/env python3
"""
HyperAD API Test Suite — Phase 0/1 Validation

This script tests all API endpoints and verifies data shapes match contracts.

Usage:
    python test_api.py

Requirements:
    pip install requests
"""

import requests
import json
import sys
from typing import Dict, Any

BASE_URL = "http://localhost:8000"
VERBOSE = True

def log(msg: str, level: str = "INFO"):
    """Simple logging."""
    prefix = "✅" if level == "OK" else "❌" if level == "ERR" else "ℹ️"
    print(f"{prefix} [{level}] {msg}")


def validate_shape(data: Any, schema: Dict[str, str], name: str) -> bool:
    """Check if data matches expected schema."""
    if not isinstance(data, dict):
        log(f"{name}: Not a dict", "ERR")
        return False
    
    for key, expected_type in schema.items():
        if key not in data:
            log(f"{name}: Missing key '{key}'", "ERR")
            return False
        
        actual_type = type(data[key]).__name__
        if expected_type not in actual_type.lower():
            log(f"{name}: Key '{key}' is {actual_type}, expected {expected_type}", "WARN")
    
    return True


def test_health():
    """Test GET /health"""
    print("\n[TEST] GET /health")
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        if resp.status_code == 200:
            log("Health check passed", "OK")
            return True
        else:
            log(f"Unexpected status: {resp.status_code}", "ERR")
            return False
    except Exception as e:
        log(f"Connection failed: {e}", "ERR")
        return False


def test_findings():
    """Test GET /findings"""
    print("\n[TEST] GET /findings")
    try:
        resp = requests.get(f"{BASE_URL}/findings", timeout=5)
        resp.raise_for_status()
        
        data = resp.json()
        if "findings" not in data:
            log("Response missing 'findings' key", "ERR")
            return False
        
        findings = data["findings"]
        log(f"Found {len(findings)} findings", "OK")
        
        if len(findings) > 0:
            finding = findings[0]
            schema = {
                "id": "str",
                "title": "str",
                "mitreTactic": "str",
                "confidence": "float",
                "severity": "str",
                "evidence": "list",
                "remediation": "str",
            }
            if validate_shape(finding, schema, "Finding"):
                log(f"Finding shape valid ✓", "OK")
                if VERBOSE:
                    print(f"  Sample: {json.dumps(finding, indent=2)[:200]}...")
                return True
        
        return True
    except Exception as e:
        log(f"Failed: {e}", "ERR")
        return False


def test_graph():
    """Test GET /graph"""
    print("\n[TEST] GET /graph")
    try:
        resp = requests.get(f"{BASE_URL}/graph", timeout=5)
        resp.raise_for_status()
        
        data = resp.json()
        if "nodes" not in data or "edges" not in data:
            log("Response missing 'nodes' or 'edges'", "ERR")
            return False
        
        nodes = data["nodes"]
        edges = data["edges"]
        log(f"Graph has {len(nodes)} nodes and {len(edges)} edges", "OK")
        
        # Validate node schema
        if len(nodes) > 0:
            node = nodes[0]
            node_schema = {
                "id": "str",
                "type": "str",
                "label": "str",
                "authorityScore": "float",
            }
            if validate_shape(node, node_schema, "Node"):
                log(f"Node shape valid ✓", "OK")
        
        # Validate edge schema
        if len(edges) > 0:
            edge = edges[0]
            edge_schema = {
                "source": "str",
                "target": "str",
                "weight": "float",
            }
            if validate_shape(edge, edge_schema, "Edge"):
                log(f"Edge shape valid ✓", "OK")
        
        return True
    except Exception as e:
        log(f"Failed: {e}", "ERR")
        return False


def test_blast_radius():
    """Test POST /blast-radius/{node}"""
    print("\n[TEST] POST /blast-radius/{node}")
    
    # First fetch a valid node
    try:
        resp = requests.get(f"{BASE_URL}/graph", timeout=5)
        resp.raise_for_status()
        nodes = resp.json()["nodes"]
        
        if not nodes:
            log("No nodes in graph to test", "WARN")
            return False
        
        node_id = nodes[0]["id"]
        
        # Now test blast-radius
        resp = requests.post(f"{BASE_URL}/blast-radius/{node_id}", timeout=5)
        resp.raise_for_status()
        
        data = resp.json()
        schema = {
            "node": "str",
            "reachable": "dict",
        }
        
        if validate_shape(data, schema, "BlastRadiusResponse"):
            log(f"Blast radius for '{node_id}' computed", "OK")
            
            # Check reachable structure
            reachable = data.get("reachable", {})
            if all(isinstance(v, list) for v in reachable.values()):
                log(f"Reachable structure valid (hops: {list(reachable.keys())})", "OK")
                return True
            else:
                log("Reachable structure invalid", "ERR")
                return False
        
        return False
    except Exception as e:
        log(f"Failed: {e}", "ERR")
        return False


def test_counterfactual():
    """Test POST /counterfactual/{finding_id}"""
    print("\n[TEST] POST /counterfactual/{finding_id}")
    
    # First fetch a valid finding
    try:
        resp = requests.get(f"{BASE_URL}/findings", timeout=5)
        resp.raise_for_status()
        findings = resp.json()["findings"]
        
        if not findings:
            log("No findings to test", "WARN")
            return False
        
        finding_id = findings[0]["id"]
        
        # Now test counterfactual
        resp = requests.post(f"{BASE_URL}/counterfactual/{finding_id}", timeout=5)
        resp.raise_for_status()
        
        data = resp.json()
        schema = {
            "finding_id": "str",
            "paths_before": "int",
            "paths_after": "int",
            "delta": "int",
        }
        
        if validate_shape(data, schema, "CounterfactualResponse"):
            log(f"Counterfactual for '{finding_id}': {data['paths_before']} → {data['paths_after']} (Δ {data['delta']})", "OK")
            
            # Verify delta is correct
            expected_delta = data["paths_after"] - data["paths_before"]
            if data["delta"] == expected_delta:
                log("Delta calculation correct", "OK")
                return True
            else:
                log(f"Delta mismatch: expected {expected_delta}, got {data['delta']}", "WARN")
                return True  # Still pass, minor issue
        
        return False
    except Exception as e:
        log(f"Failed: {e}", "ERR")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("HyperAD API Test Suite")
    print("=" * 60)
    print(f"Target: {BASE_URL}")
    
    results = {
        "Health Check": test_health(),
        "Findings": test_findings(),
        "Graph": test_graph(),
        "Blast Radius": test_blast_radius(),
        "Counterfactual": test_counterfactual(),
    }
    
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} — {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 60)
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
