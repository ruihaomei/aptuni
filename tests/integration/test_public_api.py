from __future__ import annotations

import inspect
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path

import pytest

import aptuni.api.v1 as public_api
import aptuni.api.v1.grants as grants_module
from aptuni.api.v1 import AptuniAPIError, PluginManifest, connect
from aptuni.api.v1.grants import PluginGrantManager
from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace
from aptuni.cli.main import run


def _manifest(**updates: object) -> PluginManifest:
    value: dict[str, object] = {
        "schema_version": 1,
        "contract": "aptuni.plugin@1",
        "id": "dev.example.learning",
        "name": "Learning",
        "version": "1.2.3",
        "api_version": "v1",
        "entry_point": "learning.plugin:create_plugin",
        "capabilities": (
            "profile.read", "memory.read", "context.read", "evidence.read", "memory.propose", "memory.review.read",
        ),
        "modules": ("identity", "knowledge", "skills", "goals", "preferences", "projects"),
        "egress": ("none",),
        "retention": "canonical_proposals",
    }
    value.update(updates)
    return PluginManifest.model_validate(value)


def _ready(tmp_path: Path) -> tuple[Workspace, AptuniService]:
    workspace = Workspace(tmp_path / "state")
    service = AptuniService(workspace)
    service.init(tmp_path / "vault")
    service.remember("Build an intelligent parking system", "goals")
    service.remember("Has practical Python experience", "skills")
    service.remember("Prefers concise project-first explanations", "preferences")
    service.remember("Private identity marker", "identity")
    return workspace, service


def _client(tmp_path: Path, manifest: PluginManifest, *, capabilities: tuple[str, ...] | None = None,
            modules: tuple[str, ...] | None = None):
    workspace, _ = _ready(tmp_path)
    manager = PluginGrantManager(workspace)
    plan = manager.plan(manifest, capabilities=capabilities, modules=modules)
    grant = manager.apply(plan.action_id)
    return connect(manifest, grant.grant_id, workspace=workspace)


def test_public_reads_are_versioned_bounded_and_provenance_aware(tmp_path: Path) -> None:
    api = _client(tmp_path, _manifest())
    profile = api.get_profile(max_units=700)
    assert profile.contract == "aptuni.api@1"
    assert profile.vault_seq >= 1 and profile.policy_epoch >= 0
    assert any(item.text == "Private identity marker" for item in profile.items)

    context = api.query_context(
        "parking Python project", modules=("goals", "skills", "preferences"), max_units=3000,
    )
    assert context.contract == "aptuni.api@1"
    assert {item.module for item in context.items if item.canonical_id} <= {"goals", "skills", "preferences"}
    assert all(item.source_id is None for item in context.items if item.canonical_id)
    assert all(item.trust == "user_declared" for item in context.items if item.canonical_id)


def test_grant_narrows_manifest_and_denies_drift_or_extra_modules(tmp_path: Path) -> None:
    workspace, _ = _ready(tmp_path)
    declared = _manifest()
    manager = PluginGrantManager(workspace)
    plan = manager.plan(declared, capabilities=("context.read",), modules=("skills",))
    grant = manager.apply(plan.action_id)
    api = connect(declared, grant.grant_id, workspace=workspace)
    with pytest.raises(AptuniAPIError) as denied:
        api.get_profile()
    assert denied.value.code == "plugin_capability_denied"
    with pytest.raises(AptuniAPIError) as module_denied:
        api.query_context("parking", modules=("goals",))
    assert module_denied.value.code == "plugin_module_denied"
    with pytest.raises(AptuniAPIError) as drifted:
        connect(declared.model_copy(update={"version": "1.2.4"}), grant.grant_id, workspace=workspace)
    assert drifted.value.code == "plugin_manifest_drift"
    with pytest.raises(AptuniAPIError) as empty_capabilities:
        manager.plan(declared, capabilities=(), modules=("skills",))
    assert empty_capabilities.value.code == "plugin_capability_invalid"
    with pytest.raises(AptuniAPIError) as empty_modules:
        manager.plan(declared, capabilities=("context.read",), modules=())
    assert empty_modules.value.code == "plugin_module_invalid"


