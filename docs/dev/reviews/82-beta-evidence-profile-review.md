# Review 82 — Evidence-derived cold-start Profile (ADR-0028)

Independent high-risk review required by `AGENTS.md` because this slice changes the canonical
`ReviewEvent` contract, source authority, Profile disclosure and deletion lineage. The reviewer did
not modify production code, tests, ADRs, state/handoff files or `STATUS.json`; this report is the
only file written.

## Scope

Reviewed the complete uncommitted diff and the relevant contracts in ADR-0001, ADR-0006,
ADR-0018, ADR-0020, ADR-0025, ADR-0027 and ADR-0028. The review traced source sync and crash replay,
canonical incremental/full validation, authority/module gates, correction/removal/purge, owner
reject/edit semantics, setup consent and migration, Profile host disclosure, projection/export
consumers, and the approximately 27k-Evidence User #1 scale.

## Checks run

| Check | Result |
|---|---|
| Focused pytest: Evidence Profile, activation, setup, source removal, privacy purge and schema tests | 122 passed |
| `git diff --check` | clean |
| Owner edit followed by two source changes | reproduced: first change respected the edit; second created a new auto-derived Fact alongside the owner correction |
| Owner reject followed by source change | reproduced: the rejected claim was immediately recreated under a new deterministic Evidence/Fact id |
| Source correction lineage probe | reproduced: replacement Fact had `change_kind="assert"`, `supersedes=()`, and no reverse link from the old Fact |
| Evidence-Fact invariant adversarial probe | a second Fact/event for the same Evidence, with arbitrary ids, `valid_from="1999"` and `confidence=1.0`, passed full `RecordSet.validate()` |
| Exposure-only invariant adversarial probe | a `profile.evidence_signal` Fact with predicate `exposure` and matching `knowledge.exposure` authority passed full validation |
| Evidence Profile `accept` after reject | API returned `accepted` while the canonical derived state remained `revoked` |
| Synthetic authoritative MarginNote scale | 250=0.090s, 500=0.246s, 1,000=0.796s, 2,000=2.988s, 4,000=11.711s; doubling 2k→4k took 3.9x |

The focused green suite proves the intended happy paths, but the adversarial probes expose contract
failures not represented by those tests.

## Blocking findings

### B1 — Owner rejection/edit is not durable across the Evidence lineage, and source corrections do not create successor Facts

**Anchors:** `src/aptuni/policy/evidence_profile.py:34-62,90-110`;
`src/aptuni/application/source_commands.py:340-371`;
`src/aptuni/application/review_commands.py:215-250`;
`tests/integration/test_evidence_profile.py:88-107,110-162`.

`_evidence_profile_batch` adds the new Evidence to `visible` before calling
`evidence_profile_records`. `_previous_fact()` then asks that already-updated view for
`current_facts()`. The old Fact has lost its current supporting Evidence at that point, so it cannot
be found and the replacement is written as a fresh assertion rather than as its successor. This
contradicts ADR-0028 item 4 and loses the explicit Fact history promised by ADR-0001.

The same one-hop lookup makes the owner boundary unsafe. `_has_owner_override()` considers only a
Fact directly linked to the immediately superseded Evidence. An edit suppresses the first source
update, but because that update creates no derived Fact, the next Evidence generation has no Fact
for the lookup to find and auto-promotion resumes. A reject is not checked at all, so the very first
source update recreates the rejected claim. Reproduction over the MarginNote fixture:

- edit `Bagging` to the owner's wording;
- update source to `Bootstrap aggregation`: no replacement for that topic (expected);
- update source again to `Resampled aggregation`: a new accepted `profile.evidence_signal` appears
  alongside the owner's corrected Fact (incorrect);
- separately, reject `Bagging`, update it once, and a new accepted Fact appears immediately.

There is also a contradictory public result at `review_commands.py:222-223`: `accept` on any
Evidence-derived Fact returns `accepted` before current/revoked checks. After rejection, the method
reports `accepted` while `profile_review_state()` still reports `revoked`. The CLI continues to
publish an `accept` subcommand even though ADR-0028 says the owner actions are reject/edit, not a
second approval.

