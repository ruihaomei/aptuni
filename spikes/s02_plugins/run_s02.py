"""Reproducible S02 runner (stdlib only; offline).

Usage from ``spikes/s02_plugins``::

    /opt/homebrew/bin/python3.13 run_s02.py

Builds fixture wheels, creates disposable venvs with the pinned interpreter, installs with
``pip --no-index`` (no network), runs the acceptance tests, and writes ``results/S02-result.json``.
Exits non-zero on a baseline mismatch or any failed test.
"""

from __future__ import annotations

import json
import logging
import platform
import subprocess
import sys
import unittest
from pathlib import Path

logger = logging.getLogger("s02")
BASELINE = {"python": "3.13.3", "macos": "26.2"}
RESULT_PATH = Path(__file__).parent / "results" / "S02-result.json"


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    facts = {
        "executable": sys.executable,
        "python": platform.python_version(),
        "macos": subprocess.run(["sw_vers", "-productVersion"], capture_output=True, text=True,
                                check=True).stdout.strip(),
        "pip": subprocess.run([sys.executable, "-m", "pip", "--version"], capture_output=True, text=True,
                              check=False).stdout.split(" from ")[0],
    }
    mismatches = {k: facts[k] for k, v in BASELINE.items() if facts[k] != v}
    suite = unittest.defaultTestLoader.discover("tests", top_level_dir=".")
    outcome = unittest.TextTestRunner(verbosity=1).run(suite)
    passed = outcome.wasSuccessful() and not mismatches
    result = {"spike": "S02", "passed": passed, "baseline": facts, "baseline_mismatches": mismatches,
              "tests_run": outcome.testsRun, "failures": len(outcome.failures), "errors": len(outcome.errors)}
    RESULT_PATH.parent.mkdir(exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    logger.info(json.dumps(result, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
