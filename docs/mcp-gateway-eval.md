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
