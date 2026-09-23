"""Obsidian owner interface stays separate from source ingestion and reuses canonical actions."""

from __future__ import annotations

import json
import os
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


def test_snapshot_has_bounded_owner_views_and_promotion_state(
    service: AptuniService, tmp_path: Path,
) -> None:
    fact = service.remember("Maintains Aptuni.", "projects")
    pending = service.observe("Prefers local reproducible tools.", "knowledge")
    pinned = service.observe("Pins stable workflow preferences.", "knowledge")
    service.review_memory(pinned.memory_id, "pin")
    source_root = tmp_path / "notes"
    source_root.mkdir()
    (source_root / "one.md").write_text("Evidence body\n", encoding="utf-8")
    source = service.add_folder_source(source_root, modules=("knowledge",), role="notes")
    service.sync(source.id)

    view = service.obsidian_snapshot()

    assert view["contract"] == "aptuni.obsidian@1"
    assert view["vault_seq"] == service.snapshot()[0]
    assert fact.id in {item["id"] for item in view["profile"]}
    assert pending.memory_id in {item["id"] for item in view["pending_reviews"]}
    assert any(item["review_state"] == "auto_promoted_pending_review" for item in view["pending_reviews"])
    assert any(item["type"] == "profile.promoted_memory" for item in view["profile"])
    assert any(item["kind"] == "evidence" for item in view["evidence"])
    assert view["recent_changes"]
    assert view["truncated"] == {
        "profile": False, "memories": False, "evidence": False,
        "recent_changes": False, "pending_reviews": False,
    }
    assert all(len(section) <= 200 for section in (
        view["profile"], view["memories"], view["evidence"], view["recent_changes"],
        view["pending_reviews"],
    ))


def test_actions_reuse_review_edit_profile_and_two_phase_forget(service: AptuniService) -> None:
    accepted = service.observe("Uses Python.", "knowledge")
    assert service.obsidian_action(accepted.memory_id, "accept")["review_state"] == "accepted"

    edited = service.observe("Uses typed tests.", "knowledge")
    edit = service.obsidian_action(edited.memory_id, "edit", statement="Uses strict typed tests.")
    assert edit["record_id"] != edited.memory_id
    assert any(memory.statement == "Uses strict typed tests." for memory in service.memories())
    historical = next(
        item for item in service.obsidian_snapshot()["recent_changes"]
        if item["id"] == edited.memory_id
    )
    assert historical["actions"] == ["show_evidence"]

    pinned = service.observe("Pins stable preferences.", "knowledge")
    assert service.obsidian_action(pinned.memory_id, "pin")["review_state"] == "pinned"
    profile = service.profile_review_pending()[0]
    assert service.obsidian_action(profile.id, "accept")["review_state"] == "accepted"

    forgotten = service.observe("Temporary memory.", "knowledge")
    preview = service.obsidian_action(forgotten.memory_id, "forget")
    assert preview["confirmation_required"] is True
    with pytest.raises(AptuniError) as stale:
        service.obsidian_action(forgotten.memory_id, "forget", confirmed_digest="sha256:" + "0" * 64)
    assert stale.value.code == "confirmation_stale"
    confirmed = service.obsidian_action(
        forgotten.memory_id, "forget", confirmed_digest=preview["digest"],
    )
    assert confirmed["review_state"] == "revoked"

    with pytest.raises(AptuniError) as unsupported:
        service.obsidian_action(profile.id, "pin")
    assert unsupported.value.code == "obsidian_action_unsupported"


def test_forget_rejects_superseded_memory_before_and_after_preview(service: AptuniService) -> None:
    edited_before = service.observe("Old before preview.", "knowledge")
    service.edit_memory(edited_before.memory_id, "Replacement before preview.")
    with pytest.raises(AptuniError) as stale_before:
        service.obsidian_action(edited_before.memory_id, "forget")
    assert stale_before.value.code == "memory_not_current"

    edited_after = service.observe("Old after preview.", "knowledge")
    preview = service.obsidian_action(edited_after.memory_id, "forget")
    service.edit_memory(edited_after.memory_id, "Replacement after preview.")
    with pytest.raises(AptuniError) as stale_after:
        service.obsidian_action(
            edited_after.memory_id, "forget", confirmed_digest=preview["digest"],
        )
    assert stale_after.value.code == "memory_not_current"


