"""Content-free, restartable longitudinal maintainer dogfooding."""

from __future__ import annotations

import json
import stat
from contextlib import contextmanager
from pathlib import Path

import pytest

from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace
from aptuni.cli.main import run


@pytest.fixture()
def service(tmp_path: Path) -> AptuniService:
    result = AptuniService(Workspace(tmp_path / "state"))
    result.init(tmp_path / "Aptuni")
    return result


def test_trial_persists_ids_and_query_digest_but_no_query_or_context_text(
    service: AptuniService,
) -> None:
    fact = service.remember("Maintains a local-first context project.", "projects")
    query = "Which local-first project do I maintain?"

    trial = service.evaluation_trial(query, limit=5)

    assert fact.id in trial.record_ids
    root = service.workspace.state_dir / "evaluation"
    durable = b"".join(path.read_bytes() for path in root.rglob("*") if path.is_file())
    assert query.encode() not in durable
    assert fact.statement.encode() not in durable
    assert b"sha256:" in durable
    assert trial.used_units > 0
    assert trial.requested_units == 4000
    assert trial.exposure_violations == 0
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    assert all(stat.S_IMODE(path.stat().st_mode) == 0o600 for path in root.rglob("*") if path.is_file())


def test_scoring_requires_exact_partition_and_reports_usefulness_noise_and_provenance(
    service: AptuniService,
) -> None:
    useful = service.remember("Uses Python for Aptuni.", "projects")
    noise = service.remember("Uses tea while reading.", "preferences")
    trial = service.evaluation_trial("Uses", limit=10)
    assert {useful.id, noise.id} <= set(trial.record_ids)

    with pytest.raises(AptuniError, match="classify every returned record"):
        service.score_evaluation_trial(trial.id, useful_ids=(useful.id,), noise_ids=())

    remaining = tuple(record_id for record_id in trial.record_ids if record_id != useful.id)
    scored = service.score_evaluation_trial(trial.id, useful_ids=(useful.id,), noise_ids=remaining)
    report = service.evaluation_report()

    assert scored.scored is True
    assert report["retrieval"]["scored_trials"] == 1
    assert report["retrieval"]["useful_context_rate"] == pytest.approx(1 / len(trial.record_ids))
    assert report["retrieval"]["noise_rate"] == pytest.approx(len(remaining) / len(trial.record_ids))
    assert report["retrieval"]["traceable_useful_rate"] == 1.0
    assert report["retrieval"]["unsupported_useful_records"] == 0
    assert report["retrieval"]["trials_with_useful_context_rate"] == 1.0
    assert report["retrieval"]["used_context_units"] == trial.used_units
    assert report["retrieval"]["units_per_useful_record"] == trial.used_units
    assert report["permissions"]["exposure_violations"] == 0


def test_capture_tracks_promotion_review_correction_and_is_idempotent_per_sequence(
    service: AptuniService,
) -> None:
    promoted = service.observe("Prefers reproducible experiment pipelines.", "knowledge")
    service.review_memory(promoted.memory_id, "pin")
    fact = service.profile_review_pending()[0]
    service.review_profile_fact(fact.id, "accept")
    service.edit_memory(promoted.memory_id, "Prefers fully reproducible experiment pipelines.")

    first = service.capture_evaluation_snapshot()
    second = service.capture_evaluation_snapshot()

    assert second == first
    assert first["profile_promoted"] == 1
    assert first["profile_pending_review"] == 0
    assert first["profile_accepted"] == 1
    assert first["memory_corrections"] == 1
    assert first["memory_pinned"] == 1
    assert first["superseded_records"] >= 1
    assert first["review_backlog"] == 0
    assert first["review_decisions"] >= 2
    assert len(service.evaluation_report()["snapshots"]) == 1


def test_capture_tracks_source_updates_without_retaining_source_content(
    service: AptuniService, tmp_path: Path,
) -> None:
    source_root = tmp_path / "source"
    source_root.mkdir()
    note = source_root / "note.md"
    note.write_text("first private source value\n", encoding="utf-8")
    source = service.add_folder_source(source_root, modules=("knowledge",), role="notes")
    service.sync(source.id)
    note.write_text("second private source value\n", encoding="utf-8")
    service.sync(source.id)

    snapshot = service.capture_evaluation_snapshot()

    assert snapshot["source_updates"] == 1
    assert snapshot["source_retractions"] == 0
    durable = (service.workspace.state_dir / "evaluation" / "longitudinal.json").read_text()
    assert "private source value" not in durable


