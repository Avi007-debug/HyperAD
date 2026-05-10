import os
import json
import glob
from impacket.dcerpc.v5.srvs import NetrSessionEnum
from impacket.dcerpc.v5 import transport
from impacket.dcerpc.v5.rpcrt import DCERPC_v5
from impacket.dcerpc.v5.ndr import NULL

class SessionMapper:
    def __init__(self, snapshot_path: str, username: str, password: str, domain: str):
        self.snapshot_path = snapshot_path
        self.username = username
        self.password = password
        self.domain = domain
        self.objects = []
        self.load_snapshot()

    def load_snapshot(self):
        with open(self.snapshot_path, 'r') as f:
            self.objects = json.load(f)

    def get_computers(self) -> list:
        """Extracts computer names from the LDAP snapshot."""
        computers = []
        for obj in self.objects:
            obj_class = obj.get('objectClass', {}).get('value', [])
            if 'computer' in obj_class:
                # Try to get sAMAccountName (strip the $)
                name = obj.get('sAMAccountName', {}).get('value')
                if name:
                    computers.append(name.replace('$', ''))
        return list(set(computers))

    def map_sessions(self) -> list:
        """
        Attempts to enumerate SMB sessions on all discovered computers.
        Note: Requires local admin or specific permissions on the target.
        """
        computers = self.get_computers()
        sessions = []
        
        print(f"[*] Attempting to map SMB sessions on {len(computers)} computers...")
        
        for target in computers:
            print(f"[*] Querying {target}...")
            try:
                # Simple NetSessionEnum implementation via Impacket
                # This is a common lateral movement technique
                string_binding = f'ncacn_np:{target}[\\pipe\\srvsvc]'
                rpc_transport = transport.DCERPCTransportFactory(string_binding)
                rpc_transport.set_credentials(self.username, self.password, self.domain, '', '')
                rpc_transport.set_connect_timeout(2) # Short timeout for speed
                
                dce = rpc_transport.get_dce_rpc()
                dce.connect()
                dce.bind(NetrSessionEnum.uuid_sentinel)
                
                # Level 10 (SESI10) gives username and client computer name
                resp = NetrSessionEnum(dce, NULL, NULL, 10)
                
                for session in resp['InfoStruct']['SessionInfo']['Level10']['Buffer']:
                    user = session['sesi10_username'].replace('\x00', '')
                    computer = session['sesi10_cname'].replace('\x00', '').replace('\\', '')
                    
                    if user and user not in ['Administrator', '']:
                        sessions.append({
                            'source_user': user,
                            'target_computer': target,
                            'client_computer': computer,
                            'type': 'HasSession'
                        })
                
                dce.disconnect()
            except Exception as e:
                # print(f"[-] Could not query sessions on {target}: {e}")
                pass
                
        return sessions

if __name__ == "__main__":
    # Settings from environment (from user's previous input)
    DC_IP = os.environ.get("AD_DC_IP", "172.16.229.129")
    DOMAIN = os.environ.get("AD_DOMAIN", "MARVEL.local")
    USER = os.environ.get("AD_USER", "Administrator")
    PASS = os.environ.get("AD_PASSWORD", "P@$$w0rd!")

    snapshots = glob.glob("data/snapshot_*.json")
    if not snapshots:
        print("[-] No snapshots found.")
        exit(1)
        
    latest = max(snapshots, key=os.path.getctime)
    mapper = SessionMapper(latest, USER, PASS, DOMAIN)
    
    found_sessions = mapper.map_sessions()
    
    print(f"[+] Found {len(found_sessions)} active user sessions.")
    
    # Export results
    output_path = latest.replace("snapshot_", "sessions_")
    with open(output_path, 'w') as f:
        json.dump(found_sessions, f, indent=4)
        
    print(f"[+] Sessions exported to {output_path}")
    
    if found_sessions:
        for s in found_sessions:
            print(f"  {s['source_user']} is logged into {s['target_computer']}")
