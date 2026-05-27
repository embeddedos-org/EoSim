# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Comprehensive tests for EoSim i18n (internationalization) module."""

import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch


class TestTranslator:
    """Tests for the Translator class."""

    def setup_method(self):
        # Reset the global instance before each test
        import eosim.i18n.translator as tr
        tr._instance = None

    def test_default_language_is_english(self):
        from eosim.i18n import Translator
        t = Translator()
        assert t.lang == "en"

    def test_supported_languages_list(self):
        from eosim.i18n import Translator
        t = Translator()
        langs = t.supported_languages
        assert "en" in langs
        assert "es" in langs
        assert "zh" in langs
        assert "hi" in langs
        assert "fr" in langs
        assert "ar" in langs
        assert "pt" in langs
        assert "de" in langs
        assert "ja" in langs
        assert "ko" in langs
        assert len(langs) == 10

    def test_translate_english_key(self):
        from eosim.i18n import Translator
        t = Translator("en")
        result = t.t("app.name")
        assert "EoSim" in result

    def test_translate_spanish(self):
        from eosim.i18n import Translator
        t = Translator("es")
        result = t.t("app.tagline")
        assert result  # Should not be empty
        assert result != "app.tagline"  # Should be translated

    def test_translate_chinese(self):
        from eosim.i18n import Translator
        t = Translator("zh")
        result = t.t("app.name")
        assert "EoSim" in result

    def test_translate_hindi(self):
        from eosim.i18n import Translator
        t = Translator("hi")
        result = t.t("nav.dashboard")
        assert result
        assert result != "nav.dashboard"

    def test_translate_french(self):
        from eosim.i18n import Translator
        t = Translator("fr")
        result = t.t("sim.create")
        assert result
        assert result != "sim.create"

    def test_translate_arabic(self):
        from eosim.i18n import Translator
        t = Translator("ar")
        result = t.t("app.name")
        assert "EoSim" in result

    def test_translate_portuguese(self):
        from eosim.i18n import Translator
        t = Translator("pt")
        result = t.t("sim.start")
        assert result
        assert result != "sim.start"

    def test_translate_german(self):
        from eosim.i18n import Translator
        t = Translator("de")
        result = t.t("nav.modules")
        assert result
        assert result != "nav.modules"

    def test_translate_japanese(self):
        from eosim.i18n import Translator
        t = Translator("ja")
        result = t.t("nav.docs")
        assert result
        assert result != "nav.docs"

    def test_translate_korean(self):
        from eosim.i18n import Translator
        t = Translator("ko")
        result = t.t("sim.stop")
        assert result
        assert result != "sim.stop"

    def test_fallback_to_english_for_missing_key(self):
        from eosim.i18n import Translator
        t = Translator("es")
        # Key that exists in English but not Spanish
        result = t.t("app.name")
        assert "EoSim" in result

    def test_returns_key_when_not_found(self):
        from eosim.i18n import Translator
        t = Translator("en")
        result = t.t("nonexistent.key.xyz")
        assert result == "nonexistent.key.xyz"

    def test_format_arguments(self):
        from eosim.i18n import Translator
        t = Translator("en")
        result = t.t("app.version", version="3.0.1")
        assert "3.0.1" in result

    def test_format_error_returns_unformatted(self):
        from eosim.i18n import Translator
        t = Translator("en")
        # Should not raise even with wrong kwargs
        result = t.t("app.name", bad_key="value")
        assert result  # Should still return something

    def test_set_lang(self):
        from eosim.i18n import Translator
        t = Translator("en")
        t.set_lang("de")
        assert t.lang == "de"

    def test_set_lang_invalid_raises(self):
        from eosim.i18n import Translator
        t = Translator("en")
        with pytest.raises(ValueError):
            t.set_lang("xx")

    def test_unsupported_lang_falls_back_to_english(self):
        from eosim.i18n import Translator
        t = Translator("xx")  # unsupported
        assert t.lang == "en"

    def test_get_translator_singleton(self):
        from eosim.i18n import get_translator
        t1 = get_translator()
        t2 = get_translator()
        assert t1 is t2

    def test_set_language_global(self):
        from eosim.i18n import set_language, get_translator
        set_language("fr")
        assert get_translator().lang == "fr"

    def test_t_shorthand(self):
        import eosim.i18n.translator as tr
        tr._instance = None
        from eosim.i18n import t
        result = t("app.name")
        assert "EoSim" in result

    def test_env_language_selection(self):
        import eosim.i18n.translator as tr
        tr._instance = None
        with patch.dict(os.environ, {"EOSIM_LANG": "de"}):
            tr._instance = None
            from eosim.i18n.translator import get_translator
            inst = get_translator()
            assert inst.lang == "de"

    def test_all_locales_have_app_name(self):
        from eosim.i18n import Translator
        for lang in ["en", "es", "zh", "hi", "fr", "ar", "pt", "de", "ja", "ko"]:
            t = Translator(lang)
            result = t.t("app.name")
            assert "EoSim" in result, f"app.name missing EoSim in {lang}"

    def test_all_locales_have_production_api_url(self):
        from eosim.i18n import Translator
        for lang in ["en", "es", "zh", "hi", "fr", "ar", "pt", "de", "ja", "ko"]:
            t = Translator(lang)
            result = t.t("platform.api_url")
            assert "api.eosim.io" in result, f"api_url wrong in {lang}: {result}"

    def test_all_locales_have_nav_keys(self):
        from eosim.i18n import Translator
        nav_keys = ["nav.dashboard", "nav.simulations", "nav.modules", "nav.docs"]
        for lang in ["en", "es", "zh", "hi", "fr", "ar", "pt", "de", "ja", "ko"]:
            t = Translator(lang)
            for key in nav_keys:
                result = t.t(key)
                assert result != key, f"Key {key} not translated in {lang}"

    def test_locale_files_are_valid_json(self):
        locales_dir = Path(__file__).parent.parent.parent / "eosim" / "i18n" / "locales"
        for lang in ["en", "es", "zh", "hi", "fr", "ar", "pt", "de", "ja", "ko"]:
            path = locales_dir / f"{lang}.json"
            assert path.exists(), f"Locale file missing: {lang}.json"
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            assert isinstance(data, dict)
            assert len(data) > 0


