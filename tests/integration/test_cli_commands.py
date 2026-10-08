"""Integration tests — CLI commands via Click test runner."""
import json
from pathlib import Path

import pytest
from click.testing import CliRunner

import eosim
from eosim.cli.main import cli

# Every platform the package ships is one platform.yml under eosim/platforms.
SHIPPED_PLATFORMS = len(list((Path(eosim.__file__).parent / "platforms").glob("*/platform.yml")))


@pytest.fixture
def runner():
    return CliRunner()


class TestCLICommands:
    """Test CLI commands produce correct output without errors."""

    def test_cli_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "EoSim" in result.output

    def test_list_command(self, runner):
        result = runner.invoke(cli, ["list"])
        assert result.exit_code == 0
        # The CLI passes "" for every unset filter; that must not filter out
        # every platform (regression: "Available platforms (0)").
        # Compared with what the package ships rather than a literal, which
        # every new board def broke (149 -> 153 in b34572c).
        assert SHIPPED_PLATFORMS > 100
        assert f"Available platforms ({SHIPPED_PLATFORMS})" in result.output
        assert "stm32f4" in result.output

    def test_october_2026_boards_parse(self, runner):
        # The October 2026 board intake (DEBIX M8391-01, Arduino VENTUNO Q,
        # NXP FRDM-IMXRT1186, Bluemag Pi): every new def must parse and
        # carry the schema fields the list/search/info commands rely on.
        # New boards are asserted by name so a missing def fails loudly
        # instead of hiding inside the dynamic count.
        from eosim.core.platform import discover_platforms
        root = str(Path(eosim.__file__).parent / "platforms")
        platforms = discover_platforms(root)
        expected = {
            "debix-m8391-01": ("arm64", "qemu", "DEBIX"),
            "arduino-ventuno-q": ("arm64", "qemu", "Arduino"),
            "nxp-frdm-imxrt1186": ("arm", "eosim", "NXP"),
            "bluemag-pi": ("riscv", "qemu", "Upbeat"),
        }
        for name, (arch, engine, vendor) in expected.items():
            assert name in platforms, f"board def missing: {name}"
            p = platforms[name]
            assert p.arch == arch, f"{name}: arch"
            assert p.engine == engine, f"{name}: engine"
            assert p.vendor == vendor, f"{name}: vendor"
            assert p.soc, f"{name}: soc is empty"
            assert p.platform_class, f"{name}: class is empty"

    def test_list_with_arch_filter(self, runner):
        result = runner.invoke(cli, ["list", "--arch", "arm", "--format", "json"])
        assert result.exit_code == 0
        rows = json.loads(result.output)
        assert rows, "arm filter returned no platforms"
        assert all(r["arch"].lower() == "arm" for r in rows)

    def test_stats_command(self, runner):
        result = runner.invoke(cli, ["stats"])
        assert result.exit_code == 0

    def test_search_command(self, runner):
        result = runner.invoke(cli, ["search", "stm32"])
        assert result.exit_code == 0

    def test_info_command(self, runner):
        result = runner.invoke(cli, ["info", "stm32f4"])
        assert result.exit_code == 0

    def test_validate_all_command(self, runner):
        result = runner.invoke(cli, ["validate", "--all"])
        assert result.exit_code == 0

    def test_doctor_command(self, runner):
        result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 0

    def test_domain_list_command(self, runner):
        result = runner.invoke(cli, ["domain", "list"])
        assert result.exit_code == 0

    def test_domain_info_command(self, runner):
        result = runner.invoke(cli, ["domain", "info", "automotive"])
        assert result.exit_code == 0

    def test_modeling_list_command(self, runner):
        result = runner.invoke(cli, ["modeling", "list"])
        assert result.exit_code == 0

    def test_modeling_info_command(self, runner):
        result = runner.invoke(cli, ["modeling", "info", "deterministic"])
        assert result.exit_code == 0

    def test_invalid_command(self, runner):
        result = runner.invoke(cli, ["nonexistent"])
        assert result.exit_code != 0
