# Stable readiness report

`tools/stable_gate.py` is the canonical machine-readable evaluator for the Beta-to-Stable exit. It
does not run private queries or infer owner judgments. A Beta validation run supplies content-free
facts bound to one candidate commit; the evaluator calculates category and overall status.

```sh
python3.13 tools/stable_gate.py \
  --evidence artifacts/stable-evidence.json \
  --output artifacts/stable-readiness.json
```

Exit `0` means every release condition, including later explicit Stable publication authorization,
is satisfied. Exit `1` means the report was valid but is not ready. Exit `2` means the evidence or
repository binding is invalid. Reports are build artifacts rather than committed files because a
commit containing its own report would immediately make the candidate binding stale.

## Statuses

- `PASS`: the exact requirement passed for the candidate commit.
- `FAIL`: automated evidence is missing/malformed, a check failed, a quality threshold failed, a
  blocker remains, the clean-room audit failed, evidence belongs to another commit, or the working
  tree has uncommitted changes (only the report output path itself is tolerated).
- `INSUFFICIENT REAL-WORLD DATA`: fewer than 30 real owner-labelled trials or fewer than 14 dogfood
  days. This status never becomes PASS from fixtures.
- `OWNER ACTION REQUIRED`: the exact UX Gate, its prerequisite clean-room sequence, or final Stable
  publication authorization still belongs to the maintainer.

## Evidence shape

The root is `schema_version: 1` with `candidate`, `automated`, `ux_gate`, `clean_room_audit`, and
`stable_publication` objects. `candidate.commit` must equal the evaluated Git commit.

Categories A–F and I–J contain these boolean checks; every key is mandatory for PASS:

| Category | Required keys |
|---|---|
| A Fresh Install | `fresh_environment_install`, `initialization`, `guided_setup`, `claude_connection`, `codex_connection` |
| B Core Correctness | `full_test_suite`, `ruff`, `strict_mypy`, `contract_schema`, `migrations` |
| C Data Integrity | `canonical_validation`, `crash_restart_recovery`, `backup_restore`, `correction_supersession`, `no_known_data_loss_blocker` |
| D Privacy / Permission | `zero_known_exposure_violations`, `module_permissions`, `task_scope_isolation`, `grant_revocation`, `purge_privacy`, `aptuni_off_no_context` |
| E Agent Integration | `claude_profile_memory_full`, `codex_profile_memory_full`, `task_scope_reset`, `session_full_activation_disable` |
| F Plugin Platform | `scaffold_install_grant_invoke_revoke`, `plugin_canonical_privacy_grant_boundaries`, `top_down_learning` |
| I Documentation | `install`, `initialize`, `connect_agent`, `activate_profile_memory_full`, `connect_source`, `review_correct_context`, `install_use_plugin`, `disable_revoke` |
| J Supply Chain | `wheel_sdist_install`, `artifact_integrity`, `dependency_license`, `secret_private_data_scan`, `release_workflow` |

Category G contains integer counts: `scored_trials`, `returned_records`, `useful_records`,
`noise_records`, and `exposure_violations`. The evaluator fixes the initial Beta thresholds at 30,
0.80 useful precision, 0.20 maximum noise, and zero exposure violations. Precision and noise thresholds
apply only once 30 trials are scored; a smaller sample stays `INSUFFICIENT REAL-WORLD DATA`
whatever its early ratios, while any exposure violation or inconsistent count is always `FAIL`. Category H contains
`dogfood_days`, `final_7_day_p0_p1_blockers`, and `privacy_data_integrity_blockers`.

The UX Gate passes only when `ux_gate.statement` is exactly
`Aptuni User Experience Gate: PASS` and `ux_gate.commit` matches the candidate. A clean-room audit
and the later publication authorization are also commit-bound. Unknown input fields are never
copied to the output, which keeps accidental query/Profile content out of the report.

## Sequencing

`automated_stable_gate` aggregates A–J only. `release_readiness` then applies the required order:
Automated Stable Gate → exact UX Gate → clean-room audit → explicit Stable publication
authorization. The tool cannot grant any of those owner decisions and does not publish anything.
