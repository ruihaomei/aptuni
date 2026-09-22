"""ADR-0018 §7: per-record-type schema versions, and the v2 ReviewEvent values."""

from __future__ import annotations

import unittest
from typing import Any

from aptuni.domain.ids import new_id
from aptuni.domain.records import SchemaVersionError, parse_record
from aptuni.domain.temporal import utc_now


def _event(**overrides: Any) -> dict[str, Any]:
    raw: dict[str, Any] = {
        "record_type": "review_event",
        "id": new_id("rev"),
        "schema_version": 1,
        "recorded_at": utc_now().isoformat(),
        "target_id": new_id("cnd"),
        "decision": "accept",
        "actor": "user_cli",
        "action_digest": "sha256:" + "0" * 64,
        "policy_epoch": 0,
        "rationale_code": "owner_accept",
        "nonce_id": "n1",
    }
    raw.update(overrides)
    return raw


def _policy(**overrides: Any) -> dict[str, Any]:
    raw: dict[str, Any] = {
        "record_type": "review_policy",
        "id": new_id("rvp"),
        "schema_version": 1,
        "recorded_at": utc_now().isoformat(),
        "epoch": 0,
        "auto_promotion_enabled": True,
        "sensitive_modules": ["identity", "relationships", "behavior"],
        "pending_threshold": 10,
        "interval_days": 15,
        "snooze_days": 15,
    }
    raw.update(overrides)
    return raw


class ReviewEventVersionTests(unittest.TestCase):
    def test_version_one_and_two_are_both_accepted(self) -> None:
        self.assertEqual(1, parse_record(_event()).schema_version)
        self.assertEqual(2, parse_record(_event(schema_version=2)).schema_version)

    def test_version_three_is_rejected_with_the_migration_message(self) -> None:
        with self.assertRaises(SchemaVersionError) as caught:
            parse_record(_event(schema_version=3))
        self.assertIn("migration", str(caught.exception))

    def test_other_record_types_stay_at_version_one(self) -> None:
        with self.assertRaises(SchemaVersionError):
            parse_record(_policy(schema_version=2))

    def test_policy_auto_and_pin_are_rejected_at_version_one(self) -> None:
        for overrides in (
            {"actor": "policy_auto", "decision": "promote", "rationale_code": "policy_promote"},
            {"decision": "pin", "rationale_code": "owner_pin"},
        ):
            with self.assertRaises(ValueError, msg=str(overrides)):
                parse_record(_event(**overrides))

    def test_policy_auto_and_pin_are_accepted_at_version_two(self) -> None:
        promoted = parse_record(_event(schema_version=2, actor="policy_auto", decision="promote",
                                       rationale_code="policy_promote"))
        pinned = parse_record(_event(schema_version=2, decision="pin", rationale_code="owner_pin",
                                     target_id=new_id("mem")))

        self.assertEqual("policy_auto", promoted.actor)
        self.assertEqual("pin", pinned.decision)

    def test_an_unknown_actor_is_rejected_at_every_version(self) -> None:
        for version in (1, 2):
            with self.assertRaises(ValueError, msg=str(version)):
                parse_record(_event(schema_version=version, actor="model"))


class ReviewPolicyRecordTests(unittest.TestCase):
    def test_a_valid_policy_round_trips(self) -> None:
        record = parse_record(_policy())

        self.assertTrue(record.auto_promotion_enabled)
        self.assertEqual(10, record.pending_threshold)
        self.assertEqual(("behavior", "identity", "relationships"), tuple(sorted(record.sensitive_modules)))

    def test_out_of_range_or_unknown_values_fail_closed(self) -> None:
        for overrides in (
            {"pending_threshold": 0},
            {"pending_threshold": 10_001},
            {"interval_days": 0},
            {"snooze_days": -1},
            {"sensitive_modules": ["not_a_module"]},
        ):
            with self.assertRaises(ValueError, msg=str(overrides)):
                parse_record(_policy(**overrides))

    def test_an_empty_sensitive_set_is_allowed_and_means_nothing_is_sensitive(self) -> None:
        self.assertEqual((), tuple(parse_record(_policy(sensitive_modules=[])).sensitive_modules))


if __name__ == "__main__":
    unittest.main()
