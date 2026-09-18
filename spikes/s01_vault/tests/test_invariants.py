"""Cross-record invariants: supersession, temporal queries, lifecycle, evidence support."""

from __future__ import annotations

import unittest
from datetime import datetime

from s01.invariants import InvariantError, RecordSet
from s01.records import parse_record
from tests.helpers import golden_by_id, golden_raw

FCT1 = "fct_00000000000000000000000001"
FCT2 = "fct_00000000000000000000000002"
FCT3 = "fct_00000000000000000000000003"
FCT4 = "fct_00000000000000000000000004"
MEM1 = "mem_00000000000000000000000001"
CND1 = "cnd_00000000000000000000000001"


def build(raws: list[dict]) -> RecordSet:
    return RecordSet([parse_record(raw) for raw in raws])


def at(text: str) -> datetime:
    return datetime.fromisoformat(text)


class GoldenInvariantTests(unittest.TestCase):
    def test_golden_set_satisfies_all_invariants(self) -> None:
        build(golden_raw()).validate()

    def test_current_view_hides_superseded_and_follows_forward_links(self) -> None:
        records = build(golden_raw())
        current = {record.id for record in records.current_facts()}
        self.assertIn(FCT3, current)
        self.assertIn(FCT4, current)
        self.assertNotIn(FCT1, current)
        self.assertNotIn(FCT2, current)
        self.assertEqual(FCT3, records.superseded_by(FCT2))

    def test_as_known_at_returns_prior_belief_before_correction(self) -> None:
        records = build(golden_raw())
        before = {r.id for r in records.current_facts(as_known_at=at("2026-09-18T12:00:00+08:00"))}
        self.assertIn(FCT1, before)
        self.assertNotIn(FCT4, before)

    def test_valid_at_distinguishes_world_change_intervals(self) -> None:
        records = build(golden_raw())
        in_2024 = {r.id for r in records.facts_valid_at("2024-06")}
        in_2026 = {r.id for r in records.facts_valid_at("2026-06")}
        self.assertIn(FCT2, in_2024)
        self.assertNotIn(FCT3, in_2024)
        self.assertIn(FCT3, in_2026)
        self.assertNotIn(FCT2, in_2026)

    def test_revoked_memory_is_not_exposable_but_history_remains(self) -> None:
        records = build(golden_raw())
        self.assertNotIn(MEM1, {r.id for r in records.exposable()})
        self.assertIn(MEM1, records.ids())
        before_revoke = records.exposable(as_known_at=at("2026-09-18T13:30:00+08:00"))
        self.assertIn(MEM1, {r.id for r in before_revoke})

    def test_quarantined_records_are_never_exposable(self) -> None:
        exposable = {r.record_type for r in build(golden_raw()).exposable()}
        self.assertNotIn("observation", exposable)
        self.assertNotIn("candidate_memory", exposable)

    def test_module_policy_hides_disabled_module(self) -> None:
        raws = golden_raw()
        policy = raws[0]
        policy["modules"]["experience"]["expose_enabled"] = False
        exposed = {r.id for r in build(raws).exposable()}
        self.assertNotIn(FCT3, exposed)
        self.assertIn(FCT4, exposed)


class InvalidSetTests(unittest.TestCase):
    def assert_invalid(self, raws: list[dict], fragment: str) -> None:
        with self.assertRaises(InvariantError) as ctx:
            build(raws).validate()
        self.assertIn(fragment, str(ctx.exception))

    def test_dangling_supersedes(self) -> None:
        raws = golden_by_id()
        raws[FCT3]["supersedes"] = ["fct_00000000000000000000000099"]
        self.assert_invalid(list(raws.values()), "missing")

    def test_two_records_superseding_same_target(self) -> None:
        raws = golden_by_id()
        extra = dict(raws[FCT4], id="fct_00000000000000000000000005",
                     recorded_at="2026-09-18T13:30:00+08:00")
        self.assert_invalid(list(raws.values()) + [extra], "superseded more than once")

    def test_backwards_supersession_in_system_time(self) -> None:
        raws = golden_by_id()
        raws[FCT3]["recorded_at"] = "2026-09-18T10:00:00+08:00"
        self.assert_invalid(list(raws.values()), "recorded before")

    def test_supersession_across_record_types(self) -> None:
        raws = golden_by_id()
        raws[FCT3]["supersedes"] = ["evd_00000000000000000000000002"]
        self.assert_invalid(list(raws.values()), "record type")

    def test_supersession_cycle(self) -> None:
        raws = golden_by_id()
        raws[FCT2]["supersedes"] = [FCT3]
        raws[FCT2]["change_kind"] = "correction"
        self.assert_invalid(list(raws.values()), "cycle")

    def test_memory_without_accept_review(self) -> None:
        raws = [r for r in golden_raw() if r["id"] != "rev_00000000000000000000000001"]
        self.assert_invalid(raws, "accept")

    def test_knowledge_signal_not_supported_by_evidence(self) -> None:
        raws = golden_by_id()
        raws[FCT1]["predicate"] = "applied"
        self.assert_invalid(list(raws.values()), "signal")

    def test_mastery_wording_is_rejected(self) -> None:
        raws = golden_by_id()
        raws[FCT4]["statement"] = "Proficient in Cox proportional hazards models."
        self.assert_invalid(list(raws.values()), "mastery")

    def test_chinese_mastery_wording_is_rejected(self) -> None:
        raws = golden_by_id()
        raws[FCT4]["statement"] = "精通 Cox 比例风险模型。"
        self.assert_invalid(list(raws.values()), "mastery")

    def test_duplicate_observation_idempotency_key(self) -> None:
        raws = golden_by_id()
        raws["obs_00000000000000000000000002"]["idempotency_key"] = "eps_session_0001:0"
        self.assert_invalid(list(raws.values()), "idempotency")

    def test_candidate_derived_from_missing_observation(self) -> None:
        raws = golden_by_id()
        raws[CND1]["derived_from"] = ["obs_00000000000000000000000077"]
        self.assert_invalid(list(raws.values()), "missing")


if __name__ == "__main__":
    unittest.main()
