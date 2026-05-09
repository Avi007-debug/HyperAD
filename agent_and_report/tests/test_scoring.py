import unittest
from research.confidence_scorer import calculate_attack_probability, sigmoid

class TestConfidenceScorer(unittest.TestCase):
    
    def test_sigmoid(self):
        # Sigmoid of 0 is 0.5
        self.assertAlmostEqual(sigmoid(0), 0.5)

    def test_calculate_attack_probability(self):
        # Calculate P = P_active * P_weak_pwd * P_reachable
        # P_active = sigmoid((365 - 365) / 100) = sigmoid(0) = 0.5
        # P_weak_pwd = sigmoid((180 - 180) / 60) = sigmoid(0) = 0.5
        # P_reachable = 0.8
        # P = 0.5 * 0.5 * 0.8 = 0.2
        prob = calculate_attack_probability(p_reachable=0.8, days_since_login=365, pwd_age=180)
        self.assertAlmostEqual(prob, 0.2)

    def test_no_pwd_last_set(self):
        # P_weak_pwd should be 1.0
        # P_active = sigmoid((365 - 365) / 100) = 0.5
        # P_reachable = 0.8
        # P = 0.5 * 1.0 * 0.8 = 0.4
        prob = calculate_attack_probability(p_reachable=0.8, days_since_login=365, pwd_age=0, has_pwd_last_set=False)
        self.assertAlmostEqual(prob, 0.4)

    def test_invalid_p_reachable(self):
        with self.assertRaises(ValueError):
            calculate_attack_probability(1.5, 90, 60)
        with self.assertRaises(ValueError):
            calculate_attack_probability(-0.1, 90, 60)

if __name__ == '__main__':
    unittest.main()
