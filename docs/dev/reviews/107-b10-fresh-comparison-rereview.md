# Review 107 — Frozen comparison driver re-review

- **Date:** 2026-10-04.
- **Reviewer:** fresh independent GPT-6 Astra xhigh through Codex CLI0.155.1; no implementation authorship.
- **Method:** static supplied-code review; configured MCP servers and unrelated capability providers disabled, Code Mode disabled, read-only sandbox. Native trace has no observed tool calls; this is not complete host-inventory proof.
- **Scope:** one frozen paired six-task A/F comparison, 12 fresh sessions, existing grant/explicit Full/model egress, canonical66. No prompts, rubric, Vault text, labels, owner configuration or prior answers supplied.
- **Limits:** reviewer did not execute tests or inspect live grants. Lead-observed validation is separately identified. Review106 and original bytes/receipts remain retained.

Static review finds Review106’s two blockers resolved without an identified regression. The supplied implementation is consistent with the stated existing Full/Evidence permissions for one frozen paired six-task comparison.

## Re-review findings

- B1: compare_driver.py::snapshot_refused() recognizes research_snapshot_changed within native MCP errors, failed calls or isError results. main() retains the case before stopping. Successful source text containing the marker does not trigger this stop.
- B2: main() catches verify_assets() digest-mismatch ValueError and reaches receipt finalization. Completed records remain retained; the prevented launch remains unattempted. Alternating order, numeric-sequence checks and operational stops remain intact.
- Discovery requires explicit Full, reloads authorization under the lock, checks scopes/modules/egress, and rechecks canonical sequence and current exposure. Metadata derives from credential-filtered Knowledge Evidence; SourceConfig is excluded from discovery disclosure. Hydration preserves canonical Evidence provenance.
- The supplied seven synthetic scenarios agree with the inspected control flow. Their reported results are lead-observed evidence, not independently executed validation.
- A’s 4000-unit per-request guidance and possible 8000-unit total versus F’s shared 4000-unit enforcement are declared treatment differences. Compare actual calls, units, refusals, tokens and journey latency descriptively.
- First-five/first-20 coverage, imperfect blinding, credential-detector residuals and the small sample remain interpretation limits. The audit hook and host configuration checks do not establish complete host confinement.

## Conditions and independence

- Approval covers only one comparison: 12 fresh sessions in the frozen paired order at sequence 66, using Codex CLI 0.155.1, GPT-6 Astra xhigh, the existing Codex grant/model egress, and separate explicit empty 32-unit Full setup.
- Use the supplied driver, declared SHA256 3749e5a4bf48aac27aaffed7f4cd4d10f0ca05de58e2e68d288281d72d2f6a67, with unchanged frozen backend, policy, generated bundles, tasks and evaluator rubric. No retries, retuning, state rebinding or permission expansion.
- Require the runner’s capability/catalog gates before task submission. Stop further scheduling on detected drift, asset mismatch or operational failure; retain attempted and unattempted counts and raw case records.
- Preserve actor-independent grading against the locked rubric, initial arm masking and definitive Evidence-based support assessment. Keep the development result and prior zero-model failure separately visible. This approval authorizes no production adoption or release.
- Independent evidence consists solely of reasoning over the quoted static input. No tools were invoked and no private tasks, rubric, Vault sources, answers, labels or owner configuration were accessed.
- I did not execute tests, verify supplied hashes or live grants, or witness runtime confinement. Freeze and validation receipts are supplied reports; no actual comparison has run.

## Frozen identities

- Review input SHA256 `813dbaf709920ea6003b726b7c31ebc6e6611c6d2ff8ff05d4dd1559bab19a34`.
- `compare_driver.py` SHA256 `3749e5a4bf48aac27aaffed7f4cd4d10f0ca05de58e2e68d288281d72d2f6a67`.
- `synthetic_driver_check_v2.py` SHA256 `9289363cac27ee1a3a0954ac2004aa78283dabb3fd3d8f18396c0a9eb10d5624`.
- `synthetic-driver-validation-before-fix.json` SHA256 `3c62a35aeef6462d28fe0dabbdaee8a904b70933cb79018806feb6de1a98552c`.
- `synthetic-driver-validation-after-fix.json` SHA256 `0e2b813430bd01fd108150681fda9bd85e9d1035d28f64a74a40b3367fa33c28`.
- `fresh-comparison-protocol.md` SHA256 `3b141d928b42060022c91d3a90521f6df46a29b7496226e64bf8efbb7e3f6bb8`.
- `agent_e2e_discovery.py` SHA256 `5c14990e1ee5ec88e46f63810a2bd1698045cef191e51cc59f873438dc97bfca`.
- `candidate-discovery-policy.md` SHA256 `1b9a8df56e6c0f70e3fa8046ead5311f693e51b2dda5c65ee59ae84424ce5d8a`.

No production adoption, permission expansion, release, silent rerun, retuning or sequence rebinding is covered.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**
