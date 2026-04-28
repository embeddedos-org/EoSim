# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Security analysis (ISO 21434, IEC 62443)."""
from dataclasses import dataclass


@dataclass
class ThreatModel:
    asset: str = ""
    threat: str = ""
    impact: str = "medium"
    likelihood: str = "medium"
    mitigation: str = ""
    status: str = "open"


class SecurityAnalyzer:
    """Automotive and industrial cybersecurity threat analysis."""

    def __init__(self):
        self.threats = []

    def add_threat(self, threat):
        self.threats.append(threat)

    def mitigate(self, asset, mitigation):
        for t in self.threats:
            if t.asset == asset and t.status == 'open':
                t.mitigation = mitigation
                t.status = 'mitigated'

    def risk_score(self):
        impact_map = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
        likelihood_map = {'low': 1, 'medium': 2, 'high': 3}
        total = 0
        for t in self.threats:
            if t.status == 'open':
                total += impact_map.get(t.impact, 2) * likelihood_map.get(t.likelihood, 2)
        return total

    def report(self):
        return {
            'total_threats': len(self.threats),
            'open': sum(1 for t in self.threats if t.status == 'open'),
            'mitigated': sum(1 for t in self.threats if t.status == 'mitigated'),
            'risk_score': self.risk_score(),
        }
