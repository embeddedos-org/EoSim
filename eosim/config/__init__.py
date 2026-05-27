# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""EoSim configuration package."""

from .production import get_config, API_BASE, WS_BASE, DOCS_URL, STATUS_URL, ENV, IS_PRODUCTION

__all__ = ["get_config", "API_BASE", "WS_BASE", "DOCS_URL", "STATUS_URL", "ENV", "IS_PRODUCTION"]
