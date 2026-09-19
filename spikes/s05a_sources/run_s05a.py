#!/usr/bin/env python3
"""Run the S05A acceptance suite and write a machine-readable result.

Each SPIKES.md acceptance criterion maps to named tests. The run fails
(non-zero) if the interpreter differs from the pinned baseline, any test fails,
or any mapped test is missing. No network, no external dependency.
"""

from __future__ import annotations

import json
import logging
import platform
import sys
import unittest
from pathlib import Path

logger = logging.getLogger("s05a")
BASELINE_PYTHON = "3.13.3"
HERE = Path(__file__).resolve().parent
RESULT_PATH = HERE / "results" / "S05A-result.json"

CRITERIA: dict[str, list[str]] = {
    "identical_replay_is_idempotent": [
        "test_contract.DeltaTests.test_delta_id_is_deterministic_for_identical_content",
        "test_folder.FolderIdentityTests.test_identical_replay_produces_identical_delta",
        "test_opml.ReconcileTests.test_identical_replay_is_idempotent",
        "test_github.GitHubIdentityTests.test_identical_replay_is_idempotent",
        "test_ledger.LedgerTests.test_replaying_an_applied_delta_is_a_noop",
        "test_ledger.LedgerTests.test_full_sequence_replay_reproduces_the_same_state",
        "test_hardening.LedgerOrderingTests.test_content_flip_flop_is_applied_not_swallowed",
        "test_hardening.LedgerOrderingTests.test_mutated_delta_fails_integrity_check",
        "test_round2.DeliveryIdentityTests.test_sequence_makes_repeated_content_transitions_distinct_deliveries",
        "test_round2.DeliveryIdentityTests.test_late_redelivery_after_content_cycle_is_a_duplicate_not_reapplied",
        "test_round2.DeliveryIdentityTests.test_sequence_gap_is_rejected",
    ],
    "source_identity_fits_versioned_extensions": [
        "test_contract.ExtensionRegistryTests.test_three_provider_families_validate_through_one_common_contract",
        "test_contract.ExtensionRegistryTests.test_unknown_version_round_trips_but_forces_review",
        "test_folder.FolderIdentityTests.test_every_locator_passes_the_registry",
        "test_opml.ReconcileTests.test_every_locator_passes_the_registry",
        "test_github.GitHubSelectionTests.test_every_locator_passes_the_registry",
        "test_hardening.LedgerOrderingTests.test_intake_gates_unknown_versions_to_review_and_rejects_invalid",
        "test_hardening.RecordInvariantTests.test_candidates_only_on_ambiguous",
        "test_hardening.RecordInvariantTests.test_one_operation_per_subject_per_delta",
        "test_round2.GateTests.test_understood_locator_is_validated_even_when_the_other_is_unknown",
    ],
    "unknown_or_ambiguous_identity_is_reviewable": [
        "test_contract.OperationInvariantTests.test_ambiguous_has_no_subject_and_needs_review",
        "test_folder.FolderIdentityTests.test_duplicate_hash_rename_is_ambiguous_and_reviewable",
        "test_folder.FolderIdentityTests.test_rename_plus_edit_is_not_silently_linked",
        "test_opml.ReconcileTests.test_leaf_edit_is_reviewable_not_silently_linked",
        "test_opml.ReconcileTests.test_indistinguishable_duplicate_moves_are_ambiguous",
        "test_github.GitHubIdentityTests.test_different_repository_under_same_source_is_refused",
        "test_ledger.LedgerTests.test_ambiguous_operations_enter_the_review_queue",
        "test_hardening.PartialCoverageTests.test_partial_folder_scan_never_moves_an_unobserved_identity",
        "test_hardening.PartialCoverageTests.test_truncated_github_tree_never_moves_an_unlisted_identity",
        "test_hardening.PartialCoverageTests.test_opml_branch_copy_is_not_a_silent_move",
        "test_hardening.OpmlWeakSignatureTests.test_single_generic_child_does_not_link_unrelated_parents",
        "test_round2.HeldItemEditTests.test_held_item_edited_while_unobserved_is_a_reviewable_modify_of_its_identity",
    ],
    "disappearance_never_deletes_facts": [
        "test_contract.OperationInvariantTests.test_remove_is_only_a_tombstone_proposal",
        "test_folder.FolderIdentityTests.test_partial_scan_never_proposes_removal",
        "test_opml.ReconcileTests.test_branch_export_is_partial_and_never_removes",
        "test_github.GitHubIdentityTests.test_truncated_tree_is_partial_and_never_removes",
        "test_github.GitHubSelectionTests.test_selection_is_sticky_and_unselected_files_are_not_removed",
        "test_ledger.LedgerTests.test_source_loss_withdraws_evidence_but_never_deletes_facts",
        "test_hardening.PartialCoverageTests.test_held_ambiguity_candidates_survive_complete_rescans",
        "test_hardening.PartialCoverageTests.test_opml_review_reserved_node_is_held_not_tombstoned",
        "test_hardening.GitHubStickyRenameTests.test_sticky_item_renamed_outside_budget_is_a_move_not_a_tombstone",
    ],
    "authority_conflicts_and_locators_round_trip": [
        "test_contract.DeltaTests.test_json_round_trip_is_lossless",
        "test_contract.DeltaTests.test_tampered_delta_id_is_rejected",
        "test_authority.RoundTripTests.test_config_round_trips",
        "test_authority.RoundTripTests.test_conflict_resolution_round_trips",
        "test_authority.ResolveTests.test_confidence_never_overrides_missing_authority",
        "test_authority.ResolveTests.test_policy_change_before_commit_forces_review",
    ],
    "truncation_is_explicit": [
        "test_github.GitHubIdentityTests.test_truncated_tree_is_partial_and_never_removes",
        "test_github.GitHubSelectionTests.test_selection_is_bounded_deterministic_and_prioritized",
        "test_round2.GitHubPriorityTests.test_common_vanished_blob_does_not_flood_the_budget",
    ],
}


class _Recorder(unittest.TextTestResult):
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.passed: list[str] = []

    def addSuccess(self, test: unittest.TestCase) -> None:  # noqa: N802 (unittest API)
        super().addSuccess(test)
        self.passed.append(test.id())


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if platform.python_version() != BASELINE_PYTHON:
        logger.error("BLOCKED_RUNTIME_MISMATCH expected=%s", BASELINE_PYTHON)
        return 2
    suite = unittest.defaultTestLoader.discover(str(HERE / "tests"), top_level_dir=str(HERE / "tests"))
    runner = unittest.TextTestRunner(verbosity=1, resultclass=_Recorder)
    result = runner.run(suite)
    passed = set(result.passed)  # type: ignore[attr-defined]
    criteria = {
        name: {"tests": len(tests), "all_passed": all(test in passed for test in tests)}
        for name, tests in CRITERIA.items()
    }
    ok = result.wasSuccessful() and all(item["all_passed"] for item in criteria.values())
    payload = {
        "spike": "S05A",
        "status": "PASS" if ok else "FAIL",
        "baseline": {"python": platform.python_version(), "dependencies": "stdlib only", "network": "none"},
        "tests_run": result.testsRun,
        "criteria": criteria,
    }
    RESULT_PATH.parent.mkdir(exist_ok=True)
    RESULT_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    logger.info(json.dumps({"status": payload["status"], "tests_run": result.testsRun}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    raise SystemExit(main())