def _evidence_setup(service: AptuniService, tmp_path: Path) -> tuple[str, str]:
    """A source note that answers the query, plus an L3 record sharing only one query term."""
    source_root = tmp_path / "evidence-source"
    source_root.mkdir()
    (source_root / "fixture.md").write_text(
        "Integration fixture purpose: verify exact-scope read-only source synchronization.\n",
        encoding="utf-8",
    )
    source = service.add_folder_source(source_root, modules=("knowledge",), role="notes")
    service.sync(source.id)
    evidence = next(record for record in service.snapshot()[1].records() if record.record_type == "evidence")
    unrelated = service.remember("Activation fixture goal: validate the owner interface.", "goals")
    return evidence.id, unrelated.id


def test_evidence_trial_measures_l4_through_the_ordinary_context_path(
    service: AptuniService, tmp_path: Path,
) -> None:
    evidence_id, unrelated_id = _evidence_setup(service, tmp_path)
    query = "What is the purpose of the source integration fixture?"

    default = service.evaluation_trial(query, limit=5)
    expanded = service.evaluation_trial(query, limit=5, include_evidence=True)

    # Default automatic Context is L3-only by contract (ADR-0005); the trial must say so.
    assert evidence_id not in default.record_ids
    assert default.include_evidence is False
    assert expanded.include_evidence is True
    assert expanded.record_ids[0] == evidence_id  # the better match leads; the weak one may follow
    assert expanded.record_ids.index(evidence_id) < expanded.record_ids.index(unrelated_id)
    assert expanded.record_ids == tuple(
        unit.canonical_id for unit in service.context(query, budget=4000, limit=5, include_evidence=True).units
        if unit.canonical_id is not None
    )
    durable = (service.workspace.state_dir / "evaluation" / "longitudinal.json").read_text()
    assert query not in durable
    assert "exact-scope read-only" not in durable
    rows = json.loads(durable)["trials"]
    assert [row["include_evidence"] for row in rows] == [False, True]


def test_report_separates_profile_memory_and_evidence_trials(
    service: AptuniService, tmp_path: Path,
) -> None:
    evidence_id, _ = _evidence_setup(service, tmp_path)
    query = "What is the purpose of the source integration fixture?"
    default = service.evaluation_trial(query, limit=5)
    service.score_evaluation_trial(default.id, useful_ids=(), noise_ids=default.record_ids)
    expanded = service.evaluation_trial(query, limit=5, include_evidence=True)
    service.score_evaluation_trial(expanded.id, useful_ids=(evidence_id,), noise_ids=tuple(
        record_id for record_id in expanded.record_ids if record_id != evidence_id
    ))

    report = service.evaluation_report()
    modes = report["retrieval"]["by_context_mode"]

    assert report["schema_version"] == 3
    assert modes["profile_memory"]["scored_trials"] == 1
    assert modes["profile_memory"]["useful_records"] == 0
    assert modes["profile_memory"]["noise_rate"] == 1.0
    assert modes["with_evidence"]["scored_trials"] == 1
    assert modes["with_evidence"]["useful_records"] == 1
    assert modes["with_evidence"]["useful_context_rate"] == pytest.approx(1 / len(expanded.record_ids))
    assert report["retrieval"]["scored_trials"] == 2


def test_evidence_trial_keeps_the_ordinary_exposure_policy(
    service: AptuniService, tmp_path: Path,
) -> None:
    evidence_id, _ = _evidence_setup(service, tmp_path)
    service.set_module("knowledge", expose=False)

    trial = service.evaluation_trial("source integration fixture purpose", limit=5, include_evidence=True)

    assert evidence_id not in trial.record_ids
    assert trial.exposure_violations == 0


