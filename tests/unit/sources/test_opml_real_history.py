"""S05B reconciler refinements R1 (same-slot identical siblings) and R3 (weak structural match)."""

from __future__ import annotations

from aptuni.sources.opml import OpmlScan, scan_opml

PARSER = ("marginnote.opml", "1")


def doc(body: str) -> str:
    return f'<?xml version="1.0"?><opml version="2.0"><head/><body>{body}</body></opml>'


def scan(body: str, previous: OpmlScan | None = None) -> OpmlScan:
    return scan_opml(doc(body), "src_s05b", previous, PARSER)


def subject_of(result: OpmlScan, path: list[str]) -> str:
    return next(i.locator.subject_id for i in result.snapshot.items
                if i.locator.extension.fields["ancestor_path"] == path and not i.held)


def kinds(result: OpmlScan) -> list[str]:
    return sorted(op.kind for op in result.delta.operations)


def test_r1_identical_siblings_keep_identity_in_their_slot() -> None:
    """Two unchanged 'Example' labels and an image-only card stay stable across a no-op sync."""
    body = '<outline text="Topic"><outline text="Example"/><outline text=""/><outline text="Example"/></outline>'
    first = scan(body)
    second = scan(body, first)
    assert second.delta.operations == ()
    assert {i.locator.subject_id for i in first.snapshot.items} == {i.locator.subject_id for i in second.snapshot.items}


def test_indistinguishable_duplicates_that_move_still_go_to_review() -> None:
    """ADR-0006: two identical 'Example' cards moving to another parent is ambiguous, never a silent guess."""
    first = scan('<outline text="Stats"><outline text="Example"/><outline text="Example"/></outline>'
                 '<outline text="ML"/>')
    second = scan('<outline text="Stats"/><outline text="ML"><outline text="Example"/>'
                  '<outline text="Example"/></outline>', first)
    ambiguous = [op for op in second.delta.operations if op.kind == "ambiguous"]
    assert ambiguous and all("duplicate_content" in op.reasons for op in ambiguous)
    assert not [op for op in second.delta.operations if op.kind == "remove"]


def test_r3_children_signature_cannot_carry_both_text_and_parent_change() -> None:
    """A parent matched only by generic children, whose own text AND parent changed, is reviewed."""
    first = scan('<outline text="Probability"><outline text="Bayes rule">'
                 '<outline text="Definition"/><outline text="Example"/></outline></outline>'
                 '<outline text="Finance"/>')
    second = scan('<outline text="Probability"/><outline text="Finance"><outline text="Black-Scholes">'
                  '<outline text="Definition"/><outline text="Example"/></outline></outline>', first)
    ambiguous = [op for op in second.delta.operations if op.kind == "ambiguous"]
    assert ambiguous and "weak_structural_match" in ambiguous[0].reasons
    assert not [op for op in second.delta.operations if op.kind == "move" and "content_changed" in op.reasons]


def test_r3_children_signature_still_links_an_in_place_title_edit() -> None:
    first = scan('<outline text="Survival analysis"><outline text="Kaplan-Meier"/><outline text="Cox"/></outline>')
    second = scan('<outline text="Survival analysis (competing risks)"><outline text="Kaplan-Meier"/>'
                  '<outline text="Cox"/></outline>', first)
    assert kinds(second) == ["modify"]