def test_memory_submission_is_quarantined_idempotent_and_review_decisions_are_absent(tmp_path: Path) -> None:
    api = _client(tmp_path, _manifest(), capabilities=("memory.propose",), modules=("knowledge",))
    first = api.propose_memory(
        "Needs more practice explaining intersection over union", module="knowledge", idempotency_key="iou-gap",
    )
    second = api.propose_memory(
        "Needs more practice explaining intersection over union", module="knowledge", idempotency_key="iou-gap",
    )
    assert first.contract == "aptuni.api@1" and first.status == "pending_owner_review"
    assert first.candidate_id == second.candidate_id and first.created and not second.created
    for forbidden in ("accept_memory", "reject_memory", "pin_memory", "forget_memory", "remember_fact"):
        assert not hasattr(api, forbidden)


def test_memory_read_is_narrower_than_general_context(tmp_path: Path) -> None:
    workspace, service = _ready(tmp_path)
    service.observe("Practiced homography calibration", "knowledge")
    service.remember("Intelligent parking system architecture note", "knowledge")
    manifest = _manifest()
    manager = PluginGrantManager(workspace)
    grant = manager.apply(manager.plan(
        manifest, capabilities=("memory.read",), modules=("knowledge",),
    ).action_id)
    api = connect(manifest, grant.grant_id, workspace=workspace)
    result = api.search_memories("homography", modules=("knowledge",))
    assert result.items and {item.kind for item in result.items} == {"memory"}
    with pytest.raises(AptuniAPIError) as denied:
        api.query_context("homography", modules=("knowledge",))
    assert denied.value.code == "plugin_capability_denied"

    fact_only = api.search_memories("intelligent parking system", modules=("knowledge",))
    miss = api.search_memories("zzzz-unmatched", modules=("knowledge",))
    assert not fact_only.items and fact_only.layers == miss.layers
    assert fact_only.used_units == miss.used_units


def test_external_egress_manifest_cannot_be_activated_in_v1(tmp_path: Path) -> None:
    workspace, _ = _ready(tmp_path)
    manager = PluginGrantManager(workspace)
    with pytest.raises(AptuniAPIError) as denied:
        manager.plan(_manifest(egress=("cloud_api",)))
    assert denied.value.code == "plugin_egress_unsupported"


def test_public_namespace_cannot_construct_ungranted_clients() -> None:
    assert not hasattr(public_api, "PluginGrant")
    assert not hasattr(public_api, "PluginGrantManager")
    assert not hasattr(public_api, "PluginGrantPlan")
    assert "_token" in inspect.signature(public_api.AptuniAPI).parameters


