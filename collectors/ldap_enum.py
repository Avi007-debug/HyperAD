import os
import json
from datetime import datetime, timezone
from ldap3 import Server, Connection, ALL, NTLM, SUBTREE

def wrap_attribute(value, timestamp_iso: str) -> dict:
    """
    Wraps an AD attribute value in the HyperAD temporal format.
    Every attribute value is stored as a dict with its value and discovery timestamps.
    """
    return {
        'value': value,
        'last_seen': timestamp_iso,
        'first_seen': timestamp_iso
    }

class LDAPCollector:
    def __init__(self, dc_ip: str, domain: str, username: str, password: str):
        self.dc_ip = dc_ip
        self.domain = domain
        self.username = username
        self.password = password
        self.base_dn = ",".join([f"DC={part}" for part in domain.split(".")])
        self.collection_time = datetime.now(timezone.utc).isoformat()
        
    def connect(self) -> Connection:
        """Establishes an NTLM authenticated bind to the Domain Controller."""
        server = Server(self.dc_ip, get_info=ALL)
        user_upn = f"{self.domain}\\{self.username}"
        conn = Connection(
            server, 
            user=user_upn, 
            password=self.password, 
            authentication=NTLM, 
            auto_bind=True
        )
        return conn

    def enumerate_objects(self) -> list:
        """
        Pulls users, groups, computers, OUs, and GPOs.
        Extracts requested attributes and applies the temporal wrapper.
        """
        conn = self.connect()
        print(f"[*] Bound to {self.dc_ip} as {self.domain}\\{self.username}")
        print(f"[*] Server Info: {conn.server.info}")
        
        # Attributes explicitly requested in P2 spec
        attributes_to_pull = [
            'sAMAccountName',
            'objectSid',
            'memberOf',
            'servicePrincipalName',
            'msDS-AllowedToDelegateTo',
            'userAccountControl',
            'pwdLastSet',
            'lastLogon',
            'objectClass',
            'nTSecurityDescriptor' # Needed later by acl_crawler.py
        ]
        
        # Filter for identity and structure objects
        search_filter = '(|(objectCategory=person)(objectClass=group)(objectClass=computer)(objectClass=organizationalUnit)(objectClass=groupPolicyContainer)(objectClass=domainDNS))'
        
        print(f"[*] Starting subtree search from {self.base_dn}...")
        conn.search(
            search_base=self.base_dn,
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=attributes_to_pull,
            paged_size=1000
        )
        
        objects = []
        for entry in conn.entries:
            obj_data = {
                'distinguishedName': wrap_attribute(entry.entry_dn, self.collection_time)
            }
            
            # Map ldap3 attributes into our structure
            for attr in attributes_to_pull:
                if attr in entry and entry[attr].value is not None:
                    raw_val = entry[attr].value
                    
                    # Handle raw byte arrays (like nTSecurityDescriptor) by encoding them to hex or b64
                    # for JSON serialization, or skipping them if parsing is strictly delegated to acl_crawler.
                    if attr == 'nTSecurityDescriptor':
                        # Simplistic hex representation for now. acl_crawler.py might need raw bytes.
                        obj_data[attr] = wrap_attribute(raw_val.hex(), self.collection_time)
                        continue
                        
                    # Handle multi-valued attributes (lists)
                    if isinstance(raw_val, list):
                        # Ensure all items in list are strings (e.g. memberOf)
                        str_list = [str(v) for v in raw_val]
                        obj_data[attr] = wrap_attribute(str_list, self.collection_time)
                    else:
                        # Handle datetime objects (e.g. pwdLastSet)
                        if hasattr(raw_val, 'isoformat'):
                            str_val = raw_val.isoformat()
                        else:
                            str_val = str(raw_val)
                        obj_data[attr] = wrap_attribute(str_val, self.collection_time)
                        
            objects.append(obj_data)
            
        print(f"[+] Found {len(objects)} objects.")
        conn.unbind()
        return objects

    def export_snapshot(self, objects: list, output_dir: str = "data") -> str:
        """Writes the collected objects to a timestamped JSON file."""
        os.makedirs(output_dir, exist_ok=True)
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"snapshot_{timestamp_str}.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(objects, f, indent=4)
            
        print(f"[+] Snapshot exported to {filepath}")
        return filepath

if __name__ == "__main__":
    # Test script against the Lab DC
    # Usage: python collectors/ldap_enum.py
    
    # Defaults based on Phase 0 setup
    LAB_DC_IP = os.environ.get("AD_DC_IP", "192.168.1.100") 
    LAB_DOMAIN = os.environ.get("AD_DOMAIN", "lab.local")
    LAB_USER = os.environ.get("AD_USER", "Administrator")
    LAB_PASS = os.environ.get("AD_PASSWORD", "Password@1")
    
    try:
        collector = LDAPCollector(LAB_DC_IP, LAB_DOMAIN, LAB_USER, LAB_PASS)
        data = collector.enumerate_objects()
        
        # P2 Spec: Write data/snapshot_YYYYMMDD_HHMMSS.json
        collector.export_snapshot(data, output_dir="data")
        
    except Exception as e:
        print(f"[-] LDAP Enumeration failed: {e}")
        print("[!] Ensure you have started your lab VM and 'ldap3' is installed.")
