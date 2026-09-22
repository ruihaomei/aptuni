from __future__ import annotations

import hashlib
import json
import tempfile
import threading
from collections.abc import Mapping
from pathlib import Path

import pytest

from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService
from aptuni.application.source_commands import SourceCommands
from aptuni.application.workspace import Workspace
from aptuni.cli.main import run
from aptuni.sources.github import (
    GitHubActivityBatch,
    GitHubApi,
    GitHubApiError,
    GitHubSourceSpec,
    GitHubTree,
    HttpResult,
)


class FakeGitHub:
    def __init__(self) -> None:
        self.repository_id = 1352604752
        self.commit = "1" * 40
        readme = b"# Sample\nPublic project overview."
        source = b"print('safe sample')"
        readme_sha = self.add_blob(readme)
        source_sha = self.add_blob(source)
        self.files = {"README.md": readme_sha, "src/main.py": source_sha}

    def add_blob(self, body: bytes) -> str:
        sha = hashlib.sha1(f"blob {len(body)}\0".encode() + body, usedforsecurity=False).hexdigest()
        if not hasattr(self, "blobs"):
            self.blobs: dict[str, bytes] = {}
        self.blobs[sha] = body
        return sha

    def fetch_tree(self) -> GitHubTree:
        return GitHubTree(
            {
                "repository_id": self.repository_id,
                "full_name": "ruihaomei/ctffr-app",
                "commit": self.commit,
                "truncated": False,
                "tree": [
                    {"path": path, "type": "blob", "sha": sha, "size": len(self.blobs[sha])}
                    for path, sha in self.files.items()
                ],
            },
            "main",
            (),
        )

    def fetch_blob(self, sha: str) -> bytes:
        return self.blobs[sha]


class FakeGitHubDeep:
    def __init__(self) -> None:
        self.repository_id = 1352604752
        self.items = (
            {
                "activity_id": "1" * 40,
                "activity_key": "commit:" + "1" * 40,
                "activity_kind": "commit",
                "actor": "ruihaomei",
                "commit": "1" * 40,
                "mode": "deep",
                "occurred_at": "2026-09-20T01:02:03+00:00",
                "title": "Harden parser",
            },
            {
                "activity_id": "41",
                "activity_key": "pull_request:41",
                "activity_kind": "pull_request",
                "actor": "ruihaomei",
                "mode": "deep",
                "occurred_at": "2026-09-21T01:02:03+00:00",
                "pull_number": 8,
                "state": "open",
                "title": "Bound sync",
            },
            {
                "activity_id": "91",
                "activity_key": "review:91",
                "activity_kind": "review",
                "actor": "ruihaomei",
                "mode": "deep",
                "occurred_at": "2026-09-22T01:02:03+00:00",
                "pull_number": 12,
                "state": "approved",
            },
        )
        self.complete = True

    def fetch_deep_activity(self) -> GitHubActivityBatch:
        return GitHubActivityBatch(
            self.repository_id, "ruihaomei/ctffr-app", self.items, self.complete, (),
        )

    def fetch_blob(self, _sha: str) -> bytes:
        raise AssertionError("GitHub Deep must never fetch repository blobs")


