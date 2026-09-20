"""Owner backup and restore: a verified restorable copy that never resurrects a purged record.

Acceptance cases 1-13 of `docs/dev/plans/08-owner-backup-and-restore.md`. Case 2 is the reason the
slice exists: KI-021 reproduced that a pre-purge Vault copy restored with a fresh state directory
re-admitted the purged record, because the deletion ledger lived only in the state directory.
"""

from __future__ import annotations

import errno
import json
import stat
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from aptuni.application import backup as backup_api
from aptuni.application import restore as restore_api
from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace
from aptuni.cli.backup_commands import render_restore_preview
from aptuni.cli.main import run as cli_run
from aptuni.domain.ids import sha256_text
from aptuni.domain.invariants import InvariantError
from aptuni.vault import store as store_module
from aptuni.vault.fsgate import UnsupportedFilesystemError
from aptuni.vault.store import Vault, VaultIntegrityError

MANIFEST = "aptuni-backup.json"


def _service(tmp_path: Path, name: str = "state") -> AptuniService:
    service = AptuniService(Workspace(tmp_path / name))
    service.init(tmp_path / "Aptuni")
    return service


def _populated(tmp_path: Path) -> tuple[AptuniService, str]:
    """A Vault with a fact, a correction chain, and folder Evidence."""
    service = _service(tmp_path)
    kept = service.remember("I am studying competing risks", "knowledge")
    service.correct(kept.id, "I am studying competing risks and the Fine-Gray model")
    doomed = service.remember("I want to work on quant finance", "goals")
    root = tmp_path / "source"
    root.mkdir()
    (root / "note.md").write_text("Competing risks notes", encoding="utf-8")
    source = service.add_folder_source(root, ("knowledge",), "notes")
    service.sync(source.id)
    return service, doomed.id


def _adopt(tmp_path: Path, state_name: str) -> AptuniService:
    """Point a different state directory at the same Vault: a new machine, or a wiped state dir."""
    service = AptuniService(Workspace(tmp_path / state_name))
    service.workspace.save(tmp_path / "Aptuni")
    return service


def _purge(service: AptuniService, record_id: str) -> None:
    preview = service.privacy_purge_preview((record_id,))
    receipt = service.confirm_privacy_purge(preview.action_id, preview.digest)
    assert receipt.terminal_state != "incomplete_retryable", receipt.terminal_state


def _restore(service: AptuniService, path: Path) -> restore_api.RestoreReceipt:
    preview = service.restore_preview(path)
    return service.confirm_restore(preview.action_id, preview.digest)


# ---------------------------------------------------------------- case 1: round trip


def test_case_1_backup_verify_restore_round_trips_the_canonical_vault(tmp_path: Path) -> None:
    service, _ = _populated(tmp_path)
    before = {record.id for record in service.records().records()}
    destination = tmp_path / "backup"

    summary = service.create_backup(destination)
    assert summary.ok and summary.problems == ()
    assert summary.record_count == len(before)
    assert backup_api.verify_backup(destination).ok

    service.remember("a fact recorded after the backup", "interests")
    receipt = _restore(service, destination)

    assert receipt.restored_record_count == len(before)
    assert {record.id for record in service.records().records()} == before
    assert service.doctor().ok
    service.rebuild_index()
    assert service.search("Fine-Gray")


# ---------------------------------------------------------------- case 2: KI-021


def test_case_2_a_fresh_state_directory_cannot_resurrect_a_purged_record(tmp_path: Path) -> None:
    """KI-021. The deletion ledger must travel with the backup, not with the state directory."""
    service, doomed = _populated(tmp_path)
    destination = tmp_path / "backup"
    service.create_backup(destination)
    _purge(service, doomed)
    assert doomed not in {record.id for record in service.records().records()}

    fresh = _adopt(tmp_path, "state-fresh")
    assert not (fresh.workspace.state_dir / "deletion-ledger.jsonl").exists(), \
        "precondition: the new state directory holds no deletion history of its own"
    assert fresh.vault().ledger_digests(), \
        "the deletion must be readable from the Vault, not only from the original state directory"

    preview = fresh.restore_preview(destination)
    assert preview.ledger_drop_count == 1, "the preview must say a record will be dropped"
    fresh.confirm_restore(preview.action_id, preview.digest)

    ids = {record.id for record in fresh.records().records()}
    assert doomed not in ids, "a purged record came back through restore (KI-021)"
    assert fresh.doctor().ok


def test_case_2b_the_backup_manifest_carries_the_deletion_ledger(tmp_path: Path) -> None:
    service, doomed = _populated(tmp_path)
    _purge(service, doomed)
    destination = tmp_path / "backup"
    service.create_backup(destination)

    manifest = json.loads((destination / MANIFEST).read_text(encoding="utf-8"))
    assert manifest["deletion_digests"], "a purge happened, so the manifest must carry its digest"
    assert set(manifest["deletion_digests"]) == service.vault().ledger_digests()
    assert doomed not in (destination / MANIFEST).read_text(encoding="utf-8"), "ledgers stay content-free"


def test_case_2c_restoring_a_newer_backup_keeps_a_later_purge_deleted(tmp_path: Path) -> None:
    """A purge recorded on the live side must survive a restore from a backup taken before it."""
    service, doomed = _populated(tmp_path)
    early = tmp_path / "early"
    service.create_backup(early)
    _purge(service, doomed)

    _restore(service, early)
    assert doomed not in {record.id for record in service.records().records()}


# ---------------------------------------------------------------- cases 3-5: refusals


