# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Core translator for EoSim i18n support."""

from __future__ import annotations
import os
import json
from pathlib import Path
from typing import Optional

_LOCALES_DIR = Path(__file__).parent / "locales"
_SUPPORTED = ["en", "es", "zh", "hi", "fr", "ar", "pt", "de", "ja", "ko"]
_DEFAULT_LANG = "en"

_instance: Optional["Translator"] = None


class Translator:
    """Thread-safe translator with fallback to English."""

    def __init__(self, lang: str = _DEFAULT_LANG):
        self._lang = lang if lang in _SUPPORTED else _DEFAULT_LANG
        self._cache: dict[str, dict] = {}
        self._load(self._lang)
        if self._lang != _DEFAULT_LANG:
            self._load(_DEFAULT_LANG)

    def _load(self, lang: str) -> None:
        if lang in self._cache:
            return
        path = _LOCALES_DIR / f"{lang}.json"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                self._cache[lang] = json.load(f)
        else:
            self._cache[lang] = {}

    def t(self, key: str, **kwargs) -> str:
        """Translate a key with optional format arguments."""
        text = (
            self._cache.get(self._lang, {}).get(key)
            or self._cache.get(_DEFAULT_LANG, {}).get(key)
            or key
        )
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, ValueError):
                pass
        return text

    @property
    def lang(self) -> str:
        return self._lang

    @property
    def supported_languages(self) -> list[str]:
        return list(_SUPPORTED)

    def set_lang(self, lang: str) -> None:
        if lang not in _SUPPORTED:
            raise ValueError(f"Unsupported language: {lang}. Supported: {_SUPPORTED}")
        self._lang = lang
        self._load(lang)


def get_translator() -> Translator:
    global _instance
    if _instance is None:
        lang = os.environ.get("EOSIM_LANG", _DEFAULT_LANG)
        _instance = Translator(lang)
    return _instance


def set_language(lang: str) -> None:
    get_translator().set_lang(lang)


def t(key: str, **kwargs) -> str:
    return get_translator().t(key, **kwargs)
