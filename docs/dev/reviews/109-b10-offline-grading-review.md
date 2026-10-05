# Review 109 — selection mini offline grading data path

2026-10-05. Independent stateless GPT-6 Astra xhigh static review through the same configured CLI; actual private tasks/answers/Source packets were not supplied. Configured MCP/providers disabled, read-only. No complete host-inventory proof.

Two concrete contract defects remain: incomplete freeze verification between phases and incomplete rejection of observed tool events.

- B1 — Frozen artifact bindings are not enforced before support forwarding. extract_cases.py:evidence() compares the initial assessment’s capsule hash with the map’s stored hash, but never hashes the current answer capsule. run_judge.py then forwards that capsule and records its newly computed hash. Changing final_answer after the initial lock therefore passes these checks. The stored mapping_sha256 is also never verified, allowing record-to-answer remapping without detection. Verify the frozen mapping and actual capsule digests before forwarding; support must remain bound to the originally assessed answer and its corresponding returned context.
- B2 — run_judge.py inspects only item.completed events for tools. Tool items observed in item.started or item.updated are ignored. A stream containing such an item, a valid final response and exit status zero can consequently lock assessments. Reject observed tool items across all item-bearing event phases before accepting the grading result.

No offline grading calls occurred before this verdict. Five invented regressions fail before repair; all17 checks pass after mapping/current-capsule verification and observation of every item-bearing event phase. Original review input/code receipts remain private. Review110 must approve the repaired path before forwarding.

Reviewer usage (research overhead, not runtime/judge): {"input_tokens": 39635, "cached_input_tokens": 0, "cache_write_input_tokens": 0, "output_tokens": 9169, "reasoning_output_tokens": 8476}. Input SHA256 5b771206c688dba54e29a9071df2a45a15d3ef25dfdddd64777029b5c5b1aa18.

**Verdict:** **BLOCK**
