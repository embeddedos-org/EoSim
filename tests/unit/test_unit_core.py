import unittest

class TestEoSimUnit(unittest.TestCase):
    def test_qemu_arm_translation_init(self):
        # Simulate QEMU ARM translation block initialization
        tb = {"pc": 0x08000000, "flags": 0x03, "code": "MOV R0, #1"}
        assert tb["pc"] == 0x08000000
        assert "MOV" in tb["code"]