def test_show_evidence_resolves_memory_and_promoted_profile_lineage(
    service: AptuniService,
) -> None:
    observed = service.observe("Prefers reproducible pipelines.", "knowledge")
    service.review_memory(observed.memory_id, "pin")
    profile = service.profile_review_pending()[0]

    memory_lineage = service.obsidian_evidence(observed.memory_id)
    profile_lineage = service.obsidian_evidence(profile.id)

    assert memory_lineage["record_id"] == observed.memory_id
    assert any(item["kind"] == "observation" for item in memory_lineage["supports"])
    assert {item["id"] for item in memory_lineage["supports"]} <= {
        item["id"] for item in profile_lineage["supports"]
    }
    assert all("provider" in item and "episode" in item for item in profile_lineage["supports"])
    assert profile_lineage["supports_truncated"] is False


def test_bounded_views_disclose_truncation(
    service: AptuniService, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import aptuni.application.obsidian_interface as bridge

    first = service.observe("First bounded memory.", "knowledge")
    service.observe("Second bounded memory.", "knowledge")
    service.review_memory(first.memory_id, "pin")
    profile = service.profile_review_pending()[0]
    monkeypatch.setattr(bridge, "MAX_SECTION_ITEMS", 1)
    monkeypatch.setattr(bridge, "MAX_SUPPORT_ITEMS", 1)

    view = service.obsidian_snapshot()
    evidence = service.obsidian_evidence(profile.id)

    assert len(view["memories"]) == 1 and view["truncated"]["memories"] is True
    assert len(evidence["supports"]) == 1 and evidence["supports_truncated"] is True


def test_snapshot_uses_one_captured_record_set(
    service: AptuniService, monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = service.snapshot()[0]
    original_memories = service.memories

    def mutating_memories() -> list[object]:
        service.observe("Created during a second read.", "knowledge")
        return original_memories()

    monkeypatch.setattr(service, "memories", mutating_memories)
    view = service.obsidian_snapshot()

    assert view["vault_seq"] == before
    assert not view["memories"]
    assert service.snapshot()[0] == before


def test_cli_json_bridge_and_installer_are_exact_and_non_overwriting(
    service: AptuniService, tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    memory = service.observe("Review inside Obsidian.", "knowledge")
    assert run(["interface", "obsidian", "snapshot", "--json"], service) == 0
    assert json.loads(capsys.readouterr().out)["contract"] == "aptuni.obsidian@1"
    assert run(["interface", "obsidian", "action", memory.memory_id, "accept", "--json"], service) == 0
    assert json.loads(capsys.readouterr().out)["review_state"] == "accepted"

    vault = tmp_path / "OwnerVault"
    (vault / ".obsidian").mkdir(parents=True)
    assert run(["interface", "obsidian", "install", str(vault), "--json"], service) == 0
    installed = json.loads(capsys.readouterr().out)
    target = Path(installed["plugin_dir"])
    assert {path.name for path in target.iterdir()} == {"manifest.json", "main.js", "styles.css"}
    script = (target / "main.js").read_text(encoding="utf-8")
    assert "execFile" in script and "exec(" not in script and "shell:" not in script
    assert "innerHTML" not in script and "writeFile" not in script
    assert 'value.contract !== CONTRACT' in script
    for label in ("Profile", "Memory", "Evidence", "Recent Changes", "Pending Reviews",
                  "Accept", "Edit", "Reject", "Pin", "Forget", "Show Evidence"):
        assert label in script

    with pytest.raises(AptuniError) as existing:
        service.install_obsidian_interface(vault)
    assert existing.value.code == "obsidian_plugin_exists"


def test_installer_refuses_non_vault_symlink_and_canonical_overlap(
    service: AptuniService, tmp_path: Path,
) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(AptuniError) as non_vault:
        service.install_obsidian_interface(plain)
    assert non_vault.value.code == "obsidian_vault_required"

    outside = tmp_path / "outside"
    outside.mkdir()
    linked = tmp_path / "linked"
    linked.symlink_to(outside, target_is_directory=True)
    with pytest.raises(AptuniError) as symlink:
        service.install_obsidian_interface(linked)
    assert symlink.value.code == "obsidian_install_unsafe"

    (service.vault().root / ".obsidian").mkdir()
    with pytest.raises(AptuniError) as overlap:
        service.install_obsidian_interface(service.vault().root)
    assert overlap.value.code == "obsidian_install_overlap"


def test_installer_removes_its_partial_directory_after_write_failure(
    service: AptuniService, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    vault = tmp_path / "OwnerVault"
    (vault / ".obsidian").mkdir(parents=True)

    def failed_write(_descriptor: int, _content: bytes) -> int:
        raise OSError("simulated write failure")

    monkeypatch.setattr(os, "write", failed_write)
    with pytest.raises(OSError, match="simulated write failure"):
        service.install_obsidian_interface(vault)

    assert not (vault / ".obsidian" / "plugins" / "aptuni").exists()


def test_installer_fails_closed_when_obsidian_directory_is_swapped(
    service: AptuniService, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    vault = tmp_path / "OwnerVault"
    config = vault / ".obsidian"
    config.mkdir(parents=True)
    displaced = vault / ".obsidian-displaced"
    outside = tmp_path / "outside"
    outside.mkdir()
    real_mkdir = os.mkdir
    swapped = False

    def swapping_mkdir(path: object, mode: int = 0o777, *, dir_fd: int | None = None) -> None:
        nonlocal swapped
        if path == "plugins" and dir_fd is not None and not swapped:
            config.rename(displaced)
            config.symlink_to(outside, target_is_directory=True)
            swapped = True
        real_mkdir(path, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "mkdir", swapping_mkdir)
    with pytest.raises(AptuniError) as unsafe:
        service.install_obsidian_interface(vault)

    assert unsafe.value.code == "obsidian_install_unsafe"
    assert not (outside / "plugins" / "aptuni").exists()
    assert not (displaced / "plugins" / "aptuni").exists()


def test_installer_fails_closed_when_target_directory_is_swapped(
    service: AptuniService, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import aptuni.application.obsidian_interface as bridge

    vault = tmp_path / "OwnerVault"
    (vault / ".obsidian").mkdir(parents=True)
    real_install = bridge._install_assets

    def swapping_install(plugins_fd: int) -> tuple[int, os.stat_result]:
        target_fd, target_stat = real_install(plugins_fd)
        os.rename("aptuni", "aptuni-displaced", src_dir_fd=plugins_fd, dst_dir_fd=plugins_fd)
        os.mkdir("aptuni", mode=0o700, dir_fd=plugins_fd)
        return target_fd, target_stat

    monkeypatch.setattr(bridge, "_install_assets", swapping_install)
    with pytest.raises(AptuniError) as unsafe:
        service.install_obsidian_interface(vault)

    assert unsafe.value.code == "obsidian_install_unsafe"
    plugin_root = vault / ".obsidian" / "plugins"
    assert not any((plugin_root / "aptuni-displaced" / name).exists() for name in bridge.ASSETS)
    assert not any((plugin_root / "aptuni" / name).exists() for name in bridge.ASSETS)


def test_installer_fails_closed_when_selected_vault_is_swapped(
    service: AptuniService, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    vault = tmp_path / "OwnerVault"
    (vault / ".obsidian").mkdir(parents=True)
    displaced = tmp_path / "OwnerVault-displaced"
    real_open = service._open_config

    def swapping_open(root_fd: int) -> int:
        config_fd = real_open(root_fd)
        vault.rename(displaced)
        (vault / ".obsidian").mkdir(parents=True)
        return config_fd

    monkeypatch.setattr(service, "_open_config", swapping_open)
    with pytest.raises(AptuniError) as unsafe:
        service.install_obsidian_interface(vault)

    assert unsafe.value.code == "obsidian_install_unsafe"
    assert not (vault / ".obsidian" / "plugins" / "aptuni").exists()
    assert not (displaced / ".obsidian" / "plugins" / "aptuni").exists()
