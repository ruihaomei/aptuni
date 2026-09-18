# S02 Result — Installed plugin discovery and isolation

- **Date:** 2026-09-18
- **Status:** PASS on the Gate 0 baseline, with one new mandatory mitigation (F1). Awaiting
  independent evidence review.
- **Code:** `spikes/s02_plugins/` (disposable)
- **Machine-readable result:** `spikes/s02_plugins/results/S02-result.json`

## Reproduce

```sh
cd spikes/s02_plugins && /opt/homebrew/bin/python3.13 run_s02.py   # offline; exits non-zero on failure
```

The run needs no network. Fixture wheels are hand-built PEP 427 zips (no build-backend download).
Each test environment is a fresh venv made from the pinned interpreter, and installs use the bundled
pip with `--no-index`.

## Measured facts

| Item | Value |
|---|---|
| Interpreter / pip / OS | CPython 3.13.3, pip 25.1.1, macOS 26.2 |
| Tests | 12 run, 0 failures, 0 errors (exit 0) |
| Fixtures | good plugin plus a transitive dependency, duplicate ID, broken import, future contract (`source/2`), and a plugin with undeclared network use |

### What the 12 tests establish

- **Discovery executes no plugin code.** `importlib.metadata.entry_points` plus a manifest read
  through `importlib.util.find_spec` on the plugin's *top-level* package returns every manifest, and
  no import marker is written.
- **Duplicate IDs fail closed for both claimants,** without importing either.
- **An incompatible contract** is refused at approval and at activation, before any import.
- **Activation needs an approval.** An unapproved plugin is denied and never imported. A plugin that
  is not configured is never imported, even when it is installed.
- **Failures are isolated.** A plugin that raises at import is reported as `import failed`, and the
  good plugin still activates in the same run.
- **Undeclared network use is detected** during the activation probe by a `sys.addaudithook` socket
  hook, and the plugin is refused. The output states "detection only, not containment".
- **Every activation warns** that plugins run in-process as trusted code with the user's privileges.
- **Approval records the complete installed closure.** For each distribution it records the name,
  version, a SHA-256 of RECORD, the dependency edges (`Requires-Dist`), the installer and the direct
  URL, plus the manifest SHA-256.
- **Transitive drift denies activation:**
  - an edited file in the dependency (detected through RECORD per-file hashes);
  - the dependency upgraded from 1.0.0 to 2.0.0.

  Both give "renewed approval required", with no import.
- **Bytecode gap (see F1).** A forged `provider.cpython-313.pyc`, whose header matches the source's
  mtime and size, **passes closure verification and executes**. With `sys.pycache_prefix` pointed at
  a fresh core-owned directory, the same activation runs the verified source instead.

## Interpretation and findings

- **F1 — RECORD does not protect bytecode (new, mandatory mitigation).** pip lists
  `__pycache__/*.pyc` in RECORD *without hashes* (observed). Python accepts a `.pyc` whose header
  matches the source's mtime and size, so an attacker who can write `site-packages` can change plugin
  or dependency behaviour undetected. **M1.1 must run with `sys.pycache_prefix` set to a core-owned
  state directory before importing any plugin**, so installed `__pycache__` is never read. Otherwise
  it must verify bytecode by recompiling. *Affects ADR-0002 and plan 01 Slice 5.*
  This is a local-tamper defence, and ADR-0013 accepts that an unconfined same-user process can
  modify installed code. F1 closes the specific gap where the approval check *claims* the closure is
  unchanged when it is not.
- **F2 — Manifest placement is part of the contract.** Reading the manifest without executing code
  relies on the entry point's top-level item being a **regular package** containing
  `plugin_manifest.json`. A single-module plugin or a namespace package cannot be read that way. The
  conformance suite must reject them, and `plugin-template/` must follow this layout.
- **F3 — The closure comes from installed metadata, not a lockfile.** The spike fingerprints what is
  installed. It does not record the download artifact hashes or index URLs, which an entry-point
  install does not preserve (no `direct_url.json` for index installs, observed). M1.1 should bind
  approval to the `uv.lock` / SBOM artifact hashes **and** verify the installed RECORD. Extras markers
  were ignored in the spike, and M1.1 must resolve them.
- **F4 — Detection is not containment.** The audit hook sees Python-level socket calls only. Native
  extensions, subprocesses and `ctypes` can bypass it. Also, `.pth` files in `site-packages` execute
  at interpreter startup, before core runs. Installing a package is already a trust decision, which
  ADR-0002 states.
- **F5 — Entry points are sufficient.** No pluggy or stevedore is needed for discovery, isolation,
  approval or drift detection at MVP scale. This confirms the ADR-0002 choice.

## ADR impact

| ADR | Impact |
|---|---|
| ADR-0002 | Supported. Add requirements F1 (isolated bytecode prefix), F2 (regular-package manifest placement) and F3 (lockfile artifact hashes plus RECORD verification; resolve extras). Keep the non-containment wording (F4). |
| THREAT_MODEL | Add the bytecode-forgery abuse case and the startup `.pth` non-claim. |
