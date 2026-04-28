# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Network bus peripherals for EoSim simulation."""
from eosim.engine.native.peripherals.buses import BusBase


class EthernetMAC(BusBase):
    """Ethernet MAC controller (10/100/1000 Mbps)."""
    def __init__(self, name='eth0', base_addr=0x40320000):
        super().__init__(name, base_addr)
        self.link_up = False
        self.speed_mbps = 1000
        self.duplex = 'full'
        self.rx_packets = 0
        self.tx_packets = 0
    def simulate_tick(self):
        super().simulate_tick()
        if self.link_up:
            self.rx_packets += 1
            self.tx_packets += 1


class USBController(BusBase):
    """USB 2.0/3.0 host/device controller."""
    def __init__(self, name='usb0', base_addr=0x40320100, version='2.0'):
        super().__init__(name, base_addr)
        self.version = version
        self.devices_connected = 0
        self.state = 'detached'
    def simulate_tick(self):
        super().simulate_tick()


class PCIeController(BusBase):
    """PCIe root complex / endpoint controller."""
    def __init__(self, name='pcie0', base_addr=0x40320200, lanes=4):
        super().__init__(name, base_addr)
        self.lanes = lanes
        self.gen = 3
        self.link_up = False
        self.bar_size = 0x10000
    def simulate_tick(self):
        super().simulate_tick()


class HDMIController(BusBase):
    """HDMI transmitter/receiver controller."""
    def __init__(self, name='hdmi0', base_addr=0x40320300):
        super().__init__(name, base_addr)
        self.connected = False
        self.resolution = (1920, 1080)
        self.refresh_hz = 60
        self.cec_enabled = True
    def simulate_tick(self):
        super().simulate_tick()


class I2SController(BusBase):
    """I2S digital audio bus controller."""
    def __init__(self, name='i2s0', base_addr=0x40320400):
        super().__init__(name, base_addr)
        self.sample_rate = 48000
        self.bit_depth = 16
        self.channels = 2
        self.playing = False
    def simulate_tick(self):
        super().simulate_tick()
