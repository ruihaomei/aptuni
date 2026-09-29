# Review 83 — Evidence-derived Profile remediation re-review (ADR-0028, Review 82)

Independent high-risk re-review required by `AGENTS.md`. The slice changes the canonical
`ReviewEvent` contract (schema v3 now also records owner source-authority grants), the Vault
invariant, privacy/deletion lineage, source authority, guided-setup consent and the migration of an
existing Vault. The reviewer did not modify production code, tests, ADRs, STATE/HANDOFF or
`STATUS.json`; this report is the only file written. All probes ran against disposable
`Workspace(tmp/"state")` Vaults in a scratch directory; no real Vault or home state was touched.

## Scope

The complete uncommitted diff (tracked and untracked): `src/aptuni/domain/evidence_profile.py`,
`src/aptuni/policy/evidence_profile.py`, `src/aptuni/domain/invariants.py`,
`src/aptuni/domain/records.py`, `src/aptuni/application/{source_authority,source_commands,
review_commands,obsidian_interface,evaluation,service,activation}.py`,
`src/aptuni/cli/{source_authority_cli,setup_apply,setup_commands,profile_cli,main}.py`, both i18n
catalogs, the five new Evidence-Profile/authority test modules and the appended setup tests, against
ADR-0028 (amended items 4, 5, 7–10), ADR-0001, ADR-0016, ADR-0018, ADR-0020 and ADR-0027. Each
Review 82 reproduction was re-run, and the new attack surface (authority grants, `effective_source`,
index-backed `superseded_by`, purge/removal interactions, legacy setup plans) was probed
adversarially.

## Checks run

| Check | Result |
|---|---|
| Full `pytest` suite | 1040 passed, 3 skipped (includes both 25k scale tests) |
| `ruff check .` | All checks passed |
| `mypy src` (strict) | Success: no issues in 111 source files |
| `python3.13 tools/check_relay.py` | relay check passed |
| `git diff --check` | clean |
| B1 repro: owner edit, then two source generations | no auto Fact recreated for either generation; the edit stays current |
| B1 repro: owner reject, then one and two generations; `profile refresh`; no-op sync | never recreated; `accept` after reject → `profile_action_unsupported`, state stays `revoked` |
| B1 repro: source correction lineage | successor `supersedes == (predecessor,)`, `change_kind` mirrors Evidence (`world_change`), `superseded_by(old) == new` |
| B1 extra: note retracted then re-added in MarginNote after owner reject | re-added Evidence supersedes the retraction; rejected claim not recreated; `doctor` ok |
| B1 extra: owner `retract` of the derived Fact, then source change | not recreated (user-declared successor counts as an owner decision) |
| B2 repro: forged duplicate, exposure-only, `valid_from`/`valid_until`/`confidence`, digest | rejected by both `RecordSet.validate()` and `validate(only=…)` |
| B2 extra: `change_kind`, statement, trust, review status, retention purpose, predicate, `observed_at`, subject, extra Evidence link, event nonce/epoch/`recorded_at`/schema v2, second promotion event | every variant rejected both ways |
| B3 repro: cross-version pending plan (no `primary_for`) | applied exposure-only; consent line absent; tampered `primary_for` → `setup_action_invalid` |
| B4 repro: released empty-authority Vault | preview writes nothing; `APPLY` grants, re-derives 5 Evidence as corrections and forms 5 Facts; stale digest refused; cancel leaves source reference-only; `doctor` ok |
| Grant forgeries (full and incremental) | duplicate grant, dimension already present, folder source, grant after removal: rejected; wrong actor/decision/schema: rejected at model parse |
| Grant → removal → purge | Facts non-current/non-exposable after removal; `refresh` writes nothing; purge removes grant, Evidence and Facts; `doctor` ok |
| Forged Fact from forged `studied` Evidence of an exposure-only source | Fact rejected ("exceeds its source authority") |
| **Purge of one Evidence-derived Fact (Evidence kept), then sync / `profile refresh`** | **every later sync of that source and every `profile refresh` fails `invariant_violation: purged ids cannot be committed again`** (B1 below) |
| B5 repro (authoritative MarginNote, this machine) | promoting sync 2k=0.37 s, 4k=0.76 s, 8k=1.60 s, 27k=6.20 s; no-op sync 27k=3.60 s; `doctor` 27k=2.74 s; `refresh` 27k=0.31 s; grant 27k=4.65 s (post-grant `doctor` 3.99 s) — linear |

