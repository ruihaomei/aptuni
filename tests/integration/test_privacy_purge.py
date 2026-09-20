"""Exact-preview privacy purge, durable retry, and non-resurrection behavior."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path

import pytest

from aptuni.adapters.manager import AdapterManager
from aptuni.application import privacy
from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace
from aptuni.cli.main import run as cli_run
from aptuni.domain.temporal import utc_now
from aptuni.retrieval.sqlite import SqliteProjection

REPO = Path(__file__).resolve().parents[2]


def _service(tmp_path: Path) -> AptuniService:
    service = AptuniService(Workspace(tmp_path / "state"))
    service.init(tmp_path / "Aptuni")
    return service


def _folder_source(service: AptuniService, tmp_path: Path, marker: str = "PURGE-SOURCE-MARKER") -> str:
    root = tmp_path / "source"
    root.mkdir()
    (root / "note.md").write_text(marker, encoding="utf-8")
    source = service.add_folder_source(root, ("knowledge",), "notes")
    service.sync(source.id)
    return source.id


def test_preview_is_exact_and_confirmed_purge_cleans_managed_copies(tmp_path: Path) -> None:
    service = _service(tmp_path)
    source_id = _folder_source(service, tmp_path)
    evidence_id = service.evidence(source_id)[0].id
    service.search("purge source marker")

    manager = AdapterManager(service.workspace)
    plan = manager.plan("codex", ("knowledge",), allow_host_model_egress=True)
    grant, _ = manager.apply(plan.action_id)

    before = service.status().seq
    preview = service.privacy_purge_preview((evidence_id,))
    assert service.status().seq == before
    assert preview.requested_record_ids == (evidence_id,)
    assert evidence_id in preview.record_ids
    assert source_id in preview.record_ids, "source-derived Evidence purge must unlink the source"
    assert preview.source_ids == (source_id,)
    assert preview.irreversible
    assert preview.external_action_needed

    with pytest.raises(AptuniError) as mismatch:
        service.confirm_privacy_purge(preview.action_id, "sha256:" + "0" * 64)
    assert mismatch.value.code == "confirmation_stale"

    receipt = service.confirm_privacy_purge(preview.action_id, preview.digest)
    assert receipt.terminal_state == "complete_managed_external_action_needed"
    results = {item.copy_class: item.result for item in receipt.per_copy}
    assert results["canonical"] == "deleted"
    assert results[f"source_state:{source_id}:current"] == "deleted"
    assert results["retrieval_projection"] == "deleted"
    assert results[f"adapter_grant:{grant.grant_id}.json"] == "deleted"
    assert results["deletion_ledger"] == "retained"
    assert results["privacy_receipt"] == "retained"
    assert results[f"host_external:{grant.grant_id}"] == "external_action_needed"
    assert results[f"source_original:{source_id}"] == "external_action_needed"
    assert results["profile_exports"] == "external_action_needed"

    assert source_id not in service.records().ids()
    assert evidence_id not in service.records().ids()
    assert not (service.vault().root / "sources" / f"{source_id}.json").exists()
    assert not SqliteProjection(service.workspace.state_dir).path.exists()
    assert not (service.workspace.state_dir / "adapters" / "grants" / f"{grant.grant_id}.json").exists()
    assert service.doctor().ok

    managed_text = "".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for root in (service.vault().root, service.workspace.state_dir)
        for path in root.rglob("*") if path.is_file()
    )
    assert "PURGE-SOURCE-MARKER" not in managed_text

    with pytest.raises(AptuniError) as missing_source:
        service.sync(source_id)
    assert missing_source.value.code == "source_not_found"

    repeated = service.confirm_privacy_purge(preview.action_id, preview.digest)
    assert repeated == receipt, "an exact retry returns the durable receipt without a second approval"


def test_purge_of_correction_expands_over_chain_without_reactivation(tmp_path: Path) -> None:
    service = _service(tmp_path)
    old = service.remember("old private value", "preferences")
    corrected = service.correct(old.id, "new private value")

    preview = service.privacy_purge_preview((corrected.id,))
    assert {old.id, corrected.id} <= set(preview.record_ids)
    service.confirm_privacy_purge(preview.action_id, preview.digest)

    assert old.id not in service.records().ids()
    assert corrected.id not in service.records().ids()
    assert service.facts("preferences") == []
    assert service.doctor().ok


def test_policy_change_stales_preview_and_exact_action_id_is_required(tmp_path: Path) -> None:
    service = _service(tmp_path)
    fact = service.remember("private", "preferences")
    preview = service.privacy_purge_preview((fact.id,))
    service.set_module("preferences", expose=False)

    with pytest.raises(AptuniError) as stale:
        service.confirm_privacy_purge(preview.action_id, preview.digest)
    assert stale.value.code == "confirmation_stale"
    with pytest.raises(AptuniError) as prefix:
        service.confirm_privacy_purge(preview.action_id[:-1], preview.digest)
    assert prefix.value.code == "invalid_privacy_action_id"
    assert fact.id in service.records().ids()


def test_tampered_or_expired_preview_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service = _service(tmp_path)
    first = service.remember("first private value", "preferences")
    second = service.remember("second private value", "preferences")
    preview = service.privacy_purge_preview((first.id,))
    pending = service.workspace.state_dir / "privacy" / "pending" / f"{preview.action_id}.json"
    value = json.loads(pending.read_text(encoding="utf-8"))
    value["record_ids"] = [second.id]
    pending.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(AptuniError) as tampered:
        service.pending_privacy_purge(preview.action_id)
    assert tampered.value.code == "privacy_action_invalid"

    fresh = service.privacy_purge_preview((first.id,))
    monkeypatch.setattr(privacy, "utc_now", lambda: utc_now() + timedelta(hours=1))
    with pytest.raises(AptuniError) as expired:
        service.confirm_privacy_purge(fresh.action_id, fresh.digest)
    assert expired.value.code == "confirmation_expired"
    assert {first.id, second.id} <= service.records().ids()


def test_concurrent_exact_confirmations_create_one_durable_receipt(tmp_path: Path) -> None:
    service = _service(tmp_path)
    fact = service.remember("concurrent purge", "preferences")
    preview = service.privacy_purge_preview((fact.id,))

    def confirm() -> object:
        independent = AptuniService(service.workspace)
        return independent.confirm_privacy_purge(preview.action_id, preview.digest)

    with ThreadPoolExecutor(max_workers=2) as pool:
        receipts = list(pool.map(lambda _: confirm(), range(2)))
    assert receipts[0] == receipts[1]
    assert fact.id not in service.records().ids()
    assert len(list((service.workspace.state_dir / "privacy" / "receipts").glob("*.json"))) == 1


def test_durable_source_purge_intent_blocks_later_sync(tmp_path: Path) -> None:
    service = _service(tmp_path)
    source_id = _folder_source(service, tmp_path)
    evidence_id = service.evidence(source_id)[0].id
    preview = service.privacy_purge_preview((evidence_id,))
    seq, records = service.snapshot()
    privacy._load_or_commit_intent(
        service.workspace.state_dir, preview.action_id, preview.digest, seq, service.policy_of(records).epoch
    )
    (tmp_path / "source" / "later.md").write_text("must not race purge", encoding="utf-8")

    with pytest.raises(AptuniError) as stopped:
        service.sync(source_id)
    assert stopped.value.code == "privacy_action_in_progress"
    receipt = service.confirm_privacy_purge(preview.action_id, preview.digest)
    assert receipt.terminal_state == "complete_managed_external_action_needed"
    assert not [record for record in service.records().records()
                if getattr(getattr(record, "provenance", None), "source_id", None) == source_id]


def test_preview_deletes_only_exact_adapter_copies_and_preserves_external_details(tmp_path: Path) -> None:
    service = _service(tmp_path)
    fact = service.remember("adapter-scope marker", "preferences")
    manager = AdapterManager(service.workspace)
    first_plan = manager.plan("codex", ("preferences",), allow_host_model_egress=True)
    first, _ = manager.apply(first_plan.action_id)
    preview = service.privacy_purge_preview((fact.id,))
    assert f"adapter_grant:{first.grant_id}.json" in preview.managed_copy_ids
    assert {item["provider"] for item in preview.external_copies} == {"codex"}
    assert all(item["destination"] != "unknown" for item in preview.external_copies)

    later_plan = manager.plan("claude", ("preferences",), allow_host_model_egress=True)
    later, _ = manager.apply(later_plan.action_id)
    receipt = service.confirm_privacy_purge(preview.action_id, preview.digest)
    results = {item.copy_class: item for item in receipt.per_copy}
    assert f"host_external:{first.grant_id}" in results
    external = results[f"host_external:{first.grant_id}"]
    assert external.provider == "codex"
    assert external.destination == first.destination
    assert external.data_class is not None and "modules=preferences" in external.data_class
    assert not (service.workspace.state_dir / "adapters" / "grants" / f"{first.grant_id}.json").exists()
    assert (service.workspace.state_dir / "adapters" / "grants" / f"{later.grant_id}.json").exists()


def test_projection_created_after_preview_is_still_invalidated(tmp_path: Path) -> None:
    service = _service(tmp_path)
    fact = service.remember("projection race marker", "preferences")
    preview = service.privacy_purge_preview((fact.id,))
    assert "retrieval_projection" in preview.managed_copy_ids

    service.search("projection race marker")
    projection = SqliteProjection(service.workspace.state_dir).path
    assert projection.exists()
    receipt = service.confirm_privacy_purge(preview.action_id, preview.digest)

    assert not projection.exists()
    assert {item.copy_class: item.result for item in receipt.per_copy}["retrieval_projection"] == "deleted"


def test_human_preview_and_receipt_escape_untrusted_destinations(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    service = _service(tmp_path)
    root = tmp_path / "source\n\x1b[31m；confusable"
    root.mkdir()
    (root / "note.md").write_text("terminal-safe marker", encoding="utf-8")
    source = service.add_folder_source(root, ("knowledge",), "notes")
    service.sync(source.id)
    evidence_id = service.evidence(source.id)[0].id

    assert cli_run(["privacy", "purge", "preview", evidence_id], service) == 0
    preview_output = capsys.readouterr().out
    assert str(root) not in preview_output
    assert "\\n" in preview_output and "\\u001b" in preview_output and "\\uff1b" in preview_output
    assert "control-escaped" in preview_output and "non-ascii/confusable-escaped" in preview_output
    assert "data_class=original_source_unmodified" in preview_output

    action_id = preview_output.split("Purge action: ", 1)[1].splitlines()[0]
    preview = service.pending_privacy_purge(action_id)
    assert cli_run(["privacy", "purge", "confirm", action_id,
                    "--confirm-digest", preview.digest], service) == 0
    receipt_output = capsys.readouterr().out
    assert str(root) not in receipt_output
    assert "data_class=original_source_unmodified" in receipt_output
    assert "\\n" in receipt_output and "control-escaped" in receipt_output


def test_parent_symlinks_never_delete_outside_owned_roots(tmp_path: Path) -> None:
    service = _service(tmp_path)
    fact = service.remember("symlink marker", "preferences")
    manager = AdapterManager(service.workspace)
    plan = manager.plan("codex", ("preferences",), allow_host_model_egress=True)
    grant, _ = manager.apply(plan.action_id)
    preview = service.privacy_purge_preview((fact.id,))

    adapters = service.workspace.state_dir / "adapters"
    adapters.rename(service.workspace.state_dir / "adapters-real")
    external = tmp_path / "external-adapters"
    (external / "grants").mkdir(parents=True)
    marker = external / "grants" / f"{grant.grant_id}.json"
    marker.write_text("do-not-delete", encoding="utf-8")
    adapters.symlink_to(external, target_is_directory=True)

    receipt = service.confirm_privacy_purge(preview.action_id, preview.digest)
    assert receipt.terminal_state == "incomplete_retryable"
    assert marker.exists()
    result = {item.copy_class: item.result for item in receipt.per_copy}
    assert result[f"adapter_grant:{grant.grant_id}.json"] == "failed_retryable"


def test_source_parent_symlink_never_deletes_external_state(tmp_path: Path) -> None:
    service = _service(tmp_path)
    source_id = _folder_source(service, tmp_path)
    preview = service.privacy_purge_preview((service.evidence(source_id)[0].id,))
    sources = service.vault().root / "sources"
    sources.rename(service.vault().root / "sources-real")
    external = tmp_path / "external-sources"
    external.mkdir()
    marker = external / f"{source_id}.json"
    marker.write_text("do-not-delete", encoding="utf-8")
    sources.symlink_to(external, target_is_directory=True)

    receipt = service.confirm_privacy_purge(preview.action_id, preview.digest)
    assert receipt.terminal_state == "incomplete_retryable"
    assert marker.exists()


def test_cli_exact_retry_resumes_incomplete_intent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    fact = service.remember("CLI retry marker", "preferences")
    service.search("CLI retry marker")
    preview = service.privacy_purge_preview((fact.id,))
    original = SqliteProjection.delete
    calls = 0

    def fail_once(projection: SqliteProjection) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("injected")
        original(projection)

    monkeypatch.setattr(SqliteProjection, "delete", fail_once)
    args = ["privacy", "purge", "confirm", preview.action_id, "--confirm-digest", preview.digest, "--json"]
    assert cli_run(args, service) == 2
    assert cli_run(args, service) == 0


def test_terminal_receipt_reaps_surviving_intent(tmp_path: Path) -> None:
    service = _service(tmp_path)
    first = service.remember("first purge", "preferences")
    preview = service.privacy_purge_preview((first.id,))
    seq, records = service.snapshot()
    intent_path, _, _ = privacy._load_or_commit_intent(
        service.workspace.state_dir, preview.action_id, preview.digest, seq, service.policy_of(records).epoch
    )
    saved_intent = intent_path.read_bytes()
    service.confirm_privacy_purge(preview.action_id, preview.digest)
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_bytes(saved_intent)  # receipt-written / intent-unlink-not-durable crash state

    service.confirm_privacy_purge(preview.action_id, preview.digest)
    assert not intent_path.exists()
    second = service.remember("second purge", "preferences")
    next_preview = service.privacy_purge_preview((second.id,))
    completed = service.confirm_privacy_purge(next_preview.action_id, next_preview.digest)
    assert completed.terminal_state.startswith("complete")


def test_retry_resumes_after_managed_copy_failure_without_reapproval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    fact = service.remember("retry marker", "preferences")
    service.search("retry marker")
    preview = service.privacy_purge_preview((fact.id,))

    original = SqliteProjection.delete
    calls = 0

    def fail_once(projection: SqliteProjection) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("injected_projection_delete_failure")
        original(projection)

    monkeypatch.setattr(SqliteProjection, "delete", fail_once)
    partial = service.confirm_privacy_purge(preview.action_id, preview.digest)
    assert partial.terminal_state == "incomplete_retryable"
    assert fact.id not in service.records().ids(), "canonical deletion must not roll back"

    complete = service.confirm_privacy_purge(preview.action_id, preview.digest)
    assert complete.terminal_state == "complete_managed_external_action_needed"
    assert calls == 2
    assert service.doctor().ok


def test_privacy_purge_cli_preview_then_exact_confirm(tmp_path: Path) -> None:
    state = tmp_path / "state"
    env = dict(os.environ, APTUNI_STATE_DIR=str(state), PYTHONPATH=str(REPO / "src"))

    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "-m", "aptuni", *args], env=env, capture_output=True,
                              text=True, check=False)

    assert run("init", str(tmp_path / "Aptuni")).returncode == 0
    remembered = run("remember", "CLI purge marker", "--module", "preferences")
    record_id = remembered.stdout.strip().rsplit(" ", 1)[-1]
    previewed = run("privacy", "purge", "preview", record_id, "--json")
    assert previewed.returncode == 0, previewed.stderr
    preview = json.loads(previewed.stdout)
    assert preview["requested_record_ids"] == [record_id]

    confirmed = run("privacy", "purge", "confirm", preview["action_id"],
                    "--confirm-digest", preview["digest"], "--json")
    assert confirmed.returncode == 0, confirmed.stderr
    receipt = json.loads(confirmed.stdout)
    assert receipt["terminal_state"] == "complete_managed_external_action_needed"
    assert run("doctor").returncode == 0


def _commit_intent(service: AptuniService, preview: object) -> None:
    seq, records = service.snapshot()
    privacy._load_or_commit_intent(
        service.workspace.state_dir, preview.action_id, preview.digest, seq,  # type: ignore[attr-defined]
        service.policy_of(records).epoch,
    )


def _pending_candidate(service: AptuniService, statement: str, module: str = "preferences") -> str:
    service.observe(statement, module)
    return service.pending_memories()[0].candidate_id


def _accept_bypassing_the_guard(service: AptuniService, candidate_id: str, action_id: str) -> None:
    """Land a dependent Memory/ReviewEvent on a frozen scope, as a pre-guard writer could."""
    intent = service.workspace.state_dir / "privacy" / "intents" / f"{action_id}.json"
    held = intent.read_bytes()
    intent.unlink()
    try:
        service.decide_memory(candidate_id, "accept", service.memory_preview(candidate_id).digest("accept"))
    finally:
        intent.write_bytes(held)


def test_durable_purge_intent_blocks_every_canonical_writer(tmp_path: Path) -> None:
    """Review 31 F1: only source sync was guarded; any writer can wedge the frozen purge scope."""
    service = _service(tmp_path)
    candidate_id = _pending_candidate(service, "intent guard marker")
    digest = service.memory_preview(candidate_id).digest("accept")
    preview = service.privacy_purge_preview((candidate_id,))
    _commit_intent(service, preview)

    for attempt in (
        lambda: service.remember("written during a committed purge", "preferences"),
        lambda: service.observe("observed during a committed purge", "preferences"),
        lambda: service.decide_memory(candidate_id, "accept", digest),
    ):
        with pytest.raises(AptuniError) as stopped:
            attempt()
        assert stopped.value.code == "privacy_action_in_progress"

    receipt = service.confirm_privacy_purge(preview.action_id, preview.digest)
    assert receipt.terminal_state == "complete_managed_external_action_needed"
    service.remember("allowed once the purge is terminal", "preferences")


def test_unsatisfiable_intent_is_retryable_not_an_escaping_invariant_error(tmp_path: Path) -> None:
    """Review 31 F1: a dependent record on the frozen scope must not raise InvariantError."""
    service = _service(tmp_path)
    candidate_id = _pending_candidate(service, "unsatisfiable scope marker")
    preview = service.privacy_purge_preview((candidate_id,))
    _commit_intent(service, preview)
    _accept_bypassing_the_guard(service, candidate_id, preview.action_id)

    receipt = service.confirm_privacy_purge(preview.action_id, preview.digest)
    assert receipt.terminal_state == "incomplete_retryable"
    assert {item.copy_class: item.result for item in receipt.per_copy}["canonical"] == "failed_retryable"
    assert "unsatisfiable scope marker" not in json.dumps(receipt.model_dump(mode="json"))


def test_purge_cancel_releases_a_wedged_intent(tmp_path: Path) -> None:
    """Review 31 F1: without a cancel path one stuck intent disables deletion forever."""
    service = _service(tmp_path)
    candidate_id = _pending_candidate(service, "cancel marker")
    preview = service.privacy_purge_preview((candidate_id,))
    _commit_intent(service, preview)
    _accept_bypassing_the_guard(service, candidate_id, preview.action_id)
    assert service.confirm_privacy_purge(preview.action_id, preview.digest).terminal_state == "incomplete_retryable"
    with pytest.raises(AptuniError) as blocked:
        service.remember("blocked while the intent is wedged", "preferences")
    assert blocked.value.code == "privacy_action_in_progress"

    service.cancel_privacy_purge(preview.action_id)
    assert not (service.workspace.state_dir / "privacy" / "intents" / f"{preview.action_id}.json").exists()
    service.remember("writes resume after cancel", "preferences")
    fresh = service.privacy_purge_preview((candidate_id,))
    assert service.confirm_privacy_purge(fresh.action_id, fresh.digest).terminal_state != "incomplete_retryable"
    assert candidate_id not in {record.id for record in service.records().records()}


def test_cancel_refuses_once_the_deletion_ledger_records_the_scope(tmp_path: Path) -> None:
    """Review 32 N2: the ledger, not the after-the-fact result field, decides whether cancel is safe.

    A crash between ``vault.purge()`` returning and the result being written would otherwise let
    cancel abandon a purge that had already destroyed canonical records.
    """
    service = _service(tmp_path)
    fact = service.remember("cancel-after-canonical marker", "preferences")
    preview = service.privacy_purge_preview((fact.id,))
    _commit_intent(service, preview)
    service.confirm_privacy_purge(preview.action_id, preview.digest)
    assert not (service.workspace.state_dir / "privacy" / "intents" / f"{preview.action_id}.json").exists()

    # Model the crash window: the intent is back, with no recorded canonical result.
    intent_path = service.workspace.state_dir / "privacy" / "intents" / f"{preview.action_id}.json"
    privacy._write_private_json(intent_path, {"schema_version": 1, "preview": preview.to_dict(), "results": {}})
    with pytest.raises(AptuniError) as refused:
        service.cancel_privacy_purge(preview.action_id)
    assert refused.value.code == "privacy_cancel_refused"
    assert intent_path.exists(), "a refused cancel must leave the intent for retry"

    with pytest.raises(AptuniError) as missing:
        service.cancel_privacy_purge("act-" + "0" * 16)
    assert missing.value.code == "privacy_action_not_found"
