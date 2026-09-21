#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import tempfile
from pathlib import Path

from s10.harness import FixtureDriver, run_admission


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the bounded S10 Mem0 admission harness")
    parser.add_argument("--driver", choices=("fixture", "mem0"), default="fixture")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    spike_root = Path(__file__).resolve().parent
    manifest_path = spike_root / "fixtures" / "manifest.json"
    with tempfile.TemporaryDirectory(prefix="aptuni-s10-") as temporary:
        disposable = Path(temporary)
        if args.driver == "mem0":
            from s10.mem0_driver import Mem0Driver, probe_raw_retention

            driver = Mem0Driver(disposable / "provider")
        else:
            driver = FixtureDriver(disposable / "provider")
        result = run_admission(
            manifest_path=manifest_path,
            canonical_root=manifest_path.parent,
            provider_root=disposable / "provider",
            driver=driver,
        )
        if args.driver == "mem0":
            result["raw_retention_probe"] = probe_raw_retention(disposable / "raw-provider")
            result["verdict"] = (
                "REJECT_RAW_RETENTION"
                if result["raw_retention_probe"]["verdict"] != "PASS"
                else "S10_PASS"
            )
        lock_path = spike_root / "requirements-lock.txt"
        result["runtime"] = {
            "python": platform.python_version(),
            "requirements_lock_sha256": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
        }
    encoded = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=args.output.parent,
            prefix=f".{args.output.name}.",
            delete=False,
        ) as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
            temporary_output = Path(stream.name)
        os.chmod(temporary_output, 0o600)
        temporary_output.replace(args.output)
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