def test_configure_sync_noop_move_and_remove(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeGitHub()
    monkeypatch.setattr(SourceCommands, "_github_client", staticmethod(lambda _spec: fake))
    with tempfile.TemporaryDirectory() as raw:
        base = Path(raw)
        service = AptuniService(Workspace(state_dir=base / "state"))
        service.init(base / "Aptuni")
        source = service.add_github_source(
            "https://github.com/ruihaomei/ctffr-app", ("projects",), "maintained_project"
        )
        assert GitHubSourceSpec.from_roots(source.roots).repository == "ctffr-app"

        first = service.sync(source.id)
        assert first.counts == {"add": 2}
        assert {item.subject for item in service.evidence(source.id)} == {"README.md", "src/main.py"}
        assert service.sync(source.id).counts == {}

        fake.commit = "2" * 40
        readme_sha = next(sha for sha, body in fake.blobs.items() if body.startswith(b"# Sample"))
        fake.files = {"docs/README.md": readme_sha}
        changed = service.sync(source.id)
        assert changed.counts == {"move": 1, "remove": 1}
        assert {item.subject for item in service.evidence(source.id)} == {"docs/README.md"}
        assert service.doctor().ok


def test_deep_sync_records_only_exact_actor_commit_activity(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeGitHubDeep()
    monkeypatch.setattr(SourceCommands, "_github_client", staticmethod(lambda _spec: fake))
    with tempfile.TemporaryDirectory() as raw:
        base = Path(raw)
        service = AptuniService(Workspace(state_dir=base / "state"))
        service.init(base / "Aptuni")
        source = service.add_github_source(
            "https://github.com/ruihaomei/ctffr-app", ("projects",), "authored_contributions",
            deep_actor="ruihaomei",
        )

        assert source.source_type == "github_deep"
        assert GitHubSourceSpec.from_roots(source.roots).actor == "ruihaomei"
        first = service.sync(source.id)
        assert first.counts == {"add": 3}
        evidence = service.evidence(source.id)
        assert {item.subject for item in evidence} == {
            "commit:" + "1" * 40, "pull_request:41", "review:91",
        }
        assert {item.excerpt for item in evidence} == {
            "Authored commit: Harden parser",
            "Opened pull request: Bound sync",
            "Submitted review",
        }
        assert all(
            item.provenance.locator.extension.schema_name == "github.activity"
            for item in evidence
        )
        expected_fields = {
            "activity_key", "repository_id", "actor", "activity_kind", "activity_id",
            "occurred_at", "mode",
        }
        by_subject = {
            item.subject: set(item.provenance.locator.extension.fields)
            for item in evidence
        }
        assert by_subject["commit:" + "1" * 40] == expected_fields | {"commit", "title"}
        assert by_subject["pull_request:41"] == expected_fields | {"pull_number", "state", "title"}
        assert by_subject["review:91"] == expected_fields | {"pull_number", "state"}
        assert service.sync(source.id).counts == {}

        fake.items = ()
        removed = service.sync(source.id)
        assert removed.counts == {"remove": 3}
        assert service.evidence(source.id) == []


def test_deep_cli_source_sync_is_distinct_and_searchable(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path,
) -> None:
    fake = FakeGitHubDeep()
    monkeypatch.setattr(SourceCommands, "_github_client", staticmethod(lambda _spec: fake))
    service = AptuniService(Workspace(state_dir=tmp_path / "state"))
    service.init(tmp_path / "Aptuni")

    assert run([
        "source", "add-github", "https://github.com/ruihaomei/ctffr-app",
        "--module", "projects", "--role", "authored_contributions",
        "--deep-actor", "ruihaomei",
    ], service) == 0
    output = capsys.readouterr().out
    assert "Approved GitHub Deep source" in output
    assert "ruihaomei" in output
    source = service.sources()[0]
    assert service.sync(source.id).counts == {"add": 3}
    assert service.search("Harden parser")


def test_deep_partial_history_never_withdraws_and_crash_replay_is_idempotent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    from aptuni.application import ingest

    fake = FakeGitHubDeep()
    monkeypatch.setattr(SourceCommands, "_github_client", staticmethod(lambda _spec: fake))
    service = AptuniService(Workspace(state_dir=tmp_path / "state"))
    service.init(tmp_path / "Aptuni")
    source = service.add_github_source(
        "https://github.com/ruihaomei/ctffr-app", ("projects",), "authored_contributions",
        deep_actor="ruihaomei",
    )
    assert service.sync(source.id).counts == {"add": 3}

    fake.items = ()
    fake.complete = False
    assert service.sync(source.id).counts == {}
    assert len(service.evidence(source.id)) == 3

    fake.complete = True
    original_save = ingest.SourceStateStore.save

    def crash_after_canonical_commit(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("simulated deep state-save crash")

    monkeypatch.setattr(ingest.SourceStateStore, "save", crash_after_canonical_commit)
    with pytest.raises(RuntimeError, match="deep state-save crash"):
        service.sync(source.id)
    assert service.evidence(source.id) == []

    monkeypatch.setattr(ingest.SourceStateStore, "save", original_save)
    assert service.sync(source.id).counts == {}
    assert service.evidence(source.id) == []


@pytest.mark.parametrize("failure", ["rate_limit", "oversized"])
def test_deep_late_provider_failure_leaves_canonical_and_source_state_unchanged(
    failure: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    fake = FakeGitHubDeep()
    active: list[object] = [fake]
    monkeypatch.setattr(SourceCommands, "_github_client", staticmethod(lambda _spec: active[0]))
    service = AptuniService(Workspace(state_dir=tmp_path / "state"))
    service.init(tmp_path / "Aptuni")
    source = service.add_github_source(
        "https://github.com/ruihaomei/ctffr-app", ("projects",), "authored_contributions",
        deep_actor="ruihaomei",
    )
    assert service.sync(source.id).counts == {"add": 3}
    state_path = tmp_path / "Aptuni" / "sources" / f"{source.id}.json"
    state_before = state_path.read_bytes()
    evidence_before = service.evidence(source.id)

    class LateFailureTransport:
        def get(self, url: str, headers: Mapping[str, str], max_bytes: int) -> HttpResult:
            del headers
            if url == "https://api.github.com/repos/ruihaomei/ctffr-app":
                body = {"id": fake.repository_id, "full_name": "ruihaomei/ctffr-app",
                        "default_branch": "main"}
                return HttpResult(200, url, {"content-type": "application/json"}, json.dumps(body).encode())
            if "/commits?" in url:
                body = [{
                    "sha": "2" * 40,
                    "author": {"login": "ruihaomei"},
                    "commit": {"author": {"date": "2026-09-22T01:02:03Z"},
                               "message": "A result produced before the late failure"},
                }]
                assert max_bytes == 2_000_000
                return HttpResult(200, url, {"content-type": "application/json"}, json.dumps(body).encode())
            assert "author%3Aruihaomei" in url
            assert max_bytes == 2_000_000
            if failure == "rate_limit":
                return HttpResult(403, url, {
                    "content-type": "application/json", "retry-after": "60",
                }, b"{}")
            oversized = b"{" + b" " * max_bytes + b"}"
            assert len(oversized) > max_bytes
            raise GitHubApiError("github_response_too_large")

    active[0] = GitHubApi(GitHubSourceSpec.from_roots(source.roots), LateFailureTransport())
    with pytest.raises(AptuniError, match="GitHub sync stopped safely") as error:
        service.sync(source.id)
    assert error.value.code == "github_sync_failed"
    assert service.evidence(source.id) == evidence_before
    assert state_path.read_bytes() == state_before


@pytest.mark.parametrize("repository_id", [True, 0, -1])
def test_deep_malformed_repository_identity_leaves_durable_state_unchanged(
    repository_id: object, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    fake = FakeGitHubDeep()
    monkeypatch.setattr(SourceCommands, "_github_client", staticmethod(lambda _spec: fake))
    service = AptuniService(Workspace(state_dir=tmp_path / "state"))
    service.init(tmp_path / "Aptuni")
    source = service.add_github_source(
        "https://github.com/ruihaomei/ctffr-app", ("projects",), "authored_contributions",
        deep_actor="ruihaomei",
    )
    assert service.sync(source.id).counts == {"add": 3}
    state_path = tmp_path / "Aptuni" / "sources" / f"{source.id}.json"
    state_before = state_path.read_bytes()
    evidence_before = service.evidence(source.id)

    fake.repository_id = repository_id  # type: ignore[assignment]
    with pytest.raises(AptuniError, match="GitHub sync stopped safely") as error:
        service.sync(source.id)
    assert error.value.code == "github_sync_failed"
    assert service.evidence(source.id) == evidence_before
    assert state_path.read_bytes() == state_before


def test_repository_identity_change_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeGitHub()
    monkeypatch.setattr(SourceCommands, "_github_client", staticmethod(lambda _spec: fake))
    with tempfile.TemporaryDirectory() as raw:
        base = Path(raw)
        service = AptuniService(Workspace(state_dir=base / "state"))
        service.init(base / "Aptuni")
        source = service.add_github_source(
            "https://github.com/ruihaomei/ctffr-app", ("projects",), "maintained_project"
        )
        service.sync(source.id)
        fake.repository_id += 1
        with pytest.raises(AptuniError) as error:
            service.sync(source.id)
        assert error.value.code == "github_sync_failed"


def test_ref_advance_after_commit_before_state_save_still_retracts_removed_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aptuni.application import ingest

    fake = FakeGitHub()
    monkeypatch.setattr(SourceCommands, "_github_client", staticmethod(lambda _spec: fake))
    with tempfile.TemporaryDirectory() as raw:
        base = Path(raw)
        service = AptuniService(Workspace(state_dir=base / "state"))
        service.init(base / "Aptuni")
        source = service.add_github_source(
            "https://github.com/ruihaomei/ctffr-app", ("projects",), "maintained_project"
        )
        original_save = ingest.SourceStateStore.save

        def crash_after_canonical_commit(*_args: object, **_kwargs: object) -> None:
            raise RuntimeError("simulated state-save crash")

        monkeypatch.setattr(ingest.SourceStateStore, "save", crash_after_canonical_commit)
        with pytest.raises(RuntimeError, match="state-save crash"):
            service.sync(source.id)
        assert {item.subject for item in service.evidence(source.id)} == {"README.md", "src/main.py"}

        monkeypatch.setattr(ingest.SourceStateStore, "save", original_save)
        fake.commit = "2" * 40
        fake.files = {}
        report = service.sync(source.id)
        assert report.counts == {"remove": 2}
        assert service.evidence(source.id) == []


def test_secret_hidden_and_cache_paths_never_reach_evidence_or_vault(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeGitHub()
    marker = b"APTUNI_GITHUB_SECRET_MARKER"
    marker_sha = fake.add_blob(marker)
    fake.files |= {
        "credentials.json": marker_sha,
        "deploy-token.yaml": marker_sha,
        ".hidden/config.json": marker_sha,
        "node_modules/pkg/index.js": marker_sha,
    }
    monkeypatch.setattr(SourceCommands, "_github_client", staticmethod(lambda _spec: fake))
    with tempfile.TemporaryDirectory() as raw:
        base = Path(raw)
        service = AptuniService(Workspace(state_dir=base / "state"))
        service.init(base / "Aptuni")
        source = service.add_github_source(
            "https://github.com/ruihaomei/ctffr-app", ("projects",), "maintained_project"
        )
        report = service.sync(source.id)
        assert "secret_skipped" in report.notes
        assert "excluded_dir_skipped" in report.notes
        assert {item.subject for item in service.evidence(source.id)} == {"README.md", "src/main.py"}
        assert marker not in b"".join(path.read_bytes() for path in (base / "Aptuni").rglob("*") if path.is_file())


def test_concurrent_syncs_serialize_the_pending_journal_and_canonical_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BlockingGitHub(FakeGitHub):
        def __init__(self) -> None:
            super().__init__()
            self.calls = 0
            self.calls_lock = threading.Lock()
            self.first_entered = threading.Event()
            self.release_first = threading.Event()

        def fetch_tree(self) -> GitHubTree:
            with self.calls_lock:
                self.calls += 1
                call = self.calls
            if call == 1:
                self.first_entered.set()
                assert self.release_first.wait(5)
            return super().fetch_tree()

    fake = BlockingGitHub()
    monkeypatch.setattr(SourceCommands, "_github_client", staticmethod(lambda _spec: fake))
    with tempfile.TemporaryDirectory() as raw:
        base = Path(raw)
        workspace = Workspace(state_dir=base / "state")
        first_service = AptuniService(workspace)
        first_service.init(base / "Aptuni")
        source = first_service.add_github_source(
            "https://github.com/ruihaomei/ctffr-app", ("projects",), "maintained_project"
        )
        second_service = AptuniService(workspace)
        results: list[dict[str, int]] = []
        errors: list[BaseException] = []
        second_started = threading.Event()
        second_done = threading.Event()

        def run_sync(service: AptuniService, *, second: bool = False) -> None:
            if second:
                second_started.set()
            try:
                results.append(service.sync(source.id).counts)
            except BaseException as error:  # test captures thread failures for the main assertion
                errors.append(error)
            finally:
                if second:
                    second_done.set()

        first_thread = threading.Thread(target=run_sync, args=(first_service,))
        second_thread = threading.Thread(target=run_sync, args=(second_service,), kwargs={"second": True})
        first_thread.start()
        assert fake.first_entered.wait(2)
        second_thread.start()
        assert second_started.wait(2)
        assert not second_done.wait(0.1)
        assert fake.calls == 1
        fake.release_first.set()
        first_thread.join(5)
        second_thread.join(5)

        assert not errors
        assert sorted(results, key=bool) == [{}, {"add": 2}]
        assert fake.calls == 2
        assert len(first_service.evidence(source.id)) == 2