def test_grant_integrity_revocation_and_path_confinement(tmp_path: Path) -> None:
    workspace, _ = _ready(tmp_path)
    manifest = _manifest()
    manager = PluginGrantManager(workspace)
    plan = manager.plan(manifest, capabilities=("context.read",), modules=("goals",))
    plan_path = manager.root / "pending" / f"{plan.action_id}.json"
    tampered_plan = json.loads(plan_path.read_text(encoding="utf-8"))
    tampered_plan["modules"] = ["identity"]
    plan_path.write_text(json.dumps(tampered_plan), encoding="utf-8")
    with pytest.raises(AptuniAPIError) as forged_plan:
        manager.pending(plan.action_id)
    assert forged_plan.value.code == "plugin_action_not_found"
    manager.cancel(plan.action_id)
    plan = manager.plan(manifest, capabilities=("context.read",), modules=("goals",))
    grant = manager.apply(plan.action_id)
    assert not (manager.root / "pending" / f"{plan.action_id}.json").exists()
    api = connect(manifest, grant.grant_id, workspace=workspace)
    assert api.query_context("parking", modules=("goals",)).items

    grant_path = manager.root / "grants" / f"{grant.grant_id}.json"
    tampered = json.loads(grant_path.read_text(encoding="utf-8"))
    tampered["capabilities"] = ["profile.read"]
    grant_path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(AptuniAPIError) as forged:
        manager.load(grant.grant_id)
    assert forged.value.code == "plugin_grant_not_found"

    grant_path.write_text(grant.model_dump_json(), encoding="utf-8")
    assert manager.revoke(grant.grant_id)
    with pytest.raises(AptuniAPIError) as revoked:
        api.query_context("parking", modules=("goals",))
    assert revoked.value.code == "plugin_grant_not_found"

    unsafe_workspace = Workspace(tmp_path / "unsafe-state")
    unsafe_workspace.state_dir.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (unsafe_workspace.state_dir / "developer").symlink_to(outside, target_is_directory=True)
    with pytest.raises(AptuniAPIError) as unsafe:
        PluginGrantManager(unsafe_workspace).plan(manifest)
    assert unsafe.value.code == "plugin_grant_unsafe" and not list(outside.iterdir())


def test_one_preview_has_one_crash_idempotent_grant_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, _ = _ready(tmp_path)
    manager = PluginGrantManager(workspace)
    plan = manager.plan(_manifest(), capabilities=("context.read",), modules=("goals",))
    with ThreadPoolExecutor(max_workers=2) as pool:
        grants = tuple(pool.map(manager.apply, (plan.action_id, plan.action_id)))
    assert grants[0] == grants[1]
    assert [path.name for path in (manager.root / "grants").glob("grant-*.json")] == [
        f"{grants[0].grant_id}.json",
    ]

    second = manager.plan(_manifest(), capabilities=("context.read",), modules=("skills",))
    original_unlink = manager._unlink
    failed = False

    def fail_after_publish(folder: str, name: str) -> bool:
        nonlocal failed
        if folder == "pending" and not failed:
            failed = True
            raise RuntimeError("injected crash after grant publication")
        return original_unlink(folder, name)

    monkeypatch.setattr(manager, "_unlink", fail_after_publish)
    with pytest.raises(RuntimeError, match="injected crash"):
        manager.apply(second.action_id)
    monkeypatch.setattr(manager, "_unlink", original_unlink)
    recovered = manager.apply(second.action_id)
    assert recovered.grant_id == "grant-" + second.action_id.removeprefix("act-")
    assert not (manager.root / "pending" / f"{second.action_id}.json").exists()

    cancelled_plan = manager.plan(_manifest(), capabilities=("context.read",), modules=("preferences",))
    failed = False
    monkeypatch.setattr(manager, "_unlink", fail_after_publish)
    with pytest.raises(RuntimeError, match="injected crash"):
        manager.apply(cancelled_plan.action_id)
    monkeypatch.setattr(manager, "_unlink", original_unlink)
    cancelled_grant = "grant-" + cancelled_plan.action_id.removeprefix("act-")
    assert manager.cancel(cancelled_plan.action_id)
    assert not (manager.root / "grants" / f"{cancelled_grant}.json").exists()

    expiring_plan = manager.plan(_manifest(), capabilities=("context.read",), modules=("knowledge",))
    failed = False
    monkeypatch.setattr(manager, "_unlink", fail_after_publish)
    with pytest.raises(RuntimeError, match="injected crash"):
        manager.apply(expiring_plan.action_id)
    monkeypatch.setattr(manager, "_unlink", original_unlink)

    class ExpiredClock(datetime):
        @classmethod
        def now(cls, tz: object = None) -> datetime:
            return expiring_plan.expires_at + timedelta(seconds=1)

    monkeypatch.setattr(grants_module, "datetime", ExpiredClock)
    recovered_after_expiry = manager.apply(expiring_plan.action_id)
    assert recovered_after_expiry.grant_id == "grant-" + expiring_plan.action_id.removeprefix("act-")


