# EoSim MCP server — 2026-07-28 conformance probe (findings)

Probe date: 2026-10-31. Server under test: `eosim/mcp/server.py` at
EoSim master head `3c88f36b8e88e7f3a61494ca288b155e1b9b8f52` (stdio JSON-RPC 2.0, `python -m eosim.mcp`,
`PROTOCOL_VERSION = "2026-07-28"`, `server.json` v3.1.0).
Spec: MCP specification revision **2026-07-28**, read first-party
2026-10-28 (see the 2026-10-28 research brief §3 for the quoted text).

Method: characterisation tests in
`tests/unit/test_mcp_conformance_2026_07_28.py` call
`handle_message` in-process (no stdio, no network). The tests assert
RECORDED behaviour, so the probe commit is green by design; each gap
below becomes its own filed EoSim issue, and fixes land as separate
commits. NO server behaviour was changed by the probe commit.

## Results

| # | Probe | Recorded behaviour | Spec 2026-07-28 expects | Verdict |
|---|-------|--------------------|-------------------------|---------|
| (a) | `tools/list` with NO `_meta` | Returns the tool list | Missing required `_meta` fields MUST reject with JSON-RPC `-32602` | GAP G2 |
| (a) | `tools/list` with full `_meta` (protocolVersion + clientCapabilities) | Returns the tool list | Same | Pass (behaviour matches, for the wrong reason — `_meta` is ignored, not validated) |
| (b) | `server/discover` | `-32601` method not found | Servers MUST implement it; returns DiscoverResult (supportedVersions + capabilities) | GAP G1 |
| (c) | `initialize` | Success, `protocolVersion: "2026-07-28"`, serverInfo `eosim-mcp 0.1.0` | No negotiation handshake for modern implementations; a dual-era server MAY answer it | GAP G3 (disclosure/era) |
| (d) | Response envelope `_meta` | No `_meta` on any reply | Servers SHOULD include `io.modelcontextprotocol/serverInfo` in every result's `_meta` | GAP G4 (SHOULD-level) |
| — | Unknown method | `-32601` | — | Control, pass |

## Gaps (each becomes its own issue)

- **G1 — `server/discover` unimplemented (MUST).** The highest-severity
  gap: any 2026-07-28 client that discovers first (as the spec's
  dual-era guidance recommends) gets `-32601` from a server that
  declares the 2026-07-28 revision.
- **G2 — No per-request `_meta` validation (MUST).** The server never
  reads `_meta`, so malformed requests (missing required fields) are
  served instead of rejected with `-32602`, and undeclared-capability
  requests are never answered with `-32021`.
- **G3 — `initialize` answered by a modern-declaring server.** Either
  the server is dual-era (then `server.json`/docs must say so and the
  legacy path is intentional) or it is modern-only (then answering
  `initialize` successfully misleads clients about the handshake).
  Maintainer decision; the probe records, it does not choose.
- **G4 — No response `_meta` (SHOULD).** Lowest priority; fix with G2
  (the same validation/emit path).

## Explicitly NOT claimed

- No claim is made about the eFlow `eflow_validate` server or any
  other org MCP server: this probe covers EoSim only, per the P1
  design. Each other server gets its own probe + issues.
- No claim is made about Streamable HTTP transport: the EoSim server
  is stdio-only; HTTP status rules (`400` on `-32602`) are out of
  scope for this probe.
- No certification or spec-compliance badge is claimed for EoSim:
  until G1–G3 close, the server is "2026-07-28-declared, gaps
  recorded", not "2026-07-28-conformant".
