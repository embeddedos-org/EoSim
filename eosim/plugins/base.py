# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Plugin base class for EoSim extensions."""
from abc import ABC, abstractmethod


class PluginBase(ABC):
    """Base class for all EoSim plugins."""

    NAME = "unnamed"
    VERSION = "0.0.0"
    DESCRIPTION = ""

    def __init__(self, context=None):
        self.context = context
        self.enabled = True

    @abstractmethod
    def on_load(self):
        """Called when the plugin is loaded."""
        pass

    def on_unload(self):
        """Called when the plugin is unloaded."""
        pass

    def on_tick(self, simulator, state):
        """Called each simulation tick (optional)."""
        pass

    def on_scenario_load(self, simulator, scenario_name):
        """Called when a scenario is loaded (optional)."""
        pass

    def get_info(self):
        return {"name": self.NAME, "version": self.VERSION, "description": self.DESCRIPTION, "enabled": self.enabled}
