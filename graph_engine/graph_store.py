import os
import json
import glob
from neo4j import GraphDatabase
from typing import List, Dict

class Neo4jStore:
    """
    Handles persistence of AD data to Neo4j.
    Uses MERGE patterns to ensure objects and relationships are unique.
    """
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def clear_db(self):
        """Wipes the database. Use with caution!"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("[*] Neo4j database cleared.")

    def push_nodes(self, objects: List[Dict]):
        """
        Creates or updates nodes for every AD object in the snapshot.
        """
        with self.driver.session() as session:
            print(f"[*] Pushing {len(objects)} nodes to Neo4j...")
            
            # Map objectClass to our NodeType labels
            for obj in objects:
                dn = obj['distinguishedName']['value']
                name = obj.get('sAMAccountName', {}).get('value', dn)
                obj_classes = obj.get('objectClass', {}).get('value', [])
                
                # Determine primary label
                label = "Object"
                if 'user' in obj_classes: label = "User"
                elif 'group' in obj_classes: label = "Group"
                elif 'computer' in obj_classes: label = "Computer"
                elif 'organizationalUnit' in obj_classes: label = "OU"
                elif 'domainDNS' in obj_classes: label = "Domain"
                elif 'groupPolicyContainer' in obj_classes: label = "GPO"
                
                # MERGE node by DN
                query = (
                    f"MERGE (n:{label} {{dn: $dn}}) "
                    "SET n.name = $name, n.last_seen = $ts"
                )
                session.run(query, dn=dn, name=name, ts=obj['distinguishedName']['last_seen'])

    def push_edges(self, edges: List[Dict], collection_time: str):
        """
        Creates relationships between nodes based on ACLs and group memberships.
        """
        with self.driver.session() as session:
            print(f"[*] Pushing {len(edges)} permission edges to Neo4j...")
            
            for edge in edges:
                # We match by name (simplified for demo, DN is better but edges currently use names)
                # In production, we'd ensure ACLCrawler outputs SIDs or DNs.
                query = (
                    "MATCH (a {name: $src}), (b {name: $dst}) "
                    f"MERGE (a)-[r:{edge['type'].upper()}]->(b) "
                    "SET r.last_seen = $ts"
                )
                session.run(query, src=edge['source'], dst=edge['target'], ts=collection_time)

    def push_memberships(self, objects: List[Dict]):
        """
        Special handler for 'memberOf' attributes to create graph edges.
        """
        with self.driver.session() as session:
            print("[*] Processing group memberships...")
            for obj in objects:
                src_dn = obj['distinguishedName']['value']
                memberships = obj.get('memberOf', {}).get('value', [])
                if isinstance(memberships, str): memberships = [memberships]
                
                ts = obj['distinguishedName']['last_seen']
                
                for group_dn in memberships:
                    query = (
                        "MATCH (a {dn: $src_dn}), (b {dn: $group_dn}) "
                        "MERGE (a)-[r:MEMBER_OF]->(b) "
                        "SET r.last_seen = $ts"
                    )
                    session.run(query, src_dn=src_dn, group_dn=group_dn, ts=ts)

if __name__ == "__main__":
    # Neo4j Settings (Adjust for your lab)
    NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
    NEO4J_PASS = os.environ.get("NEO4J_PASS", "password") # Default is usually 'password' or user-set

    store = Neo4jStore(NEO4J_URI, NEO4J_USER, NEO4J_PASS)
    
    # 1. Load latest data
    snapshots = glob.glob("data/snapshot_*.json")
    if not snapshots:
        print("[-] Run collectors first.")
        exit(1)
        
    latest = max(snapshots, key=os.path.getctime)
    with open(latest, 'r') as f:
        objects = json.load(f)
        
    edge_file = latest.replace("snapshot_", "edges_")
    with open(edge_file, 'r') as f:
        edges = json.load(f)
        
    collection_time = objects[0]['distinguishedName']['last_seen']

    # 2. Update Graph
    try:
        store.clear_db() # Optional: remove for incremental updates
        store.push_nodes(objects)
        store.push_memberships(objects)
        store.push_edges(edges, collection_time)
        print("[+] Neo4j Graph Update Complete.")
    except Exception as e:
        print(f"[-] Neo4j Error: {e}")
    finally:
        store.close()
