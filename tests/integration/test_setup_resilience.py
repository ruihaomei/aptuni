"""One failing source no longer stops first-run setup (Beta Day 0, 2026-09-29).

User #1's setup approved sixteen sources; one repository failed to sync and the whole setup stopped
before agent access or the plugin grant was written, with no progress shown for minutes. A source
that fails to sync is now reported with its reason and an exact retry command, the rest of the setup
completes, and every step prints progress while it runs.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from aptuni.application.service import AptuniService
from aptuni.application.source_commands import SourceCommands
from aptuni.application.workspace import Workspace
from aptuni.cli.main import run
from aptuni.cli.setup_apply import apply_setup_plan
from aptuni.sources.github import GitHubApiError, GitHubSourceSpec, GitHubTree

GOOD = "https://github.com/ruihaomei/good"
BAD = "https://github.com/ruihaomei/bad"


class Repo:
    def __init__(self, spec: GitHubSourceSpec) -> None:
        self.spec = spec
        self.body = b"# Project\nOverview."

    def fetch_tree(self) -> GitHubTree:
        if self.spec.repository == "bad":
            raise GitHubApiError("github_credential_unavailable")
        sha = hashlib.sha1(f"blob {len(self.body)}\0".encode() + self.body, usedforsecurity=False).hexdigest()
        return GitHubTree({"repository_id": 5, "full_name": "ruihaomei/good", "commit": "1" * 40,
                           "truncated": False, "tree": [{"path": "README.md", "type": "blob", "sha": sha,
                                                         "size": len(self.body)}]}, "main", ())

    def fetch_blob(self, _sha: str) -> bytes:
        return self.body


@pytest.fixture
def service(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AptuniService:
    monkeypatch.setattr(SourceCommands, "_github_client", staticmethod(Repo))
    return AptuniService(Workspace(tmp_path / "state"))


def _plan(service: AptuniService, tmp_path: Path, capsys: pytest.CaptureFixture[str], locale: str = "en") -> dict:
    argv = ["setup", "plan", "--lang", locale, "--source", "github", "--github", GOOD, "--github", BAD,
            "--memory", "basic", "--privacy", "quality", "--host", "claude_code",
            "--vault", str(tmp_path / "Aptuni"), "--json"]
    assert run(argv, service) == 0
    return json.loads(capsys.readouterr().out)


def test_a_failing_source_is_reported_and_agent_access_is_still_written(
    service: AptuniService, tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    plan = _plan(service, tmp_path, capsys)

    report = apply_setup_plan(service, plan["action_id"], plan["digest"])

    assert report.terminal_state == "complete"
    assert report.grants, "agent access is written even though one source failed"
    bad = next(source.id for source in service.sources() if source.roots[0].endswith("/bad"))
    assert report.source_failures == {bad: "github_credential_unavailable"}, "the concrete reason is kept"
    good = next(source.id for source in service.sources() if source.roots[0].endswith("/good"))
    assert [item.subject for item in service.evidence(good)] == ["README.md"]


def test_the_report_names_the_failed_source_its_reason_and_the_retry_command(
    service: AptuniService, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _plan(service, tmp_path, capsys, locale="zh-CN")
    monkeypatch.setattr("builtins.input", lambda *args: "APPLY")

    assert run(["setup", "apply", plan["action_id"]], service) == 0

    out = capsys.readouterr().out
    bad = next(source.id for source in service.sources() if source.roots[0].endswith("/bad"))
    assert "暂未读取" in out and "https://github.com/ruihaomei/bad" in out
    assert "GitHub 凭证不可用" in out, "the concrete reason, not a generic retry code"
    assert f"aptuni sync {bad}" in out


def test_apply_prints_progress_for_each_step_and_each_source(
    service: AptuniService, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _plan(service, tmp_path, capsys)
    monkeypatch.setattr("builtins.input", lambda *args: "APPLY")

    run(["setup", "apply", plan["action_id"]], service)

    err = capsys.readouterr().err
    steps = len(plan["steps"])
    assert f"[1/{steps}]" in err and f"[{steps}/{steps}]" in err
    assert 'Reading "https://github.com/ruihaomei/good" (1/2)' in err
    assert 'Reading "https://github.com/ruihaomei/bad" (2/2)' in err, "untrusted names stay delimited"
