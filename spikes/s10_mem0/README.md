# S10 — Mem0 local privacy, retention, and portability

This Milestone 2 admission spike tests Mem0 as a disposable projection behind Aptuni's canonical
Vault. It uses only digest-locked synthetic markers and writes sanitized counts, booleans, versions,
and digests to `results/`.

## Decision

**Mem0 2.0.20 is admitted only for projection with `infer=False`; Mem0-owned interaction inference
is rejected.** The projection path passed with telemetry disabled before import, zero observed or
blocked non-loopback attempts, exact content and canonical metadata, explicit add/update/delete
history, restart, a fresh-root rebuild, public enumeration, search, managed purge, and unchanged
canonical fixture bytes. The inference probe retained its raw input in the SQLite `messages` table,
violating Aptuni's default raw-retention policy. Adapter work therefore may project accepted
canonical memories but may not send raw conversations to Mem0 or expose its inference mode.

`Memory.delete()` is also insufficient for Aptuni privacy deletion: the tombstoned marker remained
in both embedded Qdrant storage bytes and Mem0 history. A production adapter must close and remove
the entire provider root, then rebuild active projections from canonical records. It must not claim
record-level deletion from the upstream call alone.

The local extraction probe uses a deterministic in-process LLM and embedder test double. This is
enough to exercise Mem0's inference pipeline and prove its unconditional `save_messages` behavior;
it is not evidence about Ollama model quality or resource usage. No Ollama/model download is needed
to decide the retention gate.

## Reproduce

Create a disposable Python 3.13 environment; never install Mem0 into Aptuni's product environment:

```sh
RUNTIME=$(mktemp -d /tmp/aptuni-s10-runtime.XXXXXX)
.tools/bin/uv venv --python /opt/homebrew/bin/python3.13 "$RUNTIME"
.tools/bin/uv pip install --python "$RUNTIME/bin/python" \
  --require-hashes -r spikes/s10_mem0/requirements-lock.txt
PYTHONPATH=spikes/s10_mem0 "$RUNTIME/bin/python" \
  -m unittest discover -s spikes/s10_mem0/tests -v
PYTHONPATH=spikes/s10_mem0 "$RUNTIME/bin/python" \
  spikes/s10_mem0/run_s10.py --driver mem0
```

The standard-library fixture path remains runnable without Mem0:

```sh
/opt/homebrew/bin/python3.13 -m unittest discover -s spikes/s10_mem0/tests -v
/opt/homebrew/bin/python3.13 spikes/s10_mem0/run_s10.py --driver fixture
```

Mem0-specific tests skip outside the isolated runtime. Expected final verdict for 2.0.20 is
`REJECT_RAW_RETENTION`; `PROJECTION_PATH_PASS` appears as the nested projection result.

## Boundaries

- The fixture has three records: active, corrected, and tombstoned.
- All provider state is confined below one disposable root; unknown files and symlinks fail closed.
- The network guard is installed before Mem0/Qdrant/PostHog import in the evidence process. It
  permits loopback runtime plumbing and rejects non-loopback resolution/bind/connect/send/sendto/
  sendmsg paths.
- Adapter purge closes every store and removes the disposable provider root; a marker scan must then
  find zero copies. It deliberately does not call Mem0/Qdrant's collection reset, whose embedded
  delete path drops a collection object without first closing its SQLite handle.
- Qdrant Client 1.19.1 also opens a temporary in-memory SQLite connection with a context manager
  during collection initialization; on Python 3.13 that context manager commits but does not close,
  so a `ResourceWarning` appears at garbage collection. It contains no marker bytes and is a pinned
  upstream lifecycle defect, not treated as proof of durable retention.
- Mem0 public enumeration is diagnostic, not an Aptuni export or backup. It does not preserve the
  canonical revision graph, tombstones, or embedding rebuild instructions.
- The test double does not establish real-model latency, RAM, extraction quality, or download size.
