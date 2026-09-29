"""``aptuni status`` speaks the owner's language like every other command (Beta Day 0, 2026-09-29).

The Agent guide asks the Agent to run ``aptuni status`` first; it rejected ``--lang`` and answered
only in English. The JSON output is a contract and does not change.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace
from aptuni.cli.main import run


@pytest.fixture
def service(tmp_path: Path) -> AptuniService:
    service = AptuniService(Workspace(tmp_path / "state"))
    service.init(tmp_path / "Vault")
    return service


def test_status_accepts_lang_and_answers_in_chinese(service: AptuniService, capsys: pytest.CaptureFixture[str]) -> None:
    assert run(["status", "--lang", "zh-CN"], service) == 0
    out = capsys.readouterr().out
    assert "你的 Vault：" in out and "对智能体隐藏：无" in out


def test_status_follows_aptuni_lang(
    service: AptuniService, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APTUNI_LANG", "zh-CN")
    assert run(["status"], service) == 0
    assert "你的 Vault：" in capsys.readouterr().out


def test_status_stays_english_by_default_and_json_is_unchanged(
    service: AptuniService, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("APTUNI_LANG", raising=False)
    assert run(["status"], service) == 0
    assert "Vault: " in capsys.readouterr().out
    assert run(["status", "--json", "--lang", "zh-CN"], service) == 0
    value = json.loads(capsys.readouterr().out)
    assert set(value) == {"vault", "state_dir", "seq", "policy_epoch", "counts", "modules", "review"}
