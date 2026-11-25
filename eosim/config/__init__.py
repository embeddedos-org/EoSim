# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""EoSim configuration package."""

from .production import API_BASE, DOCS_URL, ENV, IS_PRODUCTION, STATUS_URL, WS_BASE, get_config

__all__ = ["get_config", "API_BASE", "WS_BASE", "DOCS_URL", "STATUS_URL", "ENV", "IS_PRODUCTION"]
