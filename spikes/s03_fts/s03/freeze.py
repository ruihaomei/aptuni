"""Verify that precommitted S03 evidence inputs have not changed."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


class FreezeMismatch(RuntimeError):
    """Raised when a frozen S03 input is missing or has changed."""


def verify_freeze(root: Path) -> None:
    manifest_path = root / "FREEZE.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = manifest.get("sha256")
    if not isinstance(expected, dict) or not expected:
        raise FreezeMismatch("FREEZE.json has no sha256 entries")

    mismatches: list[str] = []
    for relative, digest in sorted(expected.items()):
        path = root / relative
        if not path.is_file():
            mismatches.append(f"missing: {relative}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != digest:
            mismatches.append(f"changed: {relative}")
    if mismatches:
        raise FreezeMismatch("frozen S03 inputs do not match:\n" + "\n".join(mismatches))
