# SPDX-License-Identifier: MIT
"""Host environment detection and binary resolution."""
import os
import platform as _platform
import shutil
import sys
from dataclasses import dataclass
from typing import Optional


@dataclass
class HostEnvironment:
    os_name: str = ""
    arch: str = ""
    python_version: str = ""

    @classmethod
    def detect(cls) -> "HostEnvironment":
        os_name = sys.platform
        if os_name.startswith("win"):
            os_name = "windows"
        elif os_name.startswith("darwin"):
            os_name = "macos"
        elif os_name.startswith("linux"):
            os_name = "linux"
        return cls(
            os_name=os_name,
            arch=_platform.machine(),
            python_version="%d.%d.%d" % sys.version_info[:3],
        )

    def platform_info(self) -> dict[str, str]:
        return {
            "os": self.os_name,
            "arch": self.arch,
            "python": self.python_version,
            "shell": os.environ.get("SHELL", os.environ.get("COMSPEC", "")),
        }

    def adapt_path(self, path: str) -> str:
        if self.os_name == "windows":
            return path.replace("/", "\\")
        return path.replace("\\", "/")

    def resolve_binary(self, name: str) -> Optional[str]:
        return shutil.which(name)

    def resolve_renode(self) -> Optional[str]:
        return self.resolve_binary("renode")
