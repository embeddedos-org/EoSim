# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Plugin discovery and loading system."""
import importlib
import os
import logging

from eosim.plugins.base import PluginBase

logger = logging.getLogger(__name__)


class PluginLoader:
    """Discovers and loads EoSim plugins from a directory."""

    def __init__(self, plugin_dirs=None):
        self.plugin_dirs = plugin_dirs or []
        self.plugins = {}

    def discover(self):
        """Scan plugin directories for plugin modules."""
        for d in self.plugin_dirs:
            if not os.path.isdir(d):
                continue
            for fname in os.listdir(d):
                if fname.endswith('.py') and not fname.startswith('_'):
                    module_name = fname[:-3]
                    try:
                        spec = importlib.util.spec_from_file_location(module_name, os.path.join(d, fname))
                        if spec and spec.loader:
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)
                            for attr_name in dir(module):
                                attr = getattr(module, attr_name)
                                if (isinstance(attr, type) and issubclass(attr, PluginBase)
                                        and attr is not PluginBase):
                                    plugin = attr()
                                    self.plugins[plugin.NAME] = plugin
                                    logger.info("Loaded plugin: %s v%s", plugin.NAME, plugin.VERSION)
                    except Exception as e:
                        logger.warning("Failed to load plugin %s: %s", fname, e)

    def load_all(self):
        for name, plugin in self.plugins.items():
            try:
                plugin.on_load()
            except Exception as e:
                logger.warning("Plugin %s on_load failed: %s", name, e)

    def unload_all(self):
        for name, plugin in self.plugins.items():
            try:
                plugin.on_unload()
            except Exception as e:
                logger.warning("Plugin %s on_unload failed: %s", name, e)

    def get_plugin(self, name):
        return self.plugins.get(name)

    def list_plugins(self):
        return {name: p.get_info() for name, p in self.plugins.items()}
