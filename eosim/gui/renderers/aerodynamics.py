# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""3D renderer for aerodynamics (domain: aerodynamics)."""
from eosim.gui.renderers import BaseRenderer, register_renderer


class AerodynamicsRenderer(BaseRenderer):
    DOMAIN = "aerodynamics"
    DISPLAY_NAME = "Aerodynamics"

    def __init__(self):
        super().__init__()

    def setup(self, ax):
        ax.set_xlim(-2, 2)
        ax.set_ylim(-2, 2)
        ax.set_zlim(-1, 3)
        ax.set_title("Aerodynamics", fontsize=9)

    def update(self, ax, state):
        aoa = state.get("aoa_deg", 0)
        cl = state.get("cl", 0)
        cd = state.get("cd", 0)
        airspeed = state.get("airspeed_mps", 0)
        mach = state.get("mach_number", 0)
        ax.set_title(f"Aero V={airspeed:.0f}m/s M={mach:.3f} AoA={aoa:.1f} Cl={cl:.3f} Cd={cd:.4f}", fontsize=8)


register_renderer("aerodynamics", AerodynamicsRenderer)
