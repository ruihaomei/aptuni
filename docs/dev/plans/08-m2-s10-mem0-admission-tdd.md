# Milestone 2 S10 Mem0 Admission Plan (TDD)

**Status:** Complete (2026-09-22). Review 52 approved the narrow projection-only admission with
non-blocking notes; raw-interaction inference remains rejected.

## Objective

Prove or falsify that an isolated Mem0 OSS configuration can satisfy Aptuni's local privacy,
retention, deletion, rebuild, and portability boundary without changing canonical Vault files.
This is a bounded admission spike, not an adapter or a new product contract.

## Bounded fixture

Use three synthetic canonical memories with stable IDs, scopes, timestamps, metadata, and distinct
marker strings. Include one corrected item and one tombstoned item. The fixture contains no user
data, credentials, prompts, source files, or private paths. A manifest fixes its schema version,
record count, byte size, and SHA-256 digest.

The harness creates all provider state below one disposable root and rejects symlinks, paths outside
that root, unbounded enumeration, or unexpected files. Sanitized evidence records only booleans,
counts, versions, durations, relative storage classes, and digests; it never records marker text.

## Failing-first cases

1. **Fixture integrity:** reject a changed digest, unknown schema, duplicate canonical ID, oversized
   field/file, path escape, or unbounded record count.
2. **Telemetry and network:** set telemetry off before provider import; deny Internet/TCP sockets;
   fail if initialization or any operation attempts outbound traffic.
3. **Retention inventory:** locate every synthetic marker under the disposable provider root after
   add/correct/search/restart; classify current memory, history, raw-message, cache/log, and unknown
   copies without persisting marker text in results.
4. **Additive/correction behavior:** distinguish provider add, explicit correction, and deletion;
   provider scores/history never become canonical confidence or history.
5. **Deletion:** delete/reset provider data, verify all managed marker copies are absent, and report
   incomplete/unknown copies as failure rather than claiming deletion.
6. **Rebuild:** rebuild a fresh provider from the canonical fixture with inference disabled, recover
   active items, retain tombstone exclusion, and keep stable canonical IDs in metadata.
7. **Canonical isolation:** byte-digest the canonical fixture tree before and after every provider
   phase; any change fails the run.
8. **Export gap:** compare public enumeration with the state required for provider-native history,
   tombstone, and stable-ID round trip; classify unsupported fields explicitly.
9. **Restart and failure:** restart the provider, inject a failed add/delete, and require bounded,
   truthful status with cleanup confined to the disposable root.

## Implementation order

1. Add fixture validation, tree-digest, socket-denial, inventory, and result-schema tests.
2. Implement a provider-neutral harness and deterministic in-process fixture provider so every
   orchestration and failure path is executable without Mem0.
3. Run the same harness through an isolated, version-pinned Mem0 driver using only local inference,
   embedding, vector, and history components.
4. Record exact dependency/runtime versions and lock hashes outside the product dependency graph.
5. Obtain independent review because the admission decision affects privacy, deletion, and the
   future public provider interface.

## Admission gate

S10 passes only when all of the following hold:

- zero outbound network attempts with telemetry forced off;
- deterministic, fully enumerated provider storage paths;
- no raw marker after successful structured extraction, or an explicit failing result if upstream
  retention cannot be disabled;
- provider deletion and rebuild leave canonical bytes unchanged;
- rebuild from canonical input reproduces the active projection without resurrecting tombstones;
- deletion/reset removes every managed marker copy and unknown copies are zero;
- results and logs contain no fixture marker text;
- public export limitations are documented and cannot be mistaken for Aptuni backup semantics.

If upstream Mem0 cannot meet a condition, record S10 as failed or conditionally rejected; do not
weaken the gate and do not begin a production adapter.

## Verification commands

The spike README will provide exact isolated-runtime commands. At minimum:

```sh
/opt/homebrew/bin/python3.13 -m unittest discover -s spikes/s10_mem0/tests -v
/opt/homebrew/bin/python3.13 spikes/s10_mem0/run_s10.py --driver fixture
```

Then run focused repository tests, Ruff, strict mypy, relay/doc checks, and the full repository gate
at the S10 decision checkpoint.
