"""Keep credentials out of canonical Evidence during source sync (ADR-0031).

A source item whose text holds an obvious credential is *withheld*: it gets no Evidence record, and
an earlier version of the same item is retracted. Every sync also sweeps the source's current
Evidence, so records ingested before this guard existed are retracted too. Retractions written here
— and by source removal and authority re-derivation — carry no excerpt and no credential-bearing
subject or locator text, so containment never copies a secret into a new record. The user's source
files are never read for anything else or modified.
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
# Owner-facing location of a withheld item: a path or native id, never a title or text (Review 93 B3).
_LOCATION_FIELDS = ("relative_path", "path", "entity_id", "activity_key", "note_id")


@dataclass(frozen=True)
class Containment:
    evidence: list[Evidence]
    withheld: int
    locations: tuple[str, ...] = ()


def _locator_fields(record: Evidence) -> dict[str, Any]:
    locator = record.provenance.locator
    return dict(locator.extension.fields) if locator is not None and locator.extension is not None else {}


def record_text(record: Evidence) -> str:
    """Every free text an Evidence record carries: subject, excerpt and string locator fields."""
    parts = [record.subject, record.excerpt or ""]
    parts.extend(value for value in _locator_fields(record).values() if isinstance(value, str))
    return " ".join(part for part in parts if part)


def location_of(record: Evidence) -> str:
    fields = _locator_fields(record)
    for name in _LOCATION_FIELDS:
        if isinstance(fields.get(name), str) and fields[name] and not contains_credential(fields[name]):
            return str(fields[name])
    locator = record.provenance.locator
    return locator.subject_id if locator is not None else record.id


def scrubbed(record: Evidence) -> Evidence:
    """``record`` without credential-bearing text: no excerpt, neutral subject and locator strings."""
    if not contains_credential(record_text(record)):
        return record
    fields = record.model_dump(by_alias=True)
    fields.update(excerpt=None, subject=WITHHELD_SUBJECT if contains_credential(record.subject) else record.subject)
    locator = fields["provenance"].get("locator")
    if locator and locator.get("extension"):
        extension = locator["extension"]
        extension["fields"] = {name: WITHHELD_SUBJECT if isinstance(value, str) and contains_credential(value)
                               else value for name, value in extension["fields"].items()}
    return Evidence.model_validate(fields)


def retraction_of(previous: Evidence, record_id: str, *, episode: str | None, policy_epoch: int) -> Evidence:
    now = utc_now()
    fields = previous.model_dump(by_alias=True)
    fields.update(id=record_id, recorded_at=now, observed_at=now, policy_epoch=policy_epoch,
                  supersedes=(previous.id,), change_kind="retraction", signals=(), excerpt=None,
                  review_status="auto_derived")
    fields["provenance"] = {**fields["provenance"], "episode": episode}
    return scrubbed(Evidence.model_validate(fields))


def rederive_or_withhold(previous: Evidence, record_id: str, signals: tuple[str, ...]) -> Evidence:
    """Authority re-derivation: a correction, unless the item holds a credential — then a retraction."""
    if contains_credential(record_text(previous)):
        return retraction_of(previous, record_id, episode=previous.provenance.episode,
                             policy_epoch=previous.policy_epoch)
    return Evidence.model_validate({
        **previous.model_dump(), "id": record_id, "recorded_at": utc_now(), "supersedes": (previous.id,),
        "change_kind": "correction", "signals": signals,
    })


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
    locations: list[str] = []
    for record in evidence:
        touched.add(record.provenance.locator.subject_id if record.provenance.locator else record.id)
        if record.change_kind == "retraction":
            kept.append(scrubbed(record))
            continue
        if not contains_credential(record_text(record)):
            kept.append(record)
            continue
        locations.append(location_of(record))
        previous = by_id.get(record.supersedes[0]) if record.supersedes else None
        if previous is not None and previous.change_kind != "retraction":
            kept.append(retraction_of(previous, record.id, episode=f"sync-{sequence}", policy_epoch=policy_epoch))
    for subject_id, previous in sorted(current.items()):
        if subject_id in touched or previous.change_kind == "retraction" \
                or not contains_credential(record_text(previous)):
            continue
        locations.append(location_of(previous))
        kept.append(retraction_of(previous, deterministic_id("evd", f"credential-withheld:{previous.id}"),
                                  episode=f"sync-{sequence}", policy_epoch=policy_epoch))
    return Containment(kept, len(locations), tuple(sorted(set(locations))))
