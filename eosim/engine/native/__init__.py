# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
import os
import time
from typing import Optional

from eosim.engine.native.cpu import CPUSimulator, CPUState
from eosim.engine.native.memory import MemoryBus, MemoryRegion
from eosim.engine.native.peripherals import (
    GPIODevice,
    I2CDevice,
    InterruptController,
    SPIDevice,
    TimerDevice,
    UARTDevice,
)


class VirtualMachine:
    def __init__(
        self, name: str = "eosim-vm", arch: str = "arm64", ram_mb: int = 512, flash_mb: int = 0
    ):
        self.name = name
        self.arch = arch
        self.bus = MemoryBus()
        self.cpu = CPUSimulator(arch)
        self.cpu.memory = self.bus
        self.running = False
        self.boot_log: list = []
        self.peripherals: dict = {}
        self.start_time = 0.0
        self.cycles_executed = 0
        # Whether real code was mapped. Without it the CPU steps over zeroed
        # memory, which must not be reported as a boot. See run().
        self.firmware_loaded = False
        self.firmware_path: Optional[str] = None

        # Add RAM
        self.bus.add_region(MemoryRegion("ram", 0x20000000, ram_mb * 1024 * 1024))

        # Add Flash if specified
        if flash_mb > 0:
            self.bus.add_region(
                MemoryRegion("flash", 0x08000000, flash_mb * 1024 * 1024, readonly=True)
            )

        # Add default peripherals
        self._add_default_peripherals()

    def _add_default_peripherals(self):
        uart = UARTDevice("uart0", 0x40000000)
        uart.on_tx = lambda ch: self.boot_log.append(ch)
        self.add_peripheral("uart0", uart)

        self.add_peripheral("gpio0", GPIODevice("gpio0", 0x40010000))
        self.add_peripheral("timer0", TimerDevice("timer0", 0x40020000))
        self.add_peripheral("spi0", SPIDevice("spi0", 0x40030000))
        self.add_peripheral("i2c0", I2CDevice("i2c0", 0x40040000))
        self.add_peripheral("nvic", InterruptController("nvic", 0xE000E000))

    def add_peripheral(self, name: str, device):
        self.peripherals[name] = device
        if hasattr(device, "base") and hasattr(device, "io_handler"):
            for offset in range(0, 64, 4):
                self.bus.add_io_handler(device.base + offset, device.io_handler)

    def load_firmware(self, path: str, addr: int = 0x08000000) -> bool:
        if not os.path.exists(path):
            return False
        with open(path, "rb") as f:
            data = f.read()
        flash = MemoryRegion("firmware", addr, len(data), bytearray(data), readonly=True)
        self.bus.add_region(flash)
        self.cpu.reset(entry=addr, stack=0x20000000 + 512 * 1024)
        self.firmware_loaded = True
        self.firmware_path = path
        return True

    def load_binary(self, data: bytes, addr: int = 0x08000000):
        region = MemoryRegion("binary", addr, len(data), bytearray(data))
        self.bus.add_region(region)
        self.cpu.reset(entry=addr, stack=0x20000000 + 512 * 1024)
        self.firmware_loaded = True
        self.firmware_path = "<memory>"

    def run(self, max_cycles: int = 100000, timeout_s: float = 30.0) -> dict:
        """Execute until halt, cycle budget, or timeout.

        `success` reports what happened. It used to be the literal True and the
        engine printed "EoS booted successfully" unconditionally, so a run over
        zeroed memory with no firmware loaded reported a successful EoS boot.
        Nothing distinguished that from a real one.
        """
        self.running = True
        self.start_time = time.time()
        self.boot_log.clear()

        self._uart_print("EoSim Virtual Machine: %s (%s)\n" % (self.name, self.arch))
        self._uart_print(
            "RAM: %d MB | Peripherals: %d\n"
            % (
                sum(r.size for r in self.bus.regions if r.name == "ram") // (1024 * 1024),
                len(self.peripherals),
            )
        )

        if not self.firmware_loaded:
            # Stepping over zeroed memory executes NOP 10000 times. That is not
            # a boot, and calling it one is how a simulator stops being evidence.
            self._uart_print(
                "No firmware loaded - nothing to execute.\n"
                "Load an image with load_firmware(path) or `eosim run <platform> "
                "--firmware <file>`.\n"
            )
            self.running = False
            elapsed = time.time() - self.start_time
            return {
                "success": False,
                "reason": "no-firmware",
                "cycles": 0,
                "duration_s": elapsed,
                "boot_log": self.get_uart_output(),
                "cpu_state": self.cpu.state.dump(),
            }

        self._uart_print("Booting %s...\n" % (self.firmware_path or "image"))

        executed = 0
        reason = "cycle-limit"
        while self.running and executed < max_cycles:
            elapsed = time.time() - self.start_time
            if elapsed > timeout_s:
                reason = "timeout"
                self._uart_print("\nTimeout after %.1fs\n" % elapsed)
                break

            # The instruction retires whether or not it halts the core, so it
            # is counted before the break. Previously the halting instruction
            # was executed but not counted, leaving run()['cycles'] one behind
            # cpu.state.cycles for every program that halts.
            undef_before = self.cpu.undefined_count
            stepped = self.cpu.step()
            executed += 1
            if not stepped:
                # Distinguish a program that chose to stop from one the decoder
                # could not follow. Both leave the core halted.
                if self.cpu.undefined_count > undef_before:
                    reason = "undefined-instruction"
                else:
                    reason = "halted"
                break

            if executed % 100 == 0:
                timer = self.peripherals.get("timer0")
                if timer:
                    timer.tick()

        self.running = False
        self.cycles_executed = executed
        elapsed = time.time() - self.start_time

        # A clean halt (UDF/breakpoint) is the only outcome the firmware chose.
        # Exhausting the cycle budget or the clock means we stopped it, and an
        # undefined opcode means the decoder could not follow the program.
        success = reason == "halted"

        if reason == "undefined-instruction" and self.cpu.last_undefined:
            pc, instr = self.cpu.last_undefined
            self._uart_print(
                "\nUndefined instruction 0x%08X at 0x%08X.\n"
                "This engine decodes a small ARM32 subset; it cannot execute a "
                "full firmware image.\n" % (instr, pc)
            )

        self._uart_print(
            "\nSimulation stopped (%s): %d cycles in %.3fs\n" % (reason, executed, elapsed)
        )

        return {
            "success": success,
            "reason": reason,
            "cycles": executed,
            "duration_s": elapsed,
            "undefined_count": self.cpu.undefined_count,
            "boot_log": self.get_uart_output(),
            "cpu_state": self.cpu.state.dump(),
        }

    def _uart_print(self, msg: str):
        uart = self.peripherals.get("uart0")
        if uart:
            for ch in msg:
                uart.output_log.append(ch)
        self.boot_log.extend(msg)

    def get_uart_output(self) -> str:
        uart = self.peripherals.get("uart0")
        return uart.get_output() if uart else "".join(self.boot_log)

    def get_status(self) -> dict:
        return {
            "name": self.name,
            "arch": self.arch,
            "running": self.running,
            "cycles": self.cycles_executed,
            "peripherals": list(self.peripherals.keys()),
            "memory_regions": [(r.name, f"0x{r.base:08X}", r.size) for r in self.bus.regions],
        }

    def dump_state(self) -> str:
        lines = [f"=== EoSim VM: {self.name} ==="]
        lines.append(self.cpu.state.dump())
        lines.append("\nPeripherals: {}".format(", ".join(self.peripherals.keys())))
        lines.append("Memory regions:")
        for r in self.bus.regions:
            lines.append("  %-10s 0x%08X  %d bytes" % (r.name, r.base, r.size))
        return "\n".join(lines)
