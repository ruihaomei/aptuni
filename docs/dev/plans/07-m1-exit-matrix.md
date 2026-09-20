# Milestone 1 Exit Matrix — audit and slice order

**Status:** Accepted 2026-09-20 (supersedes nothing; ordering input for Slices 14–18)
**Decision basis:** `ROADMAP.md` M1.1–M1.5 exit clauses, `EVALUATION_PLAN.md`, KI-014/KI-018/KI-019,
and the repository state at `db7a5d9`.

Every binary exit clause below is resolved to one of three dispositions: **MET** (named evidence
exists today), **SLICE n** (one bounded implementation slice owns it), or **RELEASE** (a public
release checklist item that is not an engineering blocker). No clause is left unassigned.

## M1.1 Foundation

| Exit clause | Disposition | Evidence or owner |
|---|---|---|
| Golden records/temporal and memory transitions round-trip | MET | `tests/unit/test_records.py`, `tests/integration/test_memory_lifecycle.py` |
| Concurrent writers have one valid serial outcome | MET | S01 (46 tests) + `tests/integration/test_concurrency.py` |
| Migration/backup restore failure matrix passes | **SLICE 14** | `Vault.restore_from` and the 10 restore/migration tests in `tests/integration/test_vault.py` cover the *internal* matrix. No product surface creates or restores a backup, so the owner-facing half of this clause is unmet. |
| Projection deletion cannot alter the Vault | MET | `tests/integration/test_retrieval.py` index delete/rebuild cases |
| Policy contract/mandatory port matrix passes | MET | `tests/unit/sources/test_contract.py`, `tests/unit/test_invariants.py` |
| Wheel/sdist clean-install CI passes | **SLICE 15** | Clean-wheel smokes are real but hand-run and unrecorded; `.github/` holds only `CODEOWNERS`. |
| SBOM/license/vulnerability/secret checks "from the first scaffold" | **SLICE 15** | `THIRD_PARTY_NOTICES.md` is maintained by hand; no SBOM artifact and no automated check exist. |
| Linux claimed only after S01 passes on Ubuntu LTS/ext4 | **SLICE 15** | The runner is the blocker. Until Slice 15 records it, Linux stays documented unsupported. |

## M1.2 Ingestion

| Exit clause | Disposition | Evidence or owner |
|---|---|---|
| Idempotent and incremental fixture suites | MET | Folder, GitHub and MarginNote sync suites; live GitHub and 82,997-note MarginNote dogfood |
| No source disappearance silently deletes facts | MET | `tests/integration/test_folder_sync.py` removal/ambiguity cases; `aptuni review` holds ambiguous identity |

## M1.3 Builtin memory and retrieval

| Exit clause | Disposition | Evidence or owner |
|---|---|---|
| Temporal, permission, bilingual relevance and rebuild tests pass | MET | `test_retrieval.py`, `test_context.py`, `test_invariants.py`, S03 frozen evidence |
| Measured context budget | MET | `tests/unit/application/test_context_budget.py`; every response reports used/remaining units |
| Versioned evaluation corpus/metrics/thresholds accepted **before** scored work | **SLICE 16** | `EVALUATION_PLAN.md` is still `Proposed`. `tests/fixtures/eval/` holds one example file that no code reads. There is no harness, no checksummed corpus and no recorded baseline, so no threshold in that plan has ever been measured. |
| Privacy inventory/status with exact unlink/forget/purge/uninstall effects | MET | Slice 12; Review 32 APPROVE with non-blocking notes |

## M1.4 Agent and human interfaces

| Exit clause | Disposition | Evidence or owner |
|---|---|---|
| CLI for init/config/sync/status/query/observe/review/export/doctor | MET | 24 commands; `aptuni --help` |
| MCP STDIO tools over application services | MET | Slice 5; `tests/integration/test_mcp.py` |
| Claude Code and Codex adapters, bounded L0 card, Starter Lite and Researcher recipes | MET | Slice 6, Slice 8 |
| Guided setup + basic Plugin Advisor, one final confirmation, install, doctor/smoke, Vault location | MET | Slice 13 at `db7a5d9`; Review 34 APPROVE |
| English and Simplified Chinese setup/help/errors | MET | catalog parity tests; every slice renders in both locales |
| MCP confirmation/replay/injection tests pass | MET | `test_mcp.py`, `test_memory_lifecycle.py` nonce/digest/idempotency cases |
| Fresh-machine scripted setup and a real daily task in both hosts | **SLICE 17** | Bundles are generated and grant-bound, but no recorded run installs them into a real host and completes a task there. |
| S12 and the ADR-0013 real-host probes deferred from S04 pass per adapter version | **SLICE 17** | KI-014 assigns these here. They need real host installations, so Slice 17 is maintainer-gated, not code-gated. |

