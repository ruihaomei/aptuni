"""Context diversification: distinct concepts first; repeats and crowded notebooks later, never dropped."""

from types import SimpleNamespace

from aptuni.domain.evidence_profile import EVIDENCE_PROFILE_TYPE
from aptuni.retrieval.diversify import concept_key, diversify


def _fact(rid: str, subject: str) -> SimpleNamespace:
    return SimpleNamespace(id=rid, record_type="fact", type=EVIDENCE_PROFILE_TYPE, subject=subject,
                           statement=f"Studied {subject}.")


def _evidence(rid: str, subject: str) -> SimpleNamespace:
    return SimpleNamespace(id=rid, record_type="evidence", subject=subject, excerpt=None)


def _declared(rid: str, statement: str) -> SimpleNamespace:
    return SimpleNamespace(id=rid, record_type="fact", type="declared_statement", subject="self", statement=statement)


def test_concept_key_collapses_case_spacing_and_repeated_path_segments() -> None:
    assert concept_key(_fact("a", "Machine Learning › Machine Learning")) == "machine learning"
    assert concept_key(_evidence("b", "  machine   learning ")) == "machine learning"
    assert concept_key(_fact("c", "A › B › B › C")) == "a › b › c"


def test_declared_facts_are_keyed_by_statement_not_their_shared_subject() -> None:
    assert concept_key(_declared("d1", "Prefers concise answers.")) == "prefers concise answers"
    assert concept_key(_declared("d1", "Prefers concise answers.")) != concept_key(_declared("d2", "Likes tea."))


def test_fact_its_evidence_and_nested_repeats_move_after_distinct_concepts() -> None:
    rows = [
        _fact("f1", "Markov › Stationary distribution"),
        _evidence("e1", "Markov › Stationary distribution"),
        _fact("f2", "Markov › Markov › Stationary distribution"),
        _fact("f3", "Markov › Hitting times"),
    ]
    assert [r.id for r in diversify(rows)] == ["f1", "f3", "e1", "f2"]


def test_a_crowded_notebook_is_demoted_not_dropped() -> None:
    rows = [_fact(f"a{i}", f"Analysis › topic {i}") for i in range(5)] + [_fact("b0", "Algebra › groups")]
    assert [r.id for r in diversify(rows, per_root=3)] == ["a0", "a1", "a2", "b0", "a3", "a4"]


def test_full_width_sentence_end_is_normalized() -> None:
    assert concept_key(_declared("d1", "喜欢简洁的回答。")) == concept_key(_declared("d2", "喜欢简洁的回答"))
