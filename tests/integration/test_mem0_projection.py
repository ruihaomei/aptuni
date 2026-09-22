"""Production Mem0 projection boundary: rebuild-only, exact, and privacy-invalidated."""

from __future__ import annotations

import importlib.util
import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from typing import Any

import pytest

from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace
from aptuni.cli.main import run
from aptuni.memory.mem0_local import LocalMem0Client, _safe_ollama_client_type, create_local_mem0_client
from aptuni.memory.provider import Mem0Projection


class FakeMem0Client:
    def __init__(self, root: Path, *, corrupt: bool = False, fail_add: bool = False) -> None:
        self.root = root
        self.corrupt = corrupt
        self.fail_add = fail_add
        self.rows: list[dict[str, Any]] = []
        self.calls: list[dict[str, Any]] = []

    def add(self, text: str, *, user_id: str, metadata: dict[str, Any], infer: bool) -> dict[str, Any]:
        self.calls.append({"text": text, "user_id": user_id, "metadata": metadata, "infer": infer})
        if self.fail_add:
            raise RuntimeError("synthetic provider failure with private content")
        row = {"id": f"provider-{len(self.rows)}", "memory": text, "metadata": dict(metadata)}
        self.rows.append(row)
        return {"results": [{"id": row["id"], "event": "ADD"}]}

    def get_all(self, *, filters: dict[str, str], top_k: int) -> dict[str, Any]:
        del filters, top_k
        rows = [dict(row) for row in self.rows]
        if self.corrupt and rows:
            rows[0] = rows[0] | {"memory": "changed provider value"}
        return {"results": rows}

    def search(self, query: str, *, user_id: str, limit: int) -> dict[str, Any]:
        del query, user_id
        return {"results": self.rows[:limit]}

    def close(self) -> None:
        (self.root / "client-closed").write_text("closed\n", encoding="ascii")


def _service(tmp_path: Path) -> AptuniService:
    service = AptuniService(Workspace(tmp_path / "state"))
    service.init(tmp_path / "vault")
    return service


def _accepted(service: AptuniService, statement: str = "Prefers exact derivations.") -> str:
    candidate = service.observe(statement, "preferences")
    preview = service.memory_preview(candidate.candidate_id)
    memory_id = service.decide_memory(candidate.candidate_id, "accept", preview.digest("accept"))
    assert memory_id is not None
    return memory_id


def test_rebuild_uses_infer_false_exact_metadata_and_whole_store_delete(tmp_path: Path) -> None:
    service = _service(tmp_path)
    memory_id = _accepted(service)
    clients: list[FakeMem0Client] = []

    def factory(root: Path) -> FakeMem0Client:
        client = FakeMem0Client(root)
        clients.append(client)
        return client

    report = service.rebuild_memory_provider(factory)
    assert report.records == 1 and report.vault_seq == service.status().seq
    assert clients[0].calls == [{
        "text": "Prefers exact derivations.",
        "user_id": "aptuni-local-profile",
        "metadata": {
            "aptuni_canonical_id": memory_id,
            "aptuni_schema_version": 1,
            "aptuni_module": "preferences",
        },
        "infer": False,
    }]
    status = service.memory_provider_status()
    assert status.state == "ready" and status.records == 1
    assert not status.capabilities.inference and not status.capabilities.incremental_delete
    assert status.capabilities.whole_store_delete
    service.remember("A later canonical change.", "preferences")
    assert service.memory_provider_status().state == "stale"
    assert service.delete_memory_provider()
    assert service.memory_provider_status().state == "absent"
    assert not service.delete_memory_provider()
    assert [memory.id for memory in service.memories()] == [memory_id]


@pytest.mark.parametrize("failure", ["add", "enumeration"])
def test_failed_rebuild_keeps_prior_generation_and_hides_provider_error(tmp_path: Path, failure: str) -> None:
    service = _service(tmp_path)
    _accepted(service)
    service.rebuild_memory_provider(FakeMem0Client)
    current = (service.workspace.state_dir / "projections" / "memory" / "mem0" / "CURRENT").read_bytes()

    with pytest.raises(AptuniError) as caught:
        service.rebuild_memory_provider(
            lambda root: FakeMem0Client(root, corrupt=failure == "enumeration", fail_add=failure == "add")
        )
    assert caught.value.code == "memory_provider_rebuild_failed"
    assert "private content" not in caught.value.message
    assert (service.workspace.state_dir / "projections" / "memory" / "mem0" / "CURRENT").read_bytes() == current
    assert service.memory_provider_status().state == "ready"


