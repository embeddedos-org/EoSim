# SPDX-License-Identifier: MIT
"""MCP 2026-07-28 conformance probe — characterisation tests (EoSim server).

These tests pin RECORDED behaviour of ``eosim.mcp.server.handle_message``
against the MCP specification revision 2026-07-28 (first-party read
2026-10-28, see docs/mcp-conformance-2026-07-28.md). They are NOT
conformance assertions: where recorded behaviour differs from the spec,
the test asserts the recorded behaviour and names the gap, so the probe
commit stays green while the gaps become filed issues. NO server fix
lives in the probe commit — that is the P1 design (growth backlog P1,
slot fixed Sat 2026-10-31).

Spec anchors used below (2026-07-28):
- Stateless: every request carries its metadata in ``_meta``; required
  per-request keys are ``io.modelcontextprotocol/protocolVersion`` and
  ``io.modelcontextprotocol/clientCapabilities``. A request missing a
  required field is malformed; the server MUST reject it with JSON-RPC
  error ``-32602`` (Invalid params).
- ``server/discover``: servers MUST implement it; it returns a
  DiscoverResult of supported versions + capabilities.
- ``initialize``: removed for modern implementations ("there is no
  negotiation handshake"); a dual-era server MAY answer it.
- Servers SHOULD include ``io.modelcontextprotocol/serverInfo`` in
  every result's ``_meta``.
"""

from eosim.mcp.server import handle_message

PROTOCOL_VERSION = "2026-07-28"

FULL_META = {
    "_meta": {
        "io.modelcontextprotocol/protocolVersion": PROTOCOL_VERSION,
        "io.modelcontextprotocol/clientCapabilities": {},
    }
}


def _tools_list(meta=True):
    req = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    if meta:
        req.update(FULL_META)
    return handle_message(req)


def test_tools_list_without_meta_is_rejected():
    """FIXED (gap G2, EoSim #66): a request missing the required _meta
    fields is rejected with -32602.

    Spec 2026-07-28: a request missing the required _meta fields MUST be
    rejected with -32602. This test was flipped from the probe's
    recorded-behaviour assertion when the fix landed.
    """
    reply = _tools_list(meta=False)
    assert reply["error"]["code"] == -32602


def test_tools_list_with_full_meta_succeeds():
    """With the required _meta keys present, tools/list succeeds."""
    reply = _tools_list(meta=True)
    assert "result" in reply
    assert reply["result"]["tools"]


def test_server_discover_returns_discover_result():
    """FIXED (gap G1, EoSim #66): server/discover is implemented.

    Spec 2026-07-28: servers MUST implement server/discover, returning a
    DiscoverResult of supported versions + capabilities. This test was
    flipped from the probe's recorded-behaviour assertion when the fix
    landed; G2 and G4 were flipped by their own fix (#73), G3 by the
    initialize-era fix closing #66.
    """
    req = {"jsonrpc": "2.0", "id": 2, "method": "server/discover"}
    req.update(FULL_META)
    reply = handle_message(req)
    assert "result" in reply
    assert PROTOCOL_VERSION in reply["result"]["supportedVersions"]
    assert reply["result"]["capabilities"] == {"tools": {}}
    assert reply["result"]["serverInfo"]["name"] == "eosim-mcp"


def test_initialize_is_rejected():
    """FIXED (gap G3, EoSim #66): the removed handshake is rejected.

    Spec 2026-07-28: there is no negotiation handshake for modern
    implementations ("There is no negotiation handshake. Every request
    carries its protocol version, and the server accepts or rejects
    each request independently"). This server declares
    protocolVersion 2026-07-28 and is modern-only, not dual-era, so
    initialize is a removed method and is rejected with JSON-RPC
    -32601 (method not found). Clients discover via server/discover
    instead. This test was flipped from the probe's
    recorded-behaviour assertion when the fix landed.
    """
    req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "initialize",
        "params": {"protocolVersion": PROTOCOL_VERSION, "capabilities": {}},
    }
    req.update(FULL_META)
    reply = handle_message(req)
    assert reply["error"]["code"] == -32601
    assert "server/discover" in reply["error"]["message"]


def test_responses_carry_server_info_meta():
    """FIXED (gap G4, EoSim #66, SHOULD-level): replies carry serverInfo
    _meta.

    Spec 2026-07-28: servers SHOULD include
    io.modelcontextprotocol/serverInfo in every result's _meta. This
    test was flipped from the probe's recorded-behaviour assertion
    when the fix landed.
    """
    reply = _tools_list(meta=True)
    assert reply["_meta"]["io.modelcontextprotocol/serverInfo"]["name"] == "eosim-mcp"


def test_unknown_method_still_rejected():
    """Control: the -32601 path the discover probe relies on is real."""
    req = {"jsonrpc": "2.0", "id": 4, "method": "no/such"}
    req.update(FULL_META)
    reply = handle_message(req)
    assert reply["error"]["code"] == -32601