def test_non_boolean_evidence_mode_fails_closed(service: AptuniService) -> None:
    service.remember("Maintains Aptuni.", "projects")
    with pytest.raises(AptuniError) as error:
        service.evaluation_trial("Maintains Aptuni", limit=5, include_evidence="yes")  # type: ignore[arg-type]
    assert error.value.code == "invalid_evaluation_trial"

    service.evaluation_trial("Maintains Aptuni", limit=5)
    path = service.workspace.state_dir / "evaluation" / "longitudinal.json"
    state = json.loads(path.read_text(encoding="utf-8"))
    state["trials"][0]["include_evidence"] = "true"
    path.write_text(json.dumps(state), encoding="utf-8")
    path.chmod(0o600)
    with pytest.raises(AptuniError) as error:
        service.evaluation_report()
    assert error.value.code == "evaluation_state_invalid"


def test_v2_trials_migrate_as_profile_memory_trials(service: AptuniService) -> None:
    useful = service.remember("Maintains Aptuni.", "projects")
    trial = service.evaluation_trial("Maintains Aptuni", limit=5)
    service.score_evaluation_trial(trial.id, useful_ids=trial.record_ids, noise_ids=())
    path = service.workspace.state_dir / "evaluation" / "longitudinal.json"
    state = json.loads(path.read_text(encoding="utf-8"))
    state["schema_version"] = 2
    for row in state["trials"]:
        row.pop("include_evidence")
    path.write_text(json.dumps(state), encoding="utf-8")
    path.chmod(0o600)

    report = service.evaluation_report()
    persisted = json.loads(path.read_text(encoding="utf-8"))

    assert persisted["schema_version"] == 3
    assert persisted["trials"][0]["include_evidence"] is False
    assert report["retrieval"]["by_context_mode"]["profile_memory"]["useful_records"] == 1
    assert useful.id in persisted["trials"][0]["useful_ids"]


@pytest.mark.parametrize("case", ["v2_with_mode", "v3_without_mode", "boolean_version"])
def test_schema_version_and_mode_fields_must_match_exactly(service: AptuniService, case: str) -> None:
    service.remember("Maintains Aptuni.", "projects")
    service.evaluation_trial("Maintains Aptuni", limit=5)
    path = service.workspace.state_dir / "evaluation" / "longitudinal.json"
    state = json.loads(path.read_text(encoding="utf-8"))
    if case == "v2_with_mode":
        state["schema_version"] = 2
    elif case == "v3_without_mode":
        state["trials"][0].pop("include_evidence")
    else:
        state["schema_version"] = True
    path.write_text(json.dumps(state), encoding="utf-8")
    path.chmod(0o600)

    with pytest.raises(AptuniError) as error:
        service.evaluation_report()

    assert error.value.code == "evaluation_state_invalid"


