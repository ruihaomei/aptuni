"""Human-readable plugin grant consent (Beta finding P3).

The default ``developer grant plan`` / ``apply`` output is the consent surface a person reads before
typing APPLY. It must say, from the real plan, who asks, what it can read, what it may propose, that
it cannot write directly, that it has no egress, and how to revoke it. ``--json`` stays unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aptuni.api.v1.grants import PluginGrantManager
from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace
from aptuni.cli.main import run

MANIFEST = (Path(__file__).resolve().parents[2] / "examples" / "plugins" / "top_down_learning" / "src"
            / "top_down_learning" / "aptuni-plugin.toml")


def _service(tmp_path: Path) -> AptuniService:
    service = AptuniService(Workspace(tmp_path / "state"))
    service.init(tmp_path / "vault")
    return service


def _pending_id(service: AptuniService) -> str:
    return next((service.workspace.state_dir / "developer" / "pending").iterdir()).stem


def test_default_plan_is_a_readable_consent_screen_rendered_from_the_real_plan(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    service = _service(tmp_path)

    assert run(["developer", "grant", "plan", str(MANIFEST), "--lang", "en"], service) == 0

    out = capsys.readouterr().out
    action_id = _pending_id(service)
    assert not out.lstrip().startswith("{"), "the default output must not be raw JSON"
    assert "\\n" not in out
    assert '"Top-Down Learning" (dev.aptuni.top_down_learning 0.2.1) requests access' in out, "plugin text is delimited"
    assert "✓ Knowledge" in out and "✓ Skills" in out and "✓ Preferences" in out
    assert "✗ Identity" not in out, "only the modules in the plan are listed"
    assert "✓ Suggest new memories (optional)" in out
    assert "✗ None" in out
    assert "no network egress" in out.lower()
    assert f"aptuni developer grant revoke grant-{action_id.removeprefix('act-')}" in out
    assert f"aptuni developer grant apply {action_id}" in out


def test_withheld_optional_capability_is_shown_as_not_granted(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    service = _service(tmp_path)

    assert run(["developer", "grant", "plan", str(MANIFEST), "--capability", "context.read",
                "--lang", "en"], service) == 0

    out = capsys.readouterr().out
    assert "✗ Suggest new memories — not granted" in out
    assert "✓ Suggest new memories" not in out


def test_chinese_consent_screen_is_natural_and_keeps_commands_in_english(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    service = _service(tmp_path)

    assert run(["developer", "grant", "plan", str(MANIFEST), "--lang", "zh-CN"], service) == 0

    out = capsys.readouterr().out
    assert "请求访问" in out
    assert "✓ 知识" in out and "✓ 技能" in out and "✓ 偏好" in out
    assert "可以随时撤销" in out
    assert "aptuni developer grant revoke grant-" in out
    assert "APPLY" in out


def test_default_apply_shows_consent_then_a_readable_result(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    assert run(["developer", "grant", "plan", str(MANIFEST), "--json"], service) == 0
    action_id = json.loads(capsys.readouterr().out)["action_id"]
    monkeypatch.setattr("builtins.input", lambda *args: "APPLY")

    assert run(["developer", "grant", "apply", action_id, "--lang", "en"], service) == 0

    out = capsys.readouterr().out
    grant_id = "grant-" + action_id.removeprefix("act-")
    assert "dev.aptuni.top_down_learning 0.2.1 requests access" in out
    assert f"Approved. Grant ID: {grant_id}" in out
    assert f"aptuni developer grant revoke {grant_id}" in out
    assert not any(line.lstrip().startswith("{") for line in out.splitlines())
    assert PluginGrantManager(service.workspace).load(grant_id).capabilities == ("context.read", "memory.propose")


def test_json_plan_keeps_the_machine_contract(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    service = _service(tmp_path)
    assert run(["developer", "grant", "plan", str(MANIFEST), "--json"], service) == 0
    value = json.loads(capsys.readouterr().out)
    assert value["contract"] == "aptuni.plugin-grant-plan@1"
    assert "Required capabilities: context.read" in value["preview"]


def test_consent_is_truthful_that_suggestions_are_stored_as_pending_items(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    service = _service(tmp_path)

    assert run(["developer", "grant", "plan", str(MANIFEST), "--lang", "en"], service) == 0

    out = capsys.readouterr().out
    assert "saved in your Vault as a pending item" in out
    assert "becomes Memory only if you accept it" in out
    assert "stays in history until you purge it" in out
    assert "nothing is kept" not in out.lower()
    assert "It can change your existing Profile, Memory or sources:" in out
    assert "Declared network use:" in out and "cannot enforce" in out


def test_chinese_consent_is_truthful_about_stored_suggestions(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    service = _service(tmp_path)

    assert run(["developer", "grant", "plan", str(MANIFEST), "--lang", "zh-CN"], service) == 0

    out = capsys.readouterr().out
    assert "作为待审核项保存在你的 Vault 中" in out
    assert "接受后，它才会成为记忆" in out
    assert "不会保存" not in out
    assert "无法强制" in out
