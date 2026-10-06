# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Execution and reporting contract for the native engine.

Two things are pinned here.

**The CPU really executes.** eosim/engine/native/cpu implements a small ARM32
subset (MOV imm, B, LDR, STR, BX LR, SVC, UDF). These tests hand-assemble
instructions, run them, and assert the resulting register and memory state, so
"there is a CPU" becomes a measured claim rather than an assumption.

**A run reports what happened.** VirtualMachine.run() used to return the literal
``success: True`` and print "EoS booted successfully" unconditionally, and
``eosim run <platform>`` never loaded any firmware. Stepping over zeroed memory
10000 times therefore printed "PASSED (10000 cycles)" and reported a successful
EoS boot with no EoS involved. These tests fix that behaviour in place:

  no firmware   -> success False, reason 'no-firmware', 0 cycles
  UDF reached   -> success True,  reason 'halted'
  runaway code  -> success False, reason 'cycle-limit'
"""
import struct

from eosim.engine.native import VirtualMachine

FLASH = 0x08000000


def arm(*words: int) -> bytes:
    """Little-endian ARM word stream."""
    return b"".join(struct.pack("<I", w) for w in words)


def mov_imm(rd: int, imm8: int) -> int:
    """MOV Rd, #imm8 — ARM data-processing, no rotate."""
    assert 0 <= rd <= 15 and 0 <= imm8 <= 0xFF
    return 0xE3A00000 | (rd << 12) | imm8


NOP = 0x00000000
UDF = 0xE7FFDEFE          # permanently undefined — used here as halt
BX_LR = 0xE12FFF1E


def _vm(prog: bytes) -> VirtualMachine:
    vm = VirtualMachine(name="test-vm", arch="arm", ram_mb=1)
    vm.load_binary(prog, addr=FLASH)
    return vm


class TestExecution:
    def test_mov_immediate_reaches_the_register(self):
        vm = _vm(arm(mov_imm(0, 0x2A), mov_imm(1, 0x07), UDF))
        r = vm.run(max_cycles=64, timeout_s=5)

        assert vm.cpu.state.regs[0] == 0x2A
        assert vm.cpu.state.regs[1] == 0x07
        assert r["cycles"] == 3   # 2 MOVs + the UDF that halts

    def test_udf_halts_and_is_the_only_success(self):
        vm = _vm(arm(mov_imm(0, 1), UDF))
        r = vm.run(max_cycles=64, timeout_s=5)

        assert vm.cpu.state.halted is True
        assert r["reason"] == "halted"
        assert r["success"] is True

    def test_running_off_the_end_is_not_success(self):
        """No halt instruction: the engine stops it, so it did not succeed."""
        vm = _vm(arm(*([NOP] * 8)))
        r = vm.run(max_cycles=16, timeout_s=5)

        assert r["reason"] == "cycle-limit"
        assert r["success"] is False
        assert r["cycles"] == 16

    def test_cycle_count_matches_instructions_retired(self):
        vm = _vm(arm(mov_imm(0, 1), mov_imm(0, 2), mov_imm(0, 3), UDF))
        r = vm.run(max_cycles=64, timeout_s=5)

        assert r["cycles"] == 4   # 3 MOVs + the UDF that halts
        assert vm.cpu.state.regs[0] == 3      # last write wins


