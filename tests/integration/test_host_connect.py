"""Connecting Claude Code or Codex after setup (Beta dogfooding, 2026-09-28).

After the grant and bundle exist, a new user must be told the exact commands that make the host use
them, derived from the real bundle, and that Aptuni stays OFF until a Profile/Memory/Full skill is
invoked. Catalog copy must not promise automatic context.
"""

from __future__ import annotations

import json
import shlex
from pathlib import Path

import pytest

from aptuni.adapters.manager import AdapterManager
from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace
from aptuni.cli.main import run
from aptuni.i18n import message_keys, t

MODULES = ("identity", "knowledge", "preferences")


def _service(tmp_path: Path) -> AptuniService:
    service = AptuniService(Workspace(tmp_path / "state"))
    service.init(tmp_path / "vault")
    return service


def _adapter(service: AptuniService, host: str, monkeypatch: pytest.MonkeyPatch,
             capsys: pytest.CaptureFixture[str], locale: str = "en") -> tuple[str, Path]:
    manager = AdapterManager(service.workspace)
    plan = manager.plan(host, MODULES, allow_host_model_egress=True)
    capsys.readouterr()
    monkeypatch.setattr("builtins.input", lambda *args: "APPLY")
    monkeypatch.setenv("APTUNI_LANG", locale)
    assert run(["adapter", "apply", plan.action_id], service) == 0
    out = capsys.readouterr().out
    bundle = next((service.workspace.state_dir / "adapters" / "bundles").iterdir())
    return out, bundle


def test_claude_adapter_apply_prints_the_exact_command_and_off_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    out, bundle = _adapter(_service(tmp_path), "claude", monkeypatch, capsys)

    assert f"claude plugin marketplace add {shlex.quote(str(bundle))}" in out
    assert "claude plugin install aptuni@aptuni-local" in out
    assert f"claude --plugin-dir {shlex.quote(str(bundle))}" in out, "one-session alternative"
    assert "/aptuni:profile" in out and "/aptuni:full" in out
    assert "OFF" in out
    marketplace = json.loads((bundle / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    assert marketplace["name"] == "aptuni-local"
    assert marketplace["plugins"] == [{"name": "aptuni", "source": "./"}]


def test_codex_adapter_apply_prints_skill_copy_and_mcp_registration_from_the_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    out, bundle = _adapter(_service(tmp_path), "codex", monkeypatch, capsys)
    grant_id = bundle.name

    assert f"cp -R {shlex.quote(str(bundle / '.agents' / 'skills'))}/. .agents/skills/" in out
    assert "codex mcp add aptuni -- " in out
    assert f"-m aptuni.mcp.server --activation-required --grant {grant_id}" in out
    assert "$aptuni-profile" in out
    assert "all your Codex projects" in out


def test_codex_registration_forwards_a_custom_state_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("APTUNI_STATE_DIR", str(tmp_path / "state"))
    out, _ = _adapter(_service(tmp_path), "codex", monkeypatch, capsys)
    assert f"--env APTUNI_STATE_DIR={shlex.quote(str(tmp_path / 'state'))}" in out


def test_connect_instructions_are_in_chinese_with_commands_kept_in_english(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    out, bundle = _adapter(_service(tmp_path), "claude", monkeypatch, capsys, locale="zh-CN")
    assert "连接 Claude Code" in out and "默认关闭" in out
    assert f"claude --plugin-dir {shlex.quote(str(bundle))}" in out


def test_agent_catalog_copy_does_not_promise_automatic_context() -> None:
    for locale in ("en", "zh-CN"):
        text = " ".join(t(key, locale) for key in message_keys(locale) if key.startswith("plugin.agent."))
        for claim in ("without you asking", "at session start", "无需你开口", "会话开始时", "主动获取"):
            assert claim not in text, (locale, claim)


def test_connect_reprints_the_commands_for_the_current_grant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    service = _service(tmp_path)
    _, bundle = _adapter(service, "claude", monkeypatch, capsys)

    assert run(["connect", "claude", "--lang", "en"], service) == 0

    assert f"claude plugin marketplace add {shlex.quote(str(bundle))}" in capsys.readouterr().out


def test_connect_without_a_grant_says_how_to_create_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    assert run(["connect", "codex", "--lang", "zh-CN"], _service(tmp_path)) == 1
    err = capsys.readouterr().err
    assert "aptuni setup plan" in err and "Codex" in err


def test_agent_guide_keeps_apply_with_the_owner_and_uses_product_language() -> None:
    for locale, source_line in (("en", "GitHub — let Aptuni understand the projects you have actually worked on"),
                                ("zh-CN", "GitHub：让 Aptuni 了解你真实参与的项目和开发经历")):
        from aptuni.cli.guide_cli import agent_guide

        text = agent_guide(locale)
        assert source_line in text
        assert "Never type APPLY" in text
        assert "aptuni setup apply" in text and "--plugin-manifest" in text
        assert "aptuni connect claude" in text and "aptuni connect codex" in text
        assert "claude plugin marketplace add ruihaomei/aptuni" in text
        assert "codex plugin marketplace add ruihaomei/aptuni" in text
        assert "aptuni attach" in text
