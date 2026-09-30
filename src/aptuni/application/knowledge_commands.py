"""Knowledge State for the owner and compact Profile activation (ADR-0029 items 8–9).

The projection is rebuilt from exposable records of one Vault snapshot, restricted to the modules the
caller may see, and cached per Vault sequence. Profile activation leads with at most
``MAX_PROFILE_STATES`` cited ``knowledge_state`` units and drops the individual Evidence and
Evidence-derived Facts they already summarise.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from aptuni.application.context import MAX_BUDGET, ContextResponse, ContextUnit, pack_units, response_from
from aptuni.application.errors import AptuniError
from aptuni.domain.evidence_profile import EVIDENCE_PROFILE_TYPE
from aptuni.domain.invariants import RecordSet
from aptuni.knowledge.state import KnowledgeIndex, KnowledgeState

__all__ = ["MAX_PROFILE_STATES", "KnowledgeCommands", "knowledge_unit"]

MAX_PROFILE_STATES = 5
MAX_CITED_IDS = 8


def knowledge_unit(state: KnowledgeState) -> ContextUnit:
    """One L2 unit; labels come from source titles, so the unit is marked tainted."""
    cited = (*state.evidence_ids[:MAX_CITED_IDS], *state.declared_ids[:2])
    return ContextUnit("L2", "knowledge_state", None, None, state.summary(), None, None, True, state.signals, cited)


class KnowledgeCommands:
    """Mixin for ``AptuniService``; the host class provides snapshots and Context retrieval."""

    _knowledge_cache: tuple[tuple[int, tuple[str, ...]], KnowledgeIndex] | None = None

    def snapshot(self) -> tuple[int, RecordSet]:
        raise NotImplementedError

    context: Callable[..., ContextResponse]  # AptuniService.context

    def knowledge_index(self, seq: int, records: RecordSet, modules: tuple[str, ...] = ()) -> KnowledgeIndex:
        key = (seq, tuple(sorted(modules)))
        cached = self._knowledge_cache
        if cached is not None and cached[0] == key:
            return cached[1]
        visible = [r for r in records.exposable() if not modules or r.module in modules]
        index = KnowledgeIndex(visible)
        self._knowledge_cache = (key, index)
        return index

    def knowledge_states(self, query: str | None = None, *, modules: tuple[str, ...] = (),
                         limit: int = 20) -> list[KnowledgeState]:
        """The owner's view: the strongest concepts, or those relevant to ``query``."""
        seq, records = self.snapshot()
        index = self.knowledge_index(seq, records, modules)
        if not query:
            return index.top(limit)
        matched = self.context(query, modules=modules, include_evidence=True, limit=limit, budget=100_000)
        return index.relevant(query, [u.canonical_id for u in matched.items if u.canonical_id], limit)

    def profile_context(self, query: str, *, modules: tuple[str, ...], budget: int, limit: int,
                        audience: str, access: Any) -> ContextResponse:
        """``aptuni.profile``: Knowledge State units first, without the rows they summarise."""
        for _ in range(3):
            # Rank the ``limit`` rows unbudgeted, then pack once at ``budget`` after summarising, so the
            # space the summaries free goes to rows that would otherwise have been cut.
            response = self.context(query, modules=modules, budget=MAX_BUDGET, limit=limit, audience=audience,
                                    access=access, include_evidence=True, _record_types=("fact", "evidence"))
            seq, records = self.snapshot()
            if seq != response.vault_seq:
                continue
            index = self.knowledge_index(seq, records, modules)
            ranked = [u.canonical_id for u in response.items if u.canonical_id]
            states = index.relevant(query, ranked, MAX_PROFILE_STATES)
            covered = {evidence_id for state in states for evidence_id in state.evidence_ids}
            sections = [u for u in response.items if u.canonical_id is None]
            rows = [u for u in response.items if u.canonical_id is not None and not _summarised(u, records, covered)]
            packed = pack_units((*sections, *(knowledge_unit(s) for s in states), *rows), budget)
            return response_from(packed, budget=budget, vault_seq=seq, policy_epoch=response.policy_epoch,
                                 more_results=response.truncated, audience=response.audience)
        raise AptuniError("concurrent_write", "The Vault kept changing during context creation; run it again.")


def _summarised(unit: ContextUnit, records: RecordSet, covered: set[str]) -> bool:
    if unit.kind == "evidence":
        return unit.canonical_id in covered
    if unit.kind != "fact" or unit.canonical_id is None:
        return False
    fact = records.get(unit.canonical_id)
    return fact.type == EVIDENCE_PROFILE_TYPE and bool(set(fact.evidence_ids) & covered)
