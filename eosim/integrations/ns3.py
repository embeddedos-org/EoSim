# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""ns-3 network simulator bridge."""
import subprocess
import shutil


class NS3Bridge:
    """Bridge to ns-3 network simulator via subprocess."""

    def __init__(self, ns3_dir=''):
        self.ns3_dir = ns3_dir
        self._available = False

    def available(self):
        return shutil.which('ns3') is not None or bool(self.ns3_dir)

    def run_script(self, script_name, args=None, timeout=60):
        cmd = ['ns3', 'run', script_name]
        if args:
            cmd.extend(args)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return {'success': result.returncode == 0, 'stdout': result.stdout, 'stderr': result.stderr}
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return {'success': False, 'error': str(e)}
