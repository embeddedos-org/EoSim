---
name: eosim-mcp
description: Drive the EoSim simulator fleet through its MCP server — discover platforms, flash firmware, launch simulations, and read console output. Use when an agent needs to run embedded firmware in simulation without shell access.
---

# EoSim MCP

The EoSim MCP server (`eosim mcp`) exposes the simulator fleet as four tools.
It speaks JSON-RPC over stdio; any MCP client can attach.

## Tools

- `list_platforms` — discover simulation targets. Filter by `arch`
  (`arm`, `riscv`, …), `vendor`, `engine` (`eosim`, `qemu`), `domain`.
  Start here; platform names are the keys everything else takes.
- `sim_flash` — stage a firmware image into a platform's simulated flash.
  Takes `platform` and `firmware` (path). Dry-run by default: validates and
  returns the plan (size, sha256, staged path) without writing anything.
  With `dry_run=false` the image is copied to `out/firmware/<platform>/`
  with a `.meta.json` sidecar; pass the returned `staged_path` as
  `firmware` to `sim_launch`.
- `sim_launch` — boot a platform, optionally with `firmware`. Dry-run by
  default: validates and returns the launch plan (the exact `eosim run`
  command). With `dry_run=false` the simulator spawns detached and a
  `session_id` plus log file path are returned.
- `console_tail` — read the tail of a session's console log
  (`<log_dir>/<platform>-<session_id>.log`). Takes `session_id` and
  `lines` (default 50, max 1000). Use it to check boot output, faults, or
  test results after a launch.

## Discipline

1. Probe with dry-runs first: `list_platforms` → `sim_flash` (dry-run) →
   `sim_launch` (dry-run). Only set `dry_run=false` when the plan looks
   right.
2. `sim_launch` with `dry_run=false` starts a real process. Prefer
   `headless=true` and a bounded `timeout`.
3. After launching, poll `console_tail` for the `session_id` to observe
   output. There is no stop tool; the simulator exits on `timeout`.
4. Firmware paths are read from the machine running the MCP server, not the
   agent — stage artifacts where the server can see them.

## Example session

```
list_platforms({arch: "arm", domain: "industrial"})
sim_flash({platform: "demo-arm", firmware: "/build/fw.bin"})
  → {ok: true, dry_run: true, sha256: "…", staged_path: "out/firmware/demo-arm/fw.bin"}
sim_flash({platform: "demo-arm", firmware: "/build/fw.bin", dry_run: false})
sim_launch({platform: "demo-arm", firmware: "out/firmware/demo-arm/fw.bin", dry_run: false})
  → {ok: true, session_id: "abc123", log_file: "out/logs/demo-arm-abc123.log"}
console_tail({session_id: "abc123", lines: 50})
```
