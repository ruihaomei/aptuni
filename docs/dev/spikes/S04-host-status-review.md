# S04 focused independent review — host status and APFS path identity

**Date:** 2026-09-19

**Verdict:** BLOCK ADR-0013 acceptance and S04 PASS pending real-host/native closure.

## Findings

1. The original ADR overclaimed that realpath/inode comparison detects APFS clones. Clones have
   distinct inodes. macOS exposes full-clone mapping signals only through native filesystem APIs;
   those signals do not prove arbitrary historical, partial or diverged clone ancestry and require
   an enumerated scan of candidate writable roots.
2. The original comparator treated a missing settings mapping as positive `profile_missing`
   evidence. If the mapping was absent because discovery was incomplete or unreadable, that would
   incorrectly produce confinement `not_in_effect` rather than `unverified`.
3. The evidence-only status domain, fixed reason codes, session isolation, ignored untrusted
   metadata, and symlink/hardlink identity checks were conservative and did not overclaim safety.
4. `evaluate_profile` remains only a deterministic comparator. S04 still needs to prove complete
   discovery and precedence-correct merging for each real host. `HostEvidenceStore` similarly does
   not authenticate its evidence source; the real adapter must do so.
5. The first remediation briefly let `profile: unverified` return before considering a successful
   unsafe canary. Re-review caught the precedence error: profile remains `unverified`, while any
   positive unsafe evidence now forces confinement `not_in_effect` and preserves both fixed reasons.

## Remediation applied in this checkpoint

- ADR-0013 now distinguishes same-object aliases from copies/clones and permits only positive,
  validated native full-clone evidence. Missing capability or incomplete scans remain `unverified`.
- Profile status now includes `unverified`. Only a complete core-observed snapshot may yield
  `installed`, `missing` or `drifted`; incomplete or ambiguous snapshots return the fixed reason
  `effective_settings_unobservable`.
- Positive unsafe evidence is evaluated before absence-of-proof branches, including when profile
  discovery is incomplete; a dedicated regression test locks this invariant.
- Local regression coverage for both cases passes. The verdict remains BLOCK because native clone
  mapping, complete effective-settings discovery, and the required Claude/host journeys are not yet
  implemented or independently re-reviewed.

## References used by the review

- [`getattrlist(2)` clone attributes](https://manp.gs/mac/2/getattrlist)
- [`clonefile(2)`](https://manp.gs/mac/2/clonefile)
- [Apple Foundation `mayShareFileContent`](https://developer.apple.com/documentation/foundation/urlresourcevalues/maysharefilecontent)
