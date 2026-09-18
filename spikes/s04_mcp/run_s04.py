#!/usr/bin/env python3
"""Run the deterministic local layer of S04; real-host evidence is separate."""

from __future__ import annotations

import importlib.metadata
import json
import platform
import sqlite3
import sys
import unittest


EXPECTED = {"python": "3.13.3", "sqlite": "3.53.2", "mcp": "2.2.0"}


def main() -> int:
    actual = {
        "python": platform.python_version(),
        "sqlite": sqlite3.sqlite_version,
        "mcp": importlib.metadata.version("mcp"),
    }
    if actual != EXPECTED:
        print(json.dumps({"status": "BLOCKED_RUNTIME_MISMATCH", "expected": EXPECTED,
                          "actual": actual}, sort_keys=True), file=sys.stderr)
        return 2
    suite = unittest.defaultTestLoader.discover("tests")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({"status": "PASS" if result.wasSuccessful() else "FAIL",
                      "runtime": actual, "tests_run": result.testsRun}, sort_keys=True))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
