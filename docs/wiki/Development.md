# Development

## Contribution source of truth

[CONTRIBUTING](https://github.com/embeddedos-org/EoSim/blob/master/CONTRIBUTING.md)

Before proposing a change, also review the [README](https://github.com/embeddedos-org/EoSim/blob/master/README.md). Keep changes scoped, add tests appropriate to the affected behavior, and follow the repository's current automation and review requirements.

## Build and dependency inputs found

`Dockerfile`, `Makefile`, `android/app/build.gradle.kts`, `docker-compose.yml`, `docs/Makefile`, `enterprise/docker/Dockerfile`, `enterprise/docker/docker-compose.yml`, `pyproject.toml`.

## Tests found in the default-branch tree

`eosim/tests/__init__.py`, `eosim/tests/runner.py`, `eosim/tests/scenarios.py`, `tests/__init__.py`, `tests/conftest.py`, `tests/functional/test_functional_e2e.py`, `tests/integration/__init__.py`, `tests/integration/test_cli_commands.py`, `tests/integration/test_platform_pipeline.py`, `tests/integration/test_scenario_runner.py`, `tests/performance/test_performance_benchmarks.py`, `tests/scenarios/full_boot.yml`, and 19 more.

## Documented test commands

These commands are reproduced from the inspected root README or contributing guide:

```bash
make test
```

```bash
make test           # Run all tests
```

## Verification baseline

This inventory comes from `master` at [`bad4fa39fec0`](https://github.com/embeddedos-org/EoSim/commit/bad4fa39fec091da32afa6aa28709a7f07150389) and found 31 test-related paths among 557 files. Re-check the source tree when that commit is no longer current.
