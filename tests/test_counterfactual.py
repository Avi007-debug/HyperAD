import unittest
import networkx as nx
from ai_agent.counterfactual import CounterfactualAnalyzer

class TestCounterfactualAnalyzer(unittest.TestCase):
    
    def setUp(self):
        # Create a simple mock AD graph
        self.graph = nx.DiGraph()
        self.graph.add_edges_from([
            ("UserA", "Group1"),
            ("Group1", "Domain_Admin"),
            ("UserB", "Group2"),
            ("Group2", "Group1"),
            ("UserC", "Domain_Admin")
        ])
        self.analyzer = CounterfactualAnalyzer(self.graph)

    def test_simulate_remediation_effective(self):
        # Removing Group1 -> Domain_Admin should break paths from UserA and UserB to Domain_Admin
        result = self.analyzer.simulate_remediation(("Group1", "Domain_Admin"), "Domain_Admin")
        
        self.assertTrue(result["is_effective"])
        self.assertGreater(result["delta"], 0)
        # Original paths: UserA->Group1->DA, Group1->DA, UserB->Group2->Group1->DA, Group2->Group1->DA, UserC->DA
        # Removing Group1->DA eliminates all except UserC->DA
        self.assertEqual(result["new_path_count"], 1)

    def test_simulate_remediation_ineffective(self):
        # Removing a non-critical edge or one not leading to the target
        self.graph.add_edge("UserD", "UserE")
        analyzer = CounterfactualAnalyzer(self.graph)
        result = analyzer.simulate_remediation(("UserD", "UserE"), "Domain_Admin")
        
        self.assertFalse(result["is_effective"])
        self.assertEqual(result["delta"], 0)

    def test_simulate_remediation_nonexistent_edge(self):
        result = self.analyzer.simulate_remediation(("UserA", "Domain_Admin"), "Domain_Admin")
        self.assertFalse(result["is_effective"])
        self.assertEqual(result["delta"], 0)

if __name__ == '__main__':
    unittest.main()
