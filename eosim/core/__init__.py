# SPDX-License-Identifier: MIT
"""EoSim core module — platform definitions, registry, validation."""

from eosim.core.platform import Platform, discover_platforms  # noqa: F401
from eosim.core.registry import PlatformRegistry  # noqa: F401
from eosim.core.schema import validate_platform  # noqa: F401
