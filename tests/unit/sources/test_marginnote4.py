"""MarginNote 4 local source: schema gate, read-only access, digest, native-ID identity (ADR-0015)."""

from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path

import pytest

from aptuni.sources.marginnote4 import MarginNoteStoreError, build_digest, probe, read_snapshot, scan_marginnote
from aptuni.sources.marginnote4.scan import MarginNoteScan
from aptuni.sources.marginnote4.store import inventory
from marginnote_fixture import Card, base_cards, build_store, nid, unknown_digest


def scan(path: Path, previous: MarginNoteScan | None = None, notebooks: frozenset[str] | None = None,
         missing: frozenset[str] = frozenset()) -> MarginNoteScan:
    return scan_marginnote(build_digest(read_snapshot(path, notebooks)), "src_mn", previous, missing)


def kinds(result: MarginNoteScan) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for op in result.delta.operations:
        out.setdefault(op.kind, []).append(str(op.subject_id))
    return out


def test_unknown_layout_or_missing_column_fails_closed(tmp_path: Path) -> None:
    for store in (build_store(tmp_path / "a.sqlite", base_cards(), digest=unknown_digest()),
                  build_store(tmp_path / "b.sqlite", base_cards(), drop_column="ZMINDLINKS")):
        with pytest.raises(MarginNoteStoreError, match="marginnote_schema_unsupported"):
            read_snapshot(store, None)


def test_reads_never_modify_the_store(tmp_path: Path) -> None:
    store = build_store(tmp_path / "s.sqlite", base_cards())
    before = hashlib.sha256(store.read_bytes()).hexdigest()
    read_snapshot(store, None)
    inventory(store)
    assert hashlib.sha256(store.read_bytes()).hexdigest() == before


def test_digest_counts_excerpts_without_copying_them(tmp_path: Path) -> None:
    result = scan(build_store(tmp_path / "s.sqlite", base_cards()))
    assert set(result.rendered) == {nid(1), nid(2), nid(3), nid(4), nid(5), nid(8)}  # concepts only
    forest = result.rendered[nid(2)]
    assert forest.subject == "Ensemble methods › Random forest"
    assert "covers: Bagging, Out-of-bag error" in forest.summary
    assert "2 excerpts" in forest.summary and "Elements of Statistical Lea… p.587–592" in forest.summary
    for rendered in result.rendered.values():
        assert "SECRET-BODY" not in rendered.summary + rendered.subject
        assert len(rendered.summary) <= 280


def test_locator_holds_identity_and_structure_only(tmp_path: Path) -> None:
    result = scan(build_store(tmp_path / "s.sqlite", base_cards()))
    for item in result.snapshot.items:
        fields = item.locator.extension.fields
        assert (item.locator.extension.schema, item.locator.extension.version) == ("marginnote.locator", 2)
        assert fields["note_id"] == item.locator.subject_id
        text_values = [v for k, v in fields.items() if isinstance(v, str) and k not in
                       {"database_id", "notebook_id", "note_id", "parent_id"}]
        assert text_values == []
    forest = next(i for i in result.snapshot.items if i.locator.subject_id == nid(2)).locator.extension.fields
    assert forest["parent_id"] == nid(1) and forest["depth"] == 1 and forest["child_count"] == 2


def test_native_identity_drives_every_operation(tmp_path: Path) -> None:
    path = tmp_path / "s.sqlite"
    first = scan(build_store(path, base_cards()))
    assert kinds(first) == {"add": sorted(first.rendered)}
    assert scan(path, first).delta.operations == ()  # re-read without changes is a no-op

    cards = base_cards()
    cards[4].title = "Bootstrap aggregating"  # edit
    cards[1].children = [2]  # Boosting moves under Random forest
    cards[2].children = [4, 6, 3]
    del cards[5]  # delete
    cards[9] = Card(title="Random forest")  # a copy is a new card, never the old identity
    second = scan(build_store(path, cards), first)
    got = kinds(second)
    assert got["move"] == [nid(3)]
    assert nid(4) in got["modify"] and nid(9) in got["add"] and got["remove"] == [nid(5)]
    assert "ambiguous" not in got


