"""Tiny JSON CLI so tests can drive the registry inside an isolated venv."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from s02 import registry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="s02")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("discover")
    approve = sub.add_parser("approve")
    approve.add_argument("--id", required=True)
    approve.add_argument("--approvals", required=True, type=Path)
    activate = sub.add_parser("activate")
    activate.add_argument("--enable", required=True)
    activate.add_argument("--approvals", required=True, type=Path)
    activate.add_argument("--isolated-bytecode", action="store_true",
                          help="ignore installed __pycache__ (RECORD does not hash .pyc files)")
    args = parser.parse_args(argv)
    if getattr(args, "isolated_bytecode", False):
        registry.isolate_bytecode()
    if args.command == "discover":
        payload = {"plugins": registry.discovered_as_dicts()}
    elif args.command == "approve":
        payload = registry.approve(args.id, args.approvals)
    else:
        payload = registry.activate([x for x in args.enable.split(",") if x], args.approvals)
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
