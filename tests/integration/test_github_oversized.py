"""A repository with a file too large to read still syncs (Beta Day 0, 2026-09-29).

User #1's private repository contained multi-megabyte notebooks. GitHub's tree already reports each
blob's size, yet the sync fetched them, hit the response bound, and the whole repository failed as a
misleading ``sync_retry``, which stopped first-run setup before any agent access was written. An
oversized file is now skipped with a note, and a real GitHub failure keeps its own error code.
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

import pytest

from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService
from aptuni.application.source_commands import SourceCommands
from aptuni.application.workspace import Workspace
from aptuni.sources.github import MAX_BLOB_BYTES, GitHubApiError, GitHubTree, scan_github

URL = "https://github.com/ruihaomei/sample"


def _sha(body: bytes) -> str:
    return hashlib.sha1(f"blob {len(body)}\0".encode() + body, usedforsecurity=False).hexdigest()


class RepoWithLargeNotebook:
    def __init__(self) -> None:
        self.small = b"# Sample\nProject overview."
        self.files = {"README.md": (_sha(self.small), len(self.small)),
                      "analysis/Figure_2.ipynb": ("f" * 40, MAX_BLOB_BYTES * 4)}
        self.fetch_error: str | None = None

    def fetch_tree(self) -> GitHubTree:
        return GitHubTree({
            "repository_id": 7, "full_name": "ruihaomei/sample", "commit": "1" * 40, "truncated": False,
            "tree": [{"path": path, "type": "blob", "sha": sha, "size": size}
                     for path, (sha, size) in self.files.items()],
        }, "main", ())

    def fetch_blob(self, sha: str) -> bytes:
        if self.fetch_error:
            raise GitHubApiError(self.fetch_error)
        if sha == _sha(self.small):
            return self.small
        raise GitHubApiError("github_response_too_large")


def _service(base: Path, fake: RepoWithLargeNotebook, monkeypatch: pytest.MonkeyPatch) -> tuple[AptuniService, str]:
    monkeypatch.setattr(SourceCommands, "_github_client", staticmethod(lambda _spec: fake))
    service = AptuniService(Workspace(state_dir=base / "state"))
    service.init(base / "Aptuni")
    source = service.add_github_source(URL, ("knowledge",), "repository")
    return service, source.id


def test_an_oversized_file_is_skipped_and_the_rest_of_the_repository_syncs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as raw:
        service, source_id = _service(Path(raw), RepoWithLargeNotebook(), monkeypatch)

        report = service.sync(source_id)

        assert {item.subject for item in service.evidence(source_id)} == {"README.md"}
        assert "oversized_files_skipped" in report.notes


def test_a_github_failure_while_reading_files_keeps_its_own_code(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = RepoWithLargeNotebook()
    fake.fetch_error = "github_access_denied"
    with tempfile.TemporaryDirectory() as raw:
        service, source_id = _service(Path(raw), fake, monkeypatch)

        with pytest.raises(AptuniError) as error:
            service.sync(source_id)

        assert error.value.code == "github_sync_failed"
        assert "github_access_denied" in str(error.value)
        assert "changed while syncing" not in str(error.value)


def test_oversized_files_do_not_use_up_the_selection_budget() -> None:
    tree = {"repository_id": 7, "full_name": "o/r", "commit": "1" * 40, "truncated": False, "tree": [
        {"path": "README.md", "type": "blob", "sha": "a" * 40, "size": MAX_BLOB_BYTES + 1},
        {"path": "src/main.py", "type": "blob", "sha": "b" * 40, "size": 10},
    ]}

    scan = scan_github(tree, "g", None, ("github.standard", "1"), budget=1)

    assert [item.locator.extension.fields["path"] for item in scan.snapshot.items] == ["src/main.py"]
    assert scan.snapshot.coverage == "complete", "a skipped oversized file is never read, like an excluded one"
