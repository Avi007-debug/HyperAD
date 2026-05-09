import networkx as nx
from typing import Tuple, List

class CounterfactualAnalyzer:
    def __init__(self, graph: nx.DiGraph):
        """
        Initialize with a base Active Directory graph.
        :param graph: A directed graph representing AD nodes and relationships.
        """
        self.base_graph = graph

    def simulate_remediation(self, edge_to_remove: Tuple[str, str], target_node: str) -> dict:
        """
        Simulate removing an edge (remediation) and calculate the delta in attack paths to a target.
        
        :param edge_to_remove: Tuple of (source, destination) representing the relationship to remove.
        :param target_node: The critical node (e.g., Domain Admin) to calculate paths to.
        :return: A dictionary containing the delta and path information.
        """
        # Clone the graph to perform What-If analysis
        what_if_graph = self.base_graph.copy()
        
        # Calculate original reachable paths to target
        original_paths = self._get_paths_to_target(self.base_graph, target_node)
        
        # Remove the edge if it exists
        if what_if_graph.has_edge(*edge_to_remove):
            what_if_graph.remove_edge(*edge_to_remove)
            
        # Calculate new reachable paths to target
        new_paths = self._get_paths_to_target(what_if_graph, target_node)
        
        # Calculate delta
        delta_paths = len(original_paths) - len(new_paths)
        
        return {
            "edge_removed": edge_to_remove,
            "target_node": target_node,
            "original_path_count": len(original_paths),
            "new_path_count": len(new_paths),
            "delta": delta_paths,
            "is_effective": delta_paths > 0,
            "paths_eliminated": [path for path in original_paths if path not in new_paths]
        }

    def _get_paths_to_target(self, g: nx.DiGraph, target: str) -> List[List[str]]:
        """
        Helper method to find all simple paths to the target from any source.
        In a real scenario, this might just check reachability or shortest paths due to scale.
        """
        all_paths = []
        for node in g.nodes():
            if node != target and nx.has_path(g, node, target):
                # For simplicity in mock, just get the shortest paths to avoid combinatorial explosion
                try:
                    paths = list(nx.all_shortest_paths(g, node, target))
                    all_paths.extend(paths)
                except nx.NetworkXNoPath:
                    continue
        # Convert to tuple for hashing/comparing, then back to list
        unique_paths = list(set(tuple(p) for p in all_paths))
        return [list(p) for p in unique_paths]

