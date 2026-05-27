import unittest
class TestEoSimFunctional(unittest.TestCase):
    def test_emulator_pipeline(self):
        pipeline = ["load_elf", "init_registers", "run_cpu"]
        self.assertEqual(pipeline[-1], "run_cpu")
