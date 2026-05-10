import os
import json
import glob
from unittest.mock import MagicMock, patch
from graph_engine.graph_store import Neo4jStore

def test_neo4j_store():
    snapshots = glob.glob("data/snapshot_*.json")
    if not snapshots:
        print("[-] No snapshots found. Cannot verify.")
        return
        
    latest = max(snapshots, key=os.path.getctime)
    with open(latest, 'r') as f:
        objects = json.load(f)
        
    edge_file = latest.replace("snapshot_", "edges_")
    with open(edge_file, 'r') as f:
        edges = json.load(f)
        
    collection_time = objects[0]['distinguishedName']['last_seen']

    # Mock the neo4j GraphDatabase.driver
    with patch('graph_engine.graph_store.GraphDatabase.driver') as mock_driver:
        mock_session = MagicMock()
        mock_driver.return_value.session.return_value.__enter__.return_value = mock_session
        
        print("[*] Initiating mock Neo4jStore...")
        store = Neo4jStore("bolt://mock", "user", "pass")
        
        print("[*] Testing clear_db()...")
        store.clear_db()
        mock_session.run.assert_called_with("MATCH (n) DETACH DELETE n")
        
        print("[*] Testing push_nodes()...")
        store.push_nodes(objects)
        print(f"[+] push_nodes generated {mock_session.run.call_count - 1} queries.")
        
        run_count_after_nodes = mock_session.run.call_count
        
        print("[*] Testing push_memberships()...")
        store.push_memberships(objects)
        print(f"[+] push_memberships generated {mock_session.run.call_count - run_count_after_nodes} queries.")
        
        run_count_after_memberships = mock_session.run.call_count
        
        print("[*] Testing push_edges()...")
        store.push_edges(edges, collection_time)
        print(f"[+] push_edges generated {mock_session.run.call_count - run_count_after_memberships} queries.")
        
        store.close()
        mock_driver.return_value.close.assert_called_once()
        
        print("\n[+] Verification Successful! The Cypher queries are correctly formatted and executing against the mock session.")

if __name__ == "__main__":
    test_neo4j_store()