def test_missing_notebook_is_partial_and_withdraws_nothing(tmp_path: Path) -> None:
    path = tmp_path / "s.sqlite"
    selected = frozenset({"NB-A", "NB-B"})
    first = scan(build_store(path, base_cards()), notebooks=selected)
    cards = {k: v for k, v in base_cards().items() if v.notebook == "NB-A"}
    second = scan(build_store(path, cards, notebooks={"NB-A": "Statistics"}), first, selected,
                  missing=frozenset({"NB-B"}))
    assert second.snapshot.coverage == "partial"
    assert "remove" not in kinds(second)
    assert nid(8) in {i.locator.subject_id for i in second.snapshot.items}


def test_notebook_scope_is_respected(tmp_path: Path) -> None:
    result = scan(build_store(tmp_path / "s.sqlite", base_cards()), notebooks=frozenset({"NB-B"}))
    assert set(result.rendered) == {nid(8)}


def test_mind_map_cycles_terminate_with_a_path(tmp_path: Path) -> None:
    cards = {1: Card(title="A", children=[2]), 2: Card(title="B", children=[1])}
    result = scan(build_store(tmp_path / "s.sqlite", cards))
    assert all(r.subject for r in result.rendered.values())


def test_probe_reports_each_state_without_hanging(tmp_path: Path) -> None:
    assert probe(tmp_path / "absent").status == "not_found"
    container = tmp_path / "container"
    store = container / "Library" / "Private Documents" / "MN4NotebookDatabase" / "0" / "MarginNotes.sqlite"
    build_store(store, base_cards())
    found = probe(container)
    assert found.status == "found" and found.stores == (store,)
    assert probe(container, timeout=0.000001).status == "permission_pending"
    os.chmod(container, 0)
    try:
        if os.geteuid() != 0:
            assert probe(container).status == "permission_denied"
    finally:
        os.chmod(container, stat.S_IRWXU)


def test_deletion_during_partial_coverage_is_withdrawn_later(tmp_path: Path) -> None:
    """Review 24 B1: an unobserved card is carried while coverage is partial, then removed."""
    path, selected = tmp_path / "s.sqlite", frozenset({"NB-A", "NB-B"})
    first = scan(build_store(path, base_cards()), notebooks=selected)
    cards = {k: v for k, v in base_cards().items() if v.notebook == "NB-A" and k != 5}
    second = scan(build_store(path, cards, notebooks={"NB-A": "Statistics"}), first, selected,
                  missing=frozenset({"NB-B"}))
    assert "remove" not in kinds(second) and nid(5) in {i.locator.subject_id for i in second.snapshot.items}
    restored = {k: v for k, v in base_cards().items() if k != 5}
    third = scan(build_store(path, restored), second, selected)
    assert kinds(third).get("remove") == [nid(5)]


def test_card_moved_out_of_a_missing_notebook_does_not_wedge(tmp_path: Path) -> None:
    """Review 24 B2: an observed card is never also carried forward."""
    path, selected = tmp_path / "s.sqlite", frozenset({"NB-A", "NB-B"})
    first = scan(build_store(path, base_cards()), notebooks=selected)
    cards = {k: v for k, v in base_cards().items() if v.notebook == "NB-A"}
    cards[8] = Card(title="Feature engineering", notebook="NB-A")
    second = scan(build_store(path, cards, notebooks={"NB-A": "Statistics"}), first, selected,
                  missing=frozenset({"NB-B"}))
    subjects = [i.locator.subject_id for i in second.snapshot.items]
    assert len(subjects) == len(set(subjects)) and nid(8) in subjects


def test_untitled_parent_label_is_a_bounded_excerpt_head(tmp_path: Path) -> None:
    long_excerpt = "Heading of a textbook section " + "x" * 400
    cards = {1: Card(excerpt=long_excerpt, children=[2]), 2: Card(title="Child")}
    result = scan(build_store(tmp_path / "s.sqlite", cards))
    label = result.rendered[nid(1)].subject
    assert len(label) <= 32 and "x" * 40 not in result.rendered[nid(2)].summary


def test_nested_merged_excerpts_count_toward_the_final_card(tmp_path: Path) -> None:
    cards = {1: Card(title="Card"), 2: Card(excerpt="a", group=1), 3: Card(excerpt="b", group=2)}
    result = scan(build_store(tmp_path / "s.sqlite", cards))
    assert "2 excerpts" in result.rendered[nid(1)].summary


def test_an_empty_read_never_withdraws_everything(tmp_path: Path) -> None:
    path = tmp_path / "s.sqlite"
    first = scan(build_store(path, base_cards()))
    with pytest.raises(MarginNoteStoreError, match="marginnote_store_empty"):
        scan(build_store(path, {}), first)
