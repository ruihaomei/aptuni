"""Folder Source end to end: configure, sync, re-sync, edit/move/delete, review, privacy guards."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest

from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace


@dataclass
class Env:
    service: AptuniService
    docs: Path
    source_id: str

    def write(self, relative: str, text: str) -> None:
        path = self.docs / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


@pytest.fixture()
def env() -> Iterator[Env]:
    with tempfile.TemporaryDirectory() as raw:
        base = Path(raw)
        service = AptuniService(Workspace(state_dir=base / "state"))
        service.init(base / "Aptuni")
        docs = base / "materials"
        docs.mkdir()
        cv = "# CV\n\nAnalyst at ACME, 2024–2025. Built churn models in Python."
        (docs / "cv.md").write_text(cv, encoding="utf-8")
        (docs / "notes.txt").write_text("Reading list: survival analysis, Cox model.", encoding="utf-8")
        config = service.add_folder_source(docs, modules=("experience", "projects"), role="application_materials")
        yield Env(service, docs, config.id)


def evidence_paths(env: Env) -> dict[str, str]:
    return {e.provenance.locator.extension.fields["relative_path"]: e.id for e in env.service.evidence(env.source_id)}


def test_first_sync_creates_minimized_exposure_evidence(env: Env) -> None:
    report = env.service.sync(env.source_id)
    assert report.counts == {"add": 2}
    evidence = env.service.evidence(env.source_id)
    assert {e.module for e in evidence} == {"experience"}
    for item in evidence:
        assert item.signals == ("exposure",)  # a document mention never implies study or mastery
        assert item.trust == "untrusted_source"
        assert item.retention.retention_class == "source_minimized"
        assert item.excerpt is not None and len(item.excerpt) <= 280
        assert item.content_hash.startswith("sha256:")


def test_resync_without_changes_is_a_noop(env: Env) -> None:
    env.service.sync(env.source_id)
    seq = env.service.status().seq
    report = env.service.sync(env.source_id)
    assert report.counts == {}
    assert env.service.status().seq == seq


def test_edit_supersedes_evidence_and_keeps_history(env: Env) -> None:
    env.service.sync(env.source_id)
    before = evidence_paths(env)["cv.md"]
    env.write("cv.md", "# CV\n\nSenior analyst at ACME.")
    assert env.service.sync(env.source_id).counts == {"modify": 1}
    after = evidence_paths(env)["cv.md"]
    assert after != before
    current = next(e for e in env.service.evidence(env.source_id) if e.id == after)
    assert current.supersedes == (before,)


def test_rename_keeps_identity_and_moves_locator(env: Env) -> None:
    env.service.sync(env.source_id)
    os.replace(env.docs / "notes.txt", env.docs / "reading.txt")
    assert env.service.sync(env.source_id).counts == {"move": 1}
    assert "reading.txt" in evidence_paths(env)
    assert "notes.txt" not in evidence_paths(env)


def test_deleted_file_withdraws_evidence_without_deleting_history(env: Env) -> None:
    env.service.sync(env.source_id)
    (env.docs / "notes.txt").unlink()
    assert env.service.sync(env.source_id).counts == {"remove": 1}
    assert "notes.txt" not in evidence_paths(env)
    history = [r for r in env.service.records().records() if r.record_type == "evidence"]
    assert any(r.change_kind == "retraction" for r in history)
    assert len(history) == 3


def test_ambiguous_identity_goes_to_review_queue(env: Env) -> None:
    env.write("copy-a.md", "same bytes")
    env.write("copy-b.md", "same bytes")
    env.service.sync(env.source_id)
    os.replace(env.docs / "copy-a.md", env.docs / "x.md")
    os.replace(env.docs / "copy-b.md", env.docs / "y.md")
    report = env.service.sync(env.source_id)
    assert report.counts.get("ambiguous") == 2
    assert len(env.service.review_queue(env.source_id)) == 2


def test_secrets_hidden_files_and_unsupported_formats_are_never_read(env: Env) -> None:
    env.write(".env", "API_KEY=secret")
    env.write("id_rsa", "PRIVATE")
    env.write("server.pem", "PRIVATE")
    env.write(".hidden/notes.md", "hidden")
    env.write("photo.jpg", "binary")
    env.service.sync(env.source_id)
    assert set(evidence_paths(env)) == {"cv.md", "notes.txt"}


def test_disabled_ingest_blocks_sync_without_advancing(env: Env) -> None:
    env.service.set_module("experience", ingest=False)
    with pytest.raises(AptuniError) as error:
        env.service.sync(env.source_id)
    assert error.value.code == "module_ingest_disabled"
    env.service.set_module("experience", ingest=True)
    assert env.service.sync(env.source_id).counts == {"add": 2}


def test_crash_after_commit_before_state_save_replays_idempotently(env: Env, monkeypatch: pytest.MonkeyPatch) -> None:
    from aptuni.application import ingest

    def boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("simulated crash")

    monkeypatch.setattr(ingest.SourceStateStore, "save", boom)
    with pytest.raises(RuntimeError):
        env.service.sync(env.source_id)
    monkeypatch.undo()
    report = env.service.sync(env.source_id)
    assert report.counts == {"add": 2}
    assert len(env.service.evidence(env.source_id)) == 2  # no duplicates after replay
    assert env.service.doctor().ok


def test_symlink_swap_after_scan_is_refused_without_reading_target(
    env: Env, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aptuni.application import ingest

    original = ingest.FolderIngest.scan
    outside = env.docs.parent / "outside.md"
    outside.write_text((env.docs / "cv.md").read_text(encoding="utf-8"), encoding="utf-8")

    def swap_after_scan(self: ingest.FolderIngest, state: ingest.SourceState | None) -> ingest.FolderScan:
        result = original(self, state)
        (env.docs / "cv.md").unlink()
        (env.docs / "cv.md").symlink_to(outside)
        return result

    monkeypatch.setattr(ingest.FolderIngest, "scan", swap_after_scan)
    before = env.service.status().seq
    with pytest.raises(AptuniError) as error:
        env.service.sync(env.source_id)
    assert error.value.code == "sync_retry"
    assert env.service.status().seq == before
    assert env.service.evidence(env.source_id) == []


def test_source_root_inside_vault_is_refused(env: Env) -> None:
    with pytest.raises(AptuniError) as error:
        env.service.add_folder_source(env.service.status().vault_path, modules=("knowledge",), role="notes")
    assert error.value.code == "source_inside_vault"


def test_sources_are_listed(env: Env) -> None:
    [config] = env.service.sources()
    assert config.id == env.source_id
    assert config.module_mapping == ("experience", "projects")
