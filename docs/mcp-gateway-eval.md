# MCP gateway evaluation — Klavis Strata selected

**Status:** Decision recorded. **Date:** 2026-10-05
**Context:** Agent fabric plan §"Agent fabric: linking everything" — one
MCP gateway fronting the org's servers (EoSim MCP, fw-context-mcp over the
eos tree, hardware bridges, CAD surface).

## Requirement

One gateway that agents connect to instead of N individual servers, with
progressive tool discovery (agents see tools only when relevant — the
anti-context-bloat requirement), self-hostable, and policy hooks
(allow/confirm/deny).

## Candidates

| Candidate | License | Progressive discovery | Verdict |
|---|---|---|---|
| **Klavis Strata** | open-source | yes (`pipx install strata-mcp`) | **selected** |
| Consiliency/pmcp | open-source | yes (~200-token minimal mode) | runner-up, watch |
| agentic-community/mcp-gateway-registry | Apache 2.0 | Keycloak/Entra integration | watch (auth story) |
| sdys666/mcp-gateway | — | SKILL.md validation + allow/confirm/deny policies | pattern reference only, not a dependency |

## Decision

**Klavis Strata.** It is open-source, self-hostable, installs via
`pipx install strata-mcp`, and progressive tool discovery is built in —
the core requirement. Caveats accepted: extra discovery round-trips, and
no SOC 2 posture (fine for a dev-fabric gateway; not for customer data).

sdys666/mcp-gateway stays useful as a *pattern reference* for SKILL.md
validation and allow/confirm/deny policies — we adopt the pattern, not the
dependency.

## Next steps

1. Stand up Strata in front of the existing EoSim MCP server.
2. Add fw-context-mcp (0.29.1) over the eos tree as the second backend
   (generate `compile_commands.json` first; defer Ollama enrichment).
3. Hardware bridges and CAD surface follow the same pattern.

## Security requirements (day-one posture)

The Agentics' *Enterprise MCP Guide 2026* (68 MCP server CVEs in one
month) names six attack classes and a control set that map 1:1 onto the
gateway's day-one posture — this is the external validation the
evaluation's existing "policy hooks (allow/confirm/deny)" requirement
needed:

- **Six attack classes the gateway must be designed against:** tool
  poisoning, schema poisoning, tool shadowing, command injection,
  shadow servers, context oversharing. (Per-class mapping for the
  IPC surface: `embeddedos-org/eIPC` `docs/mcp-attack-classes-ipc.md`.)
- **Per-agent allowlists** — which tools each agent identity may call.
- **Identity binding** — backends authenticate before the gateway lists
  them (no shadow servers).
- **Centralized policy enforcement** — the gateway *is* the one
  policy-enforcement point for all tool traffic.
- **Human approval for destructive actions** — confirm/deny hooks on
  privileged tool invocations.

The 200k-stdIO-instances stat (OX Security: stdio-transport command
execution across 150M+ downloads) is why the fabric's standing rules —
pinned versions, approval on config change, no intra-network trust —
are first-class gateway controls, not documentation niceties.

## Update — 2026-10-15

Two selection inputs refreshed; the decision above is unchanged.

- **mcp-gateway-registry (watch candidate) is at 1.32.1**
  (2026-10-06, GitHub releases). The 1.32.x line is the
  forward-proxy egress theme: 1.32.0 shipped forward-proxy egress
  controls with the credential-endpoint protection noted in the
  2026-10-14 research pass, and 1.32.1 adds forward-proxy TLS and
  an MCP 2.x pin. The egress/credential-guard criterion it
  introduced stays on this evaluation's scorecard for whichever
  gateway is stood up; the candidate itself remains "watch",
  behind the selected Strata.
- **The command-injection class now has an exploited instance
  with a name: CVE-2026-42271 (LiteLLM).** LiteLLM's MCP preview
  endpoints (`POST /mcp-rest/test/connection`,
  `POST /mcp-rest/test/tools/list`) accepted a full stdio server
  configuration — `command`, `args`, `env` — and spawned it as a
  subprocess on the proxy host; any authenticated low-privilege
  key could run arbitrary commands (CWE-78). CISA KEV-listed
  2026-06-08; fixed in LiteLLM 1.83.7 by requiring the
  PROXY_ADMIN role on those endpoints. Criterion recorded for
  the org gateway, whichever candidate is stood up: *registering
  or previewing a stdio server is code execution* — that surface
  is admin-gated, never available to ordinary tool-callers, and
  stdio server definitions are treated as code, with the same
  review discipline as code.
- A claim about an "SEP-1932" for durable/resumable MCP streams
  circulated in the 2026-10-15 research pass; it could not be
  verified against MCP specification sources and is **not**
  recorded here as a selection factor.