**Required fix:** resolve the prior Fact from the pre-delta view (or an indexed full Evidence
supersession lineage), write every source correction as a successor Fact, and carry owner
correction/rejection across all later descendants of the same source subject. Treat historical
rejection as a permanent no-recreate decision for that Evidence lineage unless the owner explicitly
reverses it. Reject `accept` as unsupported for this Fact type instead of returning a fictitious
state. Add two-or-more-generation edit and reject regressions, an exact `supersedes` assertion, and
an accept-after-reject case.

### B2 — Canonical validation does not enforce the ADR-0028 admission contract

**Anchors:** `src/aptuni/domain/invariants.py:194-237`;
`src/aptuni/policy/evidence_profile.py:13-31,90-122`;
`tests/integration/test_evidence_profile.py:179-187`.

The writer is narrow, but the Vault invariant is the security/correctness boundary. It currently
checks the rendered statement, authority membership and selected support, but it does not enforce:

- predicate membership in exactly `studied|applied|demonstrated` (an exposure-only Fact validates);
- one derived Fact per Evidence and the deterministic Fact/event ids (a forged duplicate validates);
- exact `valid_from`, `valid_until`, `confidence`, `change_kind` and `supersedes` lineage;
- the deterministic event digest/nonce relationship to Evidence, source, epoch and signal.

The adversarial duplicate changed both temporal meaning and confidence and still passed full
validation. The exposure-only probe violates ADR-0028's central unsupported-claim rule and also
passed. This repeats the class of canonical defect that Review 59 required fixing before ADR-0020
was accepted: a correct writer is insufficient when a malformed or future writer can commit a
different canonical claim.

**Required fix:** make the invariant derive and compare the complete allowed transition. Enforce the
strong-signal allow-list, deterministic ids and event digest, exact temporal/confidence/retention
fields, correct assert-versus-correction supersession, and uniqueness for an Evidence lineage.
Exercise both incremental commit validation and full `doctor` validation with forged duplicates,
exposure, changed time/confidence, invalid correction links and event mismatches.

### B3 — Guided setup silently adds Profile authority that is neither consent-rendered nor digest-bound

**Anchors:** `src/aptuni/cli/setup_commands.py:307-316,336-350,577-591`;
`src/aptuni/cli/setup_apply.py:195-205`;
`src/aptuni/i18n/messages/en.toml:179-184` and corresponding Chinese strings.

The confirmed setup step freezes only MarginNote store/notebook selection. Its rendered English and
Chinese text says the source is read-only, is read into `knowledge`, and the sync records minimized
Evidence. Apply now hard-codes `primary_for=("knowledge.studied",)`, which additionally authorizes
algorithmic creation and immediate exposure of canonical Profile Facts. That material policy is
absent from the plan target and from the owner-facing confirmation.

This is not only a wording gap: a pending setup plan created by an earlier build has the same
`source_marginnote` kind and target, so applying it with this build changes its confirmed semantics
without changing the digest-bound step. The catalog-digest check does not bind this new hard-coded
authority. That violates the exact-confirmation boundary for a privacy/canonical-growth change.

**Required fix:** put the exact authority dimensions into the immutable setup plan/action digest,
render that MarginNote membership will be treated as authoritative evidence of what was studied and
will automatically add topics to Profile, and reject/re-plan older pending actions whose semantics
did not include that field. Add English/Chinese preview, tamper and cross-version pending-plan
tests.

### B4 — The existing Vault that motivated ADR-0028 has no supported authority migration/backfill path

**Anchors:** `src/aptuni/cli/setup_apply.py:167-180,195-235`;
`src/aptuni/application/review_commands.py:168-199`;
`src/aptuni/application/marginnote_ingest.py:54-61`;
`tests/integration/test_setup_apply.py:785-789` and
`tests/integration/test_evidence_profile.py:61-85`.

An existing MarginNote source with the same roots/module/role is treated as `already_present`
because `_source_matches()` omits `authority.primary_for`, despite `planned_sources()` claiming to
match the "full policy". Its historical Evidence remains `exposure`, and `profile refresh` correctly
refuses to turn that into a Fact. Therefore the real older Vault with empty source authority cannot
receive Evidence-derived Profile Facts from this implementation; only a newly configured source or
one that already had strong authority can. The added setup test covers only fresh creation, and the
backfill tests create an authoritative source before initial sync, so neither exercises the reported
User #1 state.

