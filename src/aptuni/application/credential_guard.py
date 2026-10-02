"""Keep credentials out of canonical Evidence during source sync (ADR-0031).

A source item whose text holds an obvious credential is *withheld*: it gets no Evidence record, and
an earlier version of the same item is retracted. Every sync also sweeps the source's current
Evidence, so records ingested before this guard existed are retracted too. Retractions written here
carry no excerpt, so containment never copies a secret into a new record. The user's source files
are never read for anything else or modified.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from aptuni.domain.ids import deterministic_id
from aptuni.domain.records import Evidence
from aptuni.domain.temporal import utc_now
from aptuni.policy.secrets import contains_credential

WITHHELD_SUBJECT = "[credential withheld]"


@dataclass(frozen=True)
class Containment:
    evidence: list[Evidence]
    withheld: int


def _text(record: Any) -> str:
    return " ".join(str(part) for part in (record.subject, record.excerpt) if part)


def _retraction(record_id: str, previous: Evidence, *, episode: str, policy_epoch: int) -> Evidence:
    now = utc_now()
    fields = previous.model_dump(by_alias=True)
    fields.update(
        id=record_id, recorded_at=now, observed_at=now, policy_epoch=policy_epoch, supersedes=(previous.id,),
        change_kind="retraction", signals=(), excerpt=None, review_status="auto_derived",
        subject=WITHHELD_SUBJECT if contains_credential(previous.subject) else previous.subject,
    )
    fields["provenance"] = {**fields["provenance"], "episode": episode}
    return Evidence.model_validate(fields)


def _scrubbed(record: Evidence) -> Evidence:
    fields = record.model_dump(by_alias=True)
    fields.update(excerpt=None, subject=WITHHELD_SUBJECT if contains_credential(record.subject) else record.subject)
    return Evidence.model_validate(fields)


def contain_credentials(
    evidence: Iterable[Evidence],
    current: dict[str, Evidence],
    *,
    sequence: int,
    policy_epoch: int,
) -> Containment:
    """Withhold credential-bearing items of one sync delta and sweep the source's legacy Evidence."""
    by_id = {record.id: record for record in current.values()}
    kept: list[Evidence] = []
    touched: set[str] = set()
    withheld = 0
    for record in evidence:
        touched.add(record.provenance.locator.subject_id if record.provenance.locator else record.id)
        if record.change_kind == "retraction":
            kept.append(_scrubbed(record) if contains_credential(_text(record)) else record)
            continue
        if not contains_credential(_text(record)):
            kept.append(record)
            continue
        withheld += 1
        previous = by_id.get(record.supersedes[0]) if record.supersedes else None
        if previous is not None and previous.change_kind != "retraction":
            kept.append(_retraction(record.id, previous, episode=f"sync-{sequence}", policy_epoch=policy_epoch))
    for subject_id, previous in sorted(current.items()):
        if subject_id in touched or previous.change_kind == "retraction" or not contains_credential(_text(previous)):
            continue
        withheld += 1
        kept.append(_retraction(deterministic_id("evd", f"credential-withheld:{previous.id}"), previous,
                                episode=f"sync-{sequence}", policy_epoch=policy_epoch))
    return Containment(kept, withheld)
