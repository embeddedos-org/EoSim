# SPDX-License-Identifier: MIT
"""Cluster definitions for multi-node simulations."""
from dataclasses import dataclass, field

import yaml


@dataclass
class ClusterNode:
    name: str = ""
    platform: str = ""


@dataclass
class Cluster:
    name: str = ""
    nodes: list[ClusterNode] = field(default_factory=list)
    links: list = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str) -> "Cluster":
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        nodes = []
        for n in data.get("nodes", []):
            nodes.append(ClusterNode(
                name=n.get("name", ""),
                platform=n.get("platform", ""),
            ))
        return cls(
            name=data.get("name", ""),
            nodes=nodes,
            links=data.get("links", []),
        )

    def validate(self, known_platforms: dict) -> list[str]:
        errors = []
        seen_names = set()
        for node in self.nodes:
            if node.name in seen_names:
                errors.append(f"duplicate node name: {node.name}")
            seen_names.add(node.name)
            if node.platform not in known_platforms:
                errors.append(f"unknown platform: {node.platform}")
        return errors