def test_post_publication_cleanup_failure_keeps_new_generation_valid_and_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    _accepted(service)
    first = service.rebuild_memory_provider(FakeMem0Client)
    real_rmtree = shutil.rmtree

    def refuse_old(path: Path, *args: Any, **kwargs: Any) -> None:
        if Path(path).name == first.generation:
            raise OSError("synthetic old-generation cleanup failure")
        real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr("aptuni.memory.provider.shutil.rmtree", refuse_old)
    second = service.rebuild_memory_provider(FakeMem0Client)
    assert second.generation != first.generation and second.cleanup_pending
    status = service.memory_provider_status()
    assert status.state == "cleanup_required" and status.vault_seq == service.status().seq


def test_post_publication_generation_enumeration_failure_cannot_strand_current(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    _accepted(service)
    first = service.rebuild_memory_provider(FakeMem0Client)
    generations = service.workspace.state_dir / "projections" / "memory" / "mem0" / "generations"
    real_iterdir = Path.iterdir

    def refuse_generation_scan(path: Path) -> Any:
        if path == generations:
            raise OSError("synthetic enumeration failure after publication")
        return real_iterdir(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "iterdir", refuse_generation_scan)
        second = service.rebuild_memory_provider(FakeMem0Client)
    assert second.generation != first.generation and second.cleanup_pending
    assert service.memory_provider_status().state == "cleanup_required"


def test_malformed_provider_enumeration_row_is_rejected(tmp_path: Path) -> None:
    service = _service(tmp_path)
    _accepted(service)

    class MalformedClient(FakeMem0Client):
        def get_all(self, *, filters: dict[str, str], top_k: int) -> dict[str, Any]:
            value = super().get_all(filters=filters, top_k=top_k)
            value["results"].append("not-a-row")
            return value

    with pytest.raises(AptuniError) as caught:
        service.rebuild_memory_provider(MalformedClient)
    assert caught.value.code == "memory_provider_rebuild_failed"
    assert service.memory_provider_status().state == "absent"


def test_revocation_and_privacy_purge_remove_projection_by_rebuild_or_whole_root(tmp_path: Path) -> None:
    service = _service(tmp_path)
    memory_id = _accepted(service)
    service.rebuild_memory_provider(FakeMem0Client)

    forget = service.memory_forget_preview(memory_id)
    service.forget_memory_confirmed(memory_id, forget.digest())
    rebuilt = service.rebuild_memory_provider(FakeMem0Client)
    assert rebuilt.records == 0

    fact = service.remember("A temporary preference.", "preferences")
    preview = service.privacy_purge_preview((fact.id,))
    assert "memory_provider_projection" in preview.managed_copy_ids
    receipt = service.confirm_privacy_purge(preview.action_id, preview.digest)
    results = {item.copy_class: item.result for item in receipt.per_copy}
    assert results["memory_provider_projection"] == "deleted"
    assert service.memory_provider_status().state == "absent"


def test_confirmed_purge_cannot_race_a_rebuild_that_contains_old_canonical_state(tmp_path: Path) -> None:
    service = _service(tmp_path)
    _accepted(service)
    fact = service.remember("Delete this unrelated fact.", "preferences")
    preview = service.privacy_purge_preview((fact.id,))
    entered = Event()
    release = Event()

    class BlockingClient(FakeMem0Client):
        def add(self, text: str, *, user_id: str, metadata: dict[str, Any], infer: bool) -> dict[str, Any]:
            entered.set()
            assert release.wait(timeout=5)
            return super().add(text, user_id=user_id, metadata=metadata, infer=infer)

    with ThreadPoolExecutor(max_workers=2) as executor:
        rebuilding = executor.submit(service.rebuild_memory_provider, BlockingClient)
        assert entered.wait(timeout=5)
        purging = executor.submit(service.confirm_privacy_purge, preview.action_id, preview.digest)
        release.set()
        rebuilding.result(timeout=10)
        purging.result(timeout=10)
    assert service.memory_provider_status().state == "absent"


def test_cli_status_and_delete_are_content_free_and_rebuild_missing_is_bounded(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    assert run(["memory", "provider", "status", "--json"], service) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["state"] == "absent"
    assert payload["capabilities"]["inference"] is False

    def unavailable(_root: Path) -> LocalMem0Client:
        raise AptuniError("memory_provider_unavailable", "Optional dependency is unavailable.")

    monkeypatch.setattr("aptuni.application.memory_commands.create_local_mem0_client", unavailable)
    with pytest.raises(AptuniError) as caught:
        run(["memory", "provider", "rebuild", "--json"], service)
    assert caught.value.code == "memory_provider_unavailable"
    assert not (service.workspace.state_dir / "projections" / "memory" / "mem0").exists()
    assert run(["memory", "provider", "delete", "--json"], service) == 0
    assert json.loads(capsys.readouterr().out)["canonical_changed"] is False


def test_corrupt_or_symlinked_selector_fails_closed(tmp_path: Path) -> None:
    service = _service(tmp_path)
    root = service.workspace.state_dir / "projections" / "memory" / "mem0"
    root.mkdir(parents=True)
    (root / "CURRENT").write_text("../../escape\n", encoding="ascii")
    assert service.memory_provider_status().state == "invalid"
    (root / "CURRENT").unlink()
    (root / "CURRENT").symlink_to(tmp_path / "outside")
    assert service.memory_provider_status().state == "invalid"


def test_semantic_search_opens_only_current_generation_and_closes_client(tmp_path: Path) -> None:
    service = _service(tmp_path)
    memory_id = _accepted(service)
    rebuilt = service.rebuild_memory_provider(FakeMem0Client)
    opened: list[Path] = []

    class SearchClient(FakeMem0Client):
        def __init__(self, root: Path) -> None:
            super().__init__(root)
            self.rows = [{
                "id": "provider-result",
                "memory": "Prefers exact derivations.",
                "metadata": {"aptuni_canonical_id": memory_id},
                "score": 0.91,
            }]
            opened.append(root)

    projection = Mem0Projection(service.workspace.state_dir, SearchClient)
    assert projection.search("derivation style", vault_seq=rebuilt.vault_seq, limit=5) == [(memory_id, 0.91)]
    assert opened == [
        service.workspace.state_dir / "projections" / "memory" / "mem0" / "generations" / rebuilt.generation
    ]
    assert (opened[0] / "client-closed").read_text(encoding="ascii") == "closed\n"


def test_hybrid_cli_returns_semantic_only_canonical_memory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    service = _service(tmp_path)
    memory_id = _accepted(service, "Prefers reproducible quantitative workflows.")
    service.rebuild_memory_provider(FakeMem0Client)

    class SearchClient(FakeMem0Client):
        def search(self, query: str, *, user_id: str, limit: int) -> dict[str, Any]:
            assert query == "how should I structure experiments?"
            assert user_id == "aptuni-local-profile" and limit >= 5
            return {"results": [{
                "metadata": {"aptuni_canonical_id": memory_id},
                "score": 0.99,
            }]}

    monkeypatch.setattr("aptuni.application.service.create_local_mem0_client", SearchClient)
    assert run(["search", "how should I structure experiments?", "--hybrid", "--json"], service) == 0
    payload = json.loads(capsys.readouterr().out)
    assert [item["id"] for item in payload] == [memory_id]


@pytest.mark.parametrize("malformation", ["missing_id", "duplicate_id", "bad_score"])
def test_semantic_search_rejects_malformed_provider_rows(tmp_path: Path, malformation: str) -> None:
    service = _service(tmp_path)
    memory_id = _accepted(service)
    rebuilt = service.rebuild_memory_provider(FakeMem0Client)

    class MalformedSearchClient(FakeMem0Client):
        def search(self, query: str, *, user_id: str, limit: int) -> dict[str, Any]:
            del query, user_id, limit
            row = {"metadata": {"aptuni_canonical_id": memory_id}, "score": 0.5}
            if malformation == "missing_id":
                row["metadata"] = {}
            if malformation == "bad_score":
                row["score"] = "private provider value"
            return {"results": [row, dict(row)] if malformation == "duplicate_id" else [row]}

    with pytest.raises(AptuniError) as caught:
        Mem0Projection(service.workspace.state_dir, MalformedSearchClient).search(
            "bounded query", vault_seq=rebuilt.vault_seq, limit=5,
        )
    assert caught.value.code == "hybrid_projection_failed"
    assert "private provider value" not in caught.value.message


def test_semantic_search_rejects_stale_or_cleanup_required_generation(tmp_path: Path) -> None:
    service = _service(tmp_path)
    _accepted(service)
    rebuilt = service.rebuild_memory_provider(FakeMem0Client)
    projection = Mem0Projection(service.workspace.state_dir, FakeMem0Client)
    service.remember("Moves the Vault sequence.", "knowledge")
    with pytest.raises(AptuniError) as stale:
        projection.search("query", vault_seq=service.status().seq, limit=5)
    assert stale.value.code == "hybrid_projection_unavailable"

    generations = projection.root / "generations"
    (generations / "gen-0000000000000000").mkdir()
    with pytest.raises(AptuniError) as cleanup:
        projection.search("query", vault_seq=rebuilt.vault_seq, limit=5)
    assert cleanup.value.code == "hybrid_projection_unavailable"


def test_semantic_search_close_failure_is_bounded_and_returns_no_rows(tmp_path: Path) -> None:
    service = _service(tmp_path)
    memory_id = _accepted(service)
    rebuilt = service.rebuild_memory_provider(FakeMem0Client)

    class CloseFailureClient(FakeMem0Client):
        def __init__(self, root: Path) -> None:
            super().__init__(root)
            self.rows = [{"metadata": {"aptuni_canonical_id": memory_id}, "score": 0.5}]

        def close(self) -> None:
            raise RuntimeError("private close failure")

    with pytest.raises(AptuniError) as caught:
        Mem0Projection(service.workspace.state_dir, CloseFailureClient).search(
            "bounded query", vault_seq=rebuilt.vault_seq, limit=5,
        )
    assert caught.value.code == "hybrid_projection_failed"
    assert "private close failure" not in caught.value.message


@pytest.mark.skipif(importlib.util.find_spec("mem0") is None, reason="isolated mem0ai runtime is not installed")
def test_real_mem0_2_0_20_projection_rebuild_uses_production_boundary(tmp_path: Path) -> None:
    """Run with the S10 hash-locked runtime; no Ollama or external model is used by this test."""
    from mem0.configs.base import MemoryConfig
    from mem0.configs.llms.openai import OpenAIConfig
    from mem0.memory.main import Memory as Mem0Memory
    from mem0.utils.factory import EmbedderFactory, LlmFactory

    EmbedderFactory.provider_to_class["openai"] = "s10.mem0_driver.DeterministicEmbedder"
    LlmFactory.provider_to_class["openai"] = ("s10.mem0_driver.DeterministicLlm", OpenAIConfig)

    def factory(root: Path) -> LocalMem0Client:
        config = MemoryConfig(
            vector_store={"provider": "qdrant", "config": {
                "collection_name": "aptuni_production_boundary", "embedding_model_dims": 10,
                "path": str(root / "qdrant"), "on_disk": True,
            }},
            embedder={"provider": "openai", "config": {"embedding_dims": 10}},
            llm={"provider": "openai", "config": {"model": "unused", "api_key": "unused"}},
            history_db_path=str(root / "history.db"),
        )
        return LocalMem0Client(Mem0Memory(config))

    service = _service(tmp_path)
    _accepted(service, "Uses reproducible experiment manifests.")
    report = service.rebuild_memory_provider(factory)
    assert report.records == 1
    assert service.memory_provider_status().state == "ready"
    rows = Mem0Projection(service.workspace.state_dir, factory).search(
        "reproducible experiment manifests", vault_seq=report.vault_seq, limit=5,
    )
    assert len(rows) == 1 and rows[0][0] == service.memories()[0].id


@pytest.mark.skipif(
    importlib.util.find_spec("mem0") is None or importlib.util.find_spec("ollama") is None,
    reason="optional mem0 runtime is not installed",
)
def test_optional_local_factory_uses_existing_loopback_model_without_inference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import mem0.embeddings.ollama
    import mem0.llms.ollama
    import ollama

    client_options: list[dict[str, Any]] = []

    class FakeOllama:
        def __init__(self, host: str | None = None, **kwargs: Any) -> None:
            assert host == "http://127.0.0.1:11434"
            client_options.append(kwargs)

        def list(self) -> dict[str, Any]:
            return {"models": [SimpleNamespace(model="nomic-embed-text:latest", name=None)]}

        def embed(self, *, model: str, input: str | list[str]) -> dict[str, Any]:
            assert model == "nomic-embed-text"
            count = len(input) if isinstance(input, list) else 1
            return {"embeddings": [[0.1] * 10 for _ in range(count)]}

    monkeypatch.setattr(ollama, "Client", FakeOllama)
    monkeypatch.setattr(mem0.embeddings.ollama, "Client", FakeOllama)
    monkeypatch.setattr(mem0.llms.ollama, "Client", FakeOllama)
    monkeypatch.setenv("APTUNI_MEM0_EMBED_DIMS", "10")
    service = _service(tmp_path)
    _accepted(service, "Keeps provider state disposable.")
    report = service.rebuild_memory_provider(create_local_mem0_client)
    assert report.records == 1
    assert service.memory_provider_status().state == "ready"
    assert client_options and all(
        options["follow_redirects"] is False and options["trust_env"] is False
        for options in client_options
    )


@pytest.mark.skipif(importlib.util.find_spec("ollama") is None, reason="optional ollama runtime is not installed")
def test_safe_ollama_client_does_not_follow_remote_redirect() -> None:
    import httpx
    import ollama

    requested: list[str] = []

    def redirect(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return httpx.Response(307, headers={"location": "https://remote.invalid/exfiltrate"})

    safe_type = _safe_ollama_client_type(ollama.Client)
    client = safe_type("http://127.0.0.1:11434", transport=httpx.MockTransport(redirect))
    try:
        with pytest.raises(ollama.ResponseError):
            client.list()
    finally:
        client.close()
    assert requested == ["http://127.0.0.1:11434/api/tags"]
