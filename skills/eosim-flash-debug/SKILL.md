---
name: eosim-flash-debug
description: Flash firmware into an EoSim virtual board, boot it, and triage the console output. Use when bringing up new firmware or chasing a boot fault in simulation.
---

# EoSim flash-and-debug loop

A tight loop for firmware bring-up in simulation: flash → boot → read the
console → interpret → fix → repeat. Built on the `eosim-mcp` skill's tools.

## The loop

1. **Flash (dry-run first).**
   `sim_flash({platform, firmware})` validates the image and reports
   `size` and `sha256`. Sanity-check the size against the target's flash
   (see `list_platforms` → platform detail); an image larger than flash is
   the most common silly failure. Then `sim_flash({…, dry_run: false})`.

2. **Boot.** `sim_launch({platform, firmware: <staged_path>, dry_run:
   false})`. Note the `session_id`. Keep `timeout` modest (60–300 s) —
   a hung boot should fail fast.

3. **Read the console.** `console_tail({session_id, lines: 100})`.
   Read from the top of the tail, not just the last lines: the fault is
   usually above the hang.

4. **Interpret.** Common signatures:
   - *Nothing at all*: wrong platform (arch mismatch), or the image never
     reached the reset vector — check `sim_flash`'s sha256 against the
     file you built.
   - *Repeating reset / watchdog*: early init crash; binary-search by
     flashing a minimal blinky for the same platform to isolate board vs.
     firmware.
   - *Data abort / hard fault with an address*: compare the faulting
     address against the platform's memory map (`list_platforms` detail
     or `platforms/<name>/platform.yml`).
   - *Pass then hang at a driver*: peripheral the simulator doesn't model;
     check the platform's `domain` notes for modeled vs. stubbed
     peripherals.

5. **Fix and repeat.** Rebuild, `sim_flash` again (the sha256 in the plan
   confirms the new image actually landed), relaunch.

## Notes

- `console_tail` caps at 1000 lines; for long runs, tail repeatedly rather
  than raising `lines` — boot faults rarely need more than the first
  screenful after the last reset.
- Sessions are detached processes; there is no stop tool. A short
  `timeout` on `sim_launch` is the stop button.
- This skill debugs the *firmware*; simulator bugs (wrong peripheral
  model) go to the EoSim issue tracker with the session log attached.
