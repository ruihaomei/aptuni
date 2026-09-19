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
| annotated-types | 0.8.0 | MIT | Pydantic dependency |
| anyio | 4.15.1 | MIT | MCP dependency |
| attrs | 26.1.0 | MIT | JSON Schema dependency |
| cffi | 2.1.1 | MIT-0 | Cryptography dependency |
| click | 8.5.0 | BSD-3-Clause | Uvicorn dependency |
| cryptography | 50.0.1 | Apache-2.0 OR BSD-3-Clause | PyJWT crypto extra |
| h11 | 0.16.0 | MIT | HTTP/Uvicorn dependency |
| httpcore2 | 2.13.0 | BSD-3-Clause | HTTPX2 dependency |
| httpx2 | 2.13.0 | BSD-3-Clause | MCP dependency |
| idna | 3.20 | BSD-3-Clause | AnyIO/HTTPX2 dependency |
| jsonschema | 4.26.0 | MIT | MCP dependency |
| jsonschema-specifications | 2025.9.1 | MIT | JSON Schema dependency |
| mcp | 2.2.0 | MIT | Pinned MCP Python SDK |
| mcp-types | 2.2.0 | MIT | MCP protocol types |
| opentelemetry-api | 1.44.0 | Apache-2.0 | MCP dependency; Aptuni telemetry remains off |
| pycparser | 3.0 | BSD-3-Clause | CFFI dependency |
| pydantic | 2.13.5 | MIT | Runtime schema validation |
| pydantic-core | 2.46.5 | MIT | Pydantic dependency |
| PyJWT | 2.14.0 | MIT | MCP dependency |
| python-multipart | 0.0.32 | Apache-2.0 | MCP dependency |
| referencing | 0.37.0 | MIT | JSON Schema dependency |
| rpds-py | 2026.6.3 | MIT | JSON Schema dependency |
| sse-starlette | 3.4.11 | BSD-3-Clause | MCP dependency; HTTP transport is disabled |
| starlette | 1.6.0 | BSD-3-Clause | MCP dependency; HTTP transport is disabled |
| truststore | 0.10.4 | MIT | HTTPX2 dependency |
| typing-extensions | 4.16.0 | PSF-2.0 | Runtime typing compatibility |
| typing-inspection | 0.4.4 | MIT | Pydantic/MCP dependency |
| uvicorn | 0.53.0 | BSD-3-Clause | MCP dependency; Aptuni starts STDIO only |

## Development-only tools and spike dependencies

Spike environments under `spikes/` are used only to produce evidence. MCP Python SDK 2.2.0 has now
been promoted separately into the locked production dependency set above.
