"""MarginNote OPML reconciliation against a source-local identity manifest.

No public MarginNote contract promises stable node IDs, so vendor attributes
are preserved but untrusted unless explicitly configured (``trusted_vendor_attr``).
Matching runs to a fixed point over: trusted vendor ID, same parent + same
content, globally unique content, identical non-empty child signature. Kinds
(move/modify) are decided afterwards from final parent identity. Weak evidence
never links silently: indistinguishable duplicates and same-position leaf edits
become review items. Branch exports are partial and cannot prove removal.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field, replace
from typing import Any

from s05a.opml_parse import OpmlError, OutlineNode, parse_opml
from s05a.records import CandidateDelta, Extension, Operation, Snapshot, SnapshotItem, SourceLocator, canonical_json
from s05a.reconcile import snapshot_id_for

ROOT = "__root__"
SCHEMA = ("marginnote.locator", 1)

__all__ = ["OpmlError", "OpmlScan", "parse_opml", "scan_opml"]


@dataclass(frozen=True)
class OpmlScan:
    snapshot: Snapshot
    delta: CandidateDelta
    parser: tuple[str, str]


@dataclass
class _New:
    index: int
    position: tuple[int, ...]
    text: str
    content_hash: str
    attributes: dict[str, str]
    parent: int | None
    sibling_index: int
    children: list[int] = field(default_factory=list)
    children_signature: str | None = None


def _fields(item: SnapshotItem) -> Any:
    return item.locator.extension.fields


def _hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _flatten(roots: tuple[OutlineNode, ...]) -> list[_New]:
    nodes: list[_New] = []

    def visit(node: OutlineNode, parent: int | None, position: tuple[int, ...]) -> int:
        index = len(nodes)
        nodes.append(_New(index, position, node.text, _hash(node.text), dict(node.attributes), parent, position[-1]))
        for offset, child in enumerate(node.children):
            nodes[index].children.append(visit(child, index, (*position, offset)))
        return index

    for offset, root in enumerate(roots):
        visit(root, None, (offset,))
    for node in nodes:
        if node.children:
            hashes = sorted(nodes[child].content_hash for child in node.children)
            node.children_signature = _hash(canonical_json(hashes))
    return nodes


class _Matcher:
    def __init__(self, nodes: list[_New], old: dict[str, SnapshotItem], vendor_attr: str | None) -> None:
        self.nodes, self.old, self.vendor_attr = nodes, old, vendor_attr
        self.matched: dict[int, tuple[str, str]] = {}  # new index -> (old subject, reason)

    def used(self) -> set[str]:
        return {subject for subject, _ in self.matched.values()}

    def parent_subject(self, node: _New) -> str | None:
        if node.parent is None:
            return ROOT
        hit = self.matched.get(node.parent)
        return hit[0] if hit else None

    def _pair(self, key_new: Any, key_old: Any, reason: str) -> bool:
        free_new = [n for n in self.nodes if n.index not in self.matched]
        used = self.used()
        by_new: dict[Any, list[int]] = defaultdict(list)
        by_old: dict[Any, list[str]] = defaultdict(list)
        for node in free_new:
            key = key_new(node)
            if key is not None:
                by_new[key].append(node.index)
        for subject, item in self.old.items():
            key = None if subject in used else key_old(item)
            if key is not None:
                by_old[key].append(subject)
        progress = False
        for key, indexes in by_new.items():
            if len(indexes) == 1 and len(by_old.get(key, [])) == 1:
                self.matched[indexes[0]] = (by_old[key][0], reason)
                progress = True
        return progress

    def run(self) -> None:
        phases = [
            (lambda n: n.attributes.get(self.vendor_attr) if self.vendor_attr else None,
             lambda i: _fields(i)["vendor_node_id"], "vendor_id_match"),
            (lambda n: (n.content_hash, self.parent_subject(n)) if self.parent_subject(n) else None,
             lambda i: (i.content_hash, _fields(i).get("parent_node_id")), "parent_content_match"),
            (lambda n: n.content_hash, lambda i: i.content_hash, "exact_content_unique"),
            # A single (often generic) child is too weak to link parents (review F5).
            (lambda n: n.children_signature if len(n.children) >= 2 else None,
             lambda i: _fields(i).get("children_signature"), "children_signature_match"),
        ]
        while any([self._pair(new_key, old_key, reason) for new_key, old_key, reason in phases]):
            pass

    def demote_partial_relocations(self) -> dict[int, str]:
        """In a partial (branch) export, a parent change may be a copy outside scope: review it (F2)."""
        demoted: dict[int, str] = {}
        changed = True
        while changed:
            changed = False
            for index, (subject, _) in list(self.matched.items()):
                node = self.nodes[index]
                if node.parent is None:
                    continue  # top of the exported branch: parent is outside scope by construction
                if self.parent_subject(node) != _fields(self.old[subject]).get("parent_node_id"):
                    demoted[index] = subject
                    del self.matched[index]
                    changed = True
        return demoted


def scan_opml(
    text: str,
    source_id: str,
    previous: OpmlScan | None,
    parser: tuple[str, str],
    export_scope: str = "full",
    trusted_vendor_attr: str | None = None,
) -> OpmlScan:
    nodes = _flatten(parse_opml(text))
    prior = previous.snapshot.items if previous else ()
    held = [item for item in prior if item.held]  # reserved by unresolved review: never re-matched
    old = {item.locator.subject_id: item for item in prior if not item.held}
    base_id = previous.snapshot.snapshot_id if previous else None
    matcher = _Matcher(nodes, old, trusted_vendor_attr)
    matcher.run()
    branch = export_scope != "full"
    demoted = matcher.demote_partial_relocations() if branch else {}
    subjects: dict[int, str] = {i: s for i, (s, _) in matcher.matched.items()}
    pending: dict[int, tuple[str, ...]] = {}
    matched_subjects = matcher.used()
    used = set(matched_subjects) | set(demoted.values())  # grows with review reservations

    for node in nodes:  # review items for weak or indistinguishable evidence
        if node.index in subjects:
            continue
        subjects[node.index] = "marginnote-" + _hash(canonical_json([source_id, base_id, node.position,
                                                                     node.content_hash]))[7:27]
        if node.index in demoted:
            pending[node.index] = (demoted[node.index], "partial_scope_relocation")
            continue
        # Indistinguishable duplicates share one candidate set, so compare with matcher results only.
        same = [s for s, item in old.items()
                if s not in matched_subjects and s not in demoted.values()
                and item.content_hash == node.content_hash]
        parent = matcher.parent_subject(node)
        slot = [s for s, item in old.items() if s not in used and parent and not node.children
                and item.locator.extension.fields.get("parent_node_id") == parent
                and item.locator.extension.fields.get("sibling_index") == node.sibling_index
                and item.locator.extension.fields.get("children_signature") is None]
        found, reason = (same, "duplicate_content") if same else (slot, "same_position_text_changed")
        if found:
            pending[node.index] = (*found, reason)
            used.update(found)

    def locator(node: _New) -> SourceLocator:
        chain, cursor = [], node
        while cursor is not None:
            chain.append(cursor)
            cursor = nodes[cursor.parent] if cursor.parent is not None else None
        top = chain[-1]
        prefix: list[str] = []
        parent_id = subjects[node.parent] if node.parent is not None else ROOT
        if branch and top.index in matcher.matched:
            top_fields = old[matcher.matched[top.index][0]].locator.extension.fields
            prefix = list(top_fields["ancestor_path"][:-1])
            if node is top:
                parent_id = top_fields["parent_node_id"]
        fields: dict[str, Any] = {
            "canonical_node_id": subjects[node.index],
            "ancestor_path": prefix + [n.text for n in reversed(chain)],
            "vendor_node_id": node.attributes.get(trusted_vendor_attr) if trusted_vendor_attr else None,
            "unknown_attributes": node.attributes,
            "parent_node_id": parent_id,
            "children_signature": node.children_signature,
            "sibling_index": node.sibling_index,
            "export_scope": export_scope,
        }
        return SourceLocator(source_id, "marginnote", subjects[node.index], Extension(*SCHEMA, fields))

    ops: list[Operation] = []
    items: list[SnapshotItem] = []
    parser_changed = previous is not None and previous.parser != parser
    for node in nodes:
        after = locator(node)
        items.append(SnapshotItem(after, node.content_hash))
        if node.index in pending:
            *candidates, reason = pending[node.index]
            if len(candidates) == 1:
                candidates.append(subjects[node.index])
            ops.append(Operation.ambiguous(after, tuple(candidates), (reason,), content_hash=node.content_hash))
        elif node.index not in matcher.matched:
            ops.append(Operation.add(after, node.content_hash))
        else:
            ops.extend(_matched_op(old[subjects[node.index]], after, node, matcher, branch, parser_changed))

    reserved = sorted(s for s in used if s not in matched_subjects)
    items.extend([*held, *(replace(old[s], held=True) for s in reserved)])
    leftovers = sorted(s for s in old if s not in used)
    if branch:
        items.extend(old[s] for s in leftovers)
    else:
        ops.extend(Operation.remove(s, old[s].locator, old[s].content_hash, reasons=("source_node_missing",))
                   for s in leftovers)
    ordered = tuple(sorted(items, key=lambda item: item.locator.subject_id))
    coverage = "partial" if branch else "complete"
    snapshot = Snapshot(snapshot_id_for(source_id, coverage, ordered), source_id, coverage, ordered)
    delta = CandidateDelta.build(source_id, base_id, snapshot.snapshot_id, parser, tuple(ops))
    return OpmlScan(snapshot, delta, parser)


def _matched_op(
    old: SnapshotItem, after: SourceLocator, node: _New, matcher: _Matcher, branch: bool, parser_changed: bool
) -> list[Operation]:
    reason = matcher.matched[node.index][1]
    before = old.locator
    old_fields, new_fields = before.extension.fields, after.extension.fields
    top_of_branch = branch and node.parent is None
    moved = not top_of_branch and old_fields.get("parent_node_id") != new_fields["parent_node_id"]
    changed = old.content_hash != node.content_hash
    subject = after.subject_id
    if moved:
        reasons = (reason, "content_changed") if changed else (reason,)
        return [Operation.move(subject, before, after, node.content_hash, reasons=reasons)]
    if changed:
        return [Operation.modify(before, after, node.content_hash, reasons=(reason,))]
    if old_fields.get("unknown_attributes") != new_fields["unknown_attributes"]:
        return [Operation.modify(before, after, node.content_hash, reasons=("attributes_changed",))]
    if parser_changed:
        return [Operation.modify(before, after, node.content_hash, reasons=("parser_upgrade",))]
    return []
