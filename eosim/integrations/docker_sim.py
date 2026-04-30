# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Docker container-based simulation runner."""
import subprocess
import shutil


class DockerSimRunner:
    """Run simulations inside Docker containers."""

    def __init__(self):
        self._available = shutil.which('docker') is not None

    def available(self):
        return self._available

    def run(self, image, command, timeout=120, volumes=None):
        cmd = ['docker', 'run', '--rm']
        if volumes:
            for v in volumes:
                cmd.extend(['-v', v])
        cmd.extend([image] + (command if isinstance(command, list) else [command]))
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return {'success': result.returncode == 0, 'stdout': result.stdout, 'stderr': result.stderr}
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return {'success': False, 'error': str(e)}

    def pull(self, image):
        try:
            subprocess.run(['docker', 'pull', image], capture_output=True, timeout=300)
        except Exception:
            pass
