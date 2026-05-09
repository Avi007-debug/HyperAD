"""
HyperAD — Shared data models and types.
All algorithm modules import from here for consistency.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class RiskLevel(str, Enum):
    CRITICAL = "Critical"
    HIGH     = "High"
    MEDIUM   = "Medium"
    LOW      = "Low"
    INFO     = "Info"

    @classmethod
    def from_score(cls, score: float) -> "RiskLevel":
        if score >= 8.0:  return cls.CRITICAL
        if score >= 6.0:  return cls.HIGH
        if score >= 3.0:  return cls.MEDIUM
        if score > 0.0:   return cls.LOW
        return cls.INFO


class NodeType(str, Enum):
    USER             = "User"
    GROUP            = "Group"
    COMPUTER         = "Computer"
    SERVICE_ACCOUNT  = "ServiceAccount"
    OU               = "OU"
    GPO              = "GPO"
    DOMAIN           = "Domain"


class EdgeType(str, Enum):
    MEMBER_OF               = "MemberOf"
    ADMIN_TO                = "AdminTo"
    HAS_SESSION             = "HasSession"
    ALLOWED_TO_DELEGATE     = "AllowedToDelegate"
    ALLOWED_TO_ACT          = "AllowedToActOnBehalfOf"
    GENERIC_ALL             = "GenericAll"
    WRITE_DACL              = "WriteDACL"
    WRITE_OWNER             = "WriteOwner"
    GENERIC_WRITE           = "GenericWrite"
    DC_SYNC                 = "DCSync"
    GET_CHANGES             = "GetChanges"
    FORCE_CHANGE_PASSWORD   = "ForceChangePassword"
    OWNS                    = "Owns"
    GPO_APPLIES             = "GPOApplies"


# Base risk scores per edge type — used by temporal decay formula
BASE_RISK: Dict[str, float] = {
    EdgeType.GENERIC_ALL:           10.0,
    EdgeType.DC_SYNC:               10.0,
    EdgeType.WRITE_DACL:             8.0,
    EdgeType.WRITE_OWNER:            8.0,
    EdgeType.ALLOWED_TO_DELEGATE:    7.5,
    EdgeType.ALLOWED_TO_ACT:         7.5,
    EdgeType.ADMIN_TO:               9.0,
    EdgeType.GENERIC_WRITE:          6.0,
    EdgeType.FORCE_CHANGE_PASSWORD:  5.0,
    EdgeType.OWNS:                   7.0,
    EdgeType.GET_CHANGES:            4.0,
    EdgeType.HAS_SESSION:            3.0,
    EdgeType.MEMBER_OF:              2.0,
    EdgeType.GPO_APPLIES:            2.5,
}


@dataclass
class EscalationPath:
    """One privilege escalation path from source to Domain Admin."""
    nodes:       List[str]          # ordered list of node names
    edges:       List[str]          # edge types along the path
    weights:     List[float]        # temporal weights per edge
    total_score: float              # sum of weights (higher = more dangerous)
    hop_count:   int                = field(init=False)
    risk_level:  RiskLevel          = field(init=False)

    def __post_init__(self):
        self.hop_count  = len(self.nodes) - 1
        self.risk_level = RiskLevel.from_score(self.total_score)

    @property
    def source(self) -> str:
        return self.nodes[0]

    @property
    def target(self) -> str:
        return self.nodes[-1]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source":      self.source,
            "target":      self.target,
            "nodes":       self.nodes,
            "edges":       self.edges,
            "weights":     [round(w, 4) for w in self.weights],
            "total_score": round(self.total_score, 4),
            "hop_count":   self.hop_count,
            "risk_level":  self.risk_level.value,
        }


@dataclass
class SCCFinding:
    """A circular delegation / trust loop detected by Tarjan SCC."""
    nodes:      List[str]
    size:       int           = field(init=False)
    risk_level: RiskLevel     = field(init=False)
    edge_types: List[str]     = field(default_factory=list)

    def __post_init__(self):
        self.size = len(self.nodes)
        # Any cycle in delegation subgraph is at minimum High
        self.risk_level = RiskLevel.CRITICAL if self.size >= 3 else RiskLevel.HIGH

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes":      self.nodes,
            "size":       self.size,
            "risk_level": self.risk_level.value,
            "edge_types": self.edge_types,
            "description": (
                f"Circular delegation loop detected among {self.size} accounts. "
                "An attacker compromising any one of these accounts gains "
                "effective control over all others."
            ),
        }


@dataclass
class HITSResult:
    """Authority and hub scores from the HITS algorithm."""
    node:           str
    authority:      float
    hub:            float
    node_type:      str
    is_da_path:     bool = False   # True if this node has a path to Domain Admin

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node":       self.node,
            "authority":  round(self.authority, 6),
            "hub":        round(self.hub, 6),
            "node_type":  self.node_type,
            "is_da_path": self.is_da_path,
            "priority":   "HIGH" if self.authority > 0.5 else "MEDIUM" if self.authority > 0.2 else "LOW",
        }


@dataclass
class BlastRadiusResult:
    """Reachability from a compromised node."""
    compromised_node: str
    reachable:        Dict[str, int]   # node → min hop distance
    da_reachable:     bool
    da_nodes_hit:     List[str]
    max_hops:         int

    @property
    def total_reachable(self) -> int:
        return len(self.reachable)

    def by_hop(self, hop: int) -> List[str]:
        return [n for n, h in self.reachable.items() if h == hop]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "compromised_node":  self.compromised_node,
            "da_reachable":      self.da_reachable,
            "da_nodes_hit":      self.da_nodes_hit,
            "total_reachable":   self.total_reachable,
            "max_hops":          self.max_hops,
            "by_hop":            {
                h: self.by_hop(h)
                for h in range(1, self.max_hops + 1)
            },
            "risk_level": (
                RiskLevel.CRITICAL.value if self.da_reachable
                else RiskLevel.HIGH.value if self.total_reachable > 20
                else RiskLevel.MEDIUM.value
            ),
        }
