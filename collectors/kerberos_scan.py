import os
import json
import glob
from datetime import datetime, timezone

class KerberosScanner:
    def __init__(self, snapshot_path: str):
        self.snapshot_path = snapshot_path
        self.objects = []
        self.load_snapshot()

    def load_snapshot(self):
        with open(self.snapshot_path, 'r') as f:
            self.objects = json.load(f)

    def scan(self) -> dict:
        """
        Identifies Kerberoastable and AS-REP roastable accounts from the snapshot.
        """
        results = {
            'kerberoastable': [],
            'as_rep_roastable': []
        }
        
        print(f"[*] Scanning {len(self.objects)} objects for Kerberos vulnerabilities...")
        
        for obj in self.objects:
            name = obj.get('sAMAccountName', {}).get('value')
            if not name:
                continue
                
            # 1. Kerberoasting (User accounts with ServicePrincipalNames set)
            spns = obj.get('servicePrincipalName', {}).get('value')
            obj_class = obj.get('objectClass', {}).get('value', [])
            
            # Filter for Users (Computers usually have SPNs but are not Kerberoastable)
            is_user = 'person' in obj_class or 'user' in obj_class
            is_computer = 'computer' in obj_class
            
            if spns and is_user and not is_computer:
                results['kerberoastable'].append({
                    'name': name,
                    'spns': spns if isinstance(spns, list) else [spns],
                    'dn': obj.get('distinguishedName', {}).get('value')
                })

            # 2. AS-REP Roasting (DONT_REQ_PREAUTH flag in UAC)
            # UAC flag 0x400000 = UF_DONT_REQUIRE_PREAUTH
            uac_str = obj.get('userAccountControl', {}).get('value')
            if uac_str:
                try:
                    uac = int(uac_str)
                    if (uac & 0x400000):
                        results['as_rep_roastable'].append({
                            'name': name,
                            'uac': uac,
                            'dn': obj.get('distinguishedName', {}).get('value')
                        })
                except ValueError:
                    pass
                    
        return results

if __name__ == "__main__":
    # Find latest snapshot
    snapshots = glob.glob("data/snapshot_*.json")
    if not snapshots:
        print("[-] No snapshots found. Run ldap_enum.py first.")
        exit(1)
        
    latest_snapshot = max(snapshots, key=os.path.getctime)
    scanner = KerberosScanner(latest_snapshot)
    vulnerabilities = scanner.scan()
    
    print(f"[+] Found {len(vulnerabilities['kerberoastable'])} Kerberoastable accounts.")
    print(f"[+] Found {len(vulnerabilities['as_rep_roastable'])} AS-REP roastable accounts.")
    
    # Export results
    output_path = latest_snapshot.replace("snapshot_", "kerberos_")
    with open(output_path, 'w') as f:
        json.dump(vulnerabilities, f, indent=4)
        
    print(f"[+] Kerberos findings exported to {output_path}")
    
    # Print sample
    if vulnerabilities['kerberoastable']:
        print(f"[*] Sample Kerberoastable: {vulnerabilities['kerberoastable'][0]['name']}")
    if vulnerabilities['as_rep_roastable']:
        print(f"[*] Sample AS-REP Roastable: {vulnerabilities['as_rep_roastable'][0]['name']}")
