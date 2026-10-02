# b10 continuation checkpoint — 2026-10-02

The first priority reached the owner-only boundary; later phases are pending.

| Requested outcome | Verified status |
|---|---|
| Credential cleanup / historical status | Contained; two known historical records remain. Exact targeted preview prepared, not confirmed. |
| Vault health | Doctor passes, commit 61, 110,196 records. |
| Adapter/grants | Three existing Claude/Codex grants load successfully; not revoked yet. Purge will revoke them and a developer grant. |
| Original ten E2E runs | Located and preserved; grading pending. |
| Root causes / guidance changes | Pending grading; no new guidance change. |
| Fresh mini-holdout | Not yet locked or run. |
| Call/retry frequency, concept count/specificity, language behavior | Not newly measured; previously observed h01/h04/h10 failures retained. |
| KI-018 | Concept retrieval evidence preserved; actual Agent product gate still open. |
| Remaining issues | Review 96 non-blocking notes; pre-existing memory-id purge wedge separately tracked. |
| Review verdict | Review 96 APPROVE WITH NON-BLOCKING NOTES, already committed at 7fa5c6d. |
| b10 release | Not released; gate remains closed. |
| Clean backup / old backup | No new clean backup; old 2026-10-01 backup retained and not cleared for deletion. |
| Owner action | Confirm targeted credential-history purge through the CLI; rotate exposed credentials personally. |

Use the exact action shown by the live preview. Previews expire after ten minutes;
if expired, create a new `--credential-history` preview before confirmation.
Never use the public b9 binary for this cleanup, a whole-source purge, or the
known-buggy memory-id purge path.