## Blocking findings

### B1 — Purging an Evidence-derived Fact permanently breaks sync of its source and every `profile refresh`

**Anchors:** `src/aptuni/domain/evidence_profile.py:43-48` (deterministic Fact/event ids);
`src/aptuni/policy/evidence_profile.py:58-61` (only an *existing* record suppresses re-derivation);
`src/aptuni/application/source_commands.py:340-359` (every sync, including the duplicate/no-op path
at 305-317, re-derives over *all* current Evidence of the source);
`src/aptuni/application/review_commands.py:178-181` (`refresh_profile` re-derives over all sources);
`src/aptuni/application/privacy.py:154-175` (purging a Fact does not pull in its Evidence);
`src/aptuni/vault/store.py:325-327` (commit refuses ids in the deletion ledger).

Privacy purge accepts an exact Fact id. Purging an Evidence-derived Fact removes the Fact, its
promotion event and its supersession chain (plus an owner correction, if any), but its supporting
Evidence stays current, as the purge-scope rules intend. Because every sync now reconsiders all
current Evidence and the Fact/event ids are deterministic, the next sync derives the same
`fct_…`/`rev_…` ids again. `Vault.commit` refuses them because their digests are in the deletion
ledger. The refused commit also contains the source delta, so the source is frozen. No later change
can be ingested, and the pending replay journal is left behind. `profile refresh` fails the same way
for the whole Vault, which also blocks pinned-Memory promotion. The only way out that does not remove
the source is the undocumented workaround of disabling auto-promotion. Re-enabling it fails again.
Had the ids not been ledgered, the same code would silently recreate a claim the owner had just
purged, which is also a privacy/owner-decision failure. Memory-derived Facts use `new_id` and do not
share this failure; the defect is specific to the new ADR-0028 path. Review 82 N1 asked for exactly
this purge regression. The BACKLOG entry says purge is "covered", but the only test purges the whole
source (`tests/integration/test_source_authority.py`, the final purge test).

Reproduction (MarginNote fixture, `primary_for=("knowledge.studied",)`):

```python
f = next(f for f in service.facts() if f.subject == "Ensemble methods › Random forest › Bagging")
p = service.privacy_purge_preview((f.id,))          # scope: the fct_ + its rev_ only
service.confirm_privacy_purge(p.action_id, p.digest) # doctor ok
service.sync(source_id)       # AptuniError invariant_violation: purged ids cannot be committed again
service.refresh_profile()     # same
# change another card and sync: same failure; Evidence count unchanged; *.pending.json left behind
# purging the owner's edit of that Fact instead (scope: both facts + event) fails identically
```

**Required fix:** make a purged derivation a permanent owner withdrawal for that Evidence lineage.
For example, the writer can skip any candidate whose deterministic Fact or event id, or any id in its
lineage, is in the Vault's deletion ledger (the ledger is canonical and travels with the Vault). The
alternative is to define and render that purging such a Fact also purges its supporting Evidence.
Either way, a purge must never make a later sync or refresh fail or recreate the claim. Add
regressions for Fact-only purge followed by no-op sync, changed sync and `profile refresh`, purge of
an owner edit, and purge in the middle of a successor chain.

## Non-blocking notes

1. **Owner decisions and review policy are writer-only, not invariant-enforced.** A forged successor
   Fact for Evidence whose lineage the owner rejected passes both full and incremental validation.
   Likewise, a Fact written while auto-promotion is disabled or the module is sensitive would still
   validate. ADR-0028 item 9 does not list these, and the writers enforce them, so this does not
   block. Encoding "no owner withdrawal earlier in the lineage than this Fact" would close the class.
