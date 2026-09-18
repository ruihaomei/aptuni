"""Schema-level tests: golden records round-trip exactly; invalid cases fail loudly."""

from __future__ import annotations

import json
import unittest

from pydantic import ValidationError

from s01.records import (
    DeletionReceipt,
    PendingAction,
    SchemaVersionError,
    canonical_json,
    parse_record,
)
from tests.helpers import apply_case, golden_raw, schema_cases


class GoldenRoundTripTests(unittest.TestCase):
    def test_every_golden_record_round_trips_exactly(self) -> None:
        for raw in golden_raw():
            with self.subTest(record=raw["id"]):
                record = parse_record(raw)
                again = parse_record(json.loads(canonical_json(record)))
                self.assertEqual(record, again)
                self.assertEqual(canonical_json(record), canonical_json(again))

    def test_canonical_json_is_deterministic_and_keeps_cjk_readable(self) -> None:
        raw = next(r for r in golden_raw() if r["id"] == "obs_00000000000000000000000002")
        text = canonical_json(parse_record(raw))
        self.assertIn("用户要求回答简短", text)
        self.assertEqual(text, canonical_json(parse_record(json.loads(text))))
        self.assertNotIn("\n", text)

    def test_records_are_immutable(self) -> None:
        record = parse_record(golden_raw()[3])
        with self.assertRaises(ValidationError):
            record.statement = "changed"  # type: ignore[misc]


class InvalidSchemaTests(unittest.TestCase):
    def test_every_invalid_case_is_rejected_with_expected_reason(self) -> None:
        for name, case in schema_cases().items():
            with self.subTest(case=name):
                with self.assertRaises((ValidationError, SchemaVersionError, ValueError)) as ctx:
                    parse_record(apply_case(case))
                self.assertIn(case["expect"].lower(), str(ctx.exception).lower())

    def test_unknown_record_type_is_rejected(self) -> None:
        raw = golden_raw()[0] | {"record_type": "mystery"}
        with self.assertRaises((ValidationError, ValueError)):
            parse_record(raw)

    def test_overlong_excerpt_is_rejected(self) -> None:
        raw = next(r for r in golden_raw() if r["id"] == "evd_00000000000000000000000002")
        raw["excerpt"] = "x" * 281
        with self.assertRaises(ValidationError):
            parse_record(raw)


class ActionAndReceiptTests(unittest.TestCase):
    def test_pending_action_digest_binds_canonical_scope(self) -> None:
        action = PendingAction.create(
            action_type="accept_candidate",
            scope={"target_id": "cnd_00000000000000000000000001"},
            policy_epoch=1,
            created_at="2026-09-18T12:00:00+08:00",
            ttl_seconds=600,
        )
        same = PendingAction.create(
            action_type="accept_candidate",
            scope={"target_id": "cnd_00000000000000000000000001"},
            policy_epoch=1,
            created_at="2026-09-18T12:00:00+08:00",
            ttl_seconds=600,
        )
        widened = PendingAction.create(
            action_type="accept_candidate",
            scope={"target_id": "cnd_00000000000000000000000001", "also": "mem_x"},
            policy_epoch=1,
            created_at="2026-09-18T12:00:00+08:00",
            ttl_seconds=600,
        )
        self.assertEqual(action.digest, same.digest)
        self.assertNotEqual(action.digest, widened.digest)
        self.assertRegex(action.action_id, r"^[a-z0-9-]+$")

    def test_deletion_receipt_rejects_bare_deleted_state(self) -> None:
        with self.assertRaises(ValidationError):
            DeletionReceipt.model_validate(
                {
                    "id": "rcp_00000000000000000000000001",
                    "schema_version": 1,
                    "recorded_at": "2026-09-18T15:00:00+08:00",
                    "purge_id": "prg_1",
                    "terminal_state": "deleted",
                    "per_copy": [],
                }
            )


class SchemaVersionTests(unittest.TestCase):
    def test_unknown_version_error_names_migration(self) -> None:
        raw = golden_raw()[3] | {"schema_version": 99}
        with self.assertRaises(SchemaVersionError) as ctx:
            parse_record(raw)
        self.assertIn("migration", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
