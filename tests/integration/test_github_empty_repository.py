"""An empty GitHub repository syncs as zero files (Beta Day 0 P2, 2026-09-29).

GitHub answers ``409 Git Repository is empty`` for the commit of an empty repository. Setup reported
three of User #1's repositories as failed sources (``github_request_failed``) although nothing was
wrong with them. Only that exact answer means "empty"; any other 409 stays a failure.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

import pytest

from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService
from aptuni.application.source_commands import SourceCommands
from aptuni.application.workspace import Workspace
from aptuni.sources.github import GitHubApi, GitHubSourceSpec, HttpResult

URL = "https://github.com/ruihaomei/empty"
API = "https://api.github.com"
JSON = {"content-type": "application/json; charset=utf-8"}
REPO = {"id": 42, "full_name": "ruihaomei/empty", "default_branch": "main"}
EMPTY = {"message": "Git Repository is empty.", "documentation_url": "https://docs.github.com/rest",
         "status": "409"}


class EmptyRepositoryTransport:
    def __init__(self, conflict: dict[str, str] | None = None) -> None:
        self.conflict = EMPTY if conflict is None else conflict

    def get(self, url: str, headers: Mapping[str, str], max_bytes: int) -> HttpResult:
        path = url.removeprefix(API)
        if path == "/repos/ruihaomei/empty":
            return HttpResult(200, url, JSON, json.dumps(REPO).encode())
        if path.startswith("/repos/ruihaomei/empty/commits"):
            return HttpResult(409, url, JSON, json.dumps(self.conflict).encode())
        return HttpResult(404, url, JSON, b'{"message": "Not Found"}')


def _service(tmp_path: Path, transport: EmptyRepositoryTransport,
             monkeypatch: pytest.MonkeyPatch) -> tuple[AptuniService, str]:
    monkeypatch.setattr(SourceCommands, "_github_client",
                        staticmethod(lambda spec: GitHubApi(spec, transport)))
    service = AptuniService(Workspace(state_dir=tmp_path / "state"))
    service.init(tmp_path / "Aptuni")
    return service, service.add_github_source(URL, ("knowledge",), "repository").id


def test_an_empty_repository_syncs_as_zero_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service, source_id = _service(tmp_path, EmptyRepositoryTransport(), monkeypatch)

    report = service.sync(source_id)

    assert report.evidence_written == 0
    assert "repository_empty" in report.notes
    assert service.sync(source_id).evidence_written == 0
    assert service.doctor().ok


def test_the_api_reports_an_empty_tree_with_a_note() -> None:
    spec = GitHubSourceSpec.build(URL)
    tree = GitHubApi(spec, EmptyRepositoryTransport()).fetch_tree()

    assert tree.data["tree"] == [] and tree.data["repository_id"] == 42
    assert tree.notes == ("repository_empty",)


def test_an_empty_repository_has_no_deep_activity() -> None:
    spec = GitHubSourceSpec.build(URL, actor="ruihaomei")
    batch = GitHubApi(spec, EmptyRepositoryTransport()).fetch_authored_commits()

    assert batch.items == () and batch.complete and "repository_empty" in batch.notes


def test_any_other_conflict_is_still_a_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    other = EmptyRepositoryTransport({"message": "Something else conflicted."})
    service, source_id = _service(tmp_path, other, monkeypatch)

    with pytest.raises(AptuniError) as error:
        service.sync(source_id)
    assert "github_request_failed" in str(error.value)
