"""Rebuild-only Mem0 projection boundary (ADR-0003, S10).

The adapter intentionally has no incremental update/delete or inference method. A rebuild writes a
fresh generation from current accepted canonical memories, validates exact public enumeration, then
atomically selects it. Privacy deletion removes the whole managed provider root.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import secrets
import shutil
from collections.abc import Callable, Iterable
from contextlib import suppress
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

from aptuni.application.errors import AptuniError
from aptuni.domain.records import Memory

_GENERATION_RE = re.compile(r"gen-[0-9a-f]{16}")
_DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}")
_USER_ID = "aptuni-local-profile"


class Mem0Client(Protocol):
    def add(self, text: str, *, user_id: str, metadata: dict[str, Any], infer: bool) -> Any: ...
    def get_all(self, *, filters: dict[str, str], top_k: int) -> Any: ...
    def search(self, query: str, *, user_id: str, limit: int) -> Any: ...
    def close(self) -> None: ...


ClientFactory = Callable[[Path], Mem0Client]


@dataclass(frozen=True)
class ProviderCapabilities:
    inference: bool = False
    incremental_delete: bool = False
    whole_store_delete: bool = True
    rebuild: bool = True
    portable_export: bool = False


@dataclass(frozen=True)
class ProjectionStatus:
    provider: str
    state: str
    records: int
    vault_seq: int | None
    dependency_available: bool
    capabilities: ProviderCapabilities

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RebuildReport:
    provider: str
    records: int
    vault_seq: int
    generation: str
    cleanup_pending: bool


def _normalized_rows(value: Any) -> list[dict[str, Any]]:
    rows = value if isinstance(value, list) else value.get("results", []) if isinstance(value, dict) else []
    if not isinstance(rows, list):
        raise ValueError("provider enumeration is not a list")
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError("provider enumeration contains a malformed row")
    return rows


def _expected(memory: Memory) -> dict[str, Any]:
    return {
        "memory": memory.statement,
        "aptuni_canonical_id": memory.id,
        "aptuni_schema_version": memory.schema_version,
        "aptuni_module": memory.module,
    }


class Mem0Projection:
    """Own one Aptuni-confined Mem0 root and publish only exact rebuilt generations."""

    def __init__(self, state_dir: Path, client_factory: ClientFactory | None = None) -> None:
        self.state_dir = state_dir
        self.root = state_dir / "projections" / "memory" / "mem0"
        self._client_factory = client_factory

    @staticmethod
    def capabilities() -> ProviderCapabilities:
        return ProviderCapabilities()

    @staticmethod
    def dependency_available() -> bool:
        return importlib.util.find_spec("mem0") is not None and importlib.util.find_spec("ollama") is not None

    def _check_root(self) -> None:
        for path in (
            self.state_dir,
            self.state_dir / "projections",
            self.root.parent,
            self.root,
            self.root / "generations",
        ):
            if path.is_symlink() or (path.exists() and not path.is_dir()):
                raise AptuniError("memory_provider_state_unsafe", "The Mem0 projection path is not safe.")

    def status(self) -> ProjectionStatus:
        self._check_root()
        current = self.root / "CURRENT"
        if current.is_symlink():
            return ProjectionStatus("mem0", "invalid", 0, None, self.dependency_available(), self.capabilities())
        if not current.exists():
            return ProjectionStatus("mem0", "absent", 0, None, self.dependency_available(), self.capabilities())
        try:
            if current.stat(follow_symlinks=False).st_size > 32:
                raise ValueError
            generation = current.read_text(encoding="ascii").strip()
            if not _GENERATION_RE.fullmatch(generation):
                raise ValueError
            path = self.root / "generations" / generation
            if path.is_symlink() or not path.is_dir():
                raise ValueError
            manifest_path = path / "aptuni-projection.json"
            if manifest_path.is_symlink() or manifest_path.stat(follow_symlinks=False).st_size > 4096:
                raise ValueError
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if set(manifest) != {
                "schema_version", "provider", "generation", "vault_seq", "records",
                "projection_digest", "inference", "delete_strategy",
            }:
                raise ValueError
            if (
                manifest.get("schema_version") != 1
                or manifest.get("provider") != "mem0"
                or manifest.get("generation") != generation
                or manifest.get("inference") is not False
                or manifest.get("delete_strategy") != "whole_store_rebuild"
                or not isinstance(manifest.get("projection_digest"), str)
                or not _DIGEST_RE.fullmatch(manifest["projection_digest"])
            ):
                raise ValueError
            records = manifest["records"]
            vault_seq = manifest["vault_seq"]
            if type(records) is not int or records < 0 or type(vault_seq) is not int or vault_seq < 0:
                raise ValueError
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            return ProjectionStatus("mem0", "invalid", 0, None, self.dependency_available(), self.capabilities())
        generations = self.root / "generations"
        cleanup_pending = any(
            child.name != generation and _GENERATION_RE.fullmatch(child.name)
            for child in generations.iterdir()
        )
        state = "cleanup_required" if cleanup_pending else "ready"
        return ProjectionStatus("mem0", state, records, vault_seq, self.dependency_available(),
                                self.capabilities())

    def rebuild(self, memories: Iterable[Memory], vault_seq: int) -> RebuildReport:  # noqa: PLR0912, PLR0915
        self._check_root()
        if self._client_factory is None:
            raise AptuniError(
                "memory_provider_unavailable",
                "The optional local Mem0 runtime is not configured; the canonical Vault is unchanged.",
            )
        items = sorted(memories, key=lambda item: item.id)
        expected = {_expected(item)["aptuni_canonical_id"]: _expected(item) for item in items}
        generation = "gen-" + secrets.token_hex(8)
        path = self.root / "generations" / generation
        client: Mem0Client | None = None
        selector: Path | None = None
        try:
            path.mkdir(parents=True, mode=0o700)
            os.chmod(path, 0o700)
            client = self._client_factory(path)
            for item in items:
                result = client.add(
                    item.statement,
                    user_id=_USER_ID,
                    metadata={
                        "aptuni_canonical_id": item.id,
                        "aptuni_schema_version": item.schema_version,
                        "aptuni_module": item.module,
                    },
                    infer=False,
                )
                rows = _normalized_rows(result)
                if len(rows) != 1 or not isinstance(rows[0].get("id"), str):
                    raise ValueError("provider add result is invalid")
            actual: dict[str, dict[str, Any]] = {}
            for row in _normalized_rows(client.get_all(filters={"user_id": _USER_ID}, top_k=max(1, len(items) + 1))):
                metadata = row.get("metadata")
                if not isinstance(metadata, dict):
                    raise ValueError("provider metadata is invalid")
                canonical_id = metadata.get("aptuni_canonical_id")
                if not isinstance(canonical_id, str) or canonical_id in actual:
                    raise ValueError("provider canonical identity is invalid")
                actual[canonical_id] = {
                    "memory": row.get("memory"),
                    "aptuni_canonical_id": canonical_id,
                    "aptuni_schema_version": metadata.get("aptuni_schema_version"),
                    "aptuni_module": metadata.get("aptuni_module"),
                }
            if actual != expected:
                raise ValueError("provider projection does not exactly match canonical input")
            client.close()
            client = None
            digest = hashlib.sha256(
                json.dumps(expected, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            manifest = {
                "schema_version": 1,
                "provider": "mem0",
                "generation": generation,
                "vault_seq": vault_seq,
                "records": len(items),
                "projection_digest": "sha256:" + digest,
                "inference": False,
                "delete_strategy": "whole_store_rebuild",
            }
            manifest_path = path / "aptuni-projection.json"
            manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
                                     encoding="utf-8")
            os.chmod(manifest_path, 0o600)
            selector = self.root / (".CURRENT." + secrets.token_hex(4) + ".tmp")
            selector.write_text(generation + "\n", encoding="ascii")
            os.chmod(selector, 0o600)
            os.replace(selector, self.root / "CURRENT")
            # CURRENT is the publication commit point. Cleanup must never re-enter the failure path,
            # which would remove the selected generation and strand the selector (Review 53).
            try:
                cleanup_pending = not self._remove_old_generations(generation)
            except Exception:
                cleanup_pending = True
            return RebuildReport("mem0", len(items), vault_seq, generation, cleanup_pending)
        except AptuniError:
            if client is not None:
                with suppress(Exception):
                    client.close()
            if selector is not None:
                selector.unlink(missing_ok=True)
            shutil.rmtree(path, ignore_errors=True)
            self._prune_empty_root()
            raise
        except Exception as error:
            if client is not None:
                with suppress(Exception):
                    client.close()
            if selector is not None:
                selector.unlink(missing_ok=True)
            shutil.rmtree(path, ignore_errors=True)
            self._prune_empty_root()
            raise AptuniError(
                "memory_provider_rebuild_failed",
                "The Mem0 projection rebuild failed; the prior generation remains selected.",
            ) from error

    def search(self, query: str, *, vault_seq: int, limit: int) -> list[tuple[str, float]]:
        """Search the selected exact generation and return canonical memory IDs only."""
        if self._client_factory is None:
            raise AptuniError(
                "hybrid_projection_unavailable",
                "Hybrid search needs the optional local Mem0 runtime and a fresh rebuilt projection.",
            )
        status = self.status()
        if status.state != "ready" or status.vault_seq != vault_seq:
            raise AptuniError(
                "hybrid_projection_unavailable",
                "Hybrid search needs a fresh Mem0 projection; run `aptuni memory provider rebuild`.",
            )
        client: Mem0Client | None = None
        try:
            generation = (self.root / "CURRENT").read_text(encoding="ascii").strip()
            path = self.root / "generations" / generation
            client = self._client_factory(path)
            rows = _normalized_rows(client.search(query, user_id=_USER_ID, limit=limit))
            if len(rows) > limit:
                raise ValueError("provider returned too many rows")
            result: list[tuple[str, float]] = []
            seen: set[str] = set()
            for row in rows:
                metadata = row.get("metadata")
                canonical_id = metadata.get("aptuni_canonical_id") if isinstance(metadata, dict) else None
                if not isinstance(canonical_id, str) or canonical_id in seen:
                    raise ValueError("provider search identity is invalid")
                seen.add(canonical_id)
                raw_score = row.get("score", 0.0)
                if isinstance(raw_score, bool) or not isinstance(raw_score, (int, float)):
                    raise ValueError("provider search score is invalid")
                result.append((canonical_id, float(raw_score)))
            closing, client = client, None
            closing.close()
            return result
        except AptuniError:
            raise
        except Exception as error:
            raise AptuniError(
                "hybrid_projection_failed",
                "The local semantic projection could not be searched; canonical data is safe.",
            ) from error
        finally:
            if client is not None:
                with suppress(Exception):
                    client.close()

    def _remove_old_generations(self, current: str) -> bool:
        generations = self.root / "generations"
        if not generations.is_dir() or generations.is_symlink():
            return True
        try:
            children = tuple(generations.iterdir())
        except OSError:
            return False
        complete = True
        for child in children:
            try:
                if child.name != current and _GENERATION_RE.fullmatch(child.name) and not child.is_symlink():
                    shutil.rmtree(child)
            except OSError:
                complete = False
        return complete

    def _prune_empty_root(self) -> None:
        for directory in (self.root / "generations", self.root, self.root.parent):
            try:
                directory.rmdir()
            except OSError:
                break

    def delete(self) -> bool:
        self._check_root()
        if not self.root.exists():
            return False
        shutil.rmtree(self.root)
        return True
