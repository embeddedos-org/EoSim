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
            detail = "\n".join(f"  {name}: {errs}" for name, errs in sorted(failures.items()))
            self.fail(f"{len(failures)} platform.yml file(s) failed schema validation:\n{detail}")

    def test_no_platform_yml_defines_anything_twice(self):
        """A platform.yml must hold exactly one definition.

        Six files (nrf5340, nrf9160, pic32mz, psoc6, renesas-ra6m5,
        ti-msp432) each held two complete definitions concatenated into one
        document, and they disagreed -- on memory_mb, on display_name, on
        domain, and in pic32mz's case on arch (mipsel vs mips, which is the
        endianness of the emulated machine). PyYAML silently keeps the last
        occurrence of a duplicate key, so half of every one of those files
        was dead text that a reader would reasonably believe was in effect
        (issue #95).

        yaml.safe_load cannot see this, so the check parses with a loader
        that reports duplicate keys, and also rejects a file carrying more
        than one YAML document.
        """
        import collections

        class _DuplicateKeyLoader(yaml.SafeLoader):
            pass

        duplicates: list = []

        def _mapping(loader, node, deep=False):
            keys = [loader.construct_object(k, deep=True) for k, _ in node.value]
            repeated = [k for k, n in collections.Counter(keys).items() if n > 1]
            if repeated:
                duplicates.append(repeated)
            return loader.construct_mapping(node, deep)

        _DuplicateKeyLoader.add_constructor(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping
        )

        defs = sorted(PLATFORMS_DIR.glob("*/platform.yml"))
        self.assertGreater(len(defs), 0, "no platform.yml files found")
        failures = {}
        for path in defs:
            text = path.read_text()
            documents = list(yaml.safe_load_all(text))
            if len(documents) != 1:
                failures[path.parent.name] = f"{len(documents)} YAML documents, expected 1"
                continue
            duplicates.clear()
            yaml.load(text, Loader=_DuplicateKeyLoader)
            if duplicates:
                failures[path.parent.name] = f"keys defined more than once: {duplicates}"
        if failures:
            detail = "\n".join(f"  {name}: {why}" for name, why in sorted(failures.items()))
            self.fail(f"{len(failures)} platform.yml file(s) define something twice:\n{detail}")


if __name__ == "__main__":
    unittest.main()
