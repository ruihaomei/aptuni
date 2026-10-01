"""ADR-0030: host-structured concept queries match each concept whole and never leak on one word."""

from __future__ import annotations

from pathlib import Path

import anyio
import pytest

from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService, HostContextAccess
from aptuni.application.workspace import Workspace
from aptuni.mcp.server import create_server
from aptuni.retrieval.lexical import concept_expressions
from aptuni.retrieval.sqlite import ProjectionDocument, SqliteProjection


def _projection(tmp_path: Path, texts: dict[str, str]) -> SqliteProjection:
    projection = SqliteProjection(tmp_path / "state")
    projection.rebuild([ProjectionDocument(rid, "fact", "knowledge", None, text) for rid, text in texts.items()],
                       vault_seq=1)
    return projection


def test_concept_expressions_are_strict_and_relax_only_to_adjacent_pairs() -> None:
    assert concept_expressions("machine translation") == ('"machine" AND "translation"', None)
    strict, relaxed = concept_expressions("markov chain stationary distribution")
    assert strict == '"markov" AND "chain" AND "stationary" AND "distribution"'
    assert relaxed == ('("markov" AND "chain") OR ("chain" AND "stationary") OR '
                       '("stationary" AND "distribution")')
    assert concept_expressions("平稳分布")[0] == (
        '("平稳" AND "稳分" AND "分布" AND "平稳分" AND "稳分布" AND "平稳分布")')
    assert concept_expressions("the of") == (None, None)
    assert concept_expressions('" OR NOT *')[0] == '"not"'  # FTS syntax stays quoted data


def test_a_concept_never_matches_on_one_of_its_words(tmp_path: Path) -> None:
    projection = _projection(tmp_path, {
        "fct_hmm": "HMM model building and training.",
        "fct_shift": "Shifting theorem (translation).",
        "fct_ml": "Machine learning workflow.",
    })
    assert projection.search_concepts(("basketball training",), limit=10) == []
    assert projection.search_concepts(("machine translation", "机器翻译"), limit=10) == []


def test_records_matching_more_concepts_rank_first_and_alternates_union(tmp_path: Path) -> None:
    projection = _projection(tmp_path, {
        "fct_both": "Markov chain stationary distribution.",
        "fct_markov": "Markov chain hitting times.",
        "fct_zh": "马尔可夫链 平稳分布 的求解。",
        "fct_other": "Group theory subgroups.",
    })
    rows = projection.search_concepts(("markov chain", "stationary distribution", "平稳分布"), limit=10)
    ids = [row.record_id for row in rows]
    assert ids[0] == "fct_both"
    assert set(ids) == {"fct_both", "fct_markov", "fct_zh"}


def test_a_long_concept_without_a_full_match_relaxes_to_word_pairs(tmp_path: Path) -> None:
    projection = _projection(tmp_path, {
        "fct_pair": "Equilibrium; stationary distribution of a chain.",
        "fct_single": "Distribution of exam marks.",
    })
    ids = [row.record_id for row in projection.search_concepts(("markov chain stationary distribution",), limit=10)]
    assert ids == ["fct_pair"]


@pytest.fixture()
def service(tmp_path: Path) -> AptuniService:
    app = AptuniService(Workspace(tmp_path / "state"))
    app.init(tmp_path / "Aptuni")
    return app


def test_context_uses_concepts_and_keeps_exposure_and_the_plain_query_path(service: AptuniService) -> None:
    kept = service.remember("Studied Markov chain stationary distributions.", "knowledge")
    hidden = service.remember("Markov chain notes for a private goal.", "goals")
    service.remember("Studied HMM training.", "knowledge")
    service.set_module("goals", expose=False)
    response = service.context("help me review", concepts=("markov chain",), budget=4000)
    ids = [item.canonical_id for item in response.items if item.layer == "L3"]
    assert ids == [kept.id] and hidden.id not in ids
    assert service.context("basketball training plan", concepts=("basketball training",), budget=4000).items[0].text \
        == "no matching permitted context"
    # Without concepts the 0.2.0b9 path is unchanged: generic single words may still match.
    plain = service.context("basketball training plan", budget=4000)
    assert any(item.layer == "L3" for item in plain.items)


@pytest.mark.parametrize("concepts", [("",), ("x" * 300,), tuple(f"c{i}" for i in range(9))])
def test_invalid_concepts_are_refused(service: AptuniService, concepts: tuple[str, ...]) -> None:
    with pytest.raises(AptuniError) as refused:
        service.context("task", concepts=concepts)
    assert refused.value.code == "invalid_context"


def test_mcp_activation_and_search_accept_concepts(service: AptuniService) -> None:
    fact = service.remember("Studied Markov chain stationary distributions.", "knowledge")
    service.remember("Studied HMM training.", "knowledge")
    access = HostContextAccess("claude-adapter", frozenset({"context.read", "evidence.read"}),
                               frozenset({"knowledge"}), "remote_unknown", True)
    server = create_server(service, access, activation_required=True)

    async def exercise() -> None:
        result = await server.call_tool("aptuni_activate_context", {
            "intent": "aptuni.full", "scope": "session", "query": "review for my exam",
            "concepts": ["markov chain", "马尔可夫链"], "modules": ["knowledge"],
        })
        items = result.structured_content["context"]["items"]
        assert [i["canonical_id"] for i in items if i["layer"] == "L3"] == [fact.id]
        searched = await server.call_tool("aptuni_search_context", {
            "query": "plan", "concepts": ["basketball training"], "modules": ["knowledge"],
        })
        assert not [i for i in searched.structured_content["items"] if i["layer"] == "L3"]

    anyio.run(exercise)


def test_cli_context_accepts_repeatable_concepts(
    service: AptuniService, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    from aptuni.cli.main import main

    service.remember("Studied Markov chain stationary distributions.", "knowledge")
    service.remember("Studied HMM training.", "knowledge")
    monkeypatch.setenv("APTUNI_STATE_DIR", str(service.workspace.state_dir))
    assert main(["context", "review", "--concept", "markov chain", "--concept", "basketball training"]) == 0
    out = capsys.readouterr().out
    assert "Markov chain" in out and "HMM" not in out


def test_full_skill_asks_for_concepts() -> None:
    from aptuni.adapters.manager import AdapterManager

    assert "`concepts`" in AdapterManager._skill("full", "aptuni.full", claude=True)
