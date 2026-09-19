"""Basic Plugin Advisor: users choose experiences, the system chooses implementations (PRD §26–§30)."""

from __future__ import annotations

import pytest

from aptuni.advisor.catalog import load_catalog
from aptuni.advisor.recommend import AdvisorError, SetupAnswers, recommend


def answers(**overrides: object) -> SetupAnswers:
    values: dict[str, object] = {"locale": "en", "sources": frozenset({"folder"}), "memory": "basic",
                                 "privacy": "minimize_cloud", "hosts": frozenset({"codex"})}
    values.update(overrides)
    return SetupAnswers(**values)  # type: ignore[arg-type]


def selected(rec: object) -> set[str]:
    return {choice.plugin_id for choice in rec.selected}  # type: ignore[attr-defined]


def deferred(rec: object) -> set[str]:
    return {choice.plugin_id for choice in rec.deferred}  # type: ignore[attr-defined]


def test_case_a_codex_folder_gets_starter_lite_with_disclosed_host_egress() -> None:
    rec = recommend(answers(), load_catalog())
    assert rec.recipe_id == "starter-lite"
    assert {"source.folder", "memory.builtin", "retrieval.sqlite_fts", "agent.mcp", "agent.codex"} <= selected(rec)
    assert rec.host_release == "allowed_with_disclosure"
    assert "host_model" in rec.egress
    assert rec.required_api_keys == ()
    assert not rec.docker


def test_case_b_local_only_defers_adapters_and_discloses_host_file_access() -> None:
    """Review 20 B1: no content-free adapter mode ships, and hosts can still read files themselves."""
    rec = recommend(answers(privacy="local_only", hosts=frozenset({"claude_code"})), load_catalog())
    assert rec.host_release == "refused_local_only"
    assert "agent.claude_code" in deferred(rec)
    assert "agent.claude_code" not in selected(rec) and "agent.mcp" not in selected(rec)
    reasons = {c.plugin_id: c.reason for c in rec.deferred}
    assert reasons["agent.claude_code"] == "advisor.reason.adapter_needs_egress"
    assert rec.host_file_access
    assert "host_model" not in rec.egress
    assert "advisor.note.cli_only" not in rec.notes and "advisor.note.local_only_hosts" in rec.notes


def test_no_host_means_no_host_file_access_disclosure() -> None:
    rec = recommend(answers(hosts=frozenset()), load_catalog())
    assert not rec.host_file_access


def test_local_only_filters_plugins_that_cannot_run_locally(tmp_path: object) -> None:
    catalog = load_catalog()
    for plugin in catalog.plugins.values():
        rec = recommend(answers(privacy="local_only"), catalog)
        if not plugin.requirements.local_only_supported:
            assert plugin.id not in selected(rec)


def test_preview_reports_difficulty_and_retention() -> None:
    rec = recommend(answers(sources=frozenset({"github"})), load_catalog())
    assert rec.difficulty in {"easy", "moderate", "advanced"}
    assert "source_minimized" in rec.retention and "canonical" in rec.retention


def test_case_c_research_sources_get_researcher_and_optional_token() -> None:
    rec = recommend(answers(sources=frozenset({"github", "marginnote"}), hosts=frozenset({"claude_code", "codex"})),
                    load_catalog())
    assert rec.recipe_id == "researcher"
    assert "source.github" in selected(rec)
    assert [key.env for key in rec.optional_api_keys] == ["GITHUB_TOKEN"]
    assert "https://api.github.com" in rec.network
    assert {"agent.claude_code", "agent.codex"} <= selected(rec)


def test_case_d_no_host_is_cli_only() -> None:
    rec = recommend(answers(hosts=frozenset()), load_catalog())
    assert rec.host_release == "no_host"
    assert "interface.cli" in selected(rec)
    assert not {"agent.claude_code", "agent.codex"} & selected(rec)
    assert "advisor.note.cli_only" in rec.notes


def test_unshipped_sources_are_deferred_not_silently_dropped() -> None:
    rec = recommend(answers(sources=frozenset({"obsidian", "notion", "folder"})), load_catalog())
    assert {"source.obsidian", "source.notion"} <= deferred(rec)
    assert "source.folder" in selected(rec)


def test_automatic_memory_falls_back_to_available_recipe_and_says_why() -> None:
    rec = recommend(answers(memory="automatic"), load_catalog())
    assert rec.requested_recipe_id == "personal-memory"
    assert rec.recipe_id == "starter-lite"
    assert "memory.mem0" in deferred(rec)
    assert "memory.builtin" in selected(rec)
    assert "advisor.note.recipe_deferred" in rec.notes


def test_temporal_memory_with_research_sources_falls_back_to_researcher() -> None:
    rec = recommend(answers(memory="temporal", sources=frozenset({"github"})), load_catalog())
    assert rec.requested_recipe_id == "temporal-memory"
    assert rec.recipe_id == "researcher"
    assert "memory.graphiti" in deferred(rec)


def test_application_materials_map_to_folder_source() -> None:
    rec = recommend(answers(sources=frozenset({"application_materials"})), load_catalog())
    assert "source.folder" in selected(rec)


def test_other_hosts_are_protocol_notes_only() -> None:
    rec = recommend(answers(hosts=frozenset({"cursor", "claude_desktop"})), load_catalog())
    assert {"agent.cursor", "agent.claude_desktop"} <= deferred(rec)
    assert rec.host_release == "no_host"


def test_digest_is_stable_and_ignores_locale_but_not_choices() -> None:
    catalog = load_catalog()
    english = recommend(answers(), catalog)
    chinese = recommend(answers(locale="zh-CN"), catalog)
    assert english.digest == chinese.digest
    assert english.digest != recommend(answers(privacy="local_only"), catalog).digest


def test_setup_minutes_are_summed_ranges() -> None:
    rec = recommend(answers(), load_catalog())
    low, high = rec.setup_minutes
    assert 0 < low <= high


@pytest.mark.parametrize(("field", "value"), [
    ("memory", "telepathic"), ("privacy", "maybe"), ("locale", "fr"),
    ("sources", frozenset({"crystal-ball"})), ("hosts", frozenset({"emacs"})),
])
def test_invalid_answers_are_rejected(field: str, value: object) -> None:
    with pytest.raises(AdvisorError):
        recommend(answers(**{field: value}), load_catalog())
