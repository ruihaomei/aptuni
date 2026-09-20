---
name: audit-licenses
description: This skill should be used when the user asks to "audit licenses", "check dependencies and notices", or review Aptuni supply-chain evidence.
---

# Audit Licenses and Dependencies

## Goal

Verify that the locked runtime closure, notices, built artifacts, vulnerability report, and tracked
secret checks agree before a release decision.

## Boundaries

- Read `docs/dev/plans/09-ci-and-supply-chain.md` and `THIRD_PARTY_NOTICES.md` before editing the
  inventory.
- Do not hand-edit notices to hide lock drift. Resolve the dependency decision and record the exact
  locked version and license evidence.
- Scanner success is bounded evidence, not proof of legal compliance, absence of secrets, or safety.
- Do not fetch, upgrade, publish, push, or change credentials as part of an audit.

## Workflow

1. Run the local deterministic checks:

   ```sh
   .tools/bin/uv lock --check
   .tools/bin/uv run --no-sync python tools/check_supply_chain.py notices
   .tools/bin/uv run --no-sync python tools/check_supply_chain.py secrets
   .tools/bin/uv run --no-sync python tools/check_supply_chain.py workflow
   ```

2. Export hash-locked runtime requirements and a CycloneDX 1.5 SBOM from `uv.lock`, then run the
   locked `pip-audit` command from `.github/workflows/ci.yml` without `uvx` or an implicit upgrade.
3. Build with the locked backend and run `tools/check_supply_chain.py artifacts` over every wheel and
   sdist. Confirm `LICENSE`, `NOTICE`, and `THIRD_PARTY_NOTICES.md` are present.
4. For any added dependency, verify provenance, license compatibility, transitive closure,
   install-time behavior, network behavior, and whether `NOTICE` or `THIRD_PARTY_NOTICES.md` changes.

## Completion evidence

Report lock and notice status, exact artifact/SBOM/audit paths and hashes, findings or suppressions,
and any legal or maintainer judgment that remains open.
