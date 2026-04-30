# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Extended wireless peripherals for EoSim simulation."""
from eosim.engine.native.peripherals.wireless import WirelessBase


class NFCController(WirelessBase):
    """NFC (Near Field Communication) controller."""
    def __init__(self, name='nfc0', base_addr=0x40410000):
        super().__init__(name, base_addr)
        self.tag_present = False
        self.tag_uid = ''
        self.ndef_data = b''
    def simulate_tick(self):
        super().simulate_tick()


class UWBController(WirelessBase):
    """Ultra-Wideband (UWB) ranging controller."""
    def __init__(self, name='uwb0', base_addr=0x40410100):
        super().__init__(name, base_addr)
        self.distance_m = 0.0
        self.angle_deg = 0.0
        self.anchors = 0
    def simulate_tick(self):
        super().simulate_tick()


class SatelliteComm(WirelessBase):
    """Satellite communication module (Iridium/Starlink)."""
    def __init__(self, name='satcom0', base_addr=0x40410200):
        super().__init__(name, base_addr)
        self.signal_strength = 0
        self.link_up = False
        self.data_rate_kbps = 0
    def simulate_tick(self):
        super().simulate_tick()


class LTECatM1(WirelessBase):
    """LTE Cat-M1 cellular modem."""
    def __init__(self, name='ltem0', base_addr=0x40410300):
        super().__init__(name, base_addr)
        self.rssi_dbm = -85
        self.registered = False
        self.data_rate_kbps = 375
    def simulate_tick(self):
        super().simulate_tick()


class NBIoT(WirelessBase):
    """NB-IoT (Narrowband IoT) cellular modem."""
    def __init__(self, name='nbiot0', base_addr=0x40410400):
        super().__init__(name, base_addr)
        self.rssi_dbm = -100
        self.registered = False
        self.data_rate_kbps = 62.5
    def simulate_tick(self):
        super().simulate_tick()


class ThreadController(WirelessBase):
    """Thread mesh networking controller."""
    def __init__(self, name='thread0', base_addr=0x40410500):
        super().__init__(name, base_addr)
        self.role = 'detached'  # router, child, leader
        self.partition_id = 0
        self.neighbors = 0
    def simulate_tick(self):
        super().simulate_tick()


class MatterController(WirelessBase):
    """Matter (CHIP) smart home protocol controller."""
    def __init__(self, name='matter0', base_addr=0x40410600):
        super().__init__(name, base_addr)
        self.commissioned = False
        self.fabric_id = 0
        self.endpoint_count = 1
    def simulate_tick(self):
        super().simulate_tick()