2. **Grant ordering uses `recorded_at`, not commit order.** A grant appended after a removal but
   backdated before it validates (`invariants.py:283-296`); a Fact is also not required to postdate
   the grant that authorizes it. There is no practical effect: removed sources expose nothing. It is
   still a gap in the canonical check.
3. **Evidence signals are not bound to source authority.** Forged Evidence carrying `studied` from an
   exposure-only source validates (pre-existing). The Fact derived from it is correctly rejected, but
   such Evidence is now retrievable through `aptuni.profile` as cold-start material.
4. **`setup_source_authority_differs` message is not always accurate** (`setup_apply.py:196-201`). It
   always recommends `source authorize … --grant knowledge.studied`. That advice is wrong for an
   already-granted source met by a legacy plan, and for Obsidian/GitHub sources that were approved
   through the CLI with `--primary-for`: those previously matched as `already_present`, and
   `authorize` refuses them. The failure is closed and safe, but the owner is sent the wrong way.
5. **A legacy pending plan is applied exposure-only without saying so afterwards.** Keeping the
   confirmed meaning is an acceptable reading of the B3 requirement (nothing gains authority without
   consent). The apply report should still point to `source authorize`, so the owner is not
   surprised when no Profile forms.
6. **Grant copy overstates the effect under some policies.** `source.authorize.effect` promises
   Profile facts "right away" even when auto-promotion is off, the module is not exposed, or it is
   sensitive. In those cases the grant writes corrections but no Facts.
7. **Removing and re-approving the same store starts a new lineage.** Earlier owner rejections and
   edits no longer suppress re-derivation. This is consistent with ADR-0027's "approve it again",
   but it is worth one line in the owner-facing removal copy.

## Verified sound

- Review 82 B1: the predecessor is resolved from the pre-delta snapshot plus an indexed Evidence
  ancestry walk. Successors supersede exactly and mirror the change kind. Owner reject, edit and
  `retract` anywhere in the lineage suppress every later generation, `profile refresh` and no-op
  sync, including retraction→re-add cycles. `accept` is refused with `profile_action_unsupported`
  before any state change, and neither the CLI nor Obsidian offers it for this type.
- Review 82 B2: `check_evidence_profile_fact` is shared by incremental and full validation and pins
  the strongest-signal allow-list against effective authority, the deterministic ids, the event
  digest/nonce/epoch/`recorded_at`, exact time/confidence/statement/provenance/retention, and exact
  supersession. Existing "superseded more than once" and supersession-cycle checks prevent forks.
- Review 82 B3: the setup target carries exactly `["knowledge.studied"]` or no key. Any other value
  fails plan loading. The consent line is rendered in English and Chinese, and the displayed target
  hides the key. Existing sources with a different authority are never silently upgraded.
- Review 82 B4: `aptuni source authorize` is digest-bound to source, dimension and exact current
  Evidence ids, requires a typed `APPLY`, and writes the grant, re-derived Evidence and Facts in one
  commit under the source-operation lock and purge guard. Grants are schema-v3-only at parse time
  and validated globally (actor/decision/source type/present dimension/duplicate/after removal).
  `effective_source` is used only for sync input, listing and setup matching. No path commits it:
  every `SourceConfig` construction is a fresh `add_*_source`.
- Review 82 B5: indexes are built once per snapshot, and the batch validates and commits once.
  Measured growth is linear from 2k to 27k and matches the implementer's figures.
- Retraction and removal hide derived Facts from `current_facts` and `exposable`. The expose switch
  hides them from hosts. A whole-source purge removes grant events and entire chains, and `doctor`
  stays healthy.
- `superseded_by` now reads the cached lineage index. `RecordSet` is never mutated after
  construction, so the result matches the old linear scan under the single-successor invariant.
- ReviewEvent v3 stays a clean fail-closed signal to the released build (`SUPPORTED_SCHEMA_VERSIONS`
  was `(1, 2)` there). `owner_review_decisions` no longer counts grants or removals.

The remediation resolves all five Review 82 blockers. One new correctness and deletion failure
remains, introduced by combining deterministic derivation ids with "every sync reconsiders all
current Evidence": an ordinary Fact-level privacy purge bricks the source and `profile refresh`.

**Verdict:** **BLOCK**
