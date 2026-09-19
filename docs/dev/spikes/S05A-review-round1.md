# S05A focused review round 1 — independent evidence review

**Date:** 2026-09-19

**Reviewer:** an independent, read-only agent launched by the Claude Code relay session. It ran the
pinned acceptance run (72 tests, PASS, and the result file was rewritten byte-identically), a
six-seed `PYTHONHASHSEED` determinism check (identical digests), and throwaway adversarial scripts
under `/tmp`, which were deleted afterwards.

## Findings

| # | Severity | Finding |
|---|---|---|
| 1 | BLOCKING | The ledger checked `delta_id` for duplicates before checking the base snapshot. Content-addressed deltas repeat when content goes A→B→A→B, so the second A→B was reported as `duplicate` without moving the head. The source then got stuck (every later delta was stale), and the dependent-fact re-evaluation was swallowed. |
| 2 | BLOCKING | Under `partial` coverage, items that were simply not observed were treated as vanished and used as move sources. A partial Folder scan, a truncated GitHub tree or an OPML branch export could therefore silently move an existing identity onto a copy. |
| 3 | BLOCKING | If a sticky GitHub item was renamed to a path that did not win a fresh budget slot, `remove` was proposed under `complete` coverage. The blob was still present. |
| 4 | NON-BLOCKING | The extension-registry gate was only called from tests. Intake applied unknown-version and unexpected-field locators. |
| 5 | NON-BLOCKING | An OPML child-signature match on a single generic child linked unrelated parents without review. |
| 6 | NON-BLOCKING | `Extension.fields` could be mutated after construction, and intake did not recheck `delta_id`. |
| 7 | NON-BLOCKING | Several gaps: candidates allowed on non-ambiguous ops; several ops per subject in one delta; `bool` accepted as a version; NaN accepted in canonical JSON. |
| 8 | NON-BLOCKING | Ambiguous candidates dropped out of the snapshot, and there was no hold or feedback path. |
| 9 | NON-BLOCKING | Behaviours to disclose: a content swap is two `modify` ops; a vendor-attribute churn re-export makes every node `modify (attributes_changed)`. |
| 10 | NON-BLOCKING | The result doc overclaimed ordered delivery and partial-coverage safety. |
| 11 | — | Code quality meets the repository rules. |

## Remediation (Claude Code relay, same day)

Every remediation starts with a failing test. See the round-2 re-review for acceptance.

- **F1:** the ledger now applies when `base == head` first. It reports `duplicate` only when the
  delta was already applied and `head == new_snapshot`; anything else is stale. An A→B→A→B test was
  added.
- **F2:** under partial coverage, a would-be move becomes `ambiguous` with review. The old item is
  held rather than moved. This applies to keyed reconciliation (Folder, GitHub) and to OPML
  branch-export demotion.
- **F3:** GitHub selection gives priority to fresh paths whose blob matches a vanished sticky item.
- **F4/F6:** `Ledger` gates every operation through the registry. Unknown versions go to review;
  invalid understood locators are rejected. Intake recomputes `delta_id`.
- **F5:** a child-signature match needs at least 2 children.
- **F7:** the new invariants are enforced.
- **F8:** ambiguous candidates are carried forward as `held` snapshot items. They are never
  re-matched or tombstoned until review resolves them. The resolution → manifest loop is a recorded
  deferral.
- **F9/F10:** the result document is corrected.

**Verdict:** **BLOCK**
