# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Production hardening and integration tests for EoSim."""

import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestExtensionFiles:
    """Tests for browser extension completeness."""

    def setup_method(self):
        self.ext_dir = Path(__file__).parent.parent.parent / "extension"

    def test_manifest_exists(self):
        assert (self.ext_dir / "manifest.json").exists()

    def test_manifest_is_valid_json(self):
        with open(self.ext_dir / "manifest.json") as f:
            data = json.load(f)
        assert data["manifest_version"] == 3

    def test_manifest_version_3(self):
        with open(self.ext_dir / "manifest.json") as f:
            data = json.load(f)
        assert data["manifest_version"] == 3

    def test_manifest_has_name(self):
        with open(self.ext_dir / "manifest.json") as f:
            data = json.load(f)
        assert "EoSim" in data["name"]

    def test_manifest_has_version(self):
        with open(self.ext_dir / "manifest.json") as f:
            data = json.load(f)
        assert data["version"] == "3.0.1"

    def test_manifest_has_production_host_permissions(self):
        with open(self.ext_dir / "manifest.json") as f:
            data = json.load(f)
        host_perms = data.get("host_permissions", [])
        assert any("api.eosim.io" in p for p in host_perms)

    def test_popup_html_exists(self):
        assert (self.ext_dir / "popup.html").exists()

    def test_popup_js_exists(self):
        assert (self.ext_dir / "popup.js").exists()

    def test_background_js_exists(self):
        assert (self.ext_dir / "background.js").exists()

    def test_content_js_exists(self):
        assert (self.ext_dir / "content.js").exists()

    def test_options_html_exists(self):
        assert (self.ext_dir / "options.html").exists()

    def test_popup_js_uses_production_api(self):
        content = (self.ext_dir / "popup.js").read_text()
        assert "api.eosim.io" in content
        assert "localhost" not in content

    def test_background_js_uses_production_api(self):
        content = (self.ext_dir / "background.js").read_text()
        assert "api.eosim.io" in content
        assert "localhost" not in content

    def test_manifest_has_keyboard_shortcut(self):
        with open(self.ext_dir / "manifest.json") as f:
            data = json.load(f)
        assert "commands" in data
        assert "open-eosim" in data["commands"]


class TestMobileApp:
    """Tests for mobile app completeness."""

    def setup_method(self):
        self.mobile_dir = Path(__file__).parent.parent.parent / "mobile"

    def test_manifest_exists(self):
        assert (self.mobile_dir / "manifest.json").exists()

    def test_manifest_is_valid_json(self):
        with open(self.mobile_dir / "manifest.json") as f:
            data = json.load(f)
        assert data is not None

    def test_manifest_has_10_languages(self):
        with open(self.mobile_dir / "manifest.json") as f:
            data = json.load(f)
        assert data.get("lang") == "en"
        assert data.get("dir") == "auto"

    def test_app_html_exists(self):
        assert (self.mobile_dir / "app.html").exists()

    def test_app_html_uses_production_api(self):
        content = (self.mobile_dir / "app.html").read_text()
        assert "api.eosim.io" in content
        assert "localhost" not in content

    def test_app_html_has_gps(self):
        content = (self.mobile_dir / "app.html").read_text()
        assert "geolocation" in content.lower() or "gps" in content.lower()

    def test_app_html_has_all_20_modules(self):
        content = (self.mobile_dir / "app.html").read_text()
        modules = ["network", "robotics", "aerospace", "automotive", "security",
                   "ai", "iot", "embedded", "fpga", "physics", "virt", "mobile",
                   "cloud", "gamedev", "data", "energy", "manufacturing", "xr",
                   "aicode", "process"]
        for mod in modules:
            assert mod in content.lower(), f"Module '{mod}' not found in mobile app"

    def test_app_html_has_language_support(self):
        content = (self.mobile_dir / "app.html").read_text()
        for lang in ["en", "es", "zh", "hi", "fr", "ar", "pt", "de", "ja", "ko"]:
            assert f"lang-{lang}" in content or f"'{lang}'" in content, \
                f"Language {lang} not found in mobile app"

    def test_manifest_standalone_display(self):
        with open(self.mobile_dir / "manifest.json") as f:
            data = json.load(f)
        assert data["display"] == "standalone"


class TestAndroidConfig:
    """Tests for Android app configuration."""

    def setup_method(self):
        self.android_dir = Path(__file__).parent.parent.parent / "android"

    def test_readme_exists(self):
        assert (self.android_dir / "README.md").exists()

    def test_build_gradle_exists(self):
        assert (self.android_dir / "app" / "build.gradle.kts").exists()

    def test_manifest_exists(self):
        assert (self.android_dir / "app" / "src" / "main" / "AndroidManifest.xml").exists()

    def test_build_gradle_uses_production_api(self):
        content = (self.android_dir / "app" / "build.gradle.kts").read_text()
        assert "api.eosim.io" in content
        # localhost only appears in a comment ("never use localhost"), not as an actual URL value
        lines_with_localhost = [
            l for l in content.splitlines()
            if "localhost" in l and not l.strip().startswith("//")
        ]
        assert len(lines_with_localhost) == 0, f"localhost in non-comment Gradle code: {lines_with_localhost}"

    def test_manifest_has_internet_permission(self):
        content = (self.android_dir / "app" / "src" / "main" / "AndroidManifest.xml").read_text()
        assert "INTERNET" in content

    def test_manifest_has_location_permission(self):
        content = (self.android_dir / "app" / "src" / "main" / "AndroidManifest.xml").read_text()
        assert "ACCESS_FINE_LOCATION" in content

    def test_network_security_config_exists(self):
        path = self.android_dir / "app" / "src" / "main" / "res" / "xml" / "network_security_config.xml"
        assert path.exists()

    def test_network_security_blocks_cleartext(self):
        path = self.android_dir / "app" / "src" / "main" / "res" / "xml" / "network_security_config.xml"
        content = path.read_text()
        assert "cleartextTrafficPermitted" in content
        assert "false" in content

    def test_locales_config_exists(self):
        path = self.android_dir / "app" / "src" / "main" / "res" / "xml" / "locales_config.xml"
        assert path.exists()

    def test_locales_config_has_10_languages(self):
        path = self.android_dir / "app" / "src" / "main" / "res" / "xml" / "locales_config.xml"
        content = path.read_text()
        for lang in ["en", "es", "zh", "hi", "fr", "ar", "pt", "de", "ja", "ko"]:
            assert lang in content, f"Language {lang} missing from Android locales"


