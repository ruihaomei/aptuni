"""Reconnecting a fresh installation to an existing Vault (Beta finding P2).

A reinstall, a new machine or a wiped state directory must be able to use the owner's Vault again
without editing internal config. Attaching only reads and verifies the Vault; it never recovers,
migrates or rewrites anything inside it.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace
from aptuni.cli.main import run as cli_run
from aptuni.cli.setup_apply import apply_setup_plan


def _existing_vault(tmp_path: Path) -> Path:
    first = AptuniService(Workspace(tmp_path / "old-state"))
    first.init(tmp_path / "Vault")
    first.remember("Prefers worked examples before theory.", "preferences")
    return tmp_path / "Vault"


def _snapshot(root: Path) -> dict[str, str]:
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*")) if path.is_file()}


def _fresh(tmp_path: Path, name: str = "new-state") -> AptuniService:
    return AptuniService(Workspace(tmp_path / name))


def test_reinstall_attaches_existing_vault_without_changing_it(tmp_path: Path) -> None:
    vault = _existing_vault(tmp_path)
    before = _snapshot(vault)
    service = _fresh(tmp_path)

    result = service.attach(vault)

    assert result.already_attached is False
    assert service.workspace.vault_path() == vault.resolve()
    assert _snapshot(vault) == before, "attaching must not write inside the Vault"
    assert [fact.statement for fact in service.facts()] == ["Prefers worked examples before theory."]


def test_attach_refuses_a_folder_that_is_not_a_vault(tmp_path: Path) -> None:
    empty = tmp_path / "notes"
    empty.mkdir()
    (empty / "readme.md").write_text("not a vault", encoding="utf-8")
    service = _fresh(tmp_path)

    with pytest.raises(AptuniError) as error:
        service.attach(empty)

    assert error.value.code == "vault_invalid"
    assert "aptuni init" in error.value.message
    assert service.workspace.vault_path() is None


def test_attach_refuses_a_missing_path(tmp_path: Path) -> None:
    service = _fresh(tmp_path)
    with pytest.raises(AptuniError) as error:
        service.attach(tmp_path / "nowhere")
    assert error.value.code == "vault_invalid"
    assert service.workspace.vault_path() is None


def test_attach_refuses_a_vault_that_fails_verification_and_changes_nothing(tmp_path: Path) -> None:
    vault = _existing_vault(tmp_path)
    segment = next(path for path in (vault / "records").iterdir() if "worked" in path.read_text(encoding="utf-8"))
    segment.write_text(segment.read_text(encoding="utf-8").replace("worked", "WORKED"), encoding="utf-8")
    before = _snapshot(vault)
    service = _fresh(tmp_path)

    with pytest.raises(AptuniError) as error:
        service.attach(vault)

    assert error.value.code == "vault_unverified"
    assert "Nothing was changed" in error.value.message
    assert service.workspace.vault_path() is None
    assert _snapshot(vault) == before


def test_attach_is_idempotent_for_the_already_configured_vault(tmp_path: Path) -> None:
    vault = _existing_vault(tmp_path)
    service = _fresh(tmp_path)
    service.attach(vault)

    again = service.attach(vault)

    assert again.already_attached is True
    assert service.workspace.vault_path() == vault.resolve()


def test_attach_refuses_to_silently_switch_away_from_another_configured_vault(tmp_path: Path) -> None:
    vault = _existing_vault(tmp_path)
    service = _fresh(tmp_path)
    service.init(tmp_path / "Other")

    with pytest.raises(AptuniError) as error:
        service.attach(vault)

    assert error.value.code == "vault_already_configured"
    assert service.workspace.vault_path() == (tmp_path / "Other").resolve()


def test_attach_refuses_a_state_directory_inside_the_vault(tmp_path: Path) -> None:
    vault = _existing_vault(tmp_path)
    service = AptuniService(Workspace(vault / "state"))
    with pytest.raises(AptuniError) as error:
        service.attach(vault)
    assert error.value.code == "state_inside_vault"


def test_init_on_an_existing_vault_points_to_attach(tmp_path: Path) -> None:
    vault = _existing_vault(tmp_path)
    with pytest.raises(AptuniError) as error:
        _fresh(tmp_path).init(vault)
    assert error.value.code == "vault_exists"
    assert f"aptuni attach {vault.resolve()}" in error.value.message


@pytest.mark.parametrize(("locale", "expected"), [
    ("en", "Connected this installation to your existing Vault"),
    ("zh-CN", "已连接到你现有的 Vault"),
])
def test_attach_cli_reports_in_the_chosen_language(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], locale: str, expected: str,
) -> None:
    vault = _existing_vault(tmp_path)
    service = _fresh(tmp_path)

    assert cli_run(["attach", str(vault), "--lang", locale], service) == 0

    out = capsys.readouterr().out
    assert expected in out
    assert str(vault.resolve()) in out


def test_guided_setup_reuses_an_existing_vault_on_reinstall(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    vault = _existing_vault(tmp_path)
    before = _snapshot(vault)
    service = _fresh(tmp_path)
    assert cli_run(["setup", "plan", "--lang", "en", "--source", "other", "--memory", "basic",
                    "--privacy", "local_only", "--no-host", "--vault", str(vault)], service) == 0
    rendered = capsys.readouterr().out
    assert "use your existing Profile Vault" in rendered
    assert cli_run(["setup", "plan", "--lang", "en", "--source", "other", "--memory", "basic",
                    "--privacy", "local_only", "--no-host", "--vault", str(vault), "--json"], service) == 0
    plan = json.loads(capsys.readouterr().out)

    report = apply_setup_plan(service, plan["action_id"], plan["digest"])

    assert report.terminal_state == "complete"
    assert report.results[f"vault:{vault.resolve()}"] == "attached"
    assert _snapshot(vault) == before
    assert [fact.statement for fact in service.facts()] == ["Prefers worked examples before theory."]


def test_attach_reports_an_unreadable_record_schema_as_unverified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aptuni.domain.records import SchemaVersionError
    from aptuni.vault.store import Vault

    vault = _existing_vault(tmp_path)

    def newer_schema(self: Vault) -> None:
        raise SchemaVersionError("record schema is newer than this installation")

    monkeypatch.setattr(Vault, "verify", newer_schema)
    service = _fresh(tmp_path)
    with pytest.raises(AptuniError) as error:
        service.attach(vault)
    assert error.value.code == "vault_unverified"
    assert service.workspace.vault_path() is None


def test_setup_after_attach_uses_the_attached_vault_by_default(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    vault = _existing_vault(tmp_path)
    service = _fresh(tmp_path)
    service.attach(vault)
    capsys.readouterr()

    assert cli_run(["setup", "plan", "--lang", "en", "--source", "other", "--memory", "basic",
                    "--privacy", "local_only", "--no-host", "--json"], service) == 0
    plan = json.loads(capsys.readouterr().out)

    assert plan["vault_path"] == str(vault.resolve())
    report = apply_setup_plan(service, plan["action_id"], plan["digest"])
    assert report.terminal_state == "complete"
    assert report.results[f"vault:{vault.resolve()}"] == "already_present"


def test_setup_refuses_a_different_vault_at_plan_time(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    vault = _existing_vault(tmp_path)
    service = _fresh(tmp_path)
    service.attach(vault)
    capsys.readouterr()

    assert cli_run(["setup", "plan", "--lang", "zh-CN", "--source", "other", "--memory", "basic",
                    "--privacy", "local_only", "--no-host", "--vault", str(tmp_path / "Other")], service) == 2
    err = capsys.readouterr().err
    assert str(vault.resolve()) in err and "--vault" in err
