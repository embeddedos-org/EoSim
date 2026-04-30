# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Network topology simulation for multi-node embedded systems."""


class NetworkNode:
    """A node in the simulated network."""

    def __init__(self, name, ip='0.0.0.0', node_type='device'):
        self.name = name
        self.ip = ip
        self.node_type = node_type
        self.connections = []
        self.packets_sent = 0
        self.packets_received = 0


class NetworkTopology:
    """Simulate a network of embedded devices."""

    def __init__(self):
        self.nodes = {}
        self.links = []

    def add_node(self, node):
        self.nodes[node.name] = node

    def add_link(self, node_a, node_b, bandwidth_mbps=100, latency_ms=1):
        self.links.append({
            'a': node_a, 'b': node_b,
            'bandwidth_mbps': bandwidth_mbps, 'latency_ms': latency_ms,
        })
        if node_a in self.nodes:
            self.nodes[node_a].connections.append(node_b)
        if node_b in self.nodes:
            self.nodes[node_b].connections.append(node_a)

    def send_packet(self, src, dst, size_bytes=64):
        if src in self.nodes:
            self.nodes[src].packets_sent += 1
        if dst in self.nodes:
            self.nodes[dst].packets_received += 1

    def get_topology(self):
        return {
            'nodes': {n: {'ip': nd.ip, 'type': nd.node_type, 'connections': nd.connections}
                      for n, nd in self.nodes.items()},
            'links': self.links,
        }
