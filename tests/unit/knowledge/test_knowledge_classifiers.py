"""ADR-0029: concept resolution, per-item classifiers, the authority ceiling and the level ladder."""

from __future__ import annotations

import pytest

from aptuni.knowledge.classify import capped, github_concept_signal, marginnote_signal
from aptuni.knowledge.code_usage import file_usage, is_scanned
from aptuni.knowledge.concepts import is_placeholder, is_structural, label_concept, resolve_label, resolve_text
from aptuni.knowledge.state import evidence_level

# ---------------------------------------------------------------- concept resolution


@pytest.mark.parametrize("text", ["XGBoost", "xgboost", "XGBClassifier", "Tuning an XGBRegressor", "XGBoost 原理"])
def test_names_and_classes_of_one_library_resolve_to_one_concept(text: str) -> None:
    assert resolve_text(text) == ("ml.xgboost",)


def test_chinese_aliases_resolve_without_word_boundaries() -> None:
    assert resolve_text("卷积神经网络基础") == ("ml.neural_networks",)
    assert resolve_text("随机森林与特征重要性") == ("ml.random_forest",)


def test_common_words_that_name_a_library_only_in_code_do_not_resolve_from_text() -> None:
    assert resolve_text("Erlenmeyer flask") == ()
    assert resolve_text("How atoms react") == ()


def test_an_unregistered_label_is_its_own_normalised_concept() -> None:
    assert resolve_label("Out-of-bag  Error") == (("label:out of bag error", "Out-of-bag Error"),)
    assert label_concept("   ") is None


# ---------------------------------------------------------------- GitHub code usage


def test_import_plus_construction_and_training_call_is_applied() -> None:
    code = "import xgboost as xgb\nmodel = xgb.XGBClassifier(max_depth=3)\nmodel.fit(X, y)\n"
    assert file_usage("src/train.py", code) == {"ml.xgboost": "applied"}


def test_an_import_alone_is_only_imported_and_a_technique_needs_a_call() -> None:
    assert file_usage("src/a.py", "import xgboost\n") == {"ml.xgboost": "imported"}
    usage = file_usage("src/b.py", "from sklearn.ensemble import RandomForestClassifier\n")
    assert usage == {"ml.scikit_learn": "imported"}, "random forest is not claimed from a shared import"


def test_construction_without_a_training_call_is_not_applied() -> None:
    code = "import xgboost as xgb\nmodel = xgb.XGBClassifier()\n"
    assert file_usage("src/c.py", code) == {"ml.xgboost": "imported"}


def test_manifests_declare_and_docs_mention_but_neither_applies() -> None:
    assert file_usage("requirements.txt", "xgboost==2.1\ntorchvision\n") == {"ml.xgboost": "declared"}
    assert file_usage("README.md", "Baselines use XGBoost and neural networks.") == {
        "ml.xgboost": "mentioned", "ml.neural_networks": "mentioned",
    }


def test_notebook_json_is_read_like_code() -> None:
    notebook = '{"cells": [{"source": ["import lightgbm as lgb\\n", "booster = lgb.train(params, data)\\n"]}]}'
    assert file_usage("analysis.ipynb", notebook) == {"ml.lightgbm": "applied"}


def test_only_manifests_code_and_docs_are_read_for_concepts() -> None:
    assert is_scanned("README.md") and is_scanned("pyproject.toml") and is_scanned("src/x.py")
    assert not is_scanned("config/settings.yaml")


# ---------------------------------------------------------------- item classifiers and ceiling


@pytest.mark.parametrize(("fields", "expected"), [
    ({"child_count": 0, "excerpt_count": 0, "annotated": 0}, "exposure"),
    ({"child_count": 0, "excerpt_count": 1, "annotated": 0}, "exposure"),
    ({"child_count": 1, "excerpt_count": 0, "annotated": 0}, "studied"),
    ({"child_count": 0, "excerpt_count": 2, "annotated": 0}, "studied"),
    ({"child_count": 0, "excerpt_count": 0, "annotated": 1}, "studied"),
])
def test_marginnote_card_classifier(fields: dict[str, int], expected: str) -> None:
    assert marginnote_signal(fields) == expected


def test_pre_adr_locator_reads_the_annotation_count_from_aptunis_own_summary() -> None:
    legacy = {"child_count": 0, "excerpt_count": 0}
    assert marginnote_signal(legacy, "A › B [NB]; 0 excerpts, 1 annotated, 0 sub-concepts") == "studied"
    assert marginnote_signal(legacy, "A › B [NB]; 0 excerpts, 0 annotated, 0 sub-concepts") == "exposure"
    assert marginnote_signal(legacy, None) == "exposure", "unknown stays conservative"


def test_authority_is_a_ceiling_not_a_label() -> None:
    assert capped("studied", "knowledge", ("knowledge.studied",)) == ("studied",)
    assert capped("studied", "knowledge", ()) == ("exposure",)
    assert capped("studied", "skills", ("knowledge.studied",)) == ("exposure",)
    assert capped("exposure", "knowledge", ("knowledge.studied",)) == ("exposure",)
    assert github_concept_signal({"usage": "applied"}) == "applied"
    assert github_concept_signal({"usage": "imported"}) == "exposure"


# ---------------------------------------------------------------- level ladder


@pytest.mark.parametrize(("counts", "contexts", "level"), [
    ({}, {}, "unknown"),
    ({"exposure": 3}, {"exposure": 2}, "exposed"),
    ({"studied": 1, "exposure": 9}, {"studied": 1}, "studied"),
    ({"applied": 4}, {"applied": 1}, "practiced"),
    ({"applied": 2}, {"applied": 2}, "strongly_practiced"),
    ({"demonstrated": 1}, {"demonstrated": 1}, "demonstrated"),
])
def test_evidence_level_is_read_directly_from_counts(
    counts: dict[str, int], contexts: dict[str, int], level: str,
) -> None:
    assert evidence_level(counts, contexts) == level


# ---------------------------------------------------------------- real-Vault resolution defects (rehearsal)


def test_latin_next_to_cjk_is_split_so_a_library_name_resolves() -> None:
    assert resolve_label("XGBoost视频笔记") == (("ml.xgboost", "XGBoost"),)
    assert resolve_label("视频笔记XGBoost") == (("ml.xgboost", "XGBoost"),)


@pytest.mark.parametrize("label", ["Proof", "EXAMPLE 2", "Summary", "总结", "例 3", "Problem Set 4", "定理一"])
def test_section_headings_are_structural(label: str) -> None:
    assert is_structural(label)


@pytest.mark.parametrize("label", ["Random forest", "Matrix", "Review of linear algebra", "Poisson process"])
def test_topics_are_not_structural(label: str) -> None:
    assert not is_structural(label)


def test_marginnote_image_placeholder_names_no_topic() -> None:
    assert is_placeholder("(image)") and is_placeholder("  ") and not is_placeholder("Image segmentation")
