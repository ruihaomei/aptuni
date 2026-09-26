"""Canonical, host-syntax-neutral Agent activation intents (ADR-0025)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Lock
from typing import Literal

from aptuni.application.context import ContextResponse
from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService, HostContextAccess
from aptuni.domain.records import Module

ActivationIntent = Literal["aptuni.profile", "aptuni.memory", "aptuni.full"]
ActivationScope = Literal["task", "session"]


@dataclass
class AgentActivation:
    """One host-session controller; task requests deliberately leave no state."""

    service: AptuniService
    access: Callable[[], HostContextAccess | None]
    _session_full: bool = False
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    @property
    def session_full(self) -> bool:
        with self._lock:
            return self._session_full

    def status(self) -> dict[str, object]:
        with self._lock:
            if self._session_full:
                return {"schema_version": 1, "mode": "full", "intent": "aptuni.full"}
            return {"schema_version": 1, "mode": "off"}

    def disable(self) -> dict[str, object]:
        with self._lock:
            changed = self._session_full
            self._session_full = False
            return {"schema_version": 1, "mode": "off", "changed": changed}

    def activate(
        self,
        intent: ActivationIntent,
        scope: ActivationScope,
        query: str,
        *,
        modules: tuple[Module, ...],
        budget: int,
        limit: int,
    ) -> ContextResponse:
        with self._lock:
            if scope == "session" and intent != "aptuni.full":
                raise AptuniError(
                    "aptuni_session_scope_invalid",
                    "Only Full can be activated for a session; Profile and Memory are task-scoped.",
                )
            response = self._retrieve(intent, query, modules=modules, budget=budget, limit=limit)
            if scope == "session":
                self._session_full = True
            return response

    def session_context(
        self,
        query: str,
        *,
        modules: tuple[Module, ...],
        budget: int,
        limit: int,
    ) -> ContextResponse:
        with self._lock:
            if not self._session_full:
                raise AptuniError(
                    "aptuni_activation_required",
                    "Aptuni is OFF. Activate Profile, Memory, or Full for this task.",
                )
            return self._retrieve("aptuni.full", query, modules=modules, budget=budget, limit=limit)

    def require_session(self) -> None:
        with self._lock:
            if not self._session_full:
                raise AptuniError(
                    "aptuni_activation_required",
                    "Aptuni is OFF. Activate Profile, Memory, or Full for this task.",
                )

    def _retrieve(
        self,
        intent: ActivationIntent,
        query: str,
        *,
        modules: tuple[Module, ...],
        budget: int,
        limit: int,
    ) -> ContextResponse:
        if intent == "aptuni.profile":
            return self.service.context(
                query, modules=modules, budget=budget, limit=limit, audience="host_mcp",
                access=self.access(), _record_types=("fact",),
            )
        if intent == "aptuni.memory":
            return self.service.context(
                query, modules=modules, budget=budget, limit=limit, audience="host_mcp",
                access=self.access(), _record_types=("memory",),
            )
        return self.service.context(
            query, modules=modules, budget=budget, limit=limit, include_evidence=True,
            audience="host_mcp", access=self.access(),
        )
