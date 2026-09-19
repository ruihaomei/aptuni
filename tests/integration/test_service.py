"""Application service: init, remember, correct/retract, module policy, status and doctor."""

from __future__ import annotations

import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace


@pytest.fixture()
def service() -> Iterator[AptuniService]:
    with tempfile.TemporaryDirectory() as raw:
        base = Path(raw)
        workspace = Workspace(state_dir=base / "state")
        svc = AptuniService(workspace)
        svc.init(base / "Aptuni")
        yield svc


def test_init_creates_vault_policy_and_config(service: AptuniService) -> None:
    status = service.status()
    assert status.seq == 1
    assert status.policy_epoch == 1
    assert all(switch == (True, True) for switch in status.modules.values())
    assert status.vault_path.name == "Aptuni"


def test_init_refuses_existing_vault(service: AptuniService) -> None:
    with pytest.raises(AptuniError) as error:
        service.init(service.status().vault_path)
    assert error.value.code == "vault_exists"


def test_state_dir_must_be_outside_the_vault() -> None:
    with tempfile.TemporaryDirectory() as raw:
        vault = Path(raw) / "Aptuni"
        svc = AptuniService(Workspace(state_dir=vault / "state"))
        with pytest.raises(AptuniError) as error:
            svc.init(vault)
        assert error.value.code == "state_inside_vault"


def test_remember_then_list_current_facts(service: AptuniService) -> None:
    fact = service.remember("Prefers concise, structured explanations.", module="preferences")
    facts = service.facts()
    assert [f.id for f in facts] == [fact.id]
    assert fact.trust == "user_declared"
    assert fact.review_status == "declared"


def test_remember_respects_ingest_switch(service: AptuniService) -> None:
    service.set_module("experience", ingest=False)
    with pytest.raises(AptuniError) as error:
        service.remember("Worked at ACME.", module="experience")
    assert error.value.code == "module_ingest_disabled"


def test_expose_switch_hides_facts_from_context_but_not_from_owner(service: AptuniService) -> None:
    fact = service.remember("Worked at ACME as an analyst.", module="experience")
    service.set_module("experience", expose=False)
    assert fact.id in {f.id for f in service.facts()}
    assert fact.id not in {r.id for r in service.exposable()}
    assert service.status().policy_epoch == 2


def test_correction_supersedes_and_keeps_history(service: AptuniService) -> None:
    old = service.remember("Class rank 2.", module="experience")
    new = service.correct(old.id, "Class rank 1.")
    current = {f.id for f in service.facts()}
    assert new.id in current and old.id not in current
    assert new.supersedes == (old.id,)
    assert old.id in {r.id for r in service.history()}


def test_retract_removes_from_current_view_without_deleting(service: AptuniService) -> None:
    fact = service.remember("Interested in quantitative finance.", module="interests")
    service.retract(fact.id)
    assert fact.id not in {f.id for f in service.facts()}
    assert fact.id in {r.id for r in service.history()}


def test_mastery_claims_are_rejected(service: AptuniService) -> None:
    with pytest.raises(AptuniError) as error:
        service.remember("Proficient in XGBoost.", module="skills")
    assert error.value.code == "invariant_violation"


def test_unknown_module_is_rejected(service: AptuniService) -> None:
    with pytest.raises(AptuniError) as error:
        service.remember("x", module="secrets")
    assert error.value.code == "unknown_module"


def test_doctor_reports_healthy_vault(service: AptuniService) -> None:
    service.remember("Uses Python daily.", module="skills")
    report = service.doctor()
    assert report.ok, report.problems


def test_service_reopens_from_saved_config() -> None:
    with tempfile.TemporaryDirectory() as raw:
        base = Path(raw)
        first = AptuniService(Workspace(state_dir=base / "state"))
        first.init(base / "Aptuni")
        first.remember("Lives in Shanghai.", module="identity")
        again = AptuniService(Workspace(state_dir=base / "state"))
        assert [f.statement for f in again.facts()] == ["Lives in Shanghai."]


def test_commands_without_init_fail_with_guidance() -> None:
    with tempfile.TemporaryDirectory() as raw:
        svc = AptuniService(Workspace(state_dir=Path(raw) / "state"))
        with pytest.raises(AptuniError) as error:
            svc.status()
        assert error.value.code == "not_initialized"
