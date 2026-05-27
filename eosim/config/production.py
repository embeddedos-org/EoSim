# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Production configuration for EoSim.

All URLs, endpoints, and environment-specific settings are defined here.
The application uses production endpoints by default; local overrides are
only applied when EOSIM_ENV=development is explicitly set.
"""

from __future__ import annotations
import os

# ─── Environment Detection ────────────────────────────────────────────────────
ENV = os.environ.get("EOSIM_ENV", "production").lower()
IS_PRODUCTION = ENV == "production"
IS_DEVELOPMENT = ENV == "development"

# ─── Production Endpoints ─────────────────────────────────────────────────────
PRODUCTION_API_BASE = "https://api.eosim.io"
PRODUCTION_WS_BASE = "wss://api.eosim.io"
PRODUCTION_DOCS_URL = "https://docs.eosim.io"
PRODUCTION_STATUS_URL = "https://status.eosim.io"
PRODUCTION_CDN_URL = "https://cdn.eosim.io"
PRODUCTION_AUTH_URL = "https://auth.eosim.io"
PRODUCTION_METRICS_URL = "https://metrics.eosim.io"
PRODUCTION_REGISTRY_URL = "https://registry.eosim.io"

# ─── Development Overrides ────────────────────────────────────────────────────
DEV_API_BASE = os.environ.get("EOSIM_API_URL", "http://localhost:8080")
DEV_WS_BASE = os.environ.get("EOSIM_WS_URL", "ws://localhost:8080")

# ─── Active Config (auto-selected by environment) ─────────────────────────────
API_BASE = PRODUCTION_API_BASE if IS_PRODUCTION else DEV_API_BASE
WS_BASE = PRODUCTION_WS_BASE if IS_PRODUCTION else DEV_WS_BASE
DOCS_URL = PRODUCTION_DOCS_URL
STATUS_URL = PRODUCTION_STATUS_URL
CDN_URL = PRODUCTION_CDN_URL
AUTH_URL = PRODUCTION_AUTH_URL if IS_PRODUCTION else DEV_API_BASE + "/auth"
METRICS_URL = PRODUCTION_METRICS_URL if IS_PRODUCTION else DEV_API_BASE + "/metrics"

# ─── API Versioning ───────────────────────────────────────────────────────────
API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"

# ─── Platform Info ────────────────────────────────────────────────────────────
PLATFORM_NAME = "EoSim Universal Simulation Platform"
PLATFORM_VERSION = "3.0.1"
PLATFORM_DESCRIPTION = (
    "The world's most powerful universal simulation platform — "
    "superseding 250+ industry tools across 20 simulation domains."
)
PLATFORM_HOMEPAGE = "https://eosim.io"
PLATFORM_GITHUB = "https://github.com/embeddedos-org/EoSim"
PLATFORM_SUPPORT = "https://support.eosim.io"
PLATFORM_LICENSE = "MIT"

# ─── Feature Flags ────────────────────────────────────────────────────────────
FEATURES = {
    "websocket": True,
    "real_time_metrics": True,
    "multi_language": True,
    "mobile_app": True,
    "browser_extension": True,
    "cloud_sync": IS_PRODUCTION,
    "ai_assistance": IS_PRODUCTION,
    "gps_location": True,
    "offline_mode": True,
}

# ─── Supported Languages ──────────────────────────────────────────────────────
SUPPORTED_LANGUAGES = [
    {"code": "en", "name": "English", "native": "English", "rtl": False},
    {"code": "es", "name": "Spanish", "native": "Español", "rtl": False},
    {"code": "zh", "name": "Mandarin Chinese", "native": "中文", "rtl": False},
    {"code": "hi", "name": "Hindi", "native": "हिन्दी", "rtl": False},
    {"code": "fr", "name": "French", "native": "Français", "rtl": False},
    {"code": "ar", "name": "Arabic", "native": "العربية", "rtl": True},
    {"code": "pt", "name": "Portuguese", "native": "Português", "rtl": False},
    {"code": "de", "name": "German", "native": "Deutsch", "rtl": False},
    {"code": "ja", "name": "Japanese", "native": "日本語", "rtl": False},
    {"code": "ko", "name": "Korean", "native": "한국어", "rtl": False},
]

# ─── GPS / Location ───────────────────────────────────────────────────────────
GPS_ENABLED = True
GPS_UPDATE_INTERVAL_MS = 1000  # 1 second
LOCATION_SERVICES_URL = f"{API_BASE}/api/{API_VERSION}/location"

# ─── Security ─────────────────────────────────────────────────────────────────
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24
API_RATE_LIMIT = 1000  # requests per minute in production
CORS_ORIGINS = [
    "https://eosim.io",
    "https://app.eosim.io",
    "https://api.eosim.io",
    "chrome-extension://",
    "moz-extension://",
]

def get_config() -> dict:
    """Return the complete production configuration as a dictionary."""
    return {
        "env": ENV,
        "api_base": API_BASE,
        "ws_base": WS_BASE,
        "docs_url": DOCS_URL,
        "status_url": STATUS_URL,
        "cdn_url": CDN_URL,
        "auth_url": AUTH_URL,
        "metrics_url": METRICS_URL,
        "platform": {
            "name": PLATFORM_NAME,
            "version": PLATFORM_VERSION,
            "description": PLATFORM_DESCRIPTION,
            "homepage": PLATFORM_HOMEPAGE,
            "github": PLATFORM_GITHUB,
            "support": PLATFORM_SUPPORT,
        },
        "features": FEATURES,
        "languages": SUPPORTED_LANGUAGES,
        "gps": {"enabled": GPS_ENABLED, "update_interval_ms": GPS_UPDATE_INTERVAL_MS},
    }
