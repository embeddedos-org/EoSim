# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Industrial bus protocol peripherals for EoSim simulation."""
from collections import deque
from eosim.engine.native.peripherals.buses import BusBase


class EtherCATController(BusBase):
    """EtherCAT industrial fieldbus controller."""
    def __init__(self, name='ecat0', base_addr=0x40310000):
        super().__init__(name, base_addr)
        self.slaves = 0
        self.cycle_time_us = 1000
        self.state = 'INIT'
        self.pdo_count = 0
    def simulate_tick(self):
        super().simulate_tick()
        if self.state == 'OP':
            self.pdo_count += 1


class PROFINETController(BusBase):
    """PROFINET IO controller."""
    def __init__(self, name='pnet0', base_addr=0x40310100):
        super().__init__(name, base_addr)
        self.devices = 0
        self.cycle_time_ms = 1
        self.state = 'OFFLINE'
    def simulate_tick(self):
        super().simulate_tick()


class ModbusTCPController(BusBase):
    """Modbus TCP server/client controller."""
    def __init__(self, name='mbtcp0', base_addr=0x40310200):
        super().__init__(name, base_addr)
        self.registers = [0] * 256
        self.coils = [False] * 256
        self.connections = 0
    def simulate_tick(self):
        super().simulate_tick()
    def read_holding(self, addr, count=1):
        return self.registers[addr:addr+count]
    def write_holding(self, addr, values):
        for i, v in enumerate(values):
            if addr + i < len(self.registers):
                self.registers[addr + i] = v


class OPCUAServer(BusBase):
    """OPC UA server node."""
    def __init__(self, name='opcua0', base_addr=0x40310300):
        super().__init__(name, base_addr)
        self.nodes = {}
        self.sessions = 0
        self.subscriptions = 0
    def simulate_tick(self):
        super().simulate_tick()
    def add_node(self, node_id, value):
        self.nodes[node_id] = value
    def get_node(self, node_id):
        return self.nodes.get(node_id)


class HARTController(BusBase):
    """HART (Highway Addressable Remote Transducer) bus controller."""
    def __init__(self, name='hart0', base_addr=0x40310400):
        super().__init__(name, base_addr)
        self.current_ma = 4.0  # 4-20mA
        self.device_status = 0
    def simulate_tick(self):
        super().simulate_tick()
    def set_current(self, ma):
        self.current_ma = max(4.0, min(20.0, ma))