def test_completed_revoke_serializes_with_in_flight_operations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace, _ = _ready(tmp_path)
    manifest = _manifest()
    manager = PluginGrantManager(workspace)
    grant = manager.apply(manager.plan(
        manifest, capabilities=("context.read",), modules=("goals",),
    ).action_id)
    api = connect(manifest, grant.grant_id, workspace=workspace)
    entered = threading.Event()
    release = threading.Event()
    revoke_started = threading.Event()
    original_context = api._service.context

    def paused_context(*args: object, **kwargs: object):
        entered.set()
        assert release.wait(timeout=5)
        return original_context(*args, **kwargs)  # type: ignore[arg-type]

    def revoke() -> bool:
        revoke_started.set()
        return manager.revoke(grant.grant_id)

    monkeypatch.setattr(api._service, "context", paused_context)
    with ThreadPoolExecutor(max_workers=2) as pool:
        read = pool.submit(api.query_context, "parking", modules=("goals",))
        assert entered.wait(timeout=5)
        removal = pool.submit(revoke)
        assert revoke_started.wait(timeout=5) and not removal.done()
        release.set()
        assert read.result(timeout=5).items
        assert removal.result(timeout=5)
    with pytest.raises(AptuniAPIError) as revoked:
        api.query_context("parking", modules=("goals",))
    assert revoked.value.code == "plugin_grant_not_found"


def test_manifest_commands_and_connect_never_import_entry_point(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, _ = _ready(tmp_path)
    manifest = _manifest(entry_point="sentinel.plugin:create_plugin")
    original_import = __import__

    def guarded_import(name: str, *args: object, **kwargs: object):
        if name.startswith("sentinel"):
            raise AssertionError("entry point imported")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", guarded_import)
    manager = PluginGrantManager(workspace)
    grant = manager.apply(manager.plan(manifest).action_id)
    connect(manifest, grant.grant_id, workspace=workspace)


def test_developer_cli_scaffolds_inspects_and_owner_confirms_a_narrow_grant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    workspace, service = _ready(tmp_path)
    target = tmp_path / "coach"
    assert run([
        "developer", "scaffold", str(target), "--id", "dev.example.coach", "--name", "Coach", "--json",
    ], service) == 0
    scaffold = json.loads(capsys.readouterr().out)
    assert scaffold["contract"] == "aptuni.developer@1" and len(scaffold["files"]) == 6
    manifest_path = target / "aptuni-plugin.toml"
    assert run(["developer", "inspect", str(manifest_path), "--json"], service) == 0
    assert json.loads(capsys.readouterr().out)["id"] == "dev.example.coach"
    assert run([
        "developer", "grant", "plan", str(manifest_path), "--capability", "context.read",
        "--module", "knowledge", "--json",
    ], service) == 0
    action_id = json.loads(capsys.readouterr().out)["action_id"]
    monkeypatch.setattr("builtins.input", lambda *args: "APPLY")
    assert run(["developer", "grant", "apply", action_id, "--json"], service) == 0
    grant_id = json.loads(capsys.readouterr().out)["grant_id"]
    assert PluginGrantManager(workspace).load(grant_id).capabilities == ("context.read",)
    assert run(["developer", "grant", "list", "--json"], service) == 0
    assert json.loads(capsys.readouterr().out)["grants"][0]["grant_id"] == grant_id
    assert run(["developer", "grant", "revoke", grant_id, "--json"], service) == 0
    assert json.loads(capsys.readouterr().out)["revoked"] is True
    assert run([
        "developer", "grant", "plan", str(manifest_path), "--capability", "context.read",
        "--module", "knowledge", "--json",
    ], service) == 0
    pending_id = json.loads(capsys.readouterr().out)["action_id"]
    assert run(["developer", "grant", "cancel", pending_id, "--json"], service) == 0
    assert json.loads(capsys.readouterr().out)["cancelled"] is True
