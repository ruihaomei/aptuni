"""Bounded L0–L4 context composition over canonical records and the retrieval projection."""

from __future__ import annotations

from pathlib import Path

import pytest

from aptuni.application import service as service_module
from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace
from aptuni.retrieval.sqlite import SqliteProjection


@pytest.fixture()
def service(tmp_path: Path) -> AptuniService:
    app = AptuniService(Workspace(tmp_path / "state"))
    app.init(tmp_path / "Aptuni")
    return app


def test_identity_card_is_l0_and_uses_only_permitted_identity_facts(service: AptuniService) -> None:
    identity = service.remember("Graduate student in statistics.", "identity")
    service.remember("Uses Python for modeling.", "skills")
    response = service.identity_card(budget=1000)
    assert response.audience == "owner_cli"
    assert response.layers == ("L0",)
    [card] = response.items
    assert card.kind == "identity_card"
    assert card.text == "Graduate student in statistics."
    assert card.canonical_ids == (identity.id,)
    assert response.used_units <= response.requested_units
    assert response.used_units + response.remaining_units == response.requested_units

    service.set_module("identity", expose=False)
    hidden = service.identity_card(budget=1000)
    assert hidden.items == () and hidden.layers == ()


def test_context_returns_bounded_layers_ids_and_provenance(service: AptuniService) -> None:
    fact = service.remember("Applied 生存分析 with Kaplan-Meier curves.", "knowledge")
    response = service.context("生存", modules=("knowledge",), budget=2000)
    assert response.layers == ("L1", "L2", "L3")
    record = next(item for item in response.items if item.layer == "L3")
    assert record.canonical_id == fact.id
    assert record.module == "knowledge"
    assert record.trust == "user_declared" and not record.tainted
    assert record.source_id is None
    assert response.policy_epoch == 1
    assert response.used_units <= 2000


def test_evidence_is_l4_opt_in_tainted_and_minimized(service: AptuniService, tmp_path: Path) -> None:
    fact = service.remember("Applied causal inference in a project.", "knowledge")
    docs = tmp_path / "notes"
    docs.mkdir()
    (docs / "study.md").write_text("Studied causal inference and propensity scores.", encoding="utf-8")
    source = service.add_folder_source(docs, modules=("knowledge",), role="study_notes")
    service.sync(source.id)
    without_evidence = service.context("causal", budget=2000)
    assert all(item.layer != "L4" for item in without_evidence.items)
    assert any(item.canonical_id == fact.id for item in without_evidence.items)

    response = service.context("causal", budget=2000, include_evidence=True)
    assert response.layers == ("L1", "L2", "L3", "L4")
    evidence = next(item for item in response.items if item.layer == "L4")
    assert evidence.kind == "evidence"
    assert evidence.source_id == source.id
    assert evidence.trust == "untrusted_source" and evidence.tainted
    assert evidence.signals == ("exposure",)
    assert len(evidence.text) <= 280


def test_context_response_is_deterministic_for_an_unchanged_vault(service: AptuniService) -> None:
    service.remember("Uses deterministic context budgets.", "skills")
    first = service.context("deterministic", budget=2000)
    second = service.context("deterministic", budget=2000)
    assert first == second


def test_budget_is_exact_and_omission_sets_truncation(service: AptuniService) -> None:
    service.remember("Bayesian posterior calibration.", "knowledge")
    full = service.context("Bayesian", budget=5000)
    sections_only_budget = 32 + sum(item.units for item in full.items if item.layer in ("L1", "L2"))
    bounded = service.context("Bayesian", budget=sections_only_budget)
    assert bounded.used_units <= sections_only_budget
    assert bounded.used_units + bounded.remaining_units == sections_only_budget
    assert bounded.truncated
    assert all(item.layer != "L3" for item in bounded.items)


def test_policy_change_during_composition_retries_without_leak(
    service: AptuniService, monkeypatch: pytest.MonkeyPatch,
) -> None:
    service.remember("Private causal inference notes.", "knowledge")
    service.search("causal")
    original = SqliteProjection.search
    changed = False

    def race(self: SqliteProjection, *args: object, **kwargs: object) -> list[object]:
        nonlocal changed
        if not changed:
            changed = True
            service.set_module("knowledge", expose=False)
        return original(self, *args, **kwargs)  # type: ignore[return-value]

    monkeypatch.setattr(SqliteProjection, "search", race)
    response = service.context("causal", budget=2000)
    assert all(item.canonical_id is None for item in response.items)
    assert "knowledge" not in next((item.text for item in response.items if item.layer == "L2"), "")


def test_policy_change_during_budget_packing_discards_the_composed_response(
    service: AptuniService, monkeypatch: pytest.MonkeyPatch,
) -> None:
    service.remember("Private Bayesian notes.", "knowledge")
    original = service_module.pack_units
    changed = False

    def race(*args: object, **kwargs: object) -> object:
        nonlocal changed
        result = original(*args, **kwargs)  # type: ignore[arg-type]
        if not changed:
            changed = True
            service.set_module("knowledge", expose=False)
        return result

    monkeypatch.setattr(service_module, "pack_units", race)
    response = service.context("Bayesian", budget=2000)
    assert all(item.canonical_id is None for item in response.items)


@pytest.mark.parametrize(
    ("kwargs", "code"),
    [
        ({"query": "", "budget": 1000}, "invalid_context"),
        ({"query": "test", "budget": 31}, "invalid_context"),
        ({"query": "test", "budget": 1000, "limit": 0}, "invalid_context"),
        ({"query": "界" * 400, "budget": 1000}, "invalid_context"),
        ({"query": "test", "budget": 1000, "include_evidence": 1}, "invalid_context"),
        ({"query": "test", "budget": 1000, "audience": "remote_model"}, "egress_not_authorized"),
    ],
)
def test_invalid_or_unauthorized_context_request_fails_closed(
    service: AptuniService, kwargs: dict[str, object], code: str,
) -> None:
    with pytest.raises(AptuniError) as error:
        service.context(**kwargs)  # type: ignore[arg-type]
    assert error.value.code == code
