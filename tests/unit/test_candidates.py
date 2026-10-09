"""ADR-0032: the candidate inventory is derived from provenance only, bounded and credential-safe."""
from __future__ import annotations

import re
from types import SimpleNamespace as NS

from aptuni.application.candidates import build_inventory, candidate_id, select_evidence

SECRET = "API_KEY: sk-" + "test" + "1234567890" * 3


def evidence(identifier: str, schema: str, fields: dict, *, source: str = "src-1", subject: str = "Item",
             text: str = "Documented.") -> NS:
    return NS(id=identifier, record_type="evidence", module="knowledge", excerpt=text, statement=None,
              subject=subject, trust="untrusted_source", signals=("exposure",),
              provenance=NS(source_id=source, locator=NS(extension=NS(schema_name=schema, fields=fields))))


def repo(identifier: str, number: int, path: str, text: str = "Documented.") -> NS:
    return evidence(identifier, "github.locator",
                    {"repository_id": number, "owner_name": f"someone/Project{number}", "path": path}, text=text)


def card(identifier: str, subject: str, depth: int, subtree: int, notebook: str = "nb") -> NS:
    return evidence(identifier, "marginnote.locator",
                    {"notebook_id": notebook, "depth": depth, "subtree_concepts": subtree}, source="mn",
                    subject=subject)


def rows(inventory, category: str) -> list[dict]:
    return [candidate.row for candidate in inventory[category]]


def test_repositories_group_by_repository_with_readme_descriptor_without_markup() -> None:
    inventory = build_inventory([
        repo("a-src", 1, "src/a.py"),
        repo("a-readme", 1, "README.md", '<p align="center"><img src="x.png"></p># Project one ![b](b.svg) does X'),
        repo("b-src", 2, "src/b.py"),
    ])
    assert rows(inventory, "repositories") == [
        {"id": candidate_id("src-1", "repositories", "1"), "label": "Project1", "evidence": 2,
         "about": "Project one does X"},
        {"id": candidate_id("src-1", "repositories", "2"), "label": "Project2", "evidence": 1},
    ]
    assert [r.id for r in inventory["repositories"][0].records] == ["a-readme", "a-src"]


def test_documents_cover_folder_obsidian_and_notion_and_drop_extension() -> None:
    inventory = build_inventory([
        evidence("f", "folder.locator", {"relative_path": "recollections/club.md"}),
        evidence("o", "obsidian.locator", {"relative_path": "Projects/Thesis.md", "note_name": "Thesis",
                                           "folder_path": "Projects"}, source="obs"),
        evidence("n", "notion.locator", {"entity_id": "e1", "title": "Reading log", "entity_type": "page"},
                 source="notion"),
    ])
    assert sorted(row["label"] for row in rows(inventory, "documents")) == [
        "Projects/Thesis", "Reading log", "recollections/club"]


def test_subjects_are_large_root_topics_ranked_by_size_and_deduplicated() -> None:
    inventory = build_inventory([
        card("small", "Tiny", 0, 3),
        card("stats", "Statistics", 0, 40), card("stats-child", "Statistics › Tests", 1, 5),
        card("calc", "Calculus", 0, 90),
        card("calc-again", "Calculus", 0, 25, notebook="other"),
    ])
    assert [(row["label"], row["notes"]) for row in rows(inventory, "subjects")] == [
        ("Calculus", 90), ("Statistics", 40)]
    assert [r.id for r in inventory["subjects"][1].records] == ["stats", "stats-child"]


def test_ids_are_stable_opaque_and_category_tagged() -> None:
    first = build_inventory([repo("a", 7, "README.md")])["repositories"][0].id
    again = build_inventory([repo("b", 7, "src/x.py"), repo("c", 8, "README.md")])["repositories"][0].id
    assert first == again
    assert re.fullmatch(r"cr-[0-9a-f]{12}", first)


def test_credential_records_and_labels_never_reach_the_inventory() -> None:
    inventory = build_inventory([
        repo("secret-readme", 3, "README.md", SECRET),
        evidence("doc", "folder.locator", {"relative_path": f"{SECRET}.md"}),
        repo("clean", 4, "src/a.py"),
    ])
    assert [row["label"] for row in rows(inventory, "repositories")] == ["Project4"]
    assert rows(inventory, "documents") == []


def test_select_evidence_round_robins_caps_and_ignores_unknown_ids() -> None:
    inventory = build_inventory([
        repo("a-readme", 1, "README.md"), repo("a1", 1, "a/1.py"), repo("a2", 1, "a/2.py"), repo("a3", 1, "a/3.py"),
        repo("b-readme", 2, "README.md"),
    ])
    first, second = (candidate.id for candidate in inventory["repositories"])
    chosen, omitted = select_evidence(inventory, (first, second, "cr-000000000000"), per_candidate=3)
    assert [record.id for record in chosen] == ["a-readme", "b-readme", "a1", "a2"]
    assert omitted is True


def test_same_subject_in_several_notebooks_is_one_candidate_with_all_evidence() -> None:
    inventory = build_inventory([card("calc", "Calculus", 0, 90),
                                 card("calc-again", "Calculus", 0, 25, notebook="other")])
    (subject,) = inventory["subjects"]
    assert subject.row["notes"] == 90
    assert {record.id for record in subject.records} == {"calc", "calc-again"}
