# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""EoSim Internationalization (i18n) — 10 language support.

Supported languages:
  en  — English
  es  — Spanish
  zh  — Mandarin Chinese (Simplified)
  hi  — Hindi
  fr  — French
  ar  — Arabic
  pt  — Portuguese
  de  — German
  ja  — Japanese
  ko  — Korean
"""

from .translator import Translator, get_translator, set_language, t

__all__ = ["Translator", "get_translator", "set_language", "t"]