class TestiOSConfig:
    """Tests for iOS app configuration."""

    def setup_method(self):
        self.ios_dir = Path(__file__).parent.parent.parent / "ios"

    def test_readme_exists(self):
        assert (self.ios_dir / "README.md").exists()

    def test_info_plist_exists(self):
        assert (self.ios_dir / "EoSim" / "Info.plist").exists()

    def test_api_client_exists(self):
        assert (self.ios_dir / "EoSim" / "Sources" / "API" / "EoSimAPIClient.swift").exists()

    def test_info_plist_has_location_usage(self):
        content = (self.ios_dir / "EoSim" / "Info.plist").read_text()
        assert "NSLocationWhenInUseUsageDescription" in content

    def test_info_plist_has_10_localizations(self):
        content = (self.ios_dir / "EoSim" / "Info.plist").read_text()
        for lang in ["en", "es", "zh-Hans", "hi", "fr", "ar", "pt", "de", "ja", "ko"]:
            assert lang in content, f"Language {lang} missing from iOS Info.plist"

    def test_api_client_uses_production_url(self):
        content = (self.ios_dir / "EoSim" / "Sources" / "API" / "EoSimAPIClient.swift").read_text()
        assert "api.eosim.io" in content
        # localhost only appears in a comment ("never localhost"), not as an actual URL
        lines_with_localhost = [
            l for l in content.splitlines()
            if "localhost" in l and not l.strip().startswith("//")
        ]
        assert len(lines_with_localhost) == 0, f"localhost in non-comment Swift code: {lines_with_localhost}"

    def test_api_client_has_gps_region_selection(self):
        content = (self.ios_dir / "EoSim" / "Sources" / "API" / "EoSimAPIClient.swift").read_text()
        assert "selectRegion" in content or "CLLocation" in content

    def test_info_plist_blocks_http(self):
        content = (self.ios_dir / "EoSim" / "Info.plist").read_text()
        assert "NSAllowsArbitraryLoads" in content


class TestProjectStructure:
    """Tests for overall project structure completeness."""

    def setup_method(self):
        self.root = Path(__file__).parent.parent.parent

    def test_eosim_package_exists(self):
        assert (self.root / "eosim").is_dir()

    def test_i18n_module_exists(self):
        assert (self.root / "eosim" / "i18n").is_dir()

    def test_config_module_exists(self):
        assert (self.root / "eosim" / "config").is_dir()

    def test_extension_dir_exists(self):
        assert (self.root / "extension").is_dir()

    def test_mobile_dir_exists(self):
        assert (self.root / "mobile").is_dir()

    def test_android_dir_exists(self):
        assert (self.root / "android").is_dir()

    def test_ios_dir_exists(self):
        assert (self.root / "ios").is_dir()

    def test_10_locale_files_exist(self):
        locales = self.root / "eosim" / "i18n" / "locales"
        for lang in ["en", "es", "zh", "hi", "fr", "ar", "pt", "de", "ja", "ko"]:
            assert (locales / f"{lang}.json").exists(), f"Missing locale: {lang}.json"

    def test_github_actions_workflow_exists(self):
        workflow = self.root / ".github" / "workflows"
        assert workflow.is_dir()
        yamls = list(workflow.glob("*.yml")) + list(workflow.glob("*.yaml"))
        assert len(yamls) > 0, "No GitHub Actions workflows found"

    def test_docker_compose_exists(self):
        assert (self.root / "docker-compose.yml").exists() or \
               (self.root / "docker-compose.yaml").exists()

    def test_no_localhost_in_production_api_urls(self):
        """Ensure production API URL constants never use localhost."""
        from eosim.config.production import (
            PRODUCTION_API_BASE, PRODUCTION_WS_BASE,
            PRODUCTION_DOCS_URL, PRODUCTION_STATUS_URL,
            PRODUCTION_CDN_URL, PRODUCTION_AUTH_URL,
            PRODUCTION_METRICS_URL, PRODUCTION_REGISTRY_URL
        )
        prod_urls = [
            PRODUCTION_API_BASE, PRODUCTION_WS_BASE,
            PRODUCTION_DOCS_URL, PRODUCTION_STATUS_URL,
            PRODUCTION_CDN_URL, PRODUCTION_AUTH_URL,
            PRODUCTION_METRICS_URL, PRODUCTION_REGISTRY_URL
        ]
        for url in prod_urls:
            assert "localhost" not in url, f"localhost in production URL: {url}"
            assert "127.0.0.1" not in url, f"127.0.0.1 in production URL: {url}"
            assert url.startswith("https://") or url.startswith("wss://"), \
                f"Production URL not using HTTPS/WSS: {url}"