class TestReportingContract:
    def test_no_firmware_is_a_failure_not_a_boot(self):
        """The regression this suite exists for."""
        vm = VirtualMachine(name="empty", arch="arm", ram_mb=1)
        r = vm.run(max_cycles=10000, timeout_s=5)

        assert r["success"] is False
        assert r["reason"] == "no-firmware"
        assert r["cycles"] == 0
        assert "No firmware loaded" in r["boot_log"]
        assert "booted successfully" not in r["boot_log"]

    def test_load_binary_marks_firmware_present(self):
        vm = VirtualMachine(name="v", arch="arm", ram_mb=1)
        assert vm.firmware_loaded is False
        vm.load_binary(arm(UDF), addr=FLASH)
        assert vm.firmware_loaded is True

    def test_load_firmware_from_file(self, tmp_path):
        img = tmp_path / "fw.bin"
        img.write_bytes(arm(mov_imm(2, 0x5A), UDF))

        vm = VirtualMachine(name="v", arch="arm", ram_mb=1)
        assert vm.load_firmware(str(img)) is True
        assert vm.firmware_path == str(img)

        r = vm.run(max_cycles=64, timeout_s=5)
        assert r["success"] is True
        assert vm.cpu.state.regs[2] == 0x5A

    def test_missing_firmware_file_is_rejected(self):
        vm = VirtualMachine(name="v", arch="arm", ram_mb=1)
        assert vm.load_firmware("/nonexistent/fw.bin") is False
        assert vm.firmware_loaded is False

    def test_boot_log_has_real_newlines(self):
        """The log was written with escaped \\\\n, so it arrived as literal
        backslash-n and every consumer saw one long line."""
        vm = _vm(arm(UDF))
        r = vm.run(max_cycles=8, timeout_s=5)

        assert "\\n" not in r["boot_log"]
        assert "\n" in r["boot_log"]

    def test_dump_state_has_real_newlines(self):
        vm = _vm(arm(UDF))
        vm.run(max_cycles=8, timeout_s=5)
        assert "\\n" not in vm.dump_state()


class TestUndefinedInstructions:
    """The decoder covers a small ARM32 subset.

    An opcode outside it used to fall through the if/elif chain and be treated
    as a no-op. A real firmware image would therefore "run", compute nothing,
    and could still reach a halt and be reported as a successful boot. Since
    only a handful of instructions are decoded, that is the common case.
    """

    ADD_R0_R1_R2 = 0xE0810002      # not decoded
    PUSH_LR = 0xE52DE004           # not decoded

    def test_undefined_opcode_stops_the_run(self):
        vm = _vm(arm(mov_imm(1, 5), self.ADD_R0_R1_R2, UDF))
        r = vm.run(max_cycles=64, timeout_s=5)

        assert r["reason"] == "undefined-instruction"
        assert r["success"] is False
        assert r["undefined_count"] == 1

    def test_undefined_opcode_is_not_silently_skipped(self):
        """ADD r0,r1,r2 with r1=5, r2=3 must not leave r0 untouched and continue."""
        vm = _vm(arm(mov_imm(1, 5), mov_imm(2, 3), self.ADD_R0_R1_R2, UDF))
        r = vm.run(max_cycles=64, timeout_s=5)

        assert vm.cpu.state.regs[0] == 0          # it did not execute
        assert r["success"] is False              # and that is reported
        assert vm.cpu.last_undefined[1] == self.ADD_R0_R1_R2

    def test_prologue_of_a_real_function_is_rejected(self):
        """PUSH {lr} opens almost every compiled ARM function."""
        vm = _vm(arm(self.PUSH_LR, UDF))
        r = vm.run(max_cycles=64, timeout_s=5)

        assert r["reason"] == "undefined-instruction"
        assert "cannot execute a full firmware image" in r["boot_log"]

    def test_strict_mode_can_be_disabled(self):
        """Opt out for tracing experiments, but never by default."""
        vm = _vm(arm(mov_imm(1, 5), self.ADD_R0_R1_R2, UDF))
        vm.cpu.strict_undefined = False
        r = vm.run(max_cycles=64, timeout_s=5)

        assert r["reason"] == "halted"
        assert r["undefined_count"] == 1          # still counted, just not fatal


class TestTimeout:
    def test_timeout_is_reported_as_such(self):
        vm = _vm(arm(*([NOP] * 4)))
        r = vm.run(max_cycles=10_000_000, timeout_s=0.05)

        assert r["reason"] in ("timeout", "cycle-limit")
        assert r["success"] is False