class TestProductionConfig:
    """Tests for the production configuration module."""

    def test_production_config_import(self):
        from eosim.config.production import get_config
        config = get_config()
        assert config is not None

    def test_production_api_url(self):
        from eosim.config.production import PRODUCTION_API_BASE
        assert PRODUCTION_API_BASE == "https://api.eosim.io"

    def test_production_ws_url(self):
        from eosim.config.production import PRODUCTION_WS_BASE
        assert PRODUCTION_WS_BASE == "wss://api.eosim.io"

    def test_production_docs_url(self):
        from eosim.config.production import PRODUCTION_DOCS_URL
        assert PRODUCTION_DOCS_URL == "https://docs.eosim.io"

    def test_production_status_url(self):
        from eosim.config.production import PRODUCTION_STATUS_URL
        assert PRODUCTION_STATUS_URL == "https://status.eosim.io"

    def test_supported_languages_count(self):
        from eosim.config.production import SUPPORTED_LANGUAGES
        assert len(SUPPORTED_LANGUAGES) == 10

    def test_arabic_is_rtl(self):
        from eosim.config.production import SUPPORTED_LANGUAGES
        ar = next(l for l in SUPPORTED_LANGUAGES if l["code"] == "ar")
        assert ar["rtl"] is True

    def test_english_is_not_rtl(self):
        from eosim.config.production import SUPPORTED_LANGUAGES
        en = next(l for l in SUPPORTED_LANGUAGES if l["code"] == "en")
        assert en["rtl"] is False

    def test_gps_enabled(self):
        from eosim.config.production import GPS_ENABLED
        assert GPS_ENABLED is True

    def test_platform_version(self):
        from eosim.config.production import PLATFORM_VERSION
        assert PLATFORM_VERSION == "3.0.1"

    def test_get_config_has_all_keys(self):
        from eosim.config.production import get_config
        config = get_config()
        assert "api_base" in config
        assert "ws_base" in config
        assert "docs_url" in config
        assert "platform" in config
        assert "features" in config
        assert "languages" in config
        assert "gps" in config

    def test_no_localhost_in_production_urls(self):
        from eosim.config.production import (
            PRODUCTION_API_BASE, PRODUCTION_WS_BASE,
            PRODUCTION_DOCS_URL, PRODUCTION_STATUS_URL,
            PRODUCTION_CDN_URL, PRODUCTION_AUTH_URL
        )
        for url in [PRODUCTION_API_BASE, PRODUCTION_WS_BASE,
                    PRODUCTION_DOCS_URL, PRODUCTION_STATUS_URL,
                    PRODUCTION_CDN_URL, PRODUCTION_AUTH_URL]:
            assert "localhost" not in url, f"localhost found in production URL: {url}"
            assert "127.0.0.1" not in url, f"127.0.0.1 found in production URL: {url}"

    def test_features_dict(self):
        from eosim.config.production import FEATURES
        assert FEATURES["websocket"] is True
        assert FEATURES["multi_language"] is True
        assert FEATURES["mobile_app"] is True
        assert FEATURES["browser_extension"] is True
        assert FEATURES["gps_location"] is True

    def test_config_package_import(self):
        from eosim.config import get_config, API_BASE, WS_BASE
        assert "eosim.io" in API_BASE
        assert "eosim.io" in WS_BASE
