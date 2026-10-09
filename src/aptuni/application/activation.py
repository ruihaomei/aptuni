"""Canonical, host-syntax-neutral Agent activation intents (ADR-0025)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Lock
from typing import Literal

from aptuni.application.candidates import candidate_evidence_context, inventory_context
from aptuni.application.context import ContextResponse
from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService, HostContextAccess
from aptuni.domain.records import Module

PROPOSE_SCOPE = "memory.propose"

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
        """Describe the mode and what this grant permits; module and scope names only, no content."""
        try:
            access = self.access()
        except AptuniError:  # a revoked or unreadable grant permits nothing; status itself never fails
            access = None
        with self._lock:
            mode: dict[str, object] = (
                {"mode": "full", "intent": "aptuni.full"} if self._session_full else {"mode": "off"}
            )
            if access is None or PROPOSE_SCOPE not in access.scopes:
                proposals = "not_granted"
            else:
                proposals = "available" if self._session_full else "needs_session_full"
            return {
                "schema_version": 1,
                **mode,
                "granted_modules": sorted(access.modules) if access is not None else [],
                "memory_proposals": proposals,
            }

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
        concepts: tuple[str, ...] = (),
    ) -> ContextResponse:
        with self._lock:
            if scope == "session" and intent != "aptuni.full":
                raise AptuniError(
                    "aptuni_session_scope_invalid",
                    "Only Full can be activated for a session; Profile and Memory are task-scoped.",
                )
            response = self._retrieve(intent, query, modules=modules, budget=budget, limit=limit,
                                      concepts=concepts)
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
        concepts: tuple[str, ...] = (),
    ) -> ContextResponse:
        with self._lock:
            if not self._session_full:
                raise AptuniError(
                    "aptuni_activation_required",
                    "Aptuni is OFF. Activate Profile, Memory, or Full for this task.",
                )
            return self._retrieve("aptuni.full", query, modules=modules, budget=budget, limit=limit,
                                  concepts=concepts)

    def session_candidates(
        self,
        mode: str,
        *,
        modules: tuple[Module, ...],
        budget: int,
        limit: int,
        categories: tuple[str, ...] = (),
        candidates: tuple[str, ...] = (),
    ) -> ContextResponse:
        """ADR-0032 inventory → Evidence: only inside an explicitly enabled Full session."""
        with self._lock:
            if not self._session_full:
                raise AptuniError(
                    "aptuni_activation_required",
                    "Aptuni is OFF. Activate Profile, Memory, or Full for this task.",
                )
            if mode == "inventory":
                return inventory_context(self.service, categories, modules=modules, budget=budget,
                                         access=self.access())
            return candidate_evidence_context(self.service, candidates, modules=modules, budget=budget,
                                              limit=limit, access=self.access())

    def require_proposal_session(self) -> None:
        """Explain, in order, why a memory proposal cannot be made yet (ADR-0025: OFF captures nothing)."""
        access = self.access()
        if access is None or PROPOSE_SCOPE not in access.scopes:
            raise AptuniError(
                "mcp_scope_denied",
                f"This grant does not include {PROPOSE_SCOPE}, so the Agent cannot save memories. Tell the "
                "user; they can re-plan the adapter with --allow-memory-proposals, or save it themselves "
                "with 'aptuni observe'.",
            )
        with self._lock:
            if not self._session_full:
                raise AptuniError(
                    "aptuni_activation_required",
                    "Saving a memory needs Full for this session; a task-scoped activation leaves no state. "
                    "Ask the user whether to activate aptuni.full with scope=session, otherwise skip saving.",
                )

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
        concepts: tuple[str, ...] = (),
    ) -> ContextResponse:
        if intent == "aptuni.profile":  # ADR-0029 item 9: compact Knowledge State first
            return self.service.profile_context(
                query, modules=modules, budget=budget, limit=limit, audience="host_mcp", access=self.access(),
                concepts=concepts,
            )
        if intent == "aptuni.memory":
            return self.service.context(
                query, modules=modules, budget=budget, limit=limit, audience="host_mcp",
                access=self.access(), _record_types=("memory",), concepts=concepts,
            )
        return self.service.context(
            query, modules=modules, budget=budget, limit=limit, include_evidence=True,
            audience="host_mcp", access=self.access(), concepts=concepts,
        )
