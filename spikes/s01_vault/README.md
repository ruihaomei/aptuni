# S01 spike — disposable prototype

Gate 0 proof for canonical schemas and the crash-safe/concurrent Vault protocol. This code is
**disposable**: it is not part of any package and is never imported by production code. Findings and
the reproduce command are in [docs/dev/spikes/S01-vault.md](../../docs/dev/spikes/S01-vault.md).

- `s01/records.py`: frozen Pydantic v2 record schemas (ADR-0001, ADR-0006, ADR-0010, ADR-0011)
- `s01/invariants.py`: cross-record invariants and bi-temporal views
- `s01/vault.py`: segment + HEAD commit protocol, recovery, purge/backup/restore
- `s01/fsgate.py`: fail-closed local-APFS gate (`statfs` via ctypes)
- `s01/migrate.py`: deterministic v0 → v1 migration
- `tests/`: 46 tests; `fixtures/`: golden valid records and invalid schema cases
