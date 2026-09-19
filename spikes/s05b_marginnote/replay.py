"""S05B: replay the production MarginNote OPML reconciler over real MarginNote 4 backup history.

MarginNote 4 keeps notebook snapshots (``BackupSnapshots_v4.sqlite``) whose note objects are
zlib-compressed JSON in ``BackupStorage``. Each note carries its internal ``noteid`` and an ordered
``mindlinks`` child list. Snapshots are *incremental*: the first stores every note, later ones only
the changed notes, while ``note_count`` records the true total. A full state is reconstructed by
overlaying deltas; because a delta cannot say which note was deleted, a notebook's chain is
evaluated only while the overlay size equals ``note_count`` and stops at the first unresolvable
deletion.

For each notebook, consecutive snapshots are rendered as OPML-shaped outlines and fed through
``aptuni.sources.opml.scan_opml`` exactly as repeated syncs would be (state chained, no vendor ID
trusted). The true note ID rides along as an *untrusted* attribute that the matcher never reads,
so every identity decision can be scored:

- ``false_link``: the reconciler continued a subject across two different real notes (safety);
- ``false_split``: a real note kept its ID but was re-added under a new subject (UX cost);
- ``review``: ambiguous items held for the user.

Privacy: the database is opened read-only; note text stays in memory; only aggregate counts are
printed or written. Run: ``.venv/bin/python spikes/s05b_marginnote/replay.py [--json OUT]``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import time
import zlib
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from xml.sax.saxutils import quoteattr

from aptuni.sources.opml import OpmlScan, scan_opml

DEFAULT_ROOT = (Path.home() / "Library/Containers/QReader.MarginStudy.easy/Data/Library/Private Documents"
                / "MN4NotebookDatabase/0")
UUID = re.compile(r"[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}")
TRUTH = "x-s05b-truth"  # untrusted attribute; scan_opml only trusts an explicitly configured vendor attr
PARSER = ("marginnote.opml", "1")
EMPTY = "sha256:" + hashlib.sha256(b"").hexdigest()


class Store:
    """Read-only decoder for MarginNote 4 backup objects."""

    def __init__(self, root: Path) -> None:
        self.root = root
        index = sqlite3.connect(f"file:{root / 'BackupStorage' / 'index.sqlite'}?mode=ro", uri=True)
        self.locations = {row[0]: row[1:] for row in index.execute(
            "SELECT hash, location, pack_id, offset, compressed_size FROM object_index WHERE type='note'")}
        index.close()
        self.cache: dict[str, dict[str, Any]] = {}

    def note(self, digest: str) -> dict[str, Any]:
        if digest not in self.cache:
            location, pack_id, offset, size = self.locations[digest]
            if location == "pack":
                with open(self.root / "BackupStorage" / "objects" / "packs" / f"{pack_id}.pack", "rb") as handle:
                    handle.seek(int(offset) + 100)
                    blob = handle.read(int(size) - 12)
            else:
                data = (self.root / "BackupStorage" / "objects" / "loose" / digest[:2] / digest[2:]).read_bytes()
                if not data.startswith(b"MNCP"):
                    raise ValueError("bad_loose_header")
                blob = data[12:]
            self.cache[digest] = json.loads(zlib.decompress(blob))
        return self.cache[digest]


def _text(note: dict[str, Any]) -> str:
    """What an outline node shows: the card title, else its excerpt (comments are not node text)."""
    for key in ("notetitle", "highlight_text"):
        value = note.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def render(objects: dict[str, str], store: Store) -> tuple[str, int]:
    """Render one snapshot as OPML. Children follow ``mindlinks`` order; roots sort by note ID."""
    notes = {note_id: store.note(digest) for note_id, digest in objects.items()}
    children: dict[str, list[str]] = {}
    parented: set[str] = set()
    for note_id, note in notes.items():
        links = [c for c in UUID.findall(str(note.get("mindlinks") or "")) if c in notes and c != note_id]
        children[note_id] = [c for c in dict.fromkeys(links) if c not in parented]
        parented.update(children[note_id])
    roots = sorted(n for n in notes if n not in parented)
    out: list[str] = []
    seen: set[str] = set()

    def emit(note_id: str) -> None:
        if note_id in seen:
            return
        seen.add(note_id)
        out.append(f"<outline text={quoteattr(_text(notes[note_id]))} {TRUTH}={quoteattr(note_id)}>")
        for child in children[note_id]:
            emit(child)
        out.append("</outline>")

    for root in roots:
        emit(root)
    body = "".join(out)
    return f'<?xml version="1.0"?><opml version="2.0"><head/><body>{body}</body></opml>', len(seen)


def _truth(fields: Any) -> str:
    return str(fields["unknown_attributes"][TRUTH])


def score(previous: OpmlScan, current: OpmlScan, totals: Counter[str]) -> None:
    old = {i.locator.subject_id: i for i in previous.snapshot.items if not i.held}
    before = {subject: _truth(i.locator.extension.fields) for subject, i in old.items()}
    before_truths = set(before.values())
    after_truths = {_truth(i.locator.extension.fields) for i in current.snapshot.items if not i.held}
    for item in current.snapshot.items:
        if item.held:
            continue
        subject, truth = item.locator.subject_id, _truth(item.locator.extension.fields)
        if subject not in before:
            continue
        if before[subject] == truth:
            totals["correct_link"] += 1
            continue
        totals["false_link"] += 1
        if old[subject].content_hash != item.content_hash:
            totals["false_link_changed_content"] += 1  # safety: another note's history continued
        elif item.content_hash == EMPTY:
            totals["false_link_empty_text"] += 1
        elif before[subject] in after_truths:
            totals["false_link_duplicate_swap"] += 1
        else:
            totals["false_link_identical_recreate"] += 1
    for op in current.delta.operations:
        totals[f"op_{op.kind}"] += 1
        if op.kind == "add" and op.after is not None:
            split = _truth(op.after.extension.fields) in before_truths
            totals["false_split" if split else "true_add"] += 1
            if split:
                totals["false_split_empty_text" if op.content_hash == EMPTY else "false_split_text"] += 1
        elif op.kind == "remove" and op.before is not None:
            totals["false_remove" if _truth(op.before.extension.fields) in after_truths else "true_remove"] += 1
        elif op.kind == "ambiguous":
            totals["review_items"] += 1
            totals[f"review_{op.reasons[0]}"] += 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--json", type=Path, help="write aggregate counts (no content) to this file")
    parser.add_argument("--limit-topics", type=int, default=0)
    args = parser.parse_args()
    started = time.monotonic()
    store = Store(args.root)
    snaps = sqlite3.connect(f"file:{args.root / 'BackupSnapshots_v4.sqlite'}?mode=ro", uri=True)
    history: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for snapshot_id, topic, note_count in snaps.execute(
            "SELECT id, topicid, note_count FROM snapshots ORDER BY topicid, created_at, id"):
        history[topic].append((snapshot_id, note_count))
    objects: dict[str, dict[str, str]] = defaultdict(dict)
    for snapshot_id, object_id, digest in snaps.execute(
            "SELECT snapshot_id, object_id, hash FROM snapshot_objects WHERE object_type='note'"):
        objects[snapshot_id][object_id] = digest
    snaps.close()
    totals: Counter[str] = Counter()
    topics = [t for t, h in history.items() if len(h) >= 2]
    if args.limit_topics:
        topics = topics[: args.limit_topics]
    for number, topic in enumerate(topics, start=1):
        state: OpmlScan | None = None
        overlay: dict[str, str] = {}
        for snapshot_id, note_count in history[topic]:
            overlay.update(objects[snapshot_id])
            if len(overlay) != note_count:
                totals["chains_stopped_unresolvable_delete"] += 1
                break
            text, nodes = render(dict(overlay), store)
            totals["nodes_rendered"] += nodes
            scan = scan_opml(text, f"s05b-{number}", state, PARSER)
            if state is not None:
                totals["transitions"] += 1
                score(state, scan, totals)
                totals["noop_transitions"] += int(not scan.delta.operations)
            state = scan
        totals["topics"] += 1
    linked = totals["correct_link"] + totals["false_link"]
    summary = {
        "generated": time.strftime("%Y-%m-%d"),
        "parser": list(PARSER),
        "counts": dict(sorted(totals.items())),
        "false_link_rate": totals["false_link"] / linked if linked else 0.0,
        "continuity_recall": totals["correct_link"] / (totals["correct_link"] + totals["false_split"] or 1),
        "seconds": round(time.monotonic() - started, 1),
    }
    print(json.dumps(summary, indent=1))
    if args.json:
        args.json.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
