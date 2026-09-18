"""Shared fixture loading for the S01 spike tests."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def golden_raw() -> list[dict[str, Any]]:
    """Return the golden valid records as plain dicts, in recorded order."""
    lines = (FIXTURES / "golden_valid.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def golden_by_id() -> dict[str, dict[str, Any]]:
    """Return golden raw records keyed by id (deep copies, safe to mutate)."""
    return {item["id"]: copy.deepcopy(item) for item in golden_raw()}


def schema_cases() -> dict[str, dict[str, Any]]:
    """Return named invalid schema cases (documentation key removed)."""
    cases = json.loads((FIXTURES / "invalid" / "schema_cases.json").read_text(encoding="utf-8"))
    cases.pop("_doc", None)
    return cases


def apply_case(case: dict[str, Any]) -> dict[str, Any]:
    """Build the invalid raw record described by a schema case."""
    record = golden_by_id()[case["base"]]
    for key in case.get("drop", []):
        record.pop(key, None)
    record.update(copy.deepcopy(case.get("patch", {})))
    return record