## M1.5 Release quality

| Exit clause | Disposition | Evidence or owner |
|---|---|---|
| Unit/contract/integration/E2E suites and deterministic fixtures | MET | 395 tests + 47 subtests |
| Evaluation suite | **SLICE 16** | Same gap as M1.3. |
| README, bilingual quickstart, contribution/security/code-of-conduct docs | MET | `048556b`; README quickstart re-run at each checkpoint |
| `SECURITY.md` names supported versions, private channel, owner, disclosure process | RELEASE | The text exists; enabling GitHub private vulnerability reporting needs the published repository. |
| Threat model updated; dependency/license inventory finalized; release hardening | **SLICE 15** | Automate the inventory, then refresh `THREAT_MODEL.md` against the shipped surface. |
| Reproducible build, changelog, version policy | **SLICE 15** | `uv build` is deterministic in practice but unverified twice-over in a recorded run. |
| Rollback and migration drill | **SLICE 14** | This is the owner-visible half of the M1.1 restore clause; one slice closes both. |
| `CITATION.cff`, `CODEOWNERS`, `THIRD_PARTY_NOTICES.md` | MET | present at the repository root |
| Skills `add-source-provider`, `run-evals`, `audit-licenses`, `release`, each smoke-tested | **SLICE 18** | No `skills/` directory exists. Each skill must wait for the contract it automates: `run-evals` after Slice 16, `audit-licenses` and `release` after Slice 15. |
| Maintainer confirms public brand/package migration and license | RELEASE | Name **Aptuni** and Apache-2.0 are fixed; PyPI/npm/GitHub collision re-check is a publish-time step (Review 15 F9). |
| Independent code/security review has no blocking findings | **per slice** | Each remaining slice carries its own review; M1.5 closes when 14–18 are all non-blocking. |

## Slice order and rationale

**Slice 14 — Owner backup and restore. Highest priority.** `aptuni privacy purge confirm` deletes
canonical records irreversibly, and `aptuni export` states in its own output that it is not a
restorable backup. `Vault.restore_from` is implemented, hardened and reviewed, yet nothing in the
product can produce an input for it. An owner who purges by mistake today loses that history with no
in-product remedy. This is a live data-loss hazard, not a missing convenience, and it closes the
M1.1 restore clause and the M1.5 rollback drill together. Dependency-ready: no upstream contract
moves.

**Slice 15 — CI and supply-chain gates.** Unblocks the Linux support claim, converts four
hand-run checks into recorded ones, and is what a contributor looks at first. Depends on nothing;
ordered second only because Slice 14 removes a data-loss hazard.

**Slice 16 — Versioned evaluation harness.** `EVALUATION_PLAN.md` must move from `Proposed` to
accepted with a checksummed corpus before any threshold in it may be quoted. Ordered after 15 so the
harness runs in CI from its first commit.

**Slice 17 — Real-host S12 probes.** Maintainer-gated: needs real Claude Code and Codex
installations and a recorded daily task in each. Not code-blocked; run when the hosts are available.

**Slice 18 — Post-contract skills.** Deliberately last. Each skill automates a contract that Slices
14–16 are still shaping; writing them earlier guarantees a rewrite.

## Acceptance for this plan

1. Every M1.1–M1.5 exit clause above carries exactly one disposition.
2. No clause is marked MET without a named file, review, or recorded run.
3. `RELEASE` is used only for clauses that require the published repository, never to excuse
   unfinished engineering.
4. Slices 14–18 are ordered by user-visible risk first and contract stability second.

## Exit evidence

- `STATE.md` "Next highest-priority task" points at Slice 14 with this plan as its basis.
- Each of Slices 14–18 gets its own plan file and its own review before it is claimed complete.
- Known limitation: the MET rows record evidence that exists at `db7a5d9`; they are re-checked when a
  slice changes the surface they cover, not assumed to stay true.
