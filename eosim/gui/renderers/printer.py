# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""3D renderer for Printing."""
from eosim.gui.renderers import BaseRenderer, register_renderer


class PrinterRenderer(BaseRenderer):
    DOMAIN = "printing"
    DISPLAY_NAME = "Printing"

    def setup(self, ax):
        ax.set_xlim(-10, 10)
        ax.set_ylim(-10, 10)
        ax.set_zlim(0, 10)
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_zlabel("Z")
        ax.set_title(self.DISPLAY_NAME, fontsize=10)

    def update(self, ax, state: dict):
        ax.cla()
        self.setup(ax)
        info = "\n".join(f"{k}: {v}" for k, v in list(state.items())[:6])
        ax.text2D(0.02, 0.95, info, transform=ax.transAxes,
                  fontsize=8, verticalalignment='top', family='monospace')


register_renderer("printing", PrinterRenderer)
