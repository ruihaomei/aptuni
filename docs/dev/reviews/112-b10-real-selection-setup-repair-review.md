# Review 112 — real selection setup repair

2026-10-06. Independent read-only review of the narrow post-freeze evaluation-integrity repair. The first frozen run completed s01 A; s01 B performed no task because the B policy's unqualified activation prohibition blocked the explicit Full setup. The reviewer inspected the runner's policy guard, its new regression, and the revised B policy. No Vault content, task answer, grant material, or private source packet was supplied.

The regression failed before repair and all 11 runner checks pass after repair. The runner now rejects the known contradictory policy wording before host execution. The B policy explicitly permits the separate owner-requested Full setup and preserves the grant boundary. A zero-task model preflight with this policy observed Full activation. The text check is a guard for this known conflict, not general proof of natural-language policy compatibility.

The reviewer required that s01 A remain diagnostic and s01 B remain a pre-task operational abort. The original comparison is closed and cannot be paired with a repaired B result. A fresh rubric, task set, policy and runner hashes, snapshot/grant lock, and four new sessions must be frozen before resumed scoring. This review approves the repair and fresh evaluation procedure, not production adoption or b10 release.

**Verdict:** **APPROVE**