Profile activation can now retrieve exposure Evidence, which is a useful immediate fallback, but it
is not the automatic canonical Profile formation this slice claims to restore.

**Required fix:** provide an explicit, owner-confirmed source-authority upgrade/re-approval flow for
existing configs, with no silent mutation. It must emit/resync strong Evidence under the new policy,
preserve old lineage, be idempotent, and leave a declined source exposure-only. `_source_matches`
and `planned_sources` must include exact authority. Add a fixture that starts with the released
empty-authority config and existing exposure Evidence, then exercises consent, migration, resync,
backfill and cancellation.

### B5 — The promotion path is quadratic and does not meet the known ~27k-Evidence target

**Anchors:** `src/aptuni/application/source_commands.py:339-371`;
`src/aptuni/policy/evidence_profile.py:34-61,90-93`;
`src/aptuni/application/review_commands.py:178-196`.

For every Evidence item, `_evidence_profile_batch` copies the growing record list and reconstructs a
`RecordSet`; the policy then scans records for owner overrides, calls `current_facts()` (another
whole-view scan), and rebuilds `ids()`. `refresh_profile` repeats the same growing-view pattern.
Measured authoritative sync time scaled from 2.988s at 2,000 items to 11.711s at 4,000 items, almost
exactly the 4x signature of O(N²). A simple quadratic extrapolation to 26,932 Evidence is roughly
nine minutes before allowing for the larger real record history; the exact real time need not be
claimed to conclude that the known User #1 scale is not served by this hot path.

**Required fix:** precompute Evidence ancestry, Fact-by-Evidence, owner-decision, existing-id and
current-support indexes once; derive the batch in one pass; construct/validate the combined
`RecordSet` once at commit. Add a 25k-scale regression with a stated wall-time/memory envelope and
cover both initial sync and no-op-sync/`profile refresh` backfill.

## Non-blocking notes

### N1 — ADR-0028's required failure-path verification is not yet represented

The new tests do not exercise privacy purge of an Evidence-derived Fact or its source, projection
delete/rebuild, Profile export after support withdrawal, module ingest/expose changes, crash replay
of the combined Evidence/event/Fact commit, or evidence-scope denial on `aptuni.profile`. Existing
generic machinery appears structurally sound: the source delta and promotion share one Vault
commit; purge dependency expansion follows `evidence_ids`; source removal/current views suppress a
Fact whose support is no longer current; and host retrieval requires both `context.read` and
`evidence.read`. Add type-specific regressions so later changes cannot break those properties.

### N2 — Profile activation is now all-or-nothing for older restricted grants

`src/aptuni/application/activation.py:99-103` always requests Evidence for `aptuni.profile`, and
`src/aptuni/application/service.py:511-520` therefore requires `evidence.read`. Official adapters
already grant that scope, so there is no current official-host leak. A custom/older grant that had
only `context.read` can no longer retrieve even Facts through Profile, however. Document this
compatibility change and pin the fail-closed result in a test; alternatively, deliberately define a
Facts-only fallback when Evidence scope is absent.

## Verified sound

- Source Evidence is not converted into interaction Memory.
- The writer requires exact source authority, current module ingest/expose switches, automatic
  promotion enabled, and a non-sensitive module.
- `aptuni.profile` remains explicit/task-scoped and Evidence disclosure passes the separate host
  scope check.
- Retraction/source removal hides derived Facts from current and exposable views, and the focused
  removal test leaves `doctor` healthy.
- ReviewEvent v3 gives older readers a clean fail-closed schema-version signal.
- The sync commit itself is atomic; the pending replay journal tracks Evidence ids, which is
  sufficient only because Evidence and its event/Fact are in the same Vault segment commit.

The product direction is consistent with the maintainer's request: approved strong Evidence should
form Profile automatically, while Memory remains interaction-derived and the user rejects or edits
retrospectively. The current implementation does not yet preserve those decisions, enforce the
canonical transition, migrate the motivating Vault, or run at its stated scale.

**Verdict:** **BLOCK**
