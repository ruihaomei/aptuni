"""One confirmation for the whole first-run setup, including an optional plugin grant.

``setup plan --plugin-manifest`` shows the plugin consent inside the setup plan. The single typed
APPLY then creates the grant exactly as shown, bound to the manifest digest frozen in the plan, and
``setup cancel`` revokes it with everything else the setup created.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from aptuni.api.v1 import load_manifest
from aptuni.api.v1.grants import PluginGrantManager
from aptuni.application.service import AptuniService
from aptuni.application.setup import cancel_setup_plan
from aptuni.application.workspace import Workspace
from aptuni.cli.main import run
from aptuni.cli.setup_apply import apply_setup_plan

ROOT = Path(__file__).parents[2]
MANIFEST = ROOT / "examples" / "plugins" / "top_down_learning" / "src" / "top_down_learning" / "aptuni-plugin.toml"


def _service(tmp_path: Path) -> AptuniService:
    return AptuniService(Workspace(tmp_path / "state"))


def _argv(tmp_path: Path, manifest: Path, *extra: str, locale: str = "en") -> list[str]:
    return ["setup", "plan", "--lang", locale, "--source", "other", "--memory", "basic", "--privacy", "quality",
            "--host", "claude_code", "--vault", str(tmp_path / "Aptuni"), "--plugin-manifest", str(manifest), *extra]


def _plan(service: AptuniService, tmp_path: Path, capsys: pytest.CaptureFixture[str], manifest: Path = MANIFEST,
          *extra: str) -> dict:
    assert run([*_argv(tmp_path, manifest, *extra), "--json"], service) == 0
    return json.loads(capsys.readouterr().out)


def _grants(service: AptuniService) -> list:
    return list(PluginGrantManager(service.workspace).list_grants())


def test_plan_shows_the_plugin_consent_and_creates_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    service = _service(tmp_path)
    assert run(_argv(tmp_path, MANIFEST), service) == 0
    out = capsys.readouterr().out

    assert '"Top-Down Learning" (dev.aptuni.top_down_learning' in out
    assert "✓ Knowledge" in out and "saved in your Vault as a pending item" in out
    assert "Declared network use:" in out
    assert "approve the plugin grant shown below" in out
    assert "--plugin-capability" in out, "the narrowing hint names the setup flag"
    assert "Top-Down Learning" in out.split("Typing APPLY lets an agent read")[1].split("\n\n")[0], \
        "the release section names the plugin whose reads reach the host operator"
    assert "nothing leaves this device" not in out
    assert not (tmp_path / "Aptuni").exists() and _grants(service) == []


def test_chinese_plan_shows_the_plugin_consent(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    service = _service(tmp_path)
    assert run(_argv(tmp_path, MANIFEST, locale="zh-CN"), service) == 0
    out = capsys.readouterr().out
    assert "请求访问你的 Aptuni 个人上下文" in out and "批准下面显示的插件授权" in out


def test_one_apply_creates_exactly_the_shown_grant(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    service = _service(tmp_path)
    plan = _plan(service, tmp_path, capsys)

    report = apply_setup_plan(service, plan["action_id"], plan["digest"])

    assert report.terminal_state == "complete"
    (grant,) = _grants(service)
    manifest = load_manifest(MANIFEST)
    assert grant.manifest_digest == manifest.digest()
    assert grant.capabilities == ("context.read", "memory.propose")
    assert grant.modules == tuple(manifest.modules)
    assert grant.grant_id in report.plugin_grants


def test_plugin_capability_can_withhold_the_optional_permission(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    service = _service(tmp_path)
    plan = _plan(service, tmp_path, capsys, MANIFEST, "--plugin-capability", "context.read")
    apply_setup_plan(service, plan["action_id"], plan["digest"])
    (grant,) = _grants(service)
    assert grant.capabilities == ("context.read",)


def test_a_manifest_changed_after_planning_is_refused(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    copy = tmp_path / "plugin" / "aptuni-plugin.toml"
    copy.parent.mkdir()
    shutil.copy(MANIFEST, copy)
    service = _service(tmp_path)
    plan = _plan(service, tmp_path, capsys, copy)
    copy.write_text(copy.read_text(encoding="utf-8").replace('"skills", ', ""), encoding="utf-8")

    report = apply_setup_plan(service, plan["action_id"], plan["digest"])

    assert report.terminal_state == "incomplete_resumable"
    assert report.failure == "plugin_manifest_changed"
    assert _grants(service) == []


def test_cancel_revokes_the_plugin_grant(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    service = _service(tmp_path)
    plan = _plan(service, tmp_path, capsys)
    apply_setup_plan(service, plan["action_id"], plan["digest"])
    assert _grants(service)

    assert run(["setup", "cancel", plan["action_id"], "--lang", "en"], service) == 0

    assert _grants(service) == []


def test_a_crash_after_the_grant_is_written_is_still_rolled_back(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    plan = _plan(service, tmp_path, capsys)
    real_apply = PluginGrantManager.apply

    def crash_after_write(self: PluginGrantManager, action_id: str):  # type: ignore[no-untyped-def]
        real_apply(self, action_id)
        raise OSError("simulated crash")

    monkeypatch.setattr(PluginGrantManager, "apply", crash_after_write)
    report = apply_setup_plan(service, plan["action_id"], plan["digest"])
    assert report.terminal_state == "incomplete_resumable" and len(_grants(service)) == 1

    was_confirmed, rollback = cancel_setup_plan(service.workspace.state_dir, plan["action_id"])
    assert was_confirmed and "plugin:" + _grants(service)[0].grant_id in rollback


def test_a_manifest_that_declares_egress_is_refused_at_plan_time(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    copy = tmp_path / "egress.toml"
    copy.write_text(MANIFEST.read_text(encoding="utf-8").replace('egress = ["none"]', 'egress = ["cloud_api"]'),
                    encoding="utf-8")
    service = _service(tmp_path)
    assert run(_argv(tmp_path, copy), service) == 2
    assert "egress" in capsys.readouterr().err


@pytest.mark.parametrize("privacy_args", [
    ("--privacy", "local_only", "--no-host"),
    ("--privacy", "quality", "--no-host"),
    ("--privacy", "local_only", "--host", "claude_code"),
])
def test_a_plugin_grant_is_refused_when_no_agent_may_receive_context(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], privacy_args: tuple[str, ...],
) -> None:
    service = _service(tmp_path)
    argv = ["setup", "plan", "--lang", "en", "--source", "other", "--memory", "basic", *privacy_args,
            "--vault", str(tmp_path / "Aptuni"), "--plugin-manifest", str(MANIFEST)]
    assert run(argv, service) == 2
    assert "runs inside Claude Code or Codex" in capsys.readouterr().err
    assert _grants(service) == []


def test_a_missing_manifest_at_apply_fails_cleanly(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    copy = tmp_path / "plugin" / "aptuni-plugin.toml"
    copy.parent.mkdir()
    shutil.copy(MANIFEST, copy)
    service = _service(tmp_path)
    plan = _plan(service, tmp_path, capsys, copy)
    copy.unlink()

    report = apply_setup_plan(service, plan["action_id"], plan["digest"])

    assert report.failure == "plugin_manifest_changed" and _grants(service) == []


def test_a_resumed_apply_reuses_the_claimed_grant(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    plan = _plan(service, tmp_path, capsys)
    real_apply = PluginGrantManager.apply
    calls = {"n": 0}

    def crash_once(self: PluginGrantManager, action_id: str):  # type: ignore[no-untyped-def]
        grant = real_apply(self, action_id)
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("simulated crash")
        return grant

    monkeypatch.setattr(PluginGrantManager, "apply", crash_once)
    apply_setup_plan(service, plan["action_id"], plan["digest"])
    report = apply_setup_plan(service, plan["action_id"], plan["digest"])

    assert report.terminal_state == "complete"
    (grant,) = _grants(service)
    assert report.plugin_grants == [grant.grant_id]
    assert calls["n"] == 1, "the claimed grant is reused, not created again"


def test_apply_refuses_a_plugin_grant_without_agent_access_even_in_a_crafted_plan(tmp_path: Path) -> None:
    from aptuni.advisor import load_catalog
    from aptuni.application.setup import SetupStep, create_setup_plan
    from aptuni.cli.setup_commands import _plugin_target

    service = _service(tmp_path)
    catalog = load_catalog()
    from aptuni.advisor import SetupAnswers, recommend
    rec = recommend(SetupAnswers("en", frozenset(), "basic", "local_only", frozenset()), catalog)
    steps = (SetupStep("vault", str(tmp_path / "Aptuni")), SetupStep("plugin_grant", _plugin_target(MANIFEST, None)),
             SetupStep("doctor", "vault"), SetupStep("smoke", "context"))
    plan = create_setup_plan(
        service.workspace.state_dir, catalog_digest=catalog.version_digest(), locale="en",
        answers={"sources": [], "memory": "basic", "privacy": "local_only", "hosts": []},
        recommendation_digest=rec.digest, recipe_id=rec.recipe_id, vault_path=tmp_path / "Aptuni",
        modules=("knowledge",), host_files=(), egress=(), bundle_root=tmp_path / "bundles", steps=steps,
    )

    report = apply_setup_plan(service, plan.action_id, plan.digest)

    assert report.failure == "setup_plugin_without_host" and _grants(service) == []


def test_release_line_says_the_plugin_reaches_any_agent_that_runs_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    service = _service(tmp_path)
    assert run(_argv(tmp_path, MANIFEST), service) == 0
    assert "In addition, the plugin" in capsys.readouterr().out
