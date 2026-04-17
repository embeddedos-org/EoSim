# SPDX-License-Identifier: MIT
"""Platform dataclasses and discovery."""
import os
from dataclasses import dataclass, field
from typing import Optional

import yaml


@dataclass
class RuntimeConfig:
    memory_mb: int = 512
    headless: bool = True
    uart: Optional[str] = None
    timeout_s: Optional[int] = None


@dataclass
class QemuConfig:
    machine: str = "virt"
    cpu: Optional[str] = None
    extra_args: Optional[str] = None
    gdb_port: Optional[int] = None
    qmp_port: Optional[int] = None
    start_paused: bool = False


@dataclass
class BootConfig:
    kernel: Optional[str] = None
    rootfs: Optional[str] = None
    initrd: Optional[str] = None
    firmware: Optional[str] = None
    append: Optional[str] = None


@dataclass
class Platform:
    name: str = ""
    arch: str = ""
    engine: str = "renode"
    display_name: str = ""
    vendor: str = ""
    platform_class: str = ""
    soc: str = ""
    domain: str = ""
    modeling: str = ""
    domain_config: dict = field(default_factory=dict)
    modeling_config: dict = field(default_factory=dict)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    qemu: QemuConfig = field(default_factory=QemuConfig)
    boot: BootConfig = field(default_factory=BootConfig)
    source_dir: Optional[str] = None
    resc: Optional[str] = None

    @classmethod
    def from_yaml(cls, path: str) -> "Platform":
        with open(path) as f:
            data = yaml.safe_load(f) or {}

        runtime_data = data.pop("runtime", {}) or {}
        qemu_data = data.pop("qemu", {}) or {}
        boot_data = data.pop("boot", {}) or {}

        platform_class = data.pop("class", "")

        kwargs = {}
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        for k, v in data.items():
            if k in valid_fields:
                kwargs[k] = v

        kwargs["platform_class"] = platform_class if platform_class else kwargs.get("platform_class", "")
        kwargs.setdefault("domain_config", data.get("domain_config", {}))
        kwargs.setdefault("modeling_config", data.get("modeling_config", {}))
        kwargs["runtime"] = RuntimeConfig(**{
            k: v for k, v in runtime_data.items()
            if k in RuntimeConfig.__dataclass_fields__
        })
        kwargs["qemu"] = QemuConfig(**{
            k: v for k, v in qemu_data.items()
            if k in QemuConfig.__dataclass_fields__
        })
        kwargs["boot"] = BootConfig(**{
            k: v for k, v in boot_data.items()
            if k in BootConfig.__dataclass_fields__
        })

        if "source_dir" not in kwargs or kwargs["source_dir"] is None:
            kwargs["source_dir"] = os.path.dirname(os.path.abspath(path))

        return cls(**kwargs)


def discover_platforms(root_dir: str) -> dict[str, "Platform"]:
    platforms = {}
    if not os.path.isdir(root_dir):
        return platforms
    for entry in os.listdir(root_dir):
        sub = os.path.join(root_dir, entry)
        if os.path.isdir(sub):
            yml = os.path.join(sub, "platform.yml")
            if os.path.isfile(yml):
                try:
                    p = Platform.from_yaml(yml)
                    if p.name:
                        platforms[p.name] = p
                except Exception:
                    pass
    return platforms
