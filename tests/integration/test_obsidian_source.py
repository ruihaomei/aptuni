"""End-to-end Obsidian source: admission, minimized Evidence, replay, rename and CLI."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from aptuni.application.errors import AptuniError
from aptuni.application.ingest import SourceStateStore
from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace
from aptuni.cli.main import run

PRIVATE_PROPERTY = "A Very Private Employer Name"


def _vault(base: Path) -> Path:
    root = base / "Vault"
    (root / ".obsidian").mkdir(parents=True)
    (root / ".obsidian" / "workspace.json").write_text("{}\n", encoding="utf-8")
    return root


def _service(base: Path) -> AptuniService:
    service = AptuniService(Workspace(base / "state"))
    service.init(base / "Aptuni")
    return service


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture()
def vault_and_service(tmp_path: Path) -> tuple[Path, AptuniService]:
    return _vault(tmp_path), _service(tmp_path)


def test_a_plain_folder_is_refused_and_names_the_folder_source(tmp_path: Path) -> None:
    service = _service(tmp_path)
    plain = tmp_path / "just-markdown"
    plain.mkdir()
    (plain / "Note.md").write_text("body\n", encoding="utf-8")

    with pytest.raises(AptuniError) as error:
        service.add_obsidian_source(plain, modules=("knowledge",), role="notes")

    assert error.value.code == "source_not_a_vault"
    assert "add-folder" in error.value.message


def test_a_vault_overlapping_the_canonical_vault_is_refused(tmp_path: Path) -> None:
    service = _service(tmp_path)
    inside = tmp_path / "Aptuni" / "Notes"
    (inside / ".obsidian").mkdir(parents=True)

    with pytest.raises(AptuniError) as error:
        service.add_obsidian_source(inside, modules=("knowledge",), role="notes")

    assert error.value.code == "source_inside_vault"


def test_sync_emits_evidence_whose_excerpt_has_no_frontmatter(
    vault_and_service: tuple[Path, AptuniService],
) -> None:
    root, service = vault_and_service
    _write(root, "areas/Method.md",
           f"---\nemployer: {PRIVATE_PROPERTY}\ntags: [method]\n---\nThe visible body sentence.\n")
    source = service.add_obsidian_source(root, modules=("knowledge",), role="notes")

    report = service.sync(source.id)
    evidence = service.evidence(source.id)

    assert report.counts == {"add": 1}
    assert len(evidence) == 1
    assert "The visible body sentence." in evidence[0].excerpt
    assert PRIVATE_PROPERTY not in evidence[0].excerpt
    assert "employer" not in evidence[0].excerpt
    fields = evidence[0].provenance.locator.extension.fields
    assert fields["note_name"] == "Method" and fields["folder_path"] == "areas"
    assert fields["tags"] == ["method"] and fields["property_keys"] == ["employer", "tags"]
    assert PRIVATE_PROPERTY not in json.dumps(fields, ensure_ascii=False)


def test_a_private_property_never_reaches_the_search_index(
    vault_and_service: tuple[Path, AptuniService],
) -> None:
    root, service = vault_and_service
    _write(root, "Note.md", f"---\nemployer: {PRIVATE_PROPERTY}\n---\nPublic sentence about pipelines.\n")
    source = service.add_obsidian_source(root, modules=("knowledge",), role="notes")
    service.sync(source.id)

    assert [hit.id for hit in service.search("pipelines")] != []
    assert service.search("Employer") == []
    assert service.search("Private") == []


def test_repeat_sync_is_a_no_op_and_a_rename_keeps_identity(
    vault_and_service: tuple[Path, AptuniService],
) -> None:
    root, service = vault_and_service
    _write(root, "Note.md", "stable body\n")
    source = service.add_obsidian_source(root, modules=("knowledge",), role="notes")
    service.sync(source.id)
    subject = service.evidence(source.id)[0].provenance.locator.subject_id

    assert service.sync(source.id).counts == {}

    (root / "archive").mkdir()
    (root / "Note.md").rename(root / "archive" / "Renamed.md")
    moved = service.sync(source.id)

    assert moved.counts == {"move": 1}
    current = service.evidence(source.id)
    assert len(current) == 1
    assert current[0].provenance.locator.subject_id == subject
    assert current[0].provenance.locator.extension.fields["note_name"] == "Renamed"


def test_a_crash_between_commit_and_state_save_replays_without_duplicating(
    vault_and_service: tuple[Path, AptuniService],
) -> None:
    root, service = vault_and_service
    _write(root, "Note.md", "body\n")
    source = service.add_obsidian_source(root, modules=("knowledge",), role="notes")
    service.sync(source.id)
    store = SourceStateStore(service.vault().root, source.id)
    saved = store.load()
    assert saved is not None

    # Simulate the crash window: canonical Evidence is committed, the state save never landed.
    store.path.unlink()
    replayed = service.sync(source.id)

    assert len(service.evidence(source.id)) == 1
    assert replayed.evidence_written == 0


def test_cli_add_obsidian_sync_and_evidence_flow() -> None:
    with tempfile.TemporaryDirectory() as raw:
        base = Path(raw)
        state = base / "state"
        root = _vault(base)
        _write(root, "Note.md", f"---\nemployer: {PRIVATE_PROPERTY}\n---\nVisible sentence.\n")
        service = AptuniService(Workspace(state))
        service.init(base / "Aptuni")

        assert run(["source", "add-obsidian", str(root), "--module", "knowledge", "--json"], service) == 0
        source_id = service.sources()[0].id
        assert service.sources()[0].source_type == "obsidian"
        assert run(["sync", source_id, "--json"], service) == 0
        assert run(["evidence", "--source", source_id, "--json"], service) == 0
        assert PRIVATE_PROPERTY not in json.dumps(
            [record.model_dump(mode="json") for record in service.evidence(source_id)], ensure_ascii=False,
        )


def test_a_crafted_filename_cannot_forge_a_cli_evidence_row(
    vault_and_service: tuple[Path, AptuniService], capsys: pytest.CaptureFixture[str],
) -> None:
    """A POSIX-legal filename holding a real ESC and newline must not forge a row (Review 55 B2)."""
    root, service = vault_and_service
    hostile = "Innocent\x1b[31m\nevd_FORGED  [knowledge]  Attacker.md  exposure.md"
    _write(root, hostile, "body\n")
    source = service.add_obsidian_source(root, modules=("knowledge",), role="notes")
    service.sync(source.id)
    capsys.readouterr()

    assert run(["evidence", "--source", source.id], service) == 0
    printed = capsys.readouterr().out

    assert "\x1b" not in printed
    assert len([line for line in printed.splitlines() if line.strip()]) == 1
    assert "evd_FORGED" not in printed.split("evd_")[1] if "evd_" in printed else True
    fields = service.evidence(source.id)[0].provenance.locator.extension.fields
    assert "\x1b" not in str(fields["note_name"])
    assert "\n" not in str(fields["note_name"])


def test_a_crafted_tag_cannot_forge_a_locator_field(
    vault_and_service: tuple[Path, AptuniService],
) -> None:
    root, service = vault_and_service
    _write(root, "Note.md", '---\ntags: ["norm\x1b[31mal"]\n---\nbody\n')
    source = service.add_obsidian_source(root, modules=("knowledge",), role="notes")
    service.sync(source.id)

    fields = service.evidence(source.id)[0].provenance.locator.extension.fields
    assert fields["tags"] and all("\x1b" not in tag for tag in fields["tags"])


def test_a_bom_does_not_leak_frontmatter_into_the_excerpt_or_the_index(
    vault_and_service: tuple[Path, AptuniService],
) -> None:
    """The reviewer's B1 counterexample, end to end through sync, evidence and search."""
    root, service = vault_and_service
    (root / "Bom.md").write_bytes(
        b"\xef\xbb\xbf---\nemployer: A Very Private Employer Name\nclient: #AcmeCorp\n---\nVisible body.\n",
    )
    source = service.add_obsidian_source(root, modules=("knowledge",), role="notes")
    service.sync(source.id)

    evidence = service.evidence(source.id)[0]
    fields = evidence.provenance.locator.extension.fields

    assert evidence.excerpt == "Visible body."
    assert fields["property_keys"] == ["client", "employer"]
    assert fields["tags"] == []
    assert service.search("Employer") == []
    assert service.search("Private") == []
    assert service.search("AcmeCorp") == []


