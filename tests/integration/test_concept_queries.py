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
    assert concept_expressions("machine translation") == (
        '("machine" OR "machines") AND ("translation" OR "translations")', None)
    strict, relaxed = concept_expressions("markov chain stationary distribution")
    assert strict == ('("markov" OR "markovs") AND ("chain" OR "chains") AND ("stationary" OR "stationarys") '
                      'AND ("distribution" OR "distributions")')
    assert relaxed is not None and relaxed.count(" OR (") == 2 and '"chain" OR "chains"' in relaxed


def test_english_keywords_fold_plural_forms_in_concept_mode() -> None:
    assert concept_expressions("chains")[0] == '("chains" OR "chain")'
    assert concept_expressions("matrices")[0] == '("matrices" OR "matrice" OR "matric")'
    assert concept_expressions("probabilities")[0] == (
        '("probabilities" OR "probabilitie" OR "probabiliti" OR "probability")')
    assert concept_expressions("sql")[0] == '("sql" OR "sqls")'
    assert concept_expressions("r")[0] == '"r"'  # two letters or fewer stay exact


def test_a_concept_matches_a_different_plural_form(tmp_path: Path) -> None:
    projection = _projection(tmp_path, {"fct_pl": "Markov chains and stationary distributions.",
                                        "fct_hmm": "HMM training."})
    assert [row.record_id for row in projection.search_concepts(("markov chain",), limit=5)] == ["fct_pl"]
    assert concept_expressions("平稳分布")[0] == (
        '("平稳" AND "稳分" AND "分布" AND "平稳分" AND "稳分布" AND "平稳分布")')
    assert concept_expressions("the of") == (None, None)
    assert concept_expressions('" OR NOT *')[0] == '("not" OR "nots")'  # FTS syntax stays quoted data


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


@pytest.mark.parametrize("concepts", [("",), ("x" * 400,), tuple(f"c{i}" for i in range(9))])
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


def test_more_matched_concepts_always_rank_first_even_with_many_concepts(tmp_path: Path) -> None:
    texts = {f"fct_three_{i}": f"alpha beta gamma filler{i}" for i in range(12)}
    texts["fct_four"] = "alpha beta gamma delta"
    projection = _projection(tmp_path, texts)
    rows = projection.search_concepts(("alpha", "beta", "gamma", "delta"), limit=20)
    assert rows[0].record_id == "fct_four"


def test_concepts_differing_only_in_case_or_punctuation_count_once(tmp_path: Path) -> None:
    projection = _projection(tmp_path, {"fct_ml": "Machine learning workflow.", "fct_dl": "Deep learning notes."})
    rows = projection.search_concepts(("Machine Learning", "machine-learning", "deep learning"), limit=5)
    assert rows[0].score == rows[1].score  # the duplicate did not add a second point


def test_profile_and_memory_intents_pass_concepts(service: AptuniService) -> None:
    fact = service.remember("Studied Markov chains.", "knowledge")
    service.remember("Studied HMM training.", "knowledge")
    memory = service.observe("Prefers Markov chain examples in explanations.", "preferences")
    access = HostContextAccess("claude-adapter", frozenset({"context.read", "evidence.read"}),
                               frozenset({"knowledge", "preferences"}), "remote_unknown", True)
    server = create_server(service, access, activation_required=True)

    async def exercise() -> None:
        profile = await server.call_tool("aptuni_activate_context", {
            "intent": "aptuni.profile", "query": "teach me", "concepts": ["markov chain"],
            "modules": ["knowledge"],
        })
        ids = [i["canonical_id"] for i in profile.structured_content["context"]["items"] if i["layer"] == "L3"]
        assert ids == [fact.id]
        remembered = await server.call_tool("aptuni_activate_context", {
            "intent": "aptuni.memory", "query": "teach me", "concepts": ["basketball training"],
            "modules": ["preferences"],
        })
        assert not [i for i in remembered.structured_content["context"]["items"] if i["layer"] == "L3"]
        assert memory.memory_id is not None

    anyio.run(exercise)


def test_concept_mode_reports_more_results_and_schema_limits(service: AptuniService) -> None:
    for index in range(4):
        service.remember(f"Studied Markov chains part {index}.", "knowledge")
    assert service.context("t", concepts=("markov chain",), limit=2).truncated is True
    access = HostContextAccess("claude-adapter", frozenset({"context.read"}), frozenset({"knowledge"}),
                               "remote_unknown", True)
    server = create_server(service, access, activation_required=True)

    async def exercise() -> None:
        from mcp.server.mcpserver.exceptions import ToolError

        with pytest.raises(ToolError, match="aptuni_activation_required"):
            await server.call_tool("aptuni_search_context", {
                "query": "t", "concepts": ["markov chain"], "modules": ["knowledge"]})
        with pytest.raises(ToolError):
            await server.call_tool("aptuni_activate_context", {
                "intent": "aptuni.full", "query": "t", "concepts": [f"c{i}" for i in range(9)],
                "modules": ["knowledge"]})

    anyio.run(exercise)


def test_wrong_concept_types_get_an_accurate_message(service: AptuniService) -> None:
    with pytest.raises(AptuniError, match="list of strings"):
        service.context("t", concepts="markov chain")  # type: ignore[arg-type]
