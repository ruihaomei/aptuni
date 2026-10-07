# Grounded selection task plan

## Goal
Determine the smallest evidence-grounded two-candidate selection improvement inside the current strong-single architecture, validate it on a new frozen real-context mini-holdout if justified, and decide the b10 gate.

## Phases
- [x] Recover state, contracts, diagnostic traces, grant and activation state; run baseline.
- [x] Diagnose candidate eligibility and Evidence carry-through separately on existing dev cases.
- [x] Choose the smallest intervention and measure dev-case cost and behavior.
- [x] Freeze and execute a fresh authorized real-context three-task mini-holdout.
- [ ] Verify final records, update state and handoff, decide b10, commit local checkpoint.

## Constraints
- One strong Agent; no new runtime roles, ontology, storage migration, or retrieve product surface.
- No grant expansion or OFF-to-Full automation.
- Existing failed tasks are development evidence only.
- Preserve unrelated workspace edits and private corpus content.

## Status
Three-task paired holdout, masked grading, source support audit and scoped checks are complete. b10 remains frozen; final self-review and local checkpoint are underway.

## Errors Encountered
- The first combined research policy draft matched the runner's explicit-Full setup conflict guard. Reworded it to respect the existing activation boundary and regenerated the private freeze before any holdout task ran.
- The first index-only inbox patch had an incorrect hunk count and was rejected without staging anything. Corrected the count; staged only the new content-free observation, leaving the owner's preexisting inbox edit unstaged.