def test_cli_evidence_trial_reports_its_context_mode(
    service: AptuniService, tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    evidence_id, _ = _evidence_setup(service, tmp_path)

    assert run(["evaluate", "trial", "source integration fixture purpose", "--evidence", "--json"], service) == 0
    trial = json.loads(capsys.readouterr().out)

    assert trial["include_evidence"] is True
    assert trial["items"][0]["id"] == evidence_id
    assert trial["items"][0]["kind"] == "evidence"


def test_privacy_inventory_and_purge_cover_longitudinal_evaluation(service: AptuniService) -> None:
    fact = service.remember("Private evaluation marker.", "projects")
    service.evaluation_trial("private marker query", limit=5)
    evaluation_root = service.workspace.state_dir / "evaluation"
    assert evaluation_root.exists()
    copies = {copy.id: copy for copy in service.privacy_inventory().copies}
    assert copies["longitudinal_evaluation"].present is True

    preview = service.privacy_purge_preview((fact.id,))
    assert "longitudinal_evaluation" in preview.managed_copy_ids
    service.confirm_privacy_purge(preview.action_id, preview.digest)

    assert not evaluation_root.exists()


def test_evaluation_reset_removes_only_managed_evaluation_state(service: AptuniService) -> None:
    service.evaluation_trial("empty but valid trial", limit=5)
    root = service.workspace.state_dir / "evaluation"
    sibling = service.workspace.state_dir / "keep.txt"
    sibling.write_text("keep", encoding="utf-8")

    assert service.reset_evaluation() is True
    assert not root.exists()
    assert sibling.read_text(encoding="utf-8") == "keep"
    assert service.reset_evaluation() is False


def test_contaminated_reset_fails_before_deleting_any_managed_state(
    service: AptuniService, tmp_path: Path,
) -> None:
    service.evaluation_trial("empty but valid trial", limit=5)
    root = service.workspace.state_dir / "evaluation"
    state = root / "longitudinal.json"
    outside = tmp_path / "outside.txt"
    outside.write_text("keep", encoding="utf-8")
    (root / "zzz-unknown").symlink_to(outside)

    with pytest.raises(AptuniError) as error:
        service.reset_evaluation()

    assert error.value.code == "evaluation_state_unsafe"
    assert state.exists()
    assert outside.read_text(encoding="utf-8") == "keep"


def test_malformed_evaluation_state_fails_closed(service: AptuniService) -> None:
    root = service.workspace.state_dir / "evaluation"
    root.mkdir(parents=True)
    (root / "longitudinal.json").write_text(
        '{"schema_version":1,"trials":[{}],"snapshots":[]}\n', encoding="utf-8",
    )

    with pytest.raises(AptuniError) as error:
        service.evaluation_report()

    assert error.value.code == "evaluation_state_invalid"


def test_evaluation_state_rejects_extra_raw_content_and_bad_field_types(service: AptuniService) -> None:
    root = service.workspace.state_dir / "evaluation"
    root.mkdir(parents=True, mode=0o700)
    root.chmod(0o700)
    path = root / "longitudinal.json"
    path.write_text(
        '{"query_text":"RAW SECRET QUERY","schema_version":1,"trials":[],"snapshots":[]}\n',
        encoding="utf-8",
    )
    path.chmod(0o600)
    with pytest.raises(AptuniError) as extra:
        service.evaluation_report()
    assert extra.value.code == "evaluation_state_invalid"

    path.write_text(
        '{"schema_version":1,"trials":[{"id":42}],"snapshots":[]}\n', encoding="utf-8",
    )
    path.chmod(0o600)
    with pytest.raises(AptuniError) as typed:
        service.evaluation_report()
    assert typed.value.code == "evaluation_state_invalid"


def test_preplanted_predictable_temp_symlink_cannot_overwrite_outside_file(
    service: AptuniService, tmp_path: Path,
) -> None:
    service.remember("Maintains Aptuni.", "projects")
    root = service.workspace.state_dir / "evaluation"
    root.mkdir(parents=True, mode=0o700)
    root.chmod(0o700)
    outside = tmp_path / "outside.txt"
    outside.write_text("DO NOT REPLACE", encoding="utf-8")
    (root / "longitudinal.tmp").symlink_to(outside)

    with pytest.raises(AptuniError) as error:
        service.evaluation_trial("Maintains Aptuni", limit=5)

    assert error.value.code == "evaluation_state_unsafe"
    assert outside.read_text(encoding="utf-8") == "DO NOT REPLACE"
    assert (root / "longitudinal.tmp").is_symlink()


def test_trial_discards_a_stale_context_before_writing_state(
    service: AptuniService, monkeypatch: pytest.MonkeyPatch,
) -> None:
    service.remember("Maintains Aptuni.", "projects")
    stale = service._evaluation_context("Maintains Aptuni", 5)
    service.remember("A concurrent canonical change.", "projects")
    monkeypatch.setattr(service, "_evaluation_context", lambda _query, _limit, **_mode: stale)

    with pytest.raises(AptuniError) as error:
        service.evaluation_trial("Maintains Aptuni", limit=5)

    assert error.value.code == "concurrent_write"
    assert not (service.workspace.state_dir / "evaluation").exists()


def test_trial_uses_ordinary_exposure_policy_without_a_privileged_lane(
    service: AptuniService,
) -> None:
    hidden = service.remember("Private project detail.", "projects")
    service.set_module("projects", expose=False)

    trial = service.evaluation_trial("Private project detail", limit=5)

    assert hidden.id not in trial.record_ids
    assert trial.exposure_violations == 0
    assert service.evaluation_report()["permissions"]["exposure_violations"] == 0


def test_malformed_context_metrics_fail_closed(service: AptuniService) -> None:
    service.remember("Maintains Aptuni.", "projects")
    service.evaluation_trial("Maintains Aptuni", limit=5)
    path = service.workspace.state_dir / "evaluation" / "longitudinal.json"
    state = json.loads(path.read_text(encoding="utf-8"))
    state["trials"][0]["used_units"] = True
    path.write_text(json.dumps(state), encoding="utf-8")
    path.chmod(0o600)

    with pytest.raises(AptuniError) as error:
        service.evaluation_report()

    assert error.value.code == "evaluation_state_invalid"


def test_initial_evaluation_schema_migrates_without_losing_prior_snapshots(
    service: AptuniService,
) -> None:
    old_snapshot = service.capture_evaluation_snapshot()
    for key in (
        "source_updates", "source_retractions", "superseded_records", "review_backlog",
        "review_decisions", "extended_metrics_available",
    ):
        old_snapshot.pop(key)
    path = service.workspace.state_dir / "evaluation" / "longitudinal.json"
    path.write_text(json.dumps({"schema_version": 1, "trials": [], "snapshots": [old_snapshot]}),
                    encoding="utf-8")
    path.chmod(0o600)

    report = service.evaluation_report()
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == 3
    upgraded = service.capture_evaluation_snapshot()
    assert upgraded["extended_metrics_available"] is True
    assert len(json.loads(path.read_text(encoding="utf-8"))["snapshots"]) == 1
    service.remember("Advance the Vault for a new snapshot.", "projects")
    service.capture_evaluation_snapshot()
    persisted = json.loads(path.read_text(encoding="utf-8"))

    assert report["schema_version"] == 3
    assert report["snapshots"][0]["extended_metrics_available"] is False
    assert persisted["schema_version"] == 3
    assert len(persisted["snapshots"]) == 2


def test_fresh_report_process_opens_vault_before_source_operation_lock(
    service: AptuniService, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aptuni.application import evaluation

    service.capture_evaluation_snapshot()
    reopened = AptuniService(service.workspace)
    original = evaluation.source_operations_lock

    @contextmanager
    def assert_open_first(state_dir: Path):
        assert reopened._vault is not None
        with original(state_dir):
            yield

    monkeypatch.setattr(evaluation, "source_operations_lock", assert_open_first)

    assert reopened.evaluation_report()["schema_version"] == 3


def test_mixed_migrated_trials_do_not_inflate_context_efficiency(service: AptuniService) -> None:
    useful = service.remember("Maintains Aptuni.", "projects")
    old = service.evaluation_trial("Maintains Aptuni", limit=5)
    service.score_evaluation_trial(old.id, useful_ids=(useful.id,), noise_ids=tuple(
        record_id for record_id in old.record_ids if record_id != useful.id
    ))
    path = service.workspace.state_dir / "evaluation" / "longitudinal.json"
    state = json.loads(path.read_text(encoding="utf-8"))
    state["schema_version"] = 1
    for trial in state["trials"]:
        for key in (
            "requested_units", "used_units", "truncated", "exposure_violations",
            "context_metrics_available", "include_evidence",
        ):
            trial.pop(key)
    path.write_text(json.dumps(state), encoding="utf-8")
    path.chmod(0o600)

    current = service.evaluation_trial("Maintains", limit=5)
    service.score_evaluation_trial(current.id, useful_ids=(), noise_ids=current.record_ids)
    retrieval = service.evaluation_report()["retrieval"]

    assert retrieval["useful_records"] == 1
    assert retrieval["measured_context_trials"] == 1
    assert retrieval["units_per_useful_record"] == 0.0
    assert retrieval["useful_records_per_1000_units"] == 0.0


def test_human_trial_output_escapes_terminal_controls(
    service: AptuniService, capsys: pytest.CaptureFixture[str],
) -> None:
    service.remember("SAFE\x1b[31mFORGED\nSECOND", "projects")

    assert run(["evaluate", "trial", "SAFE"], service) == 0
    output = capsys.readouterr().out

    assert "\x1b" not in output
    assert "\\u001b" in output
    assert "\\nSECOND" in output


def test_cli_setup_trial_score_capture_report_journey(
    service: AptuniService, capsys: pytest.CaptureFixture[str],
) -> None:
    service.remember("Maintains Aptuni.", "projects")
    assert run(["evaluate", "setup", "--json"], service) == 0
    setup = json.loads(capsys.readouterr().out)
    assert setup["vault_initialized"] is True
    assert run(["evaluate", "trial", "Maintains Aptuni", "--json"], service) == 0
    trial = json.loads(capsys.readouterr().out)
    assert trial["used_units"] > 0
    ids = [item["id"] for item in trial["items"]]
    assert run(["evaluate", "score", trial["trial_id"], "--useful", *ids, "--json"], service) == 0
    capsys.readouterr()
    assert run(["evaluate", "capture", "--json"], service) == 0
    capsys.readouterr()
    assert run(["evaluate", "report", "--json"], service) == 0
    assert json.loads(capsys.readouterr().out)["retrieval"]["scored_trials"] == 1
    assert run(["evaluate", "reset", "--json"], service) == 0
    assert json.loads(capsys.readouterr().out) == {"removed": True}


def test_discard_removes_only_the_exact_trials(service: AptuniService) -> None:
    service.remember("Maintains Aptuni.", "projects")
    keep = service.evaluation_trial("Maintains Aptuni", limit=5)
    drop = service.evaluation_trial("Maintains", limit=5)
    service.score_evaluation_trial(drop.id, useful_ids=drop.record_ids, noise_ids=())
    snapshot = service.capture_evaluation_snapshot()

    assert service.discard_evaluation_trials((drop.id,)) == (drop.id,)

    report = service.evaluation_report()
    assert report["retrieval"]["trials"] == 1
    assert report["retrieval"]["scored_trials"] == 0
    assert report["retrieval"]["unscored_trial_ids"] == [keep.id]
    assert report["snapshots"] == [snapshot]


def test_discard_is_all_or_nothing_for_unknown_or_malformed_ids(service: AptuniService) -> None:
    service.remember("Maintains Aptuni.", "projects")
    trial = service.evaluation_trial("Maintains Aptuni", limit=5)

    for ids, code in (
        ((trial.id, "trial-0000000000000000"), "evaluation_trial_not_found"),
        (("not-a-trial",), "invalid_evaluation_trial"),
        ((), "invalid_evaluation_trial"),
        ((trial.id, trial.id), "invalid_evaluation_trial"),
    ):
        with pytest.raises(AptuniError) as error:
            service.discard_evaluation_trials(ids)
        assert error.value.code == code

    assert service.evaluation_report()["retrieval"]["trials"] == 1


def test_rest_noise_labels_every_unlisted_record_as_noise(service: AptuniService) -> None:
    useful = service.remember("Uses Python for Aptuni.", "projects")
    service.remember("Uses tea while reading.", "preferences")
    trial = service.evaluation_trial("Uses", limit=10)

    scored = service.score_evaluation_trial(trial.id, useful_ids=(useful.id,), noise_ids=(), rest_noise=True)

    assert scored.useful_ids == (useful.id,)
    assert set(scored.noise_ids) == set(trial.record_ids) - {useful.id}


def test_rest_noise_still_rejects_ids_the_trial_did_not_return(service: AptuniService) -> None:
    service.remember("Uses Python for Aptuni.", "projects")
    trial = service.evaluation_trial("Uses", limit=10)

    with pytest.raises(AptuniError) as error:
        service.score_evaluation_trial(
            trial.id, useful_ids=("fct_00000000000000000000000000",), noise_ids=(), rest_noise=True,
        )

    assert error.value.code == "evaluation_labels_incomplete"


def test_repeated_queries_report_first_and_latest_usefulness_per_mode(service: AptuniService) -> None:
    useful = service.remember("Maintains Aptuni.", "projects")
    first = service.evaluation_trial("Maintains Aptuni", limit=5)
    service.score_evaluation_trial(first.id, useful_ids=(), noise_ids=first.record_ids)
    latest = service.evaluation_trial("Maintains Aptuni", limit=5)
    service.score_evaluation_trial(latest.id, useful_ids=(useful.id,), noise_ids=(), rest_noise=True)
    once = service.evaluation_trial("Maintains", limit=5)
    service.score_evaluation_trial(once.id, useful_ids=once.record_ids, noise_ids=())

    [series] = service.evaluation_report()["retrieval"]["repeated_queries"]

    assert series["query_digest_prefix"] == first.query_digest.removeprefix("sha256:")[:12]
    assert series["mode"] == "profile_memory"
    assert series["scored_trials"] == 2
    assert series["first_useful_rate"] == 0.0
    assert series["latest_useful_rate"] == 1.0 / len(latest.record_ids)


def test_cli_discard_rest_noise_and_human_report(
    service: AptuniService, capsys: pytest.CaptureFixture[str],
) -> None:
    useful = service.remember("Maintains Aptuni.", "projects")
    assert run(["evaluate", "trial", "Maintains Aptuni", "--json"], service) == 0
    trial = json.loads(capsys.readouterr().out)
    assert run(["evaluate", "score", trial["trial_id"], "--useful", useful.id, "--rest-noise"], service) == 0
    capsys.readouterr()
    assert run(["evaluate", "trial", "Maintains", "--evidence", "--json"], service) == 0
    extra = json.loads(capsys.readouterr().out)

    assert run(["evaluate", "report"], service) == 0
    human = capsys.readouterr().out
    assert "Profile/Memory only: 1 scored" in human
    assert "With Evidence: 0 scored" in human
    assert extra["trial_id"] in human  # the unscored trial is listed for later scoring

    assert run(["evaluate", "discard", extra["trial_id"], "--json"], service) == 0
    assert json.loads(capsys.readouterr().out) == {"discarded": [extra["trial_id"]]}


def test_discard_refuses_to_erase_exposure_violation_evidence(service: AptuniService) -> None:
    service.remember("Maintains Aptuni.", "projects")
    trial = service.evaluation_trial("Maintains Aptuni", limit=5)
    path = service.workspace.state_dir / "evaluation" / "longitudinal.json"
    state = json.loads(path.read_text(encoding="utf-8"))
    state["trials"][0]["exposure_violations"] = 1
    path.write_text(json.dumps(state), encoding="utf-8")
    path.chmod(0o600)

    with pytest.raises(AptuniError) as error:
        service.discard_evaluation_trials((trial.id,))

    assert error.value.code == "evaluation_trial_protected"
    assert service.evaluation_report()["permissions"]["exposure_violations"] == 1


def test_discard_refuses_contaminated_evaluation_state(service: AptuniService) -> None:
    service.remember("Maintains Aptuni.", "projects")
    trial = service.evaluation_trial("Maintains Aptuni", limit=5)
    stray = service.workspace.state_dir / "evaluation" / "junk"
    stray.write_text("unmanaged", encoding="utf-8")

    with pytest.raises(AptuniError):
        service.discard_evaluation_trials((trial.id,))

    assert stray.exists()


def test_the_same_query_in_both_modes_forms_separate_series(service: AptuniService, tmp_path: Path) -> None:
    evidence_id, _ = _evidence_setup(service, tmp_path)
    query = "What is the purpose of the source integration fixture?"
    for include_evidence in (False, False, True, True):
        trial = service.evaluation_trial(query, limit=5, include_evidence=include_evidence)
        useful = (evidence_id,) if evidence_id in trial.record_ids else ()
        service.score_evaluation_trial(trial.id, useful_ids=useful, noise_ids=(), rest_noise=True)

    series = service.evaluation_report()["retrieval"]["repeated_queries"]

    assert sorted(item["mode"] for item in series) == ["profile_memory", "with_evidence"]
    assert len({item["query_digest_prefix"] for item in series}) == 1


def test_rest_noise_rejects_a_record_labelled_both_useful_and_noise(service: AptuniService) -> None:
    useful = service.remember("Uses Python for Aptuni.", "projects")
    trial = service.evaluation_trial("Uses", limit=10)

    with pytest.raises(AptuniError) as error:
        service.score_evaluation_trial(trial.id, useful_ids=(useful.id,), noise_ids=(useful.id,), rest_noise=True)

    assert error.value.code == "evaluation_labels_incomplete"
