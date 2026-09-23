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
    monkeypatch.setattr(service, "_evaluation_context", lambda _query, _limit: stale)

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
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == 2
    upgraded = service.capture_evaluation_snapshot()
    assert upgraded["extended_metrics_available"] is True
    assert len(json.loads(path.read_text(encoding="utf-8"))["snapshots"]) == 1
    service.remember("Advance the Vault for a new snapshot.", "projects")
    service.capture_evaluation_snapshot()
    persisted = json.loads(path.read_text(encoding="utf-8"))

    assert report["schema_version"] == 2
    assert report["snapshots"][0]["extended_metrics_available"] is False
    assert persisted["schema_version"] == 2
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

    assert reopened.evaluation_report()["schema_version"] == 2


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
            "context_metrics_available",
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
