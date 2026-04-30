# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Functional safety analysis (ISO 26262, IEC 61508)."""
from dataclasses import dataclass, field


@dataclass
class SafetyRequirement:
    req_id: str = ""
    description: str = ""
    standard: str = ""
    level: str = ""
    verified: bool = False


class SafetyAnalyzer:
    """Track and verify functional safety requirements."""

    def __init__(self):
        self.requirements = []

    def add_requirement(self, req):
        self.requirements.append(req)

    def verify(self, req_id, result=True):
        for r in self.requirements:
            if r.req_id == req_id:
                r.verified = result
                return True
        return False

    def coverage(self):
        if not self.requirements:
            return 0
        verified = sum(1 for r in self.requirements if r.verified)
        return verified / len(self.requirements) * 100

    def report(self):
        return {
            'total': len(self.requirements),
            'verified': sum(1 for r in self.requirements if r.verified),
            'unverified': sum(1 for r in self.requirements if not r.verified),
            'coverage_pct': self.coverage(),
            'requirements': [{'id': r.req_id, 'desc': r.description, 'verified': r.verified} for r in self.requirements],
        }
