# Grounded selection notes

## Recovered checkpoint
- `main` at `0adb0f2`, ahead of remote by 31. Unrelated modified dogfooding inbox and untracked user files are preserved.
- Live Vault and retrieval index are both at sequence 66, policy epoch 1. The existing Codex grant is `grant-c449a729973f45c6`, modules goals/identity/knowledge/preferences/projects/skills and scopes context/evidence/identity/memory-review read. Activation is process-local and defaults OFF; earlier research sessions enabled Full explicitly. No new grant or activation was made in recovery.
- Prior fresh two-task results: ordinary strict 0/2, bounded 1/2; accepted pair 1/2 each; all comparisons complete. Raw task traces were cleaned, so old answers cannot be re-parsed.
- Baseline focused synthetic research check: `tests/dev/test_selection_mvp_mock.py` passed.

## H1 structural finding
- Canonical GitHub Evidence locator already has repository ID, owner/name, and path; host Context item exposes `source_id`, `canonical_id`, text, and trust but omits locator fields.
- The bounded roster groups all GitHub file/concept Evidence by repository ID, then returns a bare anchor/label; its Evidence fetch returns ordinary Context items with no candidate-entity relationship.
- A file/tool runner in a repository can therefore be mistaken for an independent project if the Agent treats an artifact as a candidate. `source_id` can show shared source, but different projects may also share a repository; it cannot alone define project eligibility.
- First test: explicit task-relevant entity eligibility and ranking rule in research policy, with no ontology, metadata, or source filter.

## H2 structural finding
- `record_unit()` retains canonical Evidence IDs in host payload. The earlier ordinary arm received useful Evidence but its final answers omitted the IDs. The old raw traces are gone, so an exact internal point of loss cannot be proven. The observable loss is between returned tool items and final answer generation.
- First test: a compact per-candidate support ledger in the Agent policy, without changing retrieval or adding a reviewer.

## Separate development replays (not validation)
- H1 on the previous s03 bounded path: a generic instruction to treat files/tests/runners/reports as evidence about a containing project selected two documented project-level candidates, completed the comparison, and cited 4/4 returned IDs. Two retrieval calls, 94,338 task tokens, 98.506 s setup plus task. Original s03 bounded run was two calls, 91,543 tokens, 243.264 s; run-to-run latency difference is not a causal saving.
- H2 on the previous s03 ordinary path: a compact per-candidate source/ID/claim support ledger yielded two project references and 2/2 cited IDs were returned. One retrieval call, 58,486 task tokens, 111.535 s setup plus task. Original s03 ordinary run was two calls, 81,794 tokens, 104.615 s; the changed call pattern and run variance prevent a causal cost claim.
- Both are single dev replays on known failures. They justify testing a combined lightweight instruction, not product promotion.

## Fresh freeze
- Live grant/sequence audit rechecked five previously identified documented candidate groups: 18 current, exposed, non-credential Evidence records across four source IDs; no role or outcome claim admitted. The authorized knowledge corpus includes GitHub, folder, Notion, and MarginNote Evidence, but only the GitHub groups had sufficient audited project-level support for these goals. No cross-category task was forced.
- Three new task wordings cover a research-software application, a local learning workshop, and a maintainability handoff. Exact tasks, candidate pools/pairs, rubric, grant, sequence 66, policy, two-arm order and asset hashes are frozen in owner-only `/private/tmp/aptuni-b10-grounded-selection/holdout/` before execution. Manifest SHA-256: `e5c920f36c45bdb4faf1c18d04b55484c7770921dbbdc04fea66ce6ee0844db0`.
- Both arms use the same ordinary production research seam; C adds only the combined candidate-eligibility and Evidence-carry-through instruction. No roster retrieval.

## Fresh result and decision
- Six sessions completed once without operational or authorization failure. Strict A0/3, C1/3; eligible pairs A2/3, C1/3. Minimum audited candidate Evidence recall0/9 in both arms, but supported alternatives outside the minimum were returned.
- Primary R1=3, R2=0, R3=2, R4=0; one pass. A's two eligible-pair answers omitted IDs; C's one eligible-pair answer retained returned IDs. This is conditional support for H2, not general reliability. H1 had no fresh R2 errors to resolve.
- A: five retrieval calls, 283,341 task tokens, 362.332 s journey. C: five calls, 255,748 tokens, 349.773 s. No causal cost saving claim from three paired model tasks.
- Final decision: no policy promotion, no b10 release. Immediate observed bottleneck is getting a second eligible candidate into bounded packets (R1), within the larger evidence-attached two-candidate release blocker.
