"""Owner-readable Profile export: current, explicit, private, and outside the canonical Vault."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace
from aptuni.domain.ids import new_id, sha256_text
from aptuni.domain.records import Evidence, LocatorExtension, Provenance, RetentionLabel, ReviewEvent, SourceLocator
from aptuni.domain.temporal import utc_now

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture()
def service(tmp_path: Path) -> AptuniService:
    app = AptuniService(Workspace(tmp_path / "state"))
    app.init(tmp_path / "Aptuni")
    return app


def _accept(app: AptuniService, statement: str) -> str:
    proposal = app.observe(statement, "preferences")
    preview = app.memory_preview(proposal.candidate_id)
    memory_id = app.decide_memory(proposal.candidate_id, "accept", preview.digest("accept"))
    assert memory_id is not None
    return memory_id


def test_export_is_current_private_and_readable(service: AptuniService, tmp_path: Path) -> None:
    service.remember("Likes **derivations** <script>.", "preferences")
    service.set_module("preferences", expose=False)
    kept = _accept(service, "Prefers equations before library calls.")
    forgotten = _accept(service, "Temporary preference that should disappear.")
    forget = service.memory_forget_preview(forgotten)
    service.forget_memory_confirmed(forgotten, forget.digest())
    service.observe("Pending proposal that must remain quarantined.", "preferences")

    source_dir = tmp_path / "materials"
    source_dir.mkdir()
    (source_dir / "project.md").write_text("Built a bounded retrieval evaluator.", encoding="utf-8")
    source = service.add_folder_source(source_dir, ("projects",), "portfolio")
    service.sync(source.id)

    target = tmp_path / "Profile export"
    report = service.export(target)

    assert report.path == target
    assert (report.facts, report.memories, report.evidence) == (1, 1, 1)
    assert stat.S_IMODE(target.stat().st_mode) == 0o700
    assert all(stat.S_IMODE(path.stat().st_mode) == 0o600 for path in target.iterdir())
    preferences = (target / "preferences.md").read_text(encoding="utf-8")
    assert "Hidden from agents" in preferences
    assert r"Likes \*\*derivations\*\* &lt;script&gt;." in preferences
    assert kept in preferences
    assert forgotten not in preferences
    assert "Pending proposal" not in preferences
    assert "Vault remains the source of truth" in (target / "README.md").read_text(encoding="utf-8")


def test_export_omits_full_content_and_refuses_unsafe_targets(service: AptuniService, tmp_path: Path) -> None:
    seq, records = service.snapshot()
    now = utc_now()
    full_content = RetentionLabel(
        retention_class="full_content",
        purpose="test_full_content",
        expires_at=None,
        full_content=True,
    )
    evidence = Evidence(
        record_type="evidence",
        id=new_id("evd"),
        schema_version=1,
        recorded_at=now,
        valid_from=None,
        valid_until=None,
        module="knowledge",
        provenance=Provenance(
            source_id=None,
            episode="test",
            locator=SourceLocator(
                provider="folder",
                subject_id="private",
                extension=LocatorExtension(
                    schema="folder.locator",
                    version=1,
                    fields={"relative_path": "private.md", "device": 1, "inode": 2},
                ),
            ),
        ),
        trust="untrusted_source",
        retention=full_content,
        policy_epoch=service.policy_of(records).epoch,
        confidence=None,
        review_status="auto_derived",
        supersedes=(),
        change_kind="assert",
        subject="private source",
        signals=("exposure",),
        excerpt="SECRET FULL CONTENT",
        content_hash=sha256_text("SECRET FULL CONTENT"),
        observed_at=now,
    )
    full_fact = service._fact("SECRET FULL FACT", "knowledge", service.policy_of(records).epoch).model_copy(
        update={"retention": full_content}
    )
    service.vault().commit([evidence, full_fact], expected_seq=seq)

    normal_memory_id = _accept(service, "Normal accepted memory.")
    seq, records = service.snapshot()
    normal_memory = records.get(normal_memory_id)
    full_memory = normal_memory.model_copy(
        update={"id": new_id("mem"), "statement": "SECRET FULL MEMORY", "retention": full_content}
    )
    service.vault().commit([full_memory], expected_seq=seq)

    target = tmp_path / "export"
    report = service.export(target)
    assert (report.facts, report.memories, report.evidence) == (0, 1, 0)
    assert report.omitted_full_content == 3
    exported = "".join(p.read_text(encoding="utf-8") for p in target.iterdir())
    assert "SECRET FULL CONTENT" not in exported
    assert "SECRET FULL FACT" not in exported
    assert "SECRET FULL MEMORY" not in exported

    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "keep.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(AptuniError) as nonempty:
        service.export(occupied)
    assert nonempty.value.code == "export_target_not_empty"
    assert (occupied / "keep.txt").read_text(encoding="utf-8") == "keep"

    with pytest.raises(AptuniError) as inside:
        service.export(service.vault().root / "copy")
    assert inside.value.code == "export_inside_vault"


def test_export_excludes_memory_whose_candidate_was_withdrawn(service: AptuniService, tmp_path: Path) -> None:
    memory_id = _accept(service, "Accepted, then withdrawn candidate memory.")
    seq, records = service.snapshot()
    memory = records.get(memory_id)
    service.vault().commit(
        [ReviewEvent(
            record_type="review_event",
            id=new_id("rev"),
            schema_version=1,
            recorded_at=utc_now(),
            target_id=memory.candidate_id,
            decision="revoke",
            actor="user_cli",
            action_digest=sha256_text("withdraw candidate"),
            policy_epoch=service.policy_of(records).epoch,
            rationale_code="owner_revoke",
            nonce_id="test-withdrawal",
        )],
        expected_seq=seq,
    )
    report = service.export(tmp_path / "export")
    assert report.memories == 0
    assert "Accepted, then withdrawn" not in (tmp_path / "export" / "README.md").read_text(encoding="utf-8")


def test_export_cli_json(tmp_path: Path) -> None:
    state = tmp_path / "state"
    env = dict(os.environ, APTUNI_STATE_DIR=str(state), PYTHONPATH=str(REPO / "src"))

    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "-m", "aptuni", *args], env=env, capture_output=True,
                              text=True, check=False)

    assert run("init", str(tmp_path / "Aptuni")).returncode == 0
    assert run("remember", "Builds reliable research software.", "--module", "projects").returncode == 0
    done = run("export", str(tmp_path / "portable"), "--json")
    assert done.returncode == 0, done.stderr
    payload = json.loads(done.stdout)
    assert payload["path"] == str(tmp_path / "portable")
    assert payload["facts"] == 1 and payload["files"] == 2
