from __future__ import annotations

import gc
import hashlib
import json
import os
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from .harness import (
    AdmissionError,
    CanonicalRecord,
    DriverDiagnostics,
    NetworkGuard,
    marker_inventory,
)


class DeterministicEmbedder:
    """Local deterministic test double for Mem0 storage/lifecycle admission."""

    def __init__(self, config: Any = None) -> None:
        self.config = config

    def embed(self, text: str, memory_action: str | None = None) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        return [((digest[index] / 255.0) * 2.0) - 1.0 for index in range(10)]

    def embed_batch(self, texts: list[str], memory_action: str = "add") -> list[list[float]]:
        return [self.embed(text, memory_action) for text in texts]


class DeterministicLlm:
    """Local extraction double used only to expose Mem0's raw-retention behavior."""

    def __init__(self, config: Any = None) -> None:
        self.config = config

    def generate_response(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        del messages, kwargs
        return json.dumps({"memory": [{"text": "S10_STRUCTURED_EXTRACTION"}]})


class Mem0Driver:
    name = "mem0"
    version = "2.0.20"

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.ledger_path = self.root / "projection-ledger.json"
        self.history_path = self.root / "history.db"
        self._memory: Any = None
        self._ledger: dict[str, str] = {}

    def initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)
        os.environ["MEM0_DIR"] = str(self.root / "config")
        from mem0.configs.base import MemoryConfig
        from mem0.configs.llms.openai import OpenAIConfig
        from mem0.memory.main import Memory
        from mem0.utils.factory import EmbedderFactory, LlmFactory

        EmbedderFactory.provider_to_class["openai"] = "s10.mem0_driver.DeterministicEmbedder"
        LlmFactory.provider_to_class["openai"] = ("s10.mem0_driver.DeterministicLlm", OpenAIConfig)
        config = MemoryConfig(
            vector_store={
                "provider": "qdrant",
                "config": {
                    "collection_name": "aptuni_s10",
                    "embedding_model_dims": 10,
                    "path": str(self.root / "qdrant"),
                    "on_disk": True,
                },
            },
            embedder={"provider": "openai", "config": {"embedding_dims": 10}},
            llm={"provider": "openai", "config": {"model": "s10-local-double", "api_key": "unused"}},
            history_db_path=str(self.history_path),
        )
        self._memory = Memory(config)
        if self.ledger_path.exists():
            value = json.loads(self.ledger_path.read_text(encoding="utf-8"))
            if not isinstance(value, dict) or not all(isinstance(key, str) and isinstance(item, str) for key, item in value.items()):
                raise AdmissionError("mem0_projection_ledger_invalid")
            self._ledger = value
        else:
            self._write_ledger()

    def _write_ledger(self) -> None:
        temporary = self.ledger_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self._ledger, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        os.chmod(temporary, 0o600)
        temporary.replace(self.ledger_path)

    def project(self, record: CanonicalRecord) -> None:
        provider_id = self._ledger.get(record.canonical_id)
        metadata = {
            "aptuni_canonical_id": record.canonical_id,
            "aptuni_schema_version": 1,
            "aptuni_scope": record.scope,
        }
        if record.status == "tombstoned":
            if provider_id is not None:
                self._memory.delete(provider_id)
                del self._ledger[record.canonical_id]
                self._write_ledger()
            return
        if provider_id is None:
            result = self._memory.add(
                record.current_text,
                user_id="aptuni-s10",
                metadata=metadata,
                infer=False,
            )
            rows = result.get("results", [])
            if len(rows) != 1 or not isinstance(rows[0].get("id"), str):
                raise AdmissionError("mem0_add_result_invalid")
            self._ledger[record.canonical_id] = rows[0]["id"]
            self._write_ledger()
        else:
            self._memory.update(provider_id, text=record.current_text, metadata=metadata)

    def search(self, query: str, *, limit: int) -> list[dict[str, Any]]:
        result = self._memory.search(
            query,
            top_k=limit,
            threshold=0.0,
            filters={"user_id": "aptuni-s10"},
        )
        return result if isinstance(result, list) else list(result.get("results", []))

    def enumerate_public(self) -> list[dict[str, Any]]:
        result = self._memory.get_all(filters={"user_id": "aptuni-s10"}, top_k=20)
        return result if isinstance(result, list) else list(result.get("results", []))

    def _close(self) -> None:
        if self._memory is None:
            return
        vector_store = getattr(self._memory, "vector_store", None)
        client = getattr(vector_store, "client", None)
        self._memory.close()
        if client is not None and hasattr(client, "close"):
            client.close()
        self._memory = None
        gc.collect()

    def restart(self) -> Mem0Driver:
        self._close()
        restarted = Mem0Driver(self.root)
        restarted.initialize()
        return restarted

    def fresh(self, root: Path) -> Mem0Driver:
        return Mem0Driver(root)

    def diagnostics(self) -> DriverDiagnostics:
        actual_files = tuple(path.relative_to(self.root).as_posix() for path in sorted(self.root.rglob("*")) if path.is_file())
        file_classes: dict[str, str] = {}
        for relative in actual_files:
            if relative == "projection-ledger.json":
                file_classes[relative] = "projection_ledger"
            elif relative.startswith("qdrant/"):
                file_classes[relative] = "current_projection"
            elif relative.startswith("config/"):
                file_classes[relative] = "configuration"
            elif relative in {"history.db", "history.db-shm", "history.db-wal", "history.db-journal"}:
                file_classes[relative] = "history"
        event_counts: dict[str, int] = {}
        raw_count = 0
        with closing(sqlite3.connect(self.history_path)) as connection:
            for event, count in connection.execute("SELECT event, COUNT(*) FROM history GROUP BY event"):
                event_counts[str(event)] = int(count)
            raw_count = int(connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0])
        return DriverDiagnostics(
            file_classes=file_classes,
            raw_interaction_files=("history.db",) if raw_count else (),
            event_counts=event_counts,
        )

    def reset(self) -> None:
        self._close()
        shutil.rmtree(self.root)
        self._ledger = {}


def probe_raw_retention(root: Path) -> dict[str, Any]:
    raw_marker = "S10_RAW_INTERACTION_MARKER"
    previous = {name: os.environ.get(name) for name in ("MEM0_TELEMETRY", "MEM0_TELEMETRY_ENABLED")}
    driver = Mem0Driver(root)
    try:
        os.environ["MEM0_TELEMETRY"] = "False"
        os.environ["MEM0_TELEMETRY_ENABLED"] = "False"
        with NetworkGuard() as guard:
            driver.initialize()
            driver._memory.add(
                [{"role": "user", "content": raw_marker}],
                user_id="aptuni-s10-raw",
                infer=True,
            )
            with closing(sqlite3.connect(driver.history_path)) as connection:
                message_rows = int(connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0])
            before_purge = marker_inventory(root, (raw_marker,))
            driver.reset()
            after_purge = marker_inventory(root, (raw_marker,))
    finally:
        driver._close()
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
    retained = sum(before_purge.values()) > 0 and message_rows > 0
    return {
        "model_runtime": "deterministic_local_test_double",
        "network_attempts": guard.attempts,
        "message_rows": message_rows,
        "raw_marker_present_before_purge": retained,
        "raw_marker_present_after_purge": sum(after_purge.values()) > 0,
        "verdict": "FAIL_RAW_RETENTION" if retained else "PASS",
    }
