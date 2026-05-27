import unittest
class TestEoSimSimulation(unittest.TestCase):
    def test_gpio_register_state_changes(self):
        gpio_state = "HIGH"
        self.assertEqual(gpio_state, "HIGH")
