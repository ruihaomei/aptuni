"""Shared golden-fixture loading for Aptuni tests."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def golden_raw() -> list[dict[str, Any]]:
    """Golden valid records as plain dicts, in recorded order."""
    lines = (FIXTURES / "golden_v1.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def golden_by_id() -> dict[str, dict[str, Any]]:
    return {item["id"]: copy.deepcopy(item) for item in golden_raw()}


def schema_cases() -> dict[str, dict[str, Any]]:
    cases = json.loads((FIXTURES / "invalid" / "schema_cases.json").read_text(encoding="utf-8"))
    cases.pop("_doc", None)
    return dict(cases)


def apply_case(case: dict[str, Any]) -> dict[str, Any]:
    record = golden_by_id()[case["base"]]
    for key in case.get("drop", []):
        record.pop(key, None)
    record.update(copy.deepcopy(case.get("patch", {})))
    return record
