# Third-party notices

Aptuni is licensed under Apache-2.0 (`LICENSE`, `NOTICE`).

## Reuse policy

Borrow from other projects in this order of preference:

1. **Dependency** — use the upstream package unchanged, under its own license.
2. **Adapter** — wrap an upstream API behind an Aptuni contract.
3. **Clean-room implementation** — reimplement a documented idea without copying source.
4. **Direct code copy** — only after license review. Record the copied file, upstream URL, commit,
   license and copyright line below, and keep the upstream header in the copied file.

## Copied source

None. No third-party source code is copied into this repository.

## Distributed runtime dependencies

Generated from the locked production dependency set by the license check (`docs/dev/plans/01-foundation-tdd.md`,
Slice 1). Each entry records the package, version, license and source.

| Package | Version | License | Notes |
|---|---|---|---|
| — | — | — | Populated from `uv.lock` when the first runtime dependency is added. |

## Development-only tools and spike dependencies

Spike environments under `spikes/` (for example MCP Python SDK 2.2.0, MIT) are used only to produce
evidence. They are not distributed with Aptuni and are not production dependencies.