def test_case_3_a_folder_without_a_manifest_is_not_a_backup(tmp_path: Path) -> None:
    service, _ = _populated(tmp_path)
    hand_copy = tmp_path / "hand-copy"
    hand_copy.mkdir()
    (hand_copy / "records").mkdir()
    (hand_copy / "HEAD.json").write_text(
        (service.vault().root / "HEAD.json").read_text(encoding="utf-8"), encoding="utf-8")

    summary = backup_api.verify_backup(hand_copy)
    assert not summary.ok
    assert any("manifest" in problem for problem in summary.problems)
    with pytest.raises(AptuniError) as refused:
        service.restore_preview(hand_copy)
    assert refused.value.code == "backup_unverified"


@pytest.mark.parametrize("field,value", [
    ("record_count", 99),
    ("vault_seq", 99),
    ("chain", "0" * 64),
    ("segments", []),
])
def test_case_4_a_manifest_that_disagrees_with_the_segments_is_refused(
    tmp_path: Path, field: str, value: object,
) -> None:
    service, _ = _populated(tmp_path)
    destination = tmp_path / "backup"
    service.create_backup(destination)
    live_seq = service.vault().head().seq

    manifest_path = destination / MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest[field] = value
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    assert not backup_api.verify_backup(destination).ok
    with pytest.raises(AptuniError) as refused:
        service.restore_preview(destination)
    assert refused.value.code == "backup_unverified"
    assert service.vault().head().seq == live_seq, "the live Vault must be untouched"


