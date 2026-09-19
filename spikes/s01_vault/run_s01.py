"""Reproducible S01 runner: assert the Gate 0 baseline, run the suite, measure, write a result.

Usage (from ``spikes/s01_vault``, in a venv made with the pinned interpreter)::

    /opt/homebrew/bin/python3.13 -m venv <venv> && <venv>/bin/pip install 'pydantic>=2,<3'
    <venv>/bin/python run_s01.py

Exits non-zero if the baseline differs or any acceptance test fails.
"""

from __future__ import annotations

import json
import logging
import platform
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import pydantic

from s01.fsgate import statfs_info
from s01.records import parse_record
from s01.vault import Vault
from tests.helpers import golden_raw

logger = logging.getLogger("s01")
BASELINE = {"python": "3.13.3", "sqlite": "3.53.2", "macos": "26.2"}
RESULT_PATH = Path(__file__).parent / "results" / "S01-result.json"


def baseline_facts() -> dict[str, str]:
    """Collect interpreter/SQLite/OS/filesystem facts the result must record."""
    tmp_info = statfs_info(Path(tempfile.gettempdir()))
    return {
        # Never record the absolute interpreter path: it can contain the local user name.
        "executable": "venv/bin/python" if sys.prefix != sys.base_prefix else "system/python",
        "python": platform.python_version(),
        "sqlite": sqlite3.sqlite_version,
        "macos": subprocess.run(["sw_vers", "-productVersion"], capture_output=True, text=True,
                                check=True).stdout.strip(),
        "macos_build": subprocess.run(["sw_vers", "-buildVersion"], capture_output=True, text=True,
                                      check=True).stdout.strip(),
        "tmp_fs": tmp_info.fstypename,
        "tmp_fs_local": str(tmp_info.is_local),
        "pydantic": pydantic.VERSION,
    }


def measure() -> dict[str, float]:
    """Time single-record commits as the Vault grows, and full reads at the final size."""
    seed = [parse_record(r) for r in golden_raw()]
    template = next(r for r in golden_raw() if r["record_type"] == "observation")
    with tempfile.TemporaryDirectory() as raw:
        vault = Vault.init(Path(raw) / "vault", Path(raw) / "state")
        vault.commit(seed, expected_seq=0)
        latencies = []
        for index in range(300):
            record = parse_record(template | {
                "id": f"obs_{'0' * 20}8{index:05d}",
                "idempotency_key": f"bench:{index}",
            })
            start = time.perf_counter()
            vault.commit([record], expected_seq=vault.head().seq)
            latencies.append((time.perf_counter() - start) * 1000)
        reads = []
        for _ in range(20):
            start = time.perf_counter()
            vault.read_all()
            reads.append((time.perf_counter() - start) * 1000)
    ordered = sorted(latencies)
    return {
        "commit_ms_first50_median": statistics.median(latencies[:50]),
        "commit_ms_last50_median": statistics.median(latencies[-50:]),
        "commit_ms_p95": ordered[int(0.95 * len(ordered)) - 1],
        "read_all_ms_median_316_records": statistics.median(reads),
    }


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    facts = baseline_facts()
    mismatches = {k: facts[k] for k, v in BASELINE.items() if facts[k] != v}
    if facts["tmp_fs"] != "apfs" or facts["tmp_fs_local"] != "True":
        mismatches["tmp_fs"] = f"{facts['tmp_fs']} local={facts['tmp_fs_local']}"
    suite = unittest.defaultTestLoader.discover("tests", top_level_dir=".")
    outcome = unittest.TextTestRunner(verbosity=1).run(suite)
    metrics = measure() if outcome.wasSuccessful() else {}
    passed = outcome.wasSuccessful() and not mismatches
    result = {
        "spike": "S01", "passed": passed, "baseline": facts, "baseline_mismatches": mismatches,
        "tests_run": outcome.testsRun, "failures": len(outcome.failures), "errors": len(outcome.errors),
        "metrics": metrics,
    }
    RESULT_PATH.parent.mkdir(exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    logger.info(json.dumps(result, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
