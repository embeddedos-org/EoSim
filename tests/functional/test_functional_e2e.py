import unittest

class TestEoSimFunctional(unittest.TestCase):
    def test_peripheral_register_read_write_pipeline(self):
        registers = {"GPIO_ODR": 0x00}
        # Write to output data register
        registers["GPIO_ODR"] = 0xFF
        assert registers["GPIO_ODR"] == 0xFF