@pytest.mark.parametrize("mutate", ["truncate", "extend", "edit"])
def test_case_5_a_changed_segment_is_refused_before_restore_is_reachable(
    tmp_path: Path, mutate: str,
) -> None:
    service, _ = _populated(tmp_path)
    destination = tmp_path / "backup"
    service.create_backup(destination)
    segment = sorted((destination / "records").glob("seg-*.jsonl"))[-1]
    body = segment.read_bytes()
    if mutate == "truncate":
        segment.write_bytes(body[: len(body) // 2])
    elif mutate == "extend":
        segment.write_bytes(body + b'{"id":"fct_extra"}\n')
    else:
        flipped = bytes([body[0] ^ 0x20]) + body[1:]
        assert flipped != body
        segment.write_bytes(flipped)

    assert not backup_api.verify_backup(destination).ok
    with pytest.raises(AptuniError) as refused:
        service.restore_preview(destination)
    assert refused.value.code == "backup_unverified"


# ---------------------------------------------------------------- case 6: safe destinations


@pytest.mark.parametrize("where", ["self", "inside", "parent"])
def test_case_6_a_backup_never_lands_in_or_around_the_live_vault(tmp_path: Path, where: str) -> None:
    service, _ = _populated(tmp_path)
    root = service.vault().root
    target = {"self": root, "inside": root / "nested", "parent": root.parent}[where]
    with pytest.raises(AptuniError) as refused:
        service.create_backup(target)
    assert refused.value.code == "invalid_backup_destination"


def test_case_6b_a_non_empty_destination_is_never_overwritten(tmp_path: Path) -> None:
    service, _ = _populated(tmp_path)
    destination = tmp_path / "backup"
    destination.mkdir()
    (destination / "mine.txt").write_text("the owner's file", encoding="utf-8")
    with pytest.raises(AptuniError) as refused:
        service.create_backup(destination)
    assert refused.value.code == "invalid_backup_destination"
    assert (destination / "mine.txt").exists()


def test_case_6c_a_failed_create_leaves_no_partial_backup(tmp_path: Path, monkeypatch) -> None:
    service, _ = _populated(tmp_path)
    destination = tmp_path / "backup"

    def boom(*args: object, **kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(backup_api, "_copy_segment", boom)
    with pytest.raises(AptuniError) as failed:
        service.create_backup(destination)
    assert failed.value.code == "backup_write_failed"
    assert not destination.exists(), "a half-written backup must not be left behind"


# ---------------------------------------------------------------- case 7: bound confirmation


def test_case_7_restore_is_bound_to_the_preview_digest(tmp_path: Path) -> None:
    service, _ = _populated(tmp_path)
    destination = tmp_path / "backup"
    service.create_backup(destination)
    preview = service.restore_preview(destination)
    live_seq = service.vault().head().seq

    with pytest.raises(AptuniError) as wrong:
        service.confirm_restore(preview.action_id, "sha256:" + "0" * 64)
    assert wrong.value.code == "restore_digest_mismatch"
    assert service.vault().head().seq == live_seq


def test_case_7b_an_unknown_or_malformed_action_id_is_refused(tmp_path: Path) -> None:
    service, _ = _populated(tmp_path)
    for action_id, code in [("act-" + "0" * 16, "restore_action_not_found"),
                            ("not-an-action", "invalid_restore_action_id")]:
        with pytest.raises(AptuniError) as refused:
            service.confirm_restore(action_id, "sha256:" + "0" * 64)
        assert refused.value.code == code, action_id


def test_case_7c_an_expired_preview_cannot_be_confirmed(tmp_path: Path, monkeypatch) -> None:
    service, _ = _populated(tmp_path)
    destination = tmp_path / "backup"
    service.create_backup(destination)
    monkeypatch.setattr(restore_api, "RESTORE_TTL", timedelta(seconds=-1))
    preview = service.restore_preview(destination)
    with pytest.raises(AptuniError) as expired:
        service.confirm_restore(preview.action_id, preview.digest)
    assert expired.value.code == "restore_action_expired"


def test_case_7d_a_tampered_pending_preview_fails_closed(tmp_path: Path) -> None:
    service, _ = _populated(tmp_path)
    destination = tmp_path / "backup"
    service.create_backup(destination)
    preview = service.restore_preview(destination)

    path = restore_api.pending_path(service.workspace.state_dir, preview.action_id)
    stored = json.loads(path.read_text(encoding="utf-8"))
    stored["backup_record_count"] = 0
    path.write_text(json.dumps(stored), encoding="utf-8")

    with pytest.raises(AptuniError) as refused:
        service.confirm_restore(preview.action_id, preview.digest)
    assert refused.value.code == "restore_action_invalid"


def test_case_7e_cancel_changes_nothing(tmp_path: Path) -> None:
    service, _ = _populated(tmp_path)
    destination = tmp_path / "backup"
    service.create_backup(destination)
    before = {record.id for record in service.records().records()}
    preview = service.restore_preview(destination)

    service.cancel_restore(preview.action_id)
    assert {record.id for record in service.records().records()} == before
    with pytest.raises(AptuniError) as gone:
        service.confirm_restore(preview.action_id, preview.digest)
    assert gone.value.code == "restore_action_not_found"


# ---------------------------------------------------------------- case 8: crash recovery


def test_case_8_a_crash_before_confirmation_leaves_the_live_vault_alone(tmp_path: Path) -> None:
    service, _ = _populated(tmp_path)
    destination = tmp_path / "backup"
    service.create_backup(destination)
    live_seq = service.vault().head().seq
    service.restore_preview(destination)  # process "dies" here; nothing confirmed

    adopted = _adopt(tmp_path, "state")
    assert adopted.vault().head().seq == live_seq
    assert adopted.doctor().ok


def test_case_8b_a_crash_during_publication_is_completed_by_open(tmp_path: Path) -> None:
    service, _ = _populated(tmp_path)
    destination = tmp_path / "backup"
    service.create_backup(destination)
    expected = {record.id for record in service.records().records()}
    service.remember("a fact recorded after the backup", "interests")

    preview = service.restore_preview(destination)
    service.vault().crash_hook = lambda point: (
        (_ for _ in ()).throw(RuntimeError(point)) if point == "after_head_tmp" else None)
    with pytest.raises(RuntimeError, match="after_head_tmp"):
        service.confirm_restore(preview.action_id, preview.digest)

    recovered = _adopt(tmp_path, "state")
    assert recovered.doctor().ok, "the journal must be replayed on open"
    assert {record.id for record in recovered.records().records()} == expected


# ---------------------------------------------------------------- case 9: derived state


def test_case_9_restore_clears_replay_state_and_invalidates_the_projection(tmp_path: Path) -> None:
    service, _ = _populated(tmp_path)
    service.rebuild_index()
    destination = tmp_path / "backup"
    service.create_backup(destination)

    receipt = _restore(service, destination)
    assert receipt.cleared_source_state is True
    assert receipt.invalidated_projection is True
    assert not list((service.vault().root / "sources").iterdir())


# ---------------------------------------------------------------- case 11: private bytes


def test_case_11_a_backup_is_private_and_reports_no_record_content(tmp_path: Path) -> None:
    service, _ = _populated(tmp_path)
    destination = tmp_path / "backup"
    summary = service.create_backup(destination)

    assert stat.S_IMODE(destination.stat().st_mode) == 0o700
    for path in [destination / MANIFEST, *(destination / "records").iterdir()]:
        assert stat.S_IMODE(path.stat().st_mode) == 0o600, path

    rendered = json.dumps(summary.to_dict(), ensure_ascii=False)
    assert "competing risks" not in rendered.lower()
    assert "quant finance" not in rendered.lower()


def test_case_11b_list_reports_each_backup_without_reading_records(tmp_path: Path) -> None:
    service, _ = _populated(tmp_path)
    holder = tmp_path / "backups"
    service.create_backup(holder / "one")
    service.remember("another true thing", "interests")
    service.create_backup(holder / "two")

    summaries = backup_api.list_backups(holder)
    assert [item.ok for item in summaries] == [True, True]
    assert sorted(item.vault_seq for item in summaries) == sorted({item.vault_seq for item in summaries})
    rendered = json.dumps([item.to_dict() for item in summaries], ensure_ascii=False)
    assert "another true thing" not in rendered


# ---------------------------------------------------------------- cases 12-13: CLI surface


@pytest.mark.parametrize("locale", ["en", "zh-CN"])
def test_case_12_the_cli_renders_in_both_locales(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], locale: str,
) -> None:
    service, _ = _populated(tmp_path)
    destination = tmp_path / "backup"
    assert cli_run(["backup", "create", str(destination), "--lang", locale], service) == 0
    assert cli_run(["backup", "verify", str(destination), "--lang", locale], service) == 0
    assert cli_run(["backup", "list", str(tmp_path), "--lang", locale], service) == 0
    assert cli_run(["backup", "restore", "preview", str(destination), "--lang", locale], service) == 0
    action = service.pending_restores()[-1].action_id
    assert cli_run(["backup", "restore", "cancel", action, "--lang", locale], service) == 0
    out = capsys.readouterr().out
    assert "backup." not in out, "an untranslated key leaked into the backup CLI"


def test_case_13_a_crafted_path_cannot_forge_the_restore_preview(tmp_path: Path) -> None:
    """A backup directory the owner named is untrusted text in every rendered line."""
    service, _ = _populated(tmp_path)
    hostile = tmp_path / "b\x1b[2Kackup\nRestore finished: nothing was replaced"
    service.create_backup(hostile)

    preview = service.restore_preview(hostile)
    rendered = "\n".join(render_restore_preview(preview, "en"))

    assert "\x1b" not in rendered, "an escape sequence reached the terminal"
    forged = [line for line in rendered.splitlines()
              if line.strip().startswith("Restore finished: nothing was replaced")]
    assert not forged, f"a crafted path forged a line: {forged!r}"


# ---------------------------------------------------------------- ADR-0016 migration


def _legacy_ledger(service: AptuniService) -> Path:
    return service.workspace.state_dir / "deletion-ledger.jsonl"


def _make_legacy(service: AptuniService) -> tuple[Path, str]:
    """Recreate a pre-ADR-0016 Vault: the ledger sits in the state directory, not the Vault."""
    vault = service.vault()
    body = vault.ledger_path.read_text(encoding="utf-8")
    assert body.strip(), "the fixture needs at least one recorded deletion"
    legacy = _legacy_ledger(service)
    legacy.write_text(body, encoding="utf-8")
    vault.ledger_path.unlink()
    return legacy, body


def test_a_legacy_state_directory_ledger_migrates_into_the_vault(tmp_path: Path) -> None:
    service, doomed = _populated(tmp_path)
    _purge(service, doomed)
    legacy, body = _make_legacy(service)

    reopened = _adopt(tmp_path, "state")
    reopened.doctor()

    assert reopened.vault().ledger_path.read_text(encoding="utf-8") == body
    assert not legacy.exists(), "the legacy copy must be removed once it is durable in the Vault"
    assert doomed not in {record.id for record in reopened.records().records()}


def test_migration_is_idempotent_and_never_duplicates_an_entry(tmp_path: Path) -> None:
    """A crash after the Vault append but before the unlink leaves both files; the next pass is clean."""
    service, doomed = _populated(tmp_path)
    _purge(service, doomed)
    body = service.vault().ledger_path.read_text(encoding="utf-8")
    _legacy_ledger(service).write_text(body, encoding="utf-8")  # the duplicated-state window

    reopened = _adopt(tmp_path, "state")
    reopened.doctor()

    assert reopened.vault().ledger_path.read_text(encoding="utf-8") == body, "an entry was duplicated"
    assert not _legacy_ledger(service).exists()
    assert len(reopened.vault().ledger_digests()) == 1


def test_a_legacy_ledger_still_blocks_resurrection_before_it_migrates(tmp_path: Path) -> None:
    """Reads union both locations, so an unmigrated ledger is honoured from the first read."""
    service, doomed = _populated(tmp_path)
    _purge(service, doomed)
    _make_legacy(service)

    unopened = AptuniService(Workspace(tmp_path / "state"))
    unopened.workspace.save(tmp_path / "Aptuni")
    assert len(unopened.vault().ledger_digests()) == 1


def test_a_torn_legacy_ledger_tail_does_not_block_migration(tmp_path: Path) -> None:
    service, doomed = _populated(tmp_path)
    _purge(service, doomed)
    legacy, body = _make_legacy(service)
    legacy.write_text(body + '{"id": "led_torn', encoding="utf-8")

    reopened = _adopt(tmp_path, "state")
    reopened.doctor()
    assert reopened.vault().ledger_path.read_text(encoding="utf-8") == body
    assert not legacy.exists()


def test_a_scripted_confirm_applies_the_exact_previewed_restore(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """`--confirm-digest` names one pending action, so a script can finish what a preview started."""
    service, _ = _populated(tmp_path)
    destination = tmp_path / "backup"
    service.create_backup(destination)
    expected = {record.id for record in service.records().records()}
    service.remember("a fact recorded after the backup", "interests")

    assert cli_run(["backup", "restore", "preview", str(destination), "--json"], service) == 0
    preview = json.loads(capsys.readouterr().out)
    assert cli_run(["backup", "restore", "confirm", preview["action_id"],
                    "--confirm-digest", preview["digest"], "--json"], service) == 0

    assert {record.id for record in service.records().records()} == expected
    assert service.doctor().ok


def test_a_non_terminal_confirm_without_a_digest_restores_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    service, _ = _populated(tmp_path)
    destination = tmp_path / "backup"
    service.create_backup(destination)
    live_seq = service.vault().head().seq
    preview = service.restore_preview(destination)

    assert cli_run(["backup", "restore", "confirm", preview.action_id], service) == 1
    assert service.vault().head().seq == live_seq
    assert "aptuni backup restore confirm" in capsys.readouterr().out


# ---------------------------------------------------------------- Review 35 regressions


def test_b1_a_ledger_entry_that_lost_only_its_newline_is_never_discarded(tmp_path: Path) -> None:
    """Review 35 B1. `_drop_torn_tail` and `_digests_in` must agree on what a torn tail is.

    A crash that loses only the trailing newline leaves a complete entry. The reader honoured it and
    the next append truncated it, so a completed purge was forgotten and a restore re-admitted the
    record.
    """
    service, doomed = _populated(tmp_path)
    early = tmp_path / "early"
    service.create_backup(early)          # taken before the purge, so it still holds the record
    _purge(service, doomed)

    ledger = service.vault().ledger_path
    body = ledger.read_text(encoding="utf-8")
    ledger.write_text(body.rstrip("\n"), encoding="utf-8")  # the crash window
    assert len(service.vault().ledger_digests()) == 1, "the reader must still honour the entry"

    # Any later append used to truncate it. A second purge is the narrowest trigger.
    second = service.remember("another thing to delete", "interests")
    _purge(service, second.id)
    assert len(service.vault().ledger_digests()) == 2, "the earlier deletion was truncated away"

    fresh = _adopt(tmp_path, "state-after-tear")
    preview = fresh.restore_preview(early)
    assert preview.ledger_drop_count == 1
    fresh.confirm_restore(preview.action_id, preview.digest)
    assert doomed not in {record.id for record in fresh.records().records()}


def test_b1_the_manifest_digests_alone_prevent_resurrection(tmp_path: Path) -> None:
    """Review 35 N1. The two-machine shape: only the backup proves the deletion.

    `_populated` writes the Vault, a purge is recorded, a backup is taken, and the deletion is then
    erased from the live Vault entirely. Nothing but the manifest knows about it.
    """
    service, doomed = _populated(tmp_path)
    _purge(service, doomed)
    destination = tmp_path / "backup"
    service.create_backup(destination)

    # The receiving machine has no record of this deletion at all.
    service.vault().ledger_path.unlink()
    assert service.vault().ledger_digests() == set()

    preview = service.restore_preview(destination)
    assert preview.new_ledger_digest_count == 1, "the manifest must supply the unknown deletion"
    service.confirm_restore(preview.action_id, preview.digest)

    assert doomed not in {record.id for record in service.records().records()}
    assert service.vault().ledger_digests(), "the absorbed deletion must be durable afterwards"


def test_b2_the_confirmation_states_how_many_records_the_restore_deletes(tmp_path: Path) -> None:
    """Review 35 B2. Restore unlinks every live segment, so the preview must not imply retention."""
    service, _ = _populated(tmp_path)
    destination = tmp_path / "backup"
    service.create_backup(destination)
    service.remember("a fact recorded after the backup", "interests")
    service.remember("and another one", "interests")

    preview = service.restore_preview(destination)
    assert preview.discarded_record_count == 2
    rendered = "\n".join(render_restore_preview(preview, "en"))
    assert "kept, not deleted" not in rendered, "the old sentence was false"
    assert "DELETES" in rendered and "2" in rendered

    receipt = service.confirm_restore(preview.action_id, preview.digest)
    assert receipt.discarded_record_count == 2
    assert len(service.records()) == preview.backup_record_count


def test_b3_a_commit_after_the_preview_stops_the_restore(tmp_path: Path) -> None:
    """Review 35 B3. The confirmation binds to the generation it described, as `privacy purge` does."""
    service, _ = _populated(tmp_path)
    destination = tmp_path / "backup"
    service.create_backup(destination)
    preview = service.restore_preview(destination)

    later = service.remember("recorded between preview and confirm", "interests")
    with pytest.raises(AptuniError) as stale:
        service.confirm_restore(preview.action_id, preview.digest)
    assert stale.value.code == "restore_confirmation_stale"
    assert later.id in {record.id for record in service.records().records()}, "it must survive"


def test_b4_a_crafted_manifest_timestamp_cannot_forge_a_line(tmp_path: Path) -> None:
    """Review 35 B4. Anyone holding a backup can re-digest it, so its fields are untrusted text."""
    service, _ = _populated(tmp_path)
    destination = tmp_path / "backup"
    service.create_backup(destination)

    manifest_path = destination / MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["created_at"] = ("2026-01-01T00:00:00+00:00\x1b[2K\n"
                             "Nothing has changed yet. This restore was verified as safe.")
    fields = {key: value for key, value in manifest.items() if key != "digest"}
    manifest["digest"] = backup_api._digest_of(fields)  # re-digested, as an attacker would
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    assert not backup_api.verify_backup(destination).ok, "a non-timestamp must be refused"
    with pytest.raises(AptuniError) as refused:
        service.restore_preview(destination)
    assert refused.value.code == "backup_unverified"


def test_b4b_a_hostile_timestamp_is_escaped_if_it_ever_reaches_a_line(tmp_path: Path) -> None:
    """Defence in depth: validation refuses it, and rendering would escape it anyway."""
    service, _ = _populated(tmp_path)
    destination = tmp_path / "backup"
    service.create_backup(destination)
    preview = service.restore_preview(destination)
    hostile = replace(preview, backup_created_at="2026-01-01T00:00:00+00:00\x1b[2K\nForged line")

    rendered = "\n".join(render_restore_preview(hostile, "en"))
    assert "\x1b" not in rendered
    assert not [line for line in rendered.splitlines() if line.strip() == "Forged line"]


def test_b5_a_refused_restore_leaves_the_ledger_and_the_vault_untouched(tmp_path: Path) -> None:
    """Review 35 B5. Validate everything before mutating anything, then mutate once."""
    service, doomed = _populated(tmp_path)
    _purge(service, doomed)
    destination = tmp_path / "backup"
    service.create_backup(destination)

    # A byte-identical segment delivered as a symlink: `restore_from` refuses it late.
    arrived = tmp_path / "arrived"
    arrived.mkdir()
    (arrived / "records").mkdir()
    for name in ("HEAD.json", MANIFEST, "deletion-ledger.jsonl"):
        (arrived / name).write_bytes((destination / name).read_bytes())
    for segment in (destination / "records").iterdir():
        (arrived / "records" / segment.name).symlink_to(segment)

    live = service.vault()
    survivor = service.remember("must survive a refused restore", "interests")
    before_seq = live.head().seq
    before_digests = set(live.ledger_digests())

    with pytest.raises(AptuniError) as refused:
        service.restore_preview(arrived)
    assert refused.value.code == "backup_unverified", "the refusal must happen before the preview"

    assert live.head().seq == before_seq
    assert set(live.ledger_digests()) == before_digests, "a refused restore absorbed a digest"
    reopened = _adopt(tmp_path, "state")
    assert survivor.id in {record.id for record in reopened.records().records()}, \
        "recover() completed an unconfirmed purge left behind by a refused restore"


def test_b5b_a_backup_inside_the_vault_is_refused_at_preview_not_at_confirm(tmp_path: Path) -> None:
    service, _ = _populated(tmp_path)
    inside = service.vault().root / "nested-backup"
    good = tmp_path / "good"
    service.create_backup(good)
    inside.mkdir()
    for name in ("HEAD.json", MANIFEST):
        (inside / name).write_bytes((good / name).read_bytes())
    (inside / "records").mkdir()
    for segment in (good / "records").iterdir():
        (inside / "records" / segment.name).write_bytes(segment.read_bytes())

    with pytest.raises(AptuniError) as refused:
        service.restore_preview(inside)
    assert refused.value.code == "backup_unverified"


def test_n2_the_manifest_digest_catches_a_field_the_disk_cannot_contradict(tmp_path: Path) -> None:
    """Review 35 N2. `created_at` is not cross-checked against any bytes, so only the digest guards it."""
    service, _ = _populated(tmp_path)
    destination = tmp_path / "backup"
    service.create_backup(destination)

    manifest_path = destination / MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["created_at"] = "2001-01-01T00:00:00+00:00"  # a valid timestamp, so validation passes
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    summary = backup_api.verify_backup(destination)
    assert not summary.ok
    assert any("changed after it was written" in problem for problem in summary.problems)


def test_n3_a_concurrent_writer_never_produces_a_mixed_generation(tmp_path: Path) -> None:
    """Acceptance case 10. Either the restore or the commit wins, and the Vault stays verifiable."""
    service, _ = _populated(tmp_path)
    destination = tmp_path / "backup"
    service.create_backup(destination)
    backup_ids = {record.id for record in service.records().records()}
    preview = service.restore_preview(destination)

    outcomes: list[str] = []

    def restore() -> None:
        try:
            service.confirm_restore(preview.action_id, preview.digest)
            outcomes.append("restored")
        except AptuniError as error:
            outcomes.append(error.code)

    def commit() -> None:
        try:
            service.remember("written during the restore", "interests")
            outcomes.append("committed")
        except AptuniError as error:  # pragma: no cover - a refusal is also a valid serial outcome
            outcomes.append(error.code)

    with ThreadPoolExecutor(max_workers=2) as pool:
        for future in [pool.submit(restore), pool.submit(commit)]:
            future.result()

    reopened = _adopt(tmp_path, "state")
    assert reopened.doctor().ok, f"a mixed generation survived: {outcomes}"
    ids = {record.id for record in reopened.records().records()}
    assert ids == backup_ids or backup_ids < ids, f"neither serial outcome was reached: {outcomes}"


def test_n5_a_failed_create_leaves_no_partial_backup_in_a_folder_the_owner_made(
    tmp_path: Path, monkeypatch,
) -> None:
    """Review 35 N5. The owner's own empty folder must stay usable after a failure."""
    service, _ = _populated(tmp_path)
    destination = tmp_path / "backup"
    destination.mkdir()

    calls = {"n": 0}
    real = backup_api._copy_segment

    def fail_after_first(source: Path, target: Path) -> None:
        calls["n"] += 1
        if calls["n"] > 1:
            raise OSError("disk full")
        real(source, target)

    monkeypatch.setattr(backup_api, "_copy_segment", fail_after_first)
    with pytest.raises(AptuniError) as failed:
        service.create_backup(destination)
    assert failed.value.code == "backup_write_failed"
    assert list(destination.iterdir()) == [], f"a partial backup survived: {list(destination.iterdir())}"

    monkeypatch.undo()
    assert service.create_backup(destination).ok, "the folder must still be usable"


def test_n6_a_state_directory_inside_the_vault_never_wipes_the_ledger(tmp_path: Path) -> None:
    """Review 35 N6. With root == state_dir the legacy path IS the canonical one."""
    service, doomed = _populated(tmp_path)
    _purge(service, doomed)
    root = service.vault().root
    collided = Vault(root, root)
    before = set(collided.ledger_digests())
    assert before

    collided.recover()
    assert set(collided.ledger_digests()) == before, "recover() wiped the deletion history"
    assert collided.ledger_path.is_file()


def test_the_manifest_digest_detects_edits_it_does_not_prevent_them(tmp_path: Path) -> None:
    """Review 35 N2, written down plainly: the digest is unkeyed.

    Anyone holding a backup can edit a field and re-digest it. The digest catches accidental
    corruption and a careless edit; it is not an authenticity guarantee against the backup's holder.
    What protects the owner is that every field the digest covers is *also* cross-checked against the
    bytes on disk, or validated for shape — so a re-digested manifest cannot make Aptuni restore
    something different from what the segments hold.
    """
    service, _ = _populated(tmp_path)
    destination = tmp_path / "backup"
    service.create_backup(destination)

    manifest_path = destination / MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["created_at"] = "2001-01-01T00:00:00+00:00"
    fields = {key: value for key, value in manifest.items() if key != "digest"}
    manifest["digest"] = backup_api._digest_of(fields)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    # Accepted: a re-digested valid timestamp is indistinguishable from a real one, and harmless.
    assert backup_api.verify_backup(destination).ok
    assert backup_api.verify_backup(destination).created_at == "2001-01-01T00:00:00+00:00"

    # But nothing that changes what would be restored survives, re-digested or not.
    for field, value in [("record_count", 99), ("vault_seq", 99), ("chain", "0" * 64), ("segments", [])]:
        edited = dict(manifest) | {field: value}
        edited_fields = {key: item for key, item in edited.items() if key != "digest"}
        edited["digest"] = backup_api._digest_of(edited_fields)
        manifest_path.write_text(json.dumps(edited), encoding="utf-8")
        assert not backup_api.verify_backup(destination).ok, f"{field} passed after re-digesting"


# ---------------------------------------------------------------- Review 36 regressions


def test_f1_a_restore_refused_by_validation_leaves_the_ledger_untouched(tmp_path: Path) -> None:
    """Review 36 F1. Nothing is recorded until the whole outcome is known to be valid.

    The digests were appended before the drop was simulated, so a restore refused by record
    validation advanced the canonical ledger; every later `open()` then failed and the Vault was
    wedged with no in-product repair.
    """
    service, _ = _populated(tmp_path)
    service.observe("I keep reaching for survival models", "knowledge")
    destination = tmp_path / "backup"
    service.create_backup(destination)
    vault = service.vault()
    before = set(vault.ledger_digests())
    before_seq = vault.head().seq

    # A CandidateMemory requires at least one `derived_from`, so ledgering the Observation it derives
    # from leaves it invalid and `RecordSet(kept).validate()` refuses the whole restore.
    observation = next(record for record in service.records().records()
                       if record.record_type == "observation")
    with pytest.raises((InvariantError, AptuniError)):
        vault.restore_from(destination, before_seq, frozenset({sha256_text(observation.id)}))

    assert set(vault.ledger_digests()) == before, "a refused restore recorded a deletion"
    assert vault.head().seq == before_seq
    reopened = _adopt(tmp_path, "state")
    assert reopened.doctor().ok, "the Vault must still open and verify after a refused restore"


def test_f2_restoring_an_empty_generation_keeps_the_vault_readable(tmp_path: Path) -> None:
    """Review 36 F2. When every backed-up record is already deleted, HEAD must still be republished.

    The new generation has the same chain as the live one, so a chain-only comparison skipped the HEAD
    write while the old segments were unlinked anyway, leaving HEAD naming files that no longer exist.
    """
    service, _ = _populated(tmp_path)
    destination = tmp_path / "backup"
    service.create_backup(destination)
    vault = service.vault()

    # Every record in the backup is already deleted, so the restored generation is empty and its
    # chain equals the live chain -- the exact state a chain-only comparison cannot tell apart.
    everything = frozenset(sha256_text(record.id) for record in service.records().records())
    vault.restore_from(destination, vault.head().seq, everything)

    published = vault.head()
    assert published.segments == (), "the restored generation should hold nothing"
    named = {str(segment["name"]) for segment in published.segments}
    on_disk = {path.name for path in (vault.root / "records").iterdir()}
    assert named <= on_disk, f"HEAD names segments that no longer exist: {named - on_disk}"

    reopened = _adopt(tmp_path, "state")
    report = reopened.doctor()
    assert report.ok, f"the Vault is unreadable after an empty restore: {report.problems}"
    assert reopened.vault().head().seq == published.seq, "the new generation was never published"


def test_f3_a_destination_aptuni_cannot_verify_is_refused_before_anything_is_written(
    tmp_path: Path, monkeypatch,
) -> None:
    """Review 36 F3. The gate must refuse up front, not escape after the plaintext copy exists."""
    service, _ = _populated(tmp_path)
    destination = tmp_path / "on-a-synced-drive"

    def refuse(path: Path, **kwargs: object) -> None:
        raise UnsupportedFilesystemError("synchronized folder is not admitted: Dropbox")

    monkeypatch.setattr(backup_api, "check_vault_filesystem", refuse)
    with pytest.raises(AptuniError) as refused:
        service.create_backup(destination)
    assert refused.value.code == "invalid_backup_destination"
    assert "synchronized" in refused.value.message
    assert not destination.exists(), "no plaintext copy may be left behind"


def test_f3b_a_late_filesystem_failure_still_cleans_up(tmp_path: Path, monkeypatch) -> None:
    service, _ = _populated(tmp_path)
    destination = tmp_path / "backup"

    def fail(path: Path) -> object:
        raise UnsupportedFilesystemError("filesystem 'exfat' is not admitted")

    monkeypatch.setattr(backup_api, "verify_backup", fail)
    with pytest.raises(AptuniError) as failed:
        service.create_backup(destination)
    assert failed.value.code == "backup_write_failed"
    assert not destination.exists()


def test_n4_verify_refuses_a_symlinked_segment(tmp_path: Path) -> None:
    """Review 35 N4 / 36. `verify` must refuse the shapes a restore refuses, not accept them."""
    service, _ = _populated(tmp_path)
    good = tmp_path / "good"
    service.create_backup(good)

    arrived = tmp_path / "arrived"
    arrived.mkdir()
    (arrived / "records").mkdir()
    for name in ("HEAD.json", MANIFEST):
        (arrived / name).write_bytes((good / name).read_bytes())
    for segment in (good / "records").iterdir():
        (arrived / "records" / segment.name).symlink_to(segment)

    summary = backup_api.verify_backup(arrived)
    assert not summary.ok
    assert any("symlink" in problem for problem in summary.problems)


def test_n10_a_legacy_ledger_with_a_bad_digest_is_refused_not_migrated(tmp_path: Path) -> None:
    """Review 35 N10. Migration must validate what it copies into the canonical ledger."""
    service, doomed = _populated(tmp_path)
    _purge(service, doomed)
    legacy, body = _make_legacy(service)
    legacy.write_text(body.replace('"target_digest":"sha256:', '"target_digest":"not-a-digest:'),
                      encoding="utf-8")

    with pytest.raises(VaultIntegrityError, match="not a sha256 digest"):
        Vault.open(service.vault().root, service.workspace.state_dir)


# ---------------------------------------------------------------- Review 37 regressions


def _cross_machine_deletion_backup(tmp_path: Path) -> tuple[AptuniService, Path, str]:
    """A backup whose deletion is valid for the restored generation but not the live one."""
    machine_a = AptuniService(Workspace(tmp_path / "machine-a-state"))
    machine_a.init(tmp_path / "machine-a-vault")
    target = machine_a.remember("I work on causal survival analysis", "knowledge")
    fork = tmp_path / "fork-backup"
    machine_a.create_backup(fork)

    machine_b = AptuniService(Workspace(tmp_path / "machine-b-state"))
    machine_b.init(tmp_path / "machine-b-vault")
    _restore(machine_b, fork)
    _purge(machine_b, target.id)
    remote = tmp_path / "remote-backup"
    machine_b.create_backup(remote)

    # The deletion would orphan this correction if it were applied to A before replacement HEAD.
    machine_a.correct(target.id, "I work on causal survival analysis and competing risks")
    return machine_a, remote, target.id


@pytest.mark.parametrize("crash_point", [
    "after_segment_tmp", "after_segment_rename", "after_head_tmp", "after_head_rename",
])
def test_g1_restore_recovery_keeps_the_ledger_and_generation_atomic(
    tmp_path: Path, crash_point: str,
) -> None:
    """Review 37 G1. A crash cannot apply a deletion to the generation it would orphan."""
    service, remote, target_id = _cross_machine_deletion_backup(tmp_path)
    preview = service.restore_preview(remote)
    vault = service.vault()
    before_seq = vault.head().seq
    target_digest = sha256_text(target_id)

    def crash(name: str) -> None:
        if name == crash_point:
            raise RuntimeError(f"crash at {name}")

    vault.crash_hook = crash
    with pytest.raises(RuntimeError, match="crash at"):
        restore_api.confirm_restore(vault, service.workspace.state_dir, preview.action_id, preview.digest)

    # Host state is explicitly disposable. The canonical restore journal must finish recovery even
    # when the original state directory (and its lock/pending confirmation) is unavailable.
    reopened = Vault.open(vault.root, tmp_path / f"fresh-state-{crash_point}")
    assert reopened.verify().ok
    records = reopened.snapshot()[1].records()
    ledgered = target_digest in reopened.ledger_digests()
    target_present = any(record.id == target_id for record in records)
    assert ledgered is not target_present, "the ledger and published generation disagree"
    if ledgered:
        assert reopened.head().seq == before_seq + 1
    else:
        assert reopened.head().seq == before_seq


def test_g1_segment_write_failure_leaves_live_head_and_ledger_untouched(
    tmp_path: Path, monkeypatch,
) -> None:
    """Review 37 G1. ENOSPC before the journal must not commit the incoming deletion."""
    service, remote, target_id = _cross_machine_deletion_backup(tmp_path)
    preview = service.restore_preview(remote)
    vault = service.vault()
    before_head = vault.head()
    before_ledger = set(vault.ledger_digests())
    real_write = store_module._write_durable

    def fail_segment(path: Path, body: bytes) -> None:
        if path.name.startswith(".tmp-seg-"):
            raise OSError(errno.ENOSPC, "No space left on device")
        real_write(path, body)

    monkeypatch.setattr(store_module, "_write_durable", fail_segment)
    with pytest.raises(OSError) as failed:
        restore_api.confirm_restore(vault, service.workspace.state_dir, preview.action_id, preview.digest)
    assert failed.value.errno == errno.ENOSPC
    monkeypatch.undo()

    reopened = Vault.open(vault.root, vault.state_dir)
    assert reopened.verify().ok
    assert reopened.head() == before_head
    assert reopened.ledger_digests() == before_ledger
    assert sha256_text(target_id) not in reopened.ledger_digests()


def test_g2_verify_and_list_report_a_refused_backup_without_a_traceback(
    tmp_path: Path, monkeypatch, capsys,
) -> None:
    """Review 37 G2. Owner inspection stays readable when the backup filesystem is refused."""
    service, _ = _populated(tmp_path)
    backup = tmp_path / "backups" / "one"
    service.create_backup(backup)

    def refuse(path: Path, **kwargs: object) -> None:
        if backup in (path, *path.parents):
            raise UnsupportedFilesystemError("filesystem 'exfat' is not admitted")

    monkeypatch.setattr(store_module, "check_vault_filesystem", refuse)
    assert cli_run(["backup", "verify", str(backup)], service) == 1
    verify_output = capsys.readouterr().out
    assert "NOT usable for restore" in verify_output
    assert "exfat" in verify_output

    assert cli_run(["backup", "list", str(backup.parent)], service) == 1
    list_output = capsys.readouterr().out
    assert "NOT usable for restore" in list_output
    assert "exfat" in list_output
