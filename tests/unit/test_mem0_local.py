"""Local Mem0 activation is version-gated, loopback-only and inference-free."""

from __future__ import annotations

import importlib.metadata
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from aptuni.application.errors import AptuniError
from aptuni.memory.mem0_local import (
    LocalMem0Client,
    _loopback_url,
    _safe_ollama_client_type,
    create_local_mem0_client,
)


@pytest.mark.parametrize("url", [
    "https://api.openai.com", "http://192.168.1.20:11434", "https://localhost:11434",
    "http://localhost:11434", "http://user:password@127.0.0.1:11434", "http://127.0.0.1:11434/path",
])
def test_only_plain_loopback_ollama_endpoint_is_accepted(monkeypatch: pytest.MonkeyPatch, url: str) -> None:
    monkeypatch.setenv("APTUNI_MEM0_OLLAMA_URL", url)
    with pytest.raises(AptuniError) as caught:
        _loopback_url()
    assert caught.value.code == "memory_provider_config_invalid"


def test_telemetry_is_disabled_before_dependency_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MEM0_TELEMETRY", raising=False)
    monkeypatch.delenv("MEM0_TELEMETRY_ENABLED", raising=False)

    def missing(name: str) -> str:
        raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(importlib.metadata, "version", missing)
    with pytest.raises(AptuniError) as caught:
        create_local_mem0_client(tmp_path)
    assert caught.value.code == "memory_provider_unavailable"
    assert os.environ["MEM0_TELEMETRY"] == "False"
    assert os.environ["MEM0_TELEMETRY_ENABLED"] == "False"


def test_optional_runtime_versions_are_exactly_gated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    versions = {"mem0ai": "2.0.20", "ollama": "0.6.1"}
    monkeypatch.setattr(importlib.metadata, "version", versions.__getitem__)
    with pytest.raises(AptuniError) as caught:
        create_local_mem0_client(tmp_path)
    assert caught.value.code == "memory_provider_version_unsupported"
    assert "0.6.2" in caught.value.message


def test_client_wrapper_has_no_inference_path() -> None:
    class MemoryDouble:
        def add(self, *_args: Any, **_kwargs: Any) -> None:
            raise AssertionError("must not reach upstream inference")

    client = LocalMem0Client(MemoryDouble())
    with pytest.raises(AptuniError) as caught:
        client.add("raw interaction", user_id="user", metadata={}, infer=True)
    assert caught.value.code == "memory_provider_inference_forbidden"


def test_client_wrapper_uses_mem0_2_search_contract() -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    class MemoryDouble:
        def search(self, query: str, **kwargs: Any) -> dict[str, Any]:
            calls.append((query, kwargs))
            return {"results": []}

    result = LocalMem0Client(MemoryDouble()).search("semantic query", user_id="profile", limit=7)
    assert result == {"results": []}
    assert calls == [("semantic query", {
        "filters": {"user_id": "profile"}, "top_k": 7, "threshold": 0.0,
    })]


def test_client_close_releases_primary_and_telemetry_vector_stores() -> None:
    closed: list[str] = []

    class MemoryDouble:
        vector_store = SimpleNamespace(client=SimpleNamespace(close=lambda: closed.append("primary")))
        _telemetry_vector_store = SimpleNamespace(
            client=SimpleNamespace(close=lambda: closed.append("telemetry")),
        )

        @staticmethod
        def close() -> None:
            closed.append("memory")

    LocalMem0Client(MemoryDouble()).close()
    assert closed == ["memory", "primary", "telemetry"]


def test_client_close_attempts_every_store_after_one_close_failure() -> None:
    closed: list[str] = []

    def fail_primary() -> None:
        closed.append("primary")
        raise RuntimeError("primary failed")

    class MemoryDouble:
        vector_store = SimpleNamespace(client=SimpleNamespace(close=fail_primary))
        _telemetry_vector_store = SimpleNamespace(
            client=SimpleNamespace(close=lambda: closed.append("telemetry")),
        )

        @staticmethod
        def close() -> None:
            closed.append("memory")

    with pytest.raises(RuntimeError, match="primary failed"):
        LocalMem0Client(MemoryDouble()).close()
    assert closed == ["memory", "primary", "telemetry"]


def test_safe_ollama_client_overrides_redirect_and_proxy_settings() -> None:
    class ClientDouble:
        def __init__(self, host: str | None = None, **kwargs: Any) -> None:
            self.host = host
            self.options = kwargs

    safe = _safe_ollama_client_type(ClientDouble)(
        "http://127.0.0.1:11434", follow_redirects=True, trust_env=True,
    )
    assert safe.host == "http://127.0.0.1:11434"
    assert safe.options["follow_redirects"] is False
    assert safe.options["trust_env"] is False
