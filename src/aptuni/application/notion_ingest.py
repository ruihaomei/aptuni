"""Official Notion MCP fetch results -> minimized Evidence (ADR-0021)."""

from __future__ import annotations

import re
from typing import Protocol

from aptuni.application.errors import AptuniError
from aptuni.application.ingest import EXCERPT_CHARS, SOURCE_RETENTION, SourceState, _canonical_locator
from aptuni.domain.ids import deterministic_id
from aptuni.domain.records import Evidence, Provenance, SourceConfig
from aptuni.domain.temporal import utc_now
from aptuni.sources.notion import NotionEntity, NotionScan, NotionSourceSpec, scan_notion
from aptuni.sources.obsidian_parse import sanitize_token
from aptuni.sources.records import CandidateDelta, Operation

NOTION_PARSER = ("notion.mcp", "1")


class NotionReadClient(Protocol):
    """Narrow port: production implements this only through official Notion MCP `fetch`."""

    def fetch(self, entity_urls: tuple[str, ...]) -> tuple[str, list[NotionEntity]]: ...


def _plain_excerpt(entity: NotionEntity) -> str:
    text = re.sub(r"<[^>]{0,1000}>", " ", entity.text)
    text = re.sub(r"[`*_~#$>|{}\[\]()]", " ", text)
    plain = " ".join(text.split())
    if not plain.casefold().startswith(entity.title.strip().casefold()):
        plain = f"{entity.title} {plain}"
    return sanitize_token(plain)[:EXCERPT_CHARS]


class NotionIngest:
    def __init__(self, config: SourceConfig, module: str, policy_epoch: int,
                 current: dict[str, Evidence], existing_ids: set[str], client: NotionReadClient) -> None:
        self.config = config
        self.module = module
        self.policy_epoch = policy_epoch
        self.current = current
        self.existing_ids = existing_ids
        self.client = client
        self.spec = NotionSourceSpec.from_roots(config.roots)
        self._entities: dict[str, NotionEntity] = {}

    def scan(self, state: SourceState | None) -> NotionScan:
        principal_id, entities = self.client.fetch(self.spec.entity_urls)
        prior_principal = state.provider_data.get("principal_id") if state else None
        if prior_principal is not None and prior_principal != principal_id:
            raise AptuniError(
                "notion_principal_changed",
                "The official Notion MCP connection identity changed; nothing was changed.",
            )
        self._entities = {entity.entity_id: entity for entity in entities}
        previous = None
        if state is not None:
            previous_delta = CandidateDelta.build(
                self.config.id, state.snapshot.snapshot_id, state.snapshot.snapshot_id,
                state.parser, (), sequence=state.sequence,
            )
            previous = NotionScan(state.snapshot, previous_delta, state.parser, state.notes, principal_id)
        return scan_notion(self.spec, self.config.id, entities, previous, NOTION_PARSER,
                           principal_id=principal_id)

    def evidence_for(self, op: Operation, delta_id: str, sequence: int) -> Evidence | None:
        subject = op.subject_id
        if subject is None or deterministic_id("evd", f"{delta_id}:{subject}") in self.existing_ids:
            return None
        previous = self.current.get(subject)
        if op.kind == "remove":
            if previous is None:
                return None
            return self._record(op, delta_id, sequence, previous, retraction=True)
        return self._record(op, delta_id, sequence, previous, retraction=False)

    def _record(self, op: Operation, delta_id: str, sequence: int, previous: Evidence | None,
                *, retraction: bool) -> Evidence:
        locator = op.before if retraction else op.after
        assert locator is not None
        if retraction:
            assert previous is not None
            excerpt, content_hash, change_kind = previous.excerpt, previous.content_hash, "retraction"
        else:
            entity_id = str(locator.extension.fields["entity_id"])
            entity = self._entities.get(entity_id)
            if entity is None:
                raise AptuniError("notion_result_missing", "An approved Notion entity result disappeared during sync.")
            excerpt = _plain_excerpt(entity)
            content_hash = str(op.content_hash)
            change_kind = "assert" if previous is None else (
                "correction" if "parser_upgrade" in op.reasons else "world_change")
        now = utc_now()
        return Evidence(
            record_type="evidence", id=deterministic_id("evd", f"{delta_id}:{locator.subject_id}"),
            schema_version=1, recorded_at=now, valid_from=None, valid_until=None,
            module=self.module,
            provenance=Provenance(source_id=self.config.id, episode=f"sync-{sequence}",
                                  locator=_canonical_locator(locator)),
            trust="untrusted_source", retention=SOURCE_RETENTION, policy_epoch=self.policy_epoch,
            confidence=None, review_status="auto_derived", supersedes=(previous.id,) if previous else (),
            change_kind=change_kind, subject=str(locator.extension.fields["title"]),
            signals=() if retraction else ("exposure",), excerpt=excerpt,
            content_hash=content_hash, observed_at=now,
        )
