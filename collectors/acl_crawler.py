import json
import os
import glob
import uuid
from typing import List, Dict, Optional
from impacket.ldap.ldaptypes import SR_SECURITY_DESCRIPTOR, LDAP_SID

# Import EdgeTypes from our models
try:
    from algorithm.models import EdgeType
except ImportError:
    # Fallback if pathing is tricky during execution
    class EdgeType:
        GENERIC_ALL = "GenericAll"
        WRITE_DACL = "WriteDACL"
        WRITE_OWNER = "WriteOwner"
        GENERIC_WRITE = "GenericWrite"
        DC_SYNC = "DCSync"
        FORCE_CHANGE_PASSWORD = "ForceChangePassword"
        OWNS = "Owns"

# GUIDs for Extended Rights (Found in lab + Standard)
EXTENDED_RIGHTS_GUIDS = {
    "1131f6aa-9c07-11d1-f79f-00c04fc2dcd2": "DS-Replication-Get-Changes",
    "1131f6ad-9c07-11d1-f79f-00c04fc2dcd2": "DS-Replication-Get-Changes-All",
    "89e95b76-444d-4c62-991a-0facbeda640c": "DS-Replication-Get-Changes-In-Filter",
    "1131f6aa-9c07-11d1-b79e-00a0c910076e": "DS-Replication-Get-Changes", 
    "1131f6ad-9c07-11d1-b79e-00a0c910076e": "DS-Replication-Get-Changes-All",
    "00299570-246d-11d0-a768-00aa006e0529": "User-Force-Change-Password"
}

def format_guid(guid_bytes):
    """Formats 16 bytes of GUID into a canonical string."""
    if not guid_bytes or len(guid_bytes) != 16:
        return None
    return str(uuid.UUID(bytes_le=guid_bytes))

class ACLCrawler:
    def __init__(self, snapshot_path: str):
        self.snapshot_path = snapshot_path
        self.objects = []
        self.sid_to_name = {}
        self.load_snapshot()

    def load_snapshot(self):
        with open(self.snapshot_path, 'r') as f:
            self.objects = json.load(f)
        
        # Well-known SIDs
        self.sid_to_name = {
            "S-1-5-32-544": "Administrators",
            "S-1-5-32-545": "Users",
            "S-1-5-32-548": "Account Operators",
            "S-1-5-32-549": "Server Operators",
            "S-1-5-32-550": "Print Operators",
            "S-1-5-32-551": "Backup Operators",
            "S-1-1-0": "Everyone",
            "S-1-5-11": "Authenticated Users",
            "S-1-5-18": "Local System",
            "S-1-5-9": "Enterprise Domain Controllers",
        }
        
        # Build SID map from snapshot
        for obj in self.objects:
            if 'objectSid' in obj and 'sAMAccountName' in obj:
                sid = obj['objectSid']['value']
                name = obj['sAMAccountName']['value']
                self.sid_to_name[sid] = name

    def parse_acls(self) -> List[Dict]:
        edges = []
        dacl_count = 0
        print(f"[*] Parsing ACLs for {len(self.objects)} objects...")
        
        for obj in self.objects:
            # Prefer sAMAccountName, fallback to Distinguished Name for OUs/Domain
            target_name = obj.get('sAMAccountName', {}).get('value')
            if not target_name:
                target_name = obj.get('distinguishedName', {}).get('value')
                
            if not target_name:
                continue
                
            sd_hex = obj.get('nTSecurityDescriptor', {}).get('value')
            if not sd_hex:
                continue

            try:
                sd_bytes = bytes.fromhex(sd_hex)
                sd = SR_SECURITY_DESCRIPTOR(sd_bytes)
                
                # Owner relationship
                if sd['OwnerSid']:
                    owner_sid = sd['OwnerSid'].formatCanonical()
                    owner_name = self.sid_to_name.get(owner_sid, owner_sid)
                    if owner_name != target_name:
                        edges.append({'source': owner_name, 'target': target_name, 'type': EdgeType.OWNS})

                dacl = sd['Dacl']
                if dacl is None:
                    continue
                
                dacl_count += 1
                for ace in dacl['Data']:
                    if ace['AceType'] not in [0, 5]: # We care about ALLOW and OBJECT_ALLOW
                        continue
                        
                    trustee_sid = ace['Ace']['Sid'].formatCanonical()
                    trustee_name = self.sid_to_name.get(trustee_sid, trustee_sid)
                    
                    if trustee_name == target_name:
                        continue

                    mask = ace['Ace']['Mask']['Mask']
                    
                    # 1. GenericAll (0xf01ff)
                    if (mask & 0xf01ff) == 0xf01ff:
                        edges.append({'source': trustee_name, 'target': target_name, 'type': EdgeType.GENERIC_ALL})
                        continue 
                    
                    # 2. WriteDACL (0x40000)
                    if (mask & 0x40000) == 0x40000:
                        edges.append({'source': trustee_name, 'target': target_name, 'type': EdgeType.WRITE_DACL})
                    
                    # 3. WriteOwner (0x80000)
                    if (mask & 0x80000) == 0x80000:
                        edges.append({'source': trustee_name, 'target': target_name, 'type': EdgeType.WRITE_OWNER})

                    # 4. Extended Rights (DCSync, ForceChangePassword)
                    if (mask & 0x100) == 0x100: # Control Access
                        if ace['AceType'] == 5: # OBJECT_ACE
                            flags = ace['Ace']['Flags']
                            if flags & 0x01: # ACE_OBJECT_TYPE_PRESENT
                                obj_type_bytes = ace['Ace']['ObjectType']
                                obj_type_guid = format_guid(obj_type_bytes)
                                
                                if obj_type_guid in EXTENDED_RIGHTS_GUIDS:
                                    right_name = EXTENDED_RIGHTS_GUIDS[obj_type_guid]
                                    if "Get-Changes" in right_name:
                                        edges.append({'source': trustee_name, 'target': target_name, 'type': EdgeType.DC_SYNC})
                                    elif right_name == "User-Force-Change-Password":
                                        edges.append({'source': trustee_name, 'target': target_name, 'type': EdgeType.FORCE_CHANGE_PASSWORD})

            except Exception:
                pass
                
        print(f"[+] Processed {dacl_count} DACLs.")
        return edges

if __name__ == "__main__":
    # Find latest snapshot
    snapshots = glob.glob("data/snapshot_*.json")
    if not snapshots:
        print("[-] No snapshots found in data/. Run ldap_enum.py first.")
        exit(1)
        
    latest_snapshot = max(snapshots, key=os.path.getctime)
    crawler = ACLCrawler(latest_snapshot)
    edges = crawler.parse_acls()
    
    print(f"[+] Extracted {len(edges)} permission edges.")
    
    # Save edges to a file
    output_path = latest_snapshot.replace("snapshot_", "edges_")
    with open(output_path, 'w') as f:
        json.dump(edges, f, indent=4)
        
    print(f"[+] Edges exported to {output_path}")
    
    # Summary of edge types
    if edges:
        from collections import Counter
        counts = Counter(e['type'] for e in edges)
        print("\n[*] Edge distribution:")
        for etype, count in counts.items():
            print(f"  {etype:20}: {count}")
