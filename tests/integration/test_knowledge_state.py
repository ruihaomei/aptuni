"""ADR-0029: GitHub concept items, cross-source Knowledge State and compact Profile activation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import anyio
import pytest

from aptuni.application.service import AptuniService, HostContextAccess
from aptuni.application.source_commands import SourceCommands
from aptuni.application.workspace import Workspace
from aptuni.cli.main import run as cli_run
from aptuni.mcp.server import create_server
from aptuni.sources.github import GitHubTree
from marginnote_fixture import Card, build_store

APPLIED = "knowledge.applied"
TRAIN = b"import xgboost as xgb\nimport pandas as pd\nframe = pd.read_csv('d.csv')\n" \
        b"model = xgb.XGBClassifier(max_depth=4)\nmodel.fit(frame, frame.y)  # SECRET-CODE-LINE\n"


class FakeRepo:
    def __init__(self) -> None:
        self.blobs: dict[str, bytes] = {}
        self.files = {
            "README.md": self._add(b"# CT-FFR\nGradient models with XGBoost."),
            "requirements.txt": self._add(b"xgboost==2.1\npandas\nnumpy\n"),
            "src/train.py": self._add(TRAIN),
            "src/util.py": self._add(b"import numpy as np\n"),
        }
        self.fetched: list[str] = []

    def _add(self, body: bytes) -> str:
        sha = hashlib.sha1(f"blob {len(body)}\0".encode() + body, usedforsecurity=False).hexdigest()
        self.blobs[sha] = body
        return sha

    def put(self, path: str, body: bytes | None) -> None:
        if body is None:
            self.files.pop(path)
        else:
            self.files[path] = self._add(body)

    def fetch_tree(self) -> GitHubTree:
        tree = [{"path": p, "type": "blob", "sha": s, "size": len(self.blobs[s])} for p, s in self.files.items()]
        return GitHubTree({"repository_id": 42, "full_name": "ruihaomei/ctffr", "commit": "2" * 40,
                           "truncated": False, "tree": tree}, "main", ())

    def fetch_blob(self, sha: str) -> bytes:
        self.fetched.append(sha)
        return self.blobs[sha]


def _service(tmp_path: Path) -> AptuniService:
    service = AptuniService(Workspace(tmp_path / "state"))
    service.init(tmp_path / "Vault")
    return service


def _github(service: AptuniService, monkeypatch: pytest.MonkeyPatch, repo: FakeRepo) -> str:
    monkeypatch.setattr(SourceCommands, "_github_client", staticmethod(lambda _spec: repo))
    source = service.add_github_source("https://github.com/ruihaomei/ctffr", ("knowledge",), "repository")
    service.sync(source.id)
    return source.id


def _concepts(service: AptuniService, source_id: str) -> dict[str, tuple[str, ...]]:
    return {e.subject: e.signals for e in service.records().current_evidence(source_id)
            if e.provenance.locator.extension.schema_name == "github.concept" and e.change_kind != "retraction"}


def test_github_concept_items_are_exposure_until_the_owner_raises_the_ceiling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    source_id = _github(service, monkeypatch, FakeRepo())

    assert _concepts(service, source_id) == {"XGBoost": ("exposure",), "pandas": ("exposure",),
                                             "NumPy": ("exposure",)}
    xgb = next(e for e in service.records().current_evidence(source_id) if e.subject == "XGBoost")
    assert xgb.excerpt == ("XGBoost in ruihaomei/ctffr: applied in 1 file, declared in 1 file, mentioned in 1 file "
                           "(src/train.py, requirements.txt, README.md)")
    concept_items = [e for e in service.records().current_evidence(source_id)
                     if e.provenance.locator.extension.schema_name == "github.concept"]
    assert not any("SECRET-CODE-LINE" in json.dumps(e.model_dump(mode="json")) or "XGBClassifier(" in (e.excerpt or "")
                   for e in concept_items), "concept items never carry code text"
    assert service.facts() == []

    preview = service.source_authority_preview(source_id, APPLIED)
    assert len(preview.evidence_ids) == 2, "only applied usage qualifies; declared/imported/mentioned do not"
    result = service.grant_source_authority(source_id, APPLIED, preview.digest)

    assert (result.evidence_written, result.profile_written) == (2, 2)
    assert _concepts(service, source_id) == {"XGBoost": ("applied",), "pandas": ("applied",),
                                             "NumPy": ("exposure",)}
    assert {f.statement for f in service.facts()} == {"Applied XGBoost.", "Applied pandas."}
    assert service.doctor().ok


def test_concept_usage_follows_the_code_and_unchanged_files_are_not_fetched_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    repo = FakeRepo()
    source_id = _github(service, monkeypatch, repo)
    preview = service.source_authority_preview(source_id, APPLIED)
    service.grant_source_authority(source_id, APPLIED, preview.digest)
    repo.fetched.clear()

    assert service.sync(source_id).evidence_written == 0
    assert repo.fetched == [], "per-blob usage is cached in source state"

    repo.put("src/train.py", b"import xgboost as xgb\n")  # the model code is gone: import only
    service.sync(source_id)
    assert _concepts(service, source_id)["XGBoost"] == ("exposure",)
    assert _concepts(service, source_id)["pandas"] == ("exposure",), "only the manifest still names pandas"
    assert {r.statement for r in service.exposable() if r.record_type == "fact"} == set()
    assert service.doctor().ok


def test_a_marginnote_source_cannot_be_granted_applied(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service = _service(tmp_path)
    store = build_store(tmp_path / "mn" / "MarginNotes.sqlite", {1: Card(title="XGBoost", comments=True)})
    source = service.add_marginnote_source(store, ("NB-A",), ("knowledge",), "study-notes")
    with pytest.raises(Exception) as refused:
        service.source_authority_preview(source.id, APPLIED)
    assert getattr(refused.value, "code", "") == "source_authority_unsupported"


def _cross_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AptuniService:
    service = _service(tmp_path)
    cards = {1: Card(title="Machine learning", children=[2, 3], comments=True), 2: Card(title="XGBoost", comments=True),
             3: Card(title="Neural networks", comments=True)}
    store = build_store(tmp_path / "mn" / "MarginNotes.sqlite", cards)
    notes = service.add_marginnote_source(store, ("NB-A",), ("knowledge",), "study-notes",
                                          primary_for=("knowledge.studied",))
    service.sync(notes.id)
    source_id = _github(service, monkeypatch, FakeRepo())
    preview = service.source_authority_preview(source_id, APPLIED)
    service.grant_source_authority(source_id, APPLIED, preview.digest)
    service.remember("I used XGBoost for CT-FFR modelling", "knowledge")
    return service


def test_knowledge_state_aggregates_evidence_across_sources_and_keeps_claims_separate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _cross_source(tmp_path, monkeypatch)

    xgb, *_ = service.knowledge_states("How should I tune XGBoost?")
    assert xgb.concept_id == "ml.xgboost"
    assert (xgb.counts["studied"], xgb.counts["applied"], xgb.declared) == (1, 1, 1)
    assert xgb.level == "practiced"
    nn = next(s for s in service.knowledge_states() if s.concept_id == "ml.neural_networks")
    assert nn.level == "studied" and nn.counts["applied"] == 0
    assert "not a proficiency measure" in xgb.summary()


def test_profile_activation_leads_with_compact_knowledge_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service = _cross_source(tmp_path, monkeypatch)
    access = HostContextAccess("beta-host", frozenset({"context.read", "evidence.read"}), frozenset({"knowledge"}),
                               "remote_unknown", True)
    server = create_server(service, access, activation_required=True)

    async def exercise() -> dict:  # type: ignore[type-arg]
        result = await server.call_tool("aptuni_activate_context", {
            "intent": "aptuni.profile", "scope": "task", "query": "XGBoost", "modules": ["knowledge"],
            "max_units": 4000,
        })
        return result.structured_content["context"]  # type: ignore[index]

    context = anyio.run(exercise)
    items = context["items"]
    states = [item for item in items if item["kind"] == "knowledge_state"]
    assert states and states[0]["text"].startswith("Knowledge state · XGBoost: evidence level practiced")
    assert states[0]["tainted"] is True and states[0]["layer"] == "L2"
    cited = set(states[0]["canonical_ids"])
    rows = [item for item in items if item["canonical_id"]]
    assert not {item["canonical_id"] for item in rows if item["kind"] == "evidence"} & cited
    assert not any(item["text"] in {"Applied XGBoost.", "Studied Machine learning › XGBoost."} for item in rows)
    assert any(item["text"] == "I used XGBoost for CT-FFR modelling" for item in rows), "owner claims stay listed"


def test_knowledge_cli_lists_concepts_in_both_languages_and_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    service = _cross_source(tmp_path, monkeypatch)

    assert cli_run(["knowledge"], service) == 0
    out = capsys.readouterr().out
    assert "not a proficiency score" in out and "practiced" in out and "ml.xgboost" in out
    assert cli_run(["knowledge", "XGBoost", "--lang", "zh-CN"], service) == 0
    assert "实践过" in capsys.readouterr().out
    assert cli_run(["knowledge", "XGBoost", "--json"], service) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["states"][0]["concept_id"] == "ml.xgboost" and payload["states"][0]["level"] == "practiced"


def test_heading_and_image_cards_count_for_their_parent_topic(tmp_path: Path) -> None:
    service = _service(tmp_path)
    topics = {10 * n: f"Topic {n}" for n in range(1, 7)}
    cards: dict[int, Card] = {1: Card(title="Course", children=list(topics))}
    for key, title in topics.items():
        cards[key] = Card(title=title, children=[key + 1, key + 2])
        cards[key + 1] = Card(title="Worked example", comments=True)  # a heading under six parents
        cards[key + 2] = Card(title="Proof", comments=True)
    cards[99] = Card(title="", excerpt="figure", group=None)  # an untitled image card: a placeholder
    store = build_store(tmp_path / "mn" / "MarginNotes.sqlite", cards)
    source = service.add_marginnote_source(store, ("NB-A",), ("knowledge",), "study-notes",
                                           primary_for=("knowledge.studied",))
    service.sync(source.id)

    labels = {state.label for state in service.knowledge_states(limit=50)}
    assert {"Worked example", "Proof", "(image)"}.isdisjoint(labels)
    topic = next(s for s in service.knowledge_states(limit=50) if s.label == "Topic 3")
    assert topic.counts["studied"] == 3, "the topic card plus its example and proof cards"


def test_a_concept_whose_files_disappear_is_withdrawn_and_replay_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aptuni.application import ingest

    service = _service(tmp_path)
    repo = FakeRepo()
    source_id = _github(service, monkeypatch, repo)
    repo.put("src/util.py", None)
    repo.put("requirements.txt", b"xgboost==2.1\npandas\n")
    original = ingest.SourceStateStore.save

    def crash_once(self, state):  # type: ignore[no-untyped-def]
        monkeypatch.setattr(ingest.SourceStateStore, "save", original)
        raise OSError("simulated crash after the canonical commit")

    monkeypatch.setattr(ingest.SourceStateStore, "save", crash_once)
    with pytest.raises(OSError):
        service.sync(source_id)
    before = len(service.records())
    service.sync(source_id)  # recovers the pending state; nothing is written twice

    assert len(service.records()) == before
    assert "NumPy" not in _concepts(service, source_id)
    numpy = [e for e in service.records().current_evidence(source_id) if e.subject == "NumPy"]
    assert numpy and numpy[0].change_kind == "retraction"
    assert service.doctor().ok


def test_changed_rules_recompute_cached_usage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from aptuni.sources import github_concepts

    service = _service(tmp_path)
    repo = FakeRepo()
    source_id = _github(service, monkeypatch, repo)
    repo.fetched.clear()
    monkeypatch.setattr(github_concepts, "RULES_VERSION", 2)
    service.sync(source_id)
    assert len(repo.fetched) == 4, "every scanned file is read again under new rules"


def test_knowledge_state_units_respect_the_host_module_grant(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service = _cross_source(tmp_path, monkeypatch)
    service.remember("I used XGBoost at work", "experience")
    response = service.profile_context("XGBoost", modules=("experience",), budget=4000, limit=20,
                                       audience="owner_cli", access=None)
    states = [u for u in response.items if u.kind == "knowledge_state"]
    assert states and all("studied" not in u.signals and "applied" not in u.signals for u in states), \
        "knowledge-module Evidence never leaks into an experience-only request"


def test_profile_concepts_select_the_knowledge_state_the_query_does_not_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _cross_source(tmp_path, monkeypatch)
    response = service.profile_context("help me plan my next project", modules=("knowledge",), budget=4000,
                                       limit=20, audience="owner_cli", access=None, concepts=("xgboost",))
    states = [unit for unit in response.items if unit.kind == "knowledge_state"]
    assert states and states[0].text.startswith("Knowledge state · XGBoost")
