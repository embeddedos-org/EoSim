"""platform.yml enum regression test.

Every eosim/platforms/*/platform.yml must pass validate_platform() from
eosim.core.schema. This is the never-again test for the 2026-10-09
incident: two new board defs (bluemag-pi with arch "riscv",
debix-m8391-01 with domain "vision") landed with schema-invalid values
and broke the *nightly* validate-all tests instead of failing on the PR.
Push-gated, so bad board defs can never land silently again.
"""

import unittest
from pathlib import Path

import yaml

from eosim.core.schema import validate_platform

PLATFORMS_DIR = Path(__file__).resolve().parent.parent.parent / "eosim" / "platforms"


class TestPlatformSchema(unittest.TestCase):
    def test_all_platform_ymls_pass_schema(self):
        defs = sorted(PLATFORMS_DIR.glob("*/platform.yml"))
        self.assertGreater(len(defs), 0, "no platform.yml files found")
        failures = {}
        for path in defs:
            data = yaml.safe_load(path.read_text())
            errors = validate_platform(data or {})
            if errors:
                failures[path.parent.name] = errors
        if failures:
            detail = "\n".join(
                f"  {name}: {errs}" for name, errs in sorted(failures.items())
            )
            self.fail(
                f"{len(failures)} platform.yml file(s) failed schema validation:\n{detail}"
            )


if __name__ == "__main__":
    unittest.main()
