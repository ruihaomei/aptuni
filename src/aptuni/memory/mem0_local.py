"""Optional Mem0 2.0.20 client configured for loopback Ollama and embedded Qdrant only."""

from __future__ import annotations

import importlib
import importlib.metadata
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from aptuni.application.errors import AptuniError

MEM0_VERSION = "2.0.20"
OLLAMA_VERSION = "0.6.2"


def _setting(name: str, default: str) -> str:
    value = os.environ.get(name, default).strip()
    if not value or len(value) > 200:
        raise AptuniError("memory_provider_config_invalid", "The local Mem0 configuration is invalid.")
    return value


def _loopback_url() -> str:
    value = _setting("APTUNI_MEM0_OLLAMA_URL", "http://127.0.0.1:11434")
    parsed = urlsplit(value)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "::1"}:
        raise AptuniError(
            "memory_provider_config_invalid",
            "The Mem0 Ollama endpoint must be an explicit loopback HTTP URL.",
        )
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise AptuniError("memory_provider_config_invalid", "The local Mem0 configuration is invalid.")
    return value.rstrip("/")


class LocalMem0Client:
    def __init__(self, memory: Any) -> None:
        self.memory = memory

    def add(self, text: str, *, user_id: str, metadata: dict[str, Any], infer: bool) -> Any:
        if infer:
            raise AptuniError("memory_provider_inference_forbidden", "Mem0 inference is disabled by Aptuni.")
        return self.memory.add(text, user_id=user_id, metadata=metadata, infer=False)

    def get_all(self, *, filters: dict[str, str], top_k: int) -> Any:
        return self.memory.get_all(filters=filters, top_k=top_k)

    def close(self) -> None:
        vector_store = getattr(self.memory, "vector_store", None)
        client = getattr(vector_store, "client", None)
        try:
            self.memory.close()
        finally:
            if client is not None and hasattr(client, "close"):
                client.close()


def _safe_ollama_client_type(base: type[Any]) -> type[Any]:
    """Force the upstream client to ignore proxies and refuse redirects away from loopback."""
    class SafeOllamaClient(base):  # type: ignore[misc]
        def __init__(self, host: str | None = None, **kwargs: Any) -> None:
            kwargs["follow_redirects"] = False
            kwargs["trust_env"] = False
            super().__init__(host=host, **kwargs)

    return SafeOllamaClient


def create_local_mem0_client(root: Path) -> LocalMem0Client:
    """Import Mem0 only after telemetry-off and build a no-pull, loopback-only configuration."""
    os.environ["MEM0_TELEMETRY"] = "False"
    os.environ["MEM0_TELEMETRY_ENABLED"] = "False"
    os.environ["MEM0_DIR"] = str(root / "config")
    try:
        if importlib.metadata.version("mem0ai") != MEM0_VERSION:
            raise AptuniError(
                "memory_provider_version_unsupported",
                f"The optional Mem0 runtime must be exactly {MEM0_VERSION}.",
            )
        if importlib.metadata.version("ollama") != OLLAMA_VERSION:
            raise AptuniError(
                "memory_provider_version_unsupported",
                f"The optional Ollama client must be exactly {OLLAMA_VERSION}.",
            )
    except importlib.metadata.PackageNotFoundError as error:
        raise AptuniError(
            "memory_provider_unavailable",
            "Install the optional Aptuni Mem0 dependencies before rebuilding; the Vault is unchanged.",
        ) from error

    base_url = _loopback_url()
    embed_model = _setting("APTUNI_MEM0_EMBED_MODEL", "nomic-embed-text")
    llm_model = _setting("APTUNI_MEM0_LLM_MODEL", "llama3.2")  # constructed but never called
    try:
        dimensions = int(_setting("APTUNI_MEM0_EMBED_DIMS", "768"))
    except ValueError as error:
        raise AptuniError("memory_provider_config_invalid", "The embedding dimension must be an integer.") from error
    if not 1 <= dimensions <= 8192:
        raise AptuniError("memory_provider_config_invalid", "The embedding dimension is out of range.")

    # Imports happen only after the telemetry environment and version gate above.
    MemoryConfig = importlib.import_module("mem0.configs.base").MemoryConfig
    embedding_module = importlib.import_module("mem0.embeddings.ollama")
    llm_module = importlib.import_module("mem0.llms.ollama")
    ollama_module = importlib.import_module("ollama")
    safe_client = _safe_ollama_client_type(ollama_module.Client)
    embedding_module.Client = safe_client  # type: ignore[attr-defined]
    llm_module.Client = safe_client  # type: ignore[attr-defined]
    OllamaEmbedding = embedding_module.OllamaEmbedding
    Mem0Memory = importlib.import_module("mem0.memory.main").Memory
    EmbedderFactory = importlib.import_module("mem0.utils.factory").EmbedderFactory

    class NoPullOllamaEmbedding(OllamaEmbedding):  # type: ignore[misc, valid-type]
        def _ensure_model_exists(self) -> None:
            models = self.client.list()["models"]
            target = self._normalize_model_name(self.config.model)
            names = (
                (model.get("name", ""), model.get("model", ""))
                if isinstance(model, dict)
                else (getattr(model, "name", ""), getattr(model, "model", ""))
                for model in models
            )
            present = any(self._normalize_model_name(name) == target for pair in names for name in pair if name)
            if not present:
                raise AptuniError(
                    "memory_provider_model_missing",
                    "The configured local embedding model is not installed; Aptuni will not pull it automatically.",
                )

    NoPullOllamaEmbedding.__module__ = __name__
    globals()["NoPullOllamaEmbedding"] = NoPullOllamaEmbedding
    EmbedderFactory.provider_to_class["ollama"] = f"{__name__}.NoPullOllamaEmbedding"
    config = MemoryConfig(
        vector_store={
            "provider": "qdrant",
            "config": {
                "collection_name": "aptuni_memory",
                "embedding_model_dims": dimensions,
                "path": str(root / "qdrant"),
                "on_disk": True,
            },
        },
        embedder={
            "provider": "ollama",
            "config": {"model": embed_model, "embedding_dims": dimensions, "ollama_base_url": base_url},
        },
        llm={"provider": "ollama", "config": {"model": llm_model, "ollama_base_url": base_url}},
        history_db_path=str(root / "history.db"),
    )
    return LocalMem0Client(Mem0Memory(config))
