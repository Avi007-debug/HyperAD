import os
import json
import glob
from datetime import datetime
from typing import List, Dict, Tuple

class SnapshotManager:
    """
    Manages the collection and retrieval of timestamped AD snapshots.
    """
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

    def list_snapshots(self) -> List[str]:
        """Returns a list of snapshot paths, sorted by time (oldest to newest)."""
        files = glob.glob(os.path.join(self.data_dir, "snapshot_*.json"))
        return sorted(files)

    def get_latest_pair(self) -> Tuple[str, str]:
        """Returns the two most recent snapshots for comparison."""
        snapshots = self.list_snapshots()
        if len(snapshots) < 2:
            return None, None
        return snapshots[-2], snapshots[-1]

    def load_snapshot(self, path: str) -> List[Dict]:
        """Loads a specific snapshot from disk."""
        if not path or not os.path.exists(path):
            return []
        with open(path, 'r') as f:
            return json.load(f)

class GraphDiffer:
    """
    Computes the delta between two snapshots (added/removed nodes and edges).
    This is the input for Frigioni's incremental update algorithm.
    """
    def diff_objects(self, old_objs: List[Dict], new_objs: List[Dict]) -> Dict:
        """
        Compares two lists of AD objects.
        Returns added, removed, and modified object names.
        """
        # We use DistinguishedName as the unique key
        old_map = {obj['distinguishedName']['value']: obj for obj in old_objs}
        new_map = {obj['distinguishedName']['value']: obj for obj in new_objs}
        
        old_dns = set(old_map.keys())
        new_dns = set(new_map.keys())
        
        added = new_dns - old_dns
        removed = old_dns - new_dns
        
        # Check for modifications in existing objects
        modified = []
        for dn in (old_dns & new_dns):
            if self._is_modified(old_map[dn], new_map[dn]):
                modified.append(dn)
                
        return {
            'added': list(added),
            'removed': list(removed),
            'modified': modified
        }
        
    def _is_modified(self, old_obj: Dict, new_obj: Dict) -> bool:
        """Helper to check if any relevant security attributes changed."""
        # Focus on attributes that affect graph structure
        watch_attrs = ['memberOf', 'userAccountControl', 'msDS-AllowedToDelegateTo', 'nTSecurityDescriptor']
        for attr in watch_attrs:
            old_val = old_obj.get(attr, {}).get('value')
            new_val = new_obj.get(attr, {}).get('value')
            if old_val != new_val:
                return True
        return False

    def diff_edges(self, old_edges: List[Dict], new_edges: List[Dict]) -> Dict:
        """
        Compares two lists of permission edges.
        Returns newly granted or revoked permissions.
        """
        def edge_key(e): return f"{e['source']}|{e['type']}|{e['target']}"
        
        old_set = {edge_key(e) for e in old_edges}
        new_set = {edge_key(e) for e in new_edges}
        
        added_keys = new_set - old_set
        removed_keys = old_set - new_set
        
        added = [e for e in new_edges if edge_key(e) in added_keys]
        removed = [e for e in old_edges if edge_key(e) in removed_keys]
        
        return {
            'added_edges': added,
            'removed_edges': removed
        }

if __name__ == "__main__":
    # Example usage for integration testing
    manager = SnapshotManager()
    differ = GraphDiffer()
    
    old_path, new_path = manager.get_latest_pair()
    
    if not old_path:
        print("[!] Not enough snapshots to perform a diff. Run ldap_enum.py again.")
    else:
        print(f"[*] Comparing {os.path.basename(old_path)} vs {os.path.basename(new_path)}")
        
        old_data = manager.load_snapshot(old_path)
        new_data = manager.load_snapshot(new_path)
        
        delta = differ.diff_objects(old_data, new_data)
        
        print(f"[+] Snapshot Delta Summary:")
        print(f"  - New Objects:      {len(delta['added'])}")
        print(f"  - Removed Objects:  {len(delta['removed'])}")
        print(f"  - Modified Objects: {len(delta['modified'])}")
        
        # Now diff the ACL edges if they exist
        old_edge_path = old_path.replace("snapshot_", "edges_")
        new_edge_path = new_path.replace("snapshot_", "edges_")
        
        if os.path.exists(old_edge_path) and os.path.exists(new_edge_path):
            old_edges = manager.load_snapshot(old_edge_path)
            new_edges = manager.load_snapshot(new_edge_path)
            
            edge_delta = differ.diff_edges(old_edges, new_edges)
            print(f"  - New Permissions:     {len(edge_delta['added_edges'])}")
            print(f"  - Revoked Permissions: {len(edge_delta['removed_edges'])}")
            
            if edge_delta['added_edges']:
                print("\n[*] Alert: New permission edges detected!")
                for e in edge_delta['added_edges'][:5]:
                    print(f"  [+] {e['source']} --({e['type']})--> {e['target']}")
