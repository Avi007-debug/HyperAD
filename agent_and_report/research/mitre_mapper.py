from typing import Dict, TypedDict, List

class MitreMapping(TypedDict):
    tactic_id: str
    tactic_name: str
    technique_id: str
    technique_name: str

AD_VULN_TO_MITRE_MAP: Dict[str, MitreMapping] = {
    "Kerberoasting": {
        "tactic_id": "TA0006",
        "tactic_name": "Credential Access",
        "technique_id": "T1558.003",
        "technique_name": "Steal or Forge Kerberos Tickets: Kerberoasting"
    },
    "DCSync": {
        "tactic_id": "TA0006",
        "tactic_name": "Credential Access",
        "technique_id": "T1003.006",
        "technique_name": "OS Credential Dumping: DCSync"
    },
    "AS-REP Roasting": {
        "tactic_id": "TA0006",
        "tactic_name": "Credential Access",
        "technique_id": "T1558.004",
        "technique_name": "Steal or Forge Kerberos Tickets: AS-REP Roasting"
    },
    "Pass the Hash": {
        "tactic_id": "TA0008",
        "tactic_name": "Lateral Movement",
        "technique_id": "T1550.002",
        "technique_name": "Use Alternate Authentication Material: Pass the Hash"
    },
    "Pass the Ticket": {
        "tactic_id": "TA0008",
        "tactic_name": "Lateral Movement",
        "technique_id": "T1550.003",
        "technique_name": "Use Alternate Authentication Material: Pass the Ticket"
    },
    "Overpass the Hash": {
        "tactic_id": "TA0008",
        "tactic_name": "Lateral Movement",
        "technique_id": "T1550.002",
        "technique_name": "Use Alternate Authentication Material: Pass the Hash"
    },
    "Golden Ticket": {
        "tactic_id": "TA0006",
        "tactic_name": "Credential Access",
        "technique_id": "T1558.001",
        "technique_name": "Steal or Forge Kerberos Tickets: Golden Ticket"
    },
    "Silver Ticket": {
        "tactic_id": "TA0006",
        "tactic_name": "Credential Access",
        "technique_id": "T1558.002",
        "technique_name": "Steal or Forge Kerberos Tickets: Silver Ticket"
    },
    "BloodHound Reconnaissance": {
        "tactic_id": "TA0007",
        "tactic_name": "Discovery",
        "technique_id": "T1069.002",
        "technique_name": "Permission Groups Discovery: Domain Groups"
    },
    "Zerologon": {
        "tactic_id": "TA0006",
        "tactic_name": "Credential Access",
        "technique_id": "T1110.001",
        "technique_name": "Brute Force: Password Guessing"
    },
    "PrintNightmare": {
        "tactic_id": "TA0004",
        "tactic_name": "Privilege Escalation",
        "technique_id": "T1068",
        "technique_name": "Exploitation for Privilege Escalation"
    },
    "PetitPotam": {
        "tactic_id": "TA0006",
        "tactic_name": "Credential Access",
        "technique_id": "T1187",
        "technique_name": "Forced Authentication"
    },
    "Shadow Credentials": {
        "tactic_id": "TA0006",
        "tactic_name": "Credential Access",
        "technique_id": "T1556",
        "technique_name": "Modify Authentication Process"
    },
    "Unconstrained Delegation": {
        "tactic_id": "TA0004",
        "tactic_name": "Privilege Escalation",
        "technique_id": "T1134.001",
        "technique_name": "Access Token Manipulation: Token Impersonation/Theft"
    },
    "GenericAll on DA": {
        "tactic_id": "TA0003",
        "tactic_name": "Persistence",
        "technique_id": "T1098",
        "technique_name": "Account Manipulation"
    },
    "Constrained Delegation": {
        "tactic_id": "TA0004",
        "tactic_name": "Privilege Escalation",
        "technique_id": "T1078.002",
        "technique_name": "Valid Accounts: Domain Accounts"
    },
    "Resource-Based Constrained Delegation": {
        "tactic_id": "TA0004",
        "tactic_name": "Privilege Escalation",
        "technique_id": "T1078.002",
        "technique_name": "Valid Accounts: Domain Accounts"
    }
}

def get_mitre_mapping(vuln_name: str) -> MitreMapping:
    """Retrieve the MITRE ATT&CK mapping for a given vulnerability name."""
    return AD_VULN_TO_MITRE_MAP.get(vuln_name, {
        "tactic_id": "Unknown",
        "tactic_name": "Unknown",
        "technique_id": "Unknown",
        "technique_name": "Unknown"
    })
