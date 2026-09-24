"""Least-privilege task API over Aptuni application services."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from aptuni.api.v1.contracts import ContextItem, ContextResult, MemoryProposal, ReviewQueue
from aptuni.api.v1.errors import AptuniAPIError
from aptuni.api.v1.grants import PluginGrant, PluginGrantManager
from aptuni.api.v1.manifest import PluginManifest
from aptuni.application.context import ContextResponse
from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService, HostContextAccess
from aptuni.application.workspace import Workspace
from aptuni.domain.records import Module

_T = TypeVar("_T")
_CONNECT_TOKEN = object()
_SCOPE_MAP = {
    "profile.read": "identity.read",
    "memory.read": "context.read",
    "context.read": "context.read",
    "evidence.read": "evidence.read",
    "memory.propose": "memory.propose",
    "memory.review.read": "memory.review.read",
}


def _public_context(value: ContextResponse, *, kinds: frozenset[str] | None = None) -> ContextResult:
    items = tuple(
        ContextItem(
            canonical_id=item.canonical_id, canonical_ids=item.canonical_ids, kind=item.kind,
            layer=item.layer, module=item.module, text=item.text, source_id=item.source_id,
            trust=item.trust, tainted=item.tainted, signals=item.signals,
            review_state=item.review_state, units=item.units,
        )
        for item in value.items if kinds is None or item.kind in kinds
    )
    return ContextResult(
        requested_units=value.requested_units, used_units=value.used_units,
        remaining_units=value.remaining_units, truncated=value.truncated, layers=value.layers,
        vault_seq=value.vault_seq, policy_epoch=value.policy_epoch, items=items,
    )


class AptuniAPI:
    """Public v1 client. Construction is grant-bound through :func:`connect`."""

    def __init__(
        self,
        service: AptuniService,
        manifest: PluginManifest,
        grant: PluginGrant,
        manager: PluginGrantManager,
        *,
        _token: object,
    ) -> None:
        if _token is not _CONNECT_TOKEN:
            raise AptuniAPIError("plugin_connection_required", "Create public API clients with connect().")
        self._service = service
        self.manifest = manifest
        self.grant = grant
        self._manager = manager
        scopes = frozenset(_SCOPE_MAP[capability] for capability in grant.capabilities)
        self._access = HostContextAccess(
            principal=f"plugin:{manifest.id}", scopes=scopes, modules=frozenset(grant.modules),
            host_class="proven_local", host_model_egress=False,
        )

    def _call(self, operation: Callable[[], _T]) -> _T:
        try:
            with self._manager.authorization_lock():
                current = self._manager.load(self.grant.grant_id)
                if current != self.grant or current.manifest_digest != self.manifest.digest():
                    message = "The plugin grant changed; reconnect after owner review."
                    raise AptuniAPIError("plugin_grant_changed", message)
                value = operation()
                if self._manager.load(self.grant.grant_id) != current:
                    raise AptuniAPIError(
                        "plugin_grant_changed",
                        "The plugin grant changed during the operation.",
                    )
                return value
        except AptuniError as error:
            raise AptuniAPIError(error.code, error.message) from error

    def _require(self, capability: str, modules: tuple[str, ...] = ()) -> None:
        if capability not in self.grant.capabilities:
            raise AptuniAPIError("plugin_capability_denied", f"The plugin lacks {capability}.")
        if not set(modules) <= set(self.grant.modules):
            raise AptuniAPIError("plugin_module_denied", "The plugin lacks one or more requested modules.")

    def get_profile(self, *, max_units: int = 512) -> ContextResult:
        self._require("profile.read", ("identity",))
        value = self._call(lambda: self._service.identity_card(
            budget=max_units, audience="host_mcp", access=self._access,
        ))
        return _public_context(value)

    def query_context(
        self,
        query: str,
        *,
        modules: tuple[Module, ...],
        max_units: int = 1500,
        limit: int = 20,
        include_evidence: bool = False,
    ) -> ContextResult:
        self._require("context.read", tuple(modules))
        if include_evidence:
            self._require("evidence.read", tuple(modules))
        value = self._call(lambda: self._service.context(
            query, modules=tuple(modules), budget=max_units, include_evidence=include_evidence,
            limit=limit, audience="host_mcp", access=self._access,
        ))
        return _public_context(value)

    def search_memories(
        self, query: str, *, modules: tuple[Module, ...], max_units: int = 1500, limit: int = 20,
    ) -> ContextResult:
        self._require("memory.read", tuple(modules))
        value = self._call(lambda: self._service.context(
            query, modules=tuple(modules), budget=max_units, limit=limit,
            audience="host_mcp", access=self._access, _record_types=("memory",),
        ))
        return _public_context(value, kinds=frozenset({"memory"}))

    def propose_memory(self, statement: str, *, module: Module, idempotency_key: str | None = None) -> MemoryProposal:
        self._require("memory.propose", (module,))
        value = self._call(lambda: self._service.propose_from_host(
            statement, module, self._access, idempotency_key,
        ))
        return MemoryProposal(candidate_id=value.candidate_id, created=value.created)

    def pending_memory_reviews(self, *, max_units: int = 1500, limit: int = 20) -> ReviewQueue:
        self._require("memory.review.read")
        value = self._call(lambda: self._service.memory_review_feed(
            budget=max_units, limit=limit, access=self._access,
        ))
        reminder = value.reminder
        return ReviewQueue(
            context=_public_context(value.context), pending=value.pending, due=reminder.due,
            reason=reminder.reason, threshold=reminder.threshold,
            next_due_at=reminder.next_due_at.isoformat() if reminder.next_due_at else None,
        )


def connect(
    manifest: PluginManifest,
    grant_id: str,
    *,
    workspace: Workspace | None = None,
) -> AptuniAPI:
    """Connect one exact manifest to one owner-created local plugin grant."""
    selected_workspace = workspace or Workspace.default()
    manager = PluginGrantManager(selected_workspace)
    grant = manager.load(grant_id)
    if (
        grant.plugin_id != manifest.id
        or grant.plugin_version != manifest.version
        or grant.manifest_digest != manifest.digest()
    ):
        raise AptuniAPIError("plugin_manifest_drift", "The plugin manifest no longer matches its owner grant.")
    return AptuniAPI(AptuniService(selected_workspace), manifest, grant, manager, _token=_CONNECT_TOKEN)
