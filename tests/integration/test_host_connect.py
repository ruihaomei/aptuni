"""Connecting Claude Code or Codex after setup (Beta dogfooding, 2026-09-28).

After the grant and bundle exist, a new user must be told the exact commands that make the host use
them, derived from the real bundle, and that Aptuni stays OFF until a Profile/Memory/Full skill is
invoked. Catalog copy must not promise automatic context.
"""

from __future__ import annotations

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

    assert f"claude --plugin-dir {shlex.quote(str(bundle))}" in out
    assert "/aptuni:profile" in out and "/aptuni:full" in out
    assert "OFF" in out


def test_codex_adapter_apply_prints_skill_copy_and_mcp_registration_from_the_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    out, bundle = _adapter(_service(tmp_path), "codex", monkeypatch, capsys)
    grant_id = bundle.name

    assert f"cp -R {shlex.quote(str(bundle / '.agents' / 'skills'))}/. .agents/skills/" in out
    assert "codex mcp add aptuni -- " in out
    assert f"-m aptuni.mcp.server --activation-required --grant {grant_id}" in out
    assert "$aptuni-profile" in out


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
