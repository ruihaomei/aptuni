"""Pure response-unit accounting and deterministic packing."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from aptuni.application.context import METADATA_UNITS, ContextUnit, pack_units, unit_cost


def unit(text: str, layer: str = "L3") -> ContextUnit:
    return ContextUnit(
        layer=layer,
        kind="fact",
        canonical_id="fct_test",
        module="knowledge",
        text=text,
        source_id=None,
        trust="user_declared",
        tainted=False,
        signals=(),
    )


def test_unit_cost_is_canonical_utf8_payload_plus_fixed_overhead() -> None:
    item = unit("生存分析")
    payload = json.dumps(item.payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert unit_cost(item) == len(payload.encode("utf-8")) + 32


def test_pack_never_splits_records_or_exceeds_budget() -> None:
    first, second = unit("short"), unit("a much longer second record")
    budget = METADATA_UNITS + unit_cost(first)
    packed = pack_units((first, second), budget)
    assert packed.items == (first,)
    assert packed.used_units == budget
    assert packed.remaining_units == 0
    assert packed.truncated
    assert packed.layers == ("L3",)


def test_pack_may_use_a_later_smaller_unit_after_omitting_a_large_one() -> None:
    large, small = unit("x" * 200, "L1"), unit("ok", "L2")
    budget = METADATA_UNITS + unit_cost(small)
    packed = pack_units((large, small), budget)
    assert packed.items == (small,)
    assert packed.truncated
    assert packed.layers == ("L2",)


def test_frozen_context_noise_worked_example_reproduces_exactly() -> None:
    fixture = Path(__file__).resolve().parents[2] / "fixtures" / "eval" / "context-noise-example-v1.json"
    expected_digest = fixture.with_suffix(".sha256").read_text(encoding="utf-8").split()[0]
    data = fixture.read_bytes()
    assert hashlib.sha256(data).hexdigest() == expected_digest
    value = json.loads(data)
    overhead = value["fixed_overhead_per_unit"]
    total = sum(item["payload_bytes"] + overhead for item in value["units"])
    irrelevant = sum(item["payload_bytes"] + overhead for item in value["units"] if not item["relevant"])
    assert total == value["worked_result"]["total_units"]
    assert irrelevant == value["worked_result"]["irrelevant_units"]
    assert irrelevant / total == value["worked_result"]["noise_ratio"]
