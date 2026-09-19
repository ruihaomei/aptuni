# S05A — common source identity contract

Disposable Gate 0 evidence for ADR-0006. It tests whether one common envelope can represent the
Folder, MarginNote-OPML and GitHub Standard identity families before the v1 schema freezes. That
envelope is `SourceLocator` / `Snapshot` / `Operation` / `CandidateDelta` / `SourceConfig`.

This is evidence, not production code. It uses the Python 3.13.3 standard library only, with no
network and no dependencies.

```sh
/opt/homebrew/bin/python3.13 run_s05a.py        # acceptance run; writes results/S05A-result.json
python3.13 -m unittest discover -s tests -v     # from this directory
```

| Module | Responsibility |
|---|---|
| `s05a/records.py` | Common records and invariants. Identity, location and content hash are separate fields; `remove` is only a tombstone proposal; `ambiguous` needs review and at least 2 candidates; `partial` coverage cannot prove removal; content-addressed `delta_id`. |
| `s05a/extensions.py` | Versioned provider-extension registry. Unknown versions round-trip losslessly and force review. |
| `s05a/codec.py` | Canonical, lossless JSON for the envelope; rejects a tampered `delta_id`. |
| `s05a/reconcile.py` | Path + content-hash reconciliation shared by Folder and GitHub. |
| `s05a/folder.py` | Folder scan: no symlinks, VCS dirs excluded, file-count bound makes coverage partial. |
| `s05a/opml_parse.py`, `s05a/opml.py` | Safe OPML parse (no DTD/entities, node/depth limits, hierarchy kept) and a fixed-point identity matcher. |
| `s05a/github.py` | Trees-API-shaped scan: `repository_id` anchor, sticky bounded selection, truncation. |
| `s05a/authority.py` | `SourceConfig`, user-policy conflict resolution, pre-commit policy recheck. |
| `s05a/ledger.py` | Stand-in canonical intake: idempotent by `delta_id`, stale-base rejection, and no fact deletion from source loss. |

All fixtures are synthetic and inline in the tests. No private export, repository or credential is
used.
