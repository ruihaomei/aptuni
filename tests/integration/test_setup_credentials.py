"""A plan that needs a credential says so, and it does not expire mid-journey (Beta Day 0, 2026-09-29).

User #1 approved private repositories with ``--github-token-env``; the plan never said the variable
had to be set before APPLY, and its 30-minute expiry ran out while the owner created a token. A
resumed, already-confirmed setup also kept warning that it "expires", although it no longer does.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aptuni.application import setup as setup_api
from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace
from aptuni.cli.main import run

REPO = "https://github.com/ruihaomei/private-notes"


def _argv(tmp_path: Path, locale: str, *extra: str) -> list[str]:
    return ["setup", "plan", "--lang", locale, "--source", "github", "--github", REPO, *extra,
            "--memory", "basic", "--privacy", "quality", "--host", "claude_code", "--vault", str(tmp_path / "Aptuni")]


@pytest.mark.parametrize(("locale", "line"), [
    ("en", "Before you type APPLY, set APTUNI_GITHUB_TOKEN in that same terminal"),
    ("zh-CN", "输入 APPLY 之前，请先在同一个终端里设置 APTUNI_GITHUB_TOKEN"),
])
def test_a_plan_that_reads_a_token_says_to_set_it_before_apply(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], locale: str, line: str,
) -> None:
    service = AptuniService(Workspace(tmp_path / "state"))

    assert run(_argv(tmp_path, locale, "--github-token-env", "APTUNI_GITHUB_TOKEN"), service) == 0

    assert line in capsys.readouterr().out


def test_a_plan_without_a_token_does_not_mention_one(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert run(_argv(tmp_path, "en"), AptuniService(Workspace(tmp_path / "state"))) == 0
    assert "Before you type APPLY, set" not in capsys.readouterr().out


def test_a_plan_stays_valid_long_enough_to_create_a_token() -> None:
    assert setup_api.timedelta(hours=24) <= setup_api.SETUP_TTL


def test_a_confirmed_setup_does_not_claim_it_expires(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = AptuniService(Workspace(tmp_path / "state"))
    run([*_argv(tmp_path, "en"), "--json"], service)
    plan = json.loads(capsys.readouterr().out)
    setup_api.commit_setup_intent(service.workspace.state_dir, plan["action_id"], plan["digest"])
    monkeypatch.setattr("builtins.input", lambda *args: "no")

    run(["setup", "apply", plan["action_id"]], service)

    out = capsys.readouterr().out
    assert "This plan expires at" not in out
    assert "Already confirmed: resuming does not expire" in out
