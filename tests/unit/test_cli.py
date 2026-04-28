# SPDX-License-Identifier: MIT
"""Unit tests for CLI commands using Click's CliRunner."""
from unittest.mock import patch, MagicMock
from click.testing import CliRunner


class TestCLIList:
    def test_list_runs(self):
        from eosim.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['list'])
        assert result.exit_code == 0
        assert 'Available platforms' in result.output

    def test_list_json(self):
        from eosim.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['list', '--format', 'json'])
        assert result.exit_code == 0
        assert '[' in result.output  # JSON array

    def test_list_csv(self):
        from eosim.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['list', '--format', 'csv'])
        assert result.exit_code == 0
        assert 'name,arch,engine' in result.output

    def test_list_filter_domain(self):
        from eosim.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['list', '--domain', 'automotive'])
        assert result.exit_code == 0

    def test_list_filter_arch(self):
        from eosim.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['list', '--arch', 'arm64'])
        assert result.exit_code == 0

    def test_list_group_by(self):
        from eosim.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['list', '--group-by', 'arch'])
        assert result.exit_code == 0


class TestCLISearch:
    def test_search_found(self):
        from eosim.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['search', 'stm32'])
        assert result.exit_code == 0
        assert 'stm32' in result.output.lower()

    def test_search_not_found(self):
        from eosim.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['search', 'zzzznonexistent'])
        assert result.exit_code == 0
        assert 'No platforms' in result.output


class TestCLIStats:
    def test_stats(self):
        from eosim.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['stats'])
        assert result.exit_code == 0
        assert 'Platform Statistics' in result.output


class TestCLIInfo:
    def test_info_existing(self):
        from eosim.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['info', 'esp32'])
        assert result.exit_code == 0
        assert 'esp32' in result.output.lower()

    def test_info_missing(self):
        from eosim.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['info', 'nonexistent_platform_xyz'])
        assert result.exit_code != 0


class TestCLIValidate:
    def test_validate_all(self):
        from eosim.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['validate', '--all'])
        assert result.exit_code == 0
        assert 'Validated' in result.output
        assert 'passed' in result.output

    def test_validate_no_arg(self):
        from eosim.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['validate'])
        assert result.exit_code != 0

    def test_validate_missing_file(self):
        from eosim.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['validate', '/nonexistent/file.yml'])
        assert result.exit_code != 0


class TestCLIDoctor:
    def test_doctor(self):
        from eosim.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['doctor'])
        assert result.exit_code == 0
        assert 'EoSim Doctor' in result.output
        assert 'Platform Registry' in result.output


class TestCLIDomain:
    def test_domain_list(self):
        from eosim.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['domain', 'list'])
        assert result.exit_code == 0
        assert 'Simulation Domains' in result.output
        assert 'automotive' in result.output.lower()

    def test_domain_info(self):
        from eosim.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['domain', 'info', 'automotive'])
        assert result.exit_code == 0
        assert 'ISO 26262' in result.output

    def test_domain_info_missing(self):
        from eosim.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['domain', 'info', 'nonexistent'])
        assert result.exit_code != 0


class TestCLIModeling:
    def test_modeling_list(self):
        from eosim.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['modeling', 'list'])
        assert result.exit_code == 0
        assert 'Modeling Methods' in result.output

    def test_modeling_info(self):
        from eosim.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['modeling', 'info', 'deterministic'])
        assert result.exit_code == 0
        assert 'Deterministic' in result.output

    def test_modeling_info_missing(self):
        from eosim.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['modeling', 'info', 'nonexistent'])
        assert result.exit_code != 0


class TestCLIBridge:
    def test_bridge_status(self):
        from eosim.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['bridge', 'status'])
        assert result.exit_code == 0
        assert 'Bridge Status' in result.output


class TestCLISimulator:
    def test_simulator_list(self):
        from eosim.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['simulator', 'list'])
        assert result.exit_code == 0
        assert 'Available Simulators' in result.output

    def test_simulator_products(self):
        from eosim.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['simulator', 'products'])
        assert result.exit_code == 0
        assert 'Product Templates' in result.output

    def test_simulator_run(self):
        from eosim.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['simulator', 'run', 'vehicle', '--ticks', '10'])
        assert result.exit_code == 0
        assert 'Tick' in result.output

    def test_simulator_run_with_scenario(self):
        from eosim.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['simulator', 'run', 'vehicle', '--ticks', '10', '--scenario', 'highway_cruise'])
        assert result.exit_code == 0
        assert 'highway_cruise' in result.output

    def test_simulator_run_unknown(self):
        from eosim.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['simulator', 'run', 'nonexistent_xyz'])
        assert result.exit_code != 0


class TestCLIVersion:
    def test_version(self):
        from eosim.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['--version'])
        assert result.exit_code == 0
        assert '2.0.0' in result.output


class TestCLIRun:
    def test_run_eosim_engine(self, tmp_path):
        from eosim.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['run', 'esp32', '--timeout', '5',
                                      '--log-dir', str(tmp_path)])
        # Should succeed (eosim native engine)
        assert result.exit_code == 0

    def test_run_missing_platform(self):
        from eosim.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['run', 'nonexistent_xyz'])
        assert result.exit_code != 0


class TestCLITest:
    def test_test_command(self):
        from eosim.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['test', 'esp32'])
        assert result.exit_code == 0
        assert 'EoSim test' in result.output

    def test_test_missing(self):
        from eosim.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['test', 'nonexistent_xyz'])
        assert result.exit_code != 0


class TestCLIArtifact:
    def test_artifact(self, tmp_path):
        from eosim.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ['artifact', 'esp32', '--output', str(tmp_path)])
        assert result.exit_code == 0
        assert 'Artifacts exported' in result.output
