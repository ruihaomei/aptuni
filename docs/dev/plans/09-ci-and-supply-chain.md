# Slice 15 — CI and supply-chain gates

**Status:** Implementing (2026-09-20)
**Owns:** M1.1 clean-install and supply-chain clauses; M1.5 dependency inventory, threat-model
refresh, reproducible build and release hardening; Ubuntu LTS/ext4 S01 evidence.

## Runnable outcome

One least-privilege GitHub Actions workflow runs the locked Python 3.13 suite on macOS and Ubuntu,
then produces a verified wheel/sdist, CycloneDX SBOM, locked runtime requirements and build digests.
The same dependency-notice, tracked-secret and artifact-content checks run locally through
`tools/check_supply_chain.py`.

## Acceptance

1. Actions and uv are immutable-version pinned; workflow permissions are read-only and checkout does
   not persist credentials.
2. macOS and Ubuntu LTS run the complete tests, ruff, strict mypy, relay and developer checks from
   `uv.lock`.
3. `THIRD_PARTY_NOTICES.md` exactly matches the cross-platform runtime closure and versions in the
   lock; drift fails locally and in CI.
4. Tracked high-confidence private keys and provider credentials fail a content-free scanner; named
   public test vectors remain allowed.
5. Two builds under a fixed ZIP-safe `SOURCE_DATE_EPOCH` are byte-identical. Wheel and sdist both contain
   `LICENSE`, `NOTICE` and `THIRD_PARTY_NOTICES.md`.
6. A fresh environment installs only the built wheel and runs bounded CLI smokes.
7. CI exports a CycloneDX 1.5 SBOM and a hash-locked runtime requirements file, and `pip-audit`
   reports no known package vulnerability.
8. Ubuntu runs S01's real file/lock/crash tests on its hosted filesystem. This is runner evidence,
   not permission to claim general Linux runtime support until the workflow has completed remotely.

## Non-goals

- Publishing packages, releases or attestations.
- Enabling GitHub private vulnerability reporting or public-release settings.
- Claiming Linux support based only on a workflow file or local emulation.
- Replacing provider-specific secret scanning with a claim of exhaustive detection.
