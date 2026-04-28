# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Advanced composite peripherals for EoSim simulation."""
import random
from eosim.engine.native.peripherals.composites import CompositeBase


class NPUAccelerator(CompositeBase):
    """Neural Processing Unit (NPU) accelerator."""
    def __init__(self, name='npu0', base_addr=0x40510000, tops=8):
        super().__init__(name, base_addr)
        self.tops = tops  # Tera-operations per second
        self.utilization_pct = 0
        self.inference_count = 0
        self.temperature_c = 35.0
    def simulate_tick(self):
        if self.utilization_pct > 0:
            self.temperature_c += 0.01 * self.utilization_pct
            self.inference_count += 1
        self.temperature_c = max(25, min(95, self.temperature_c - 0.05))


class GPUCompute(CompositeBase):
    """GPU compute unit for parallel processing."""
    def __init__(self, name='gpu0', base_addr=0x40510100, cores=128):
        super().__init__(name, base_addr)
        self.cores = cores
        self.clock_mhz = 1000
        self.utilization_pct = 0
        self.memory_mb = 4096
        self.temperature_c = 40.0
    def simulate_tick(self):
        self.temperature_c += self.utilization_pct * 0.005
        self.temperature_c = max(30, min(100, self.temperature_c - 0.1))


class FPGAFabric(CompositeBase):
    """FPGA programmable fabric."""
    def __init__(self, name='fpga0', base_addr=0x40510200, luts=50000):
        super().__init__(name, base_addr)
        self.luts = luts
        self.utilization_pct = 0
        self.configured = False
        self.bitstream_loaded = False
    def simulate_tick(self):
        pass


class SecureElement(CompositeBase):
    """Secure element / crypto coprocessor (e.g., ATECC608)."""
    def __init__(self, name='se0', base_addr=0x40510300):
        super().__init__(name, base_addr)
        self.locked = True
        self.keys_stored = 0
        self.max_keys = 16
        self.rng_value = 0
    def simulate_tick(self):
        self.rng_value = random.randint(0, 0xFFFFFFFF)
    def read_reg(self, offset):
        if offset == 0x00: return self.rng_value
        if offset == 0x04: return self.keys_stored
        return 0


class TPMModule(CompositeBase):
    """Trusted Platform Module (TPM 2.0)."""
    def __init__(self, name='tpm0', base_addr=0x40510400):
        super().__init__(name, base_addr)
        self.pcr_count = 24
        self.pcrs = [0] * 24
        self.sealed = False
    def simulate_tick(self):
        pass
    def extend_pcr(self, index, value):
        if 0 <= index < self.pcr_count:
            self.pcrs[index] ^= value


class PowerManager(CompositeBase):
    """System power management controller (PMIC)."""
    def __init__(self, name='pmic0', base_addr=0x40510500):
        super().__init__(name, base_addr)
        self.rails = {'vcore': 1.0, 'vio': 3.3, 'vmem': 1.8}
        self.power_mode = 'run'  # run, sleep, deep_sleep, shutdown
        self.total_power_mw = 500
    def simulate_tick(self):
        if self.power_mode == 'run':
            self.total_power_mw = 500 + random.gauss(0, 10)
        elif self.power_mode == 'sleep':
            self.total_power_mw = 50 + random.gauss(0, 2)
        elif self.power_mode == 'deep_sleep':
            self.total_power_mw = 0.5 + random.gauss(0, 0.05)
    def read_reg(self, offset):
        if offset == 0x00: return int(self.total_power_mw * 100) & 0xFFFFFFFF
        return 0