def test_a_vault_that_disappears_mid_sync_withdraws_nothing(
    vault_and_service: tuple[Path, AptuniService],
) -> None:
    """An unmounted or evicted vault must fail closed, not retract every note (Review 55 N1)."""
    root, service = vault_and_service
    _write(root, "Note.md", "body\n")
    source = service.add_obsidian_source(root, modules=("knowledge",), role="notes")
    service.sync(source.id)
    assert len(service.evidence(source.id)) == 1

    (root / ".obsidian" / "workspace.json").unlink()
    (root / ".obsidian").rmdir()
    with pytest.raises(AptuniError) as error:
        service.sync(source.id)

    assert error.value.code == "obsidian_vault_unavailable"
    assert len(service.evidence(source.id)) == 1


def test_a_vault_overlapping_the_state_directory_is_refused(tmp_path: Path) -> None:
    service = _service(tmp_path)
    inside = tmp_path / "state" / "Notes"
    (inside / ".obsidian").mkdir(parents=True)

    with pytest.raises(AptuniError) as error:
        service.add_obsidian_source(inside, modules=("knowledge",), role="notes")

    assert error.value.code == "source_inside_vault"


def test_a_nested_obsidian_directory_is_excluded_like_any_hidden_directory(
    vault_and_service: tuple[Path, AptuniService],
) -> None:
    root, service = vault_and_service
    _write(root, "Kept.md", "body\n")
    _write(root, "sub/.obsidian/appearance.json", '{"theme":"dark"}\n')
    _write(root, "sub/.obsidian/Config.md", "nested config note\n")
    source = service.add_obsidian_source(root, modules=("knowledge",), role="notes")
    service.sync(source.id)

    paths = {record.provenance.locator.extension.fields["relative_path"]
             for record in service.evidence(source.id)}
    assert paths == {"Kept.md"}
