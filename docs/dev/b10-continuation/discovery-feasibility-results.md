# Real-corpus discovery feasibility — local aggregate diagnostic

2026-10-04. This is a read-only feasibility measurement, not Agent E2E or a
production catalog. No private labels, identifiers, source configuration, excerpts
or paths were exported. The six-task holdout remains sealed.

The existing knowledge/evidence grant and explicitly enabled, empty Full
evaluation scope were checked before inspecting current exposable Evidence.
Credential-bearing records and labels were excluded by the existing guard.
Only permitted GitHub locator/concept repository identifiers and display labels
were considered. SourceConfig fields were neither inspected nor exported; normal
snapshot deserialization still includes canonical record types.

| Observation | Result |
|---|---:|
| Stable canonical sequence | 62 |
| Eligible knowledge Evidence | 26,999 |
| Evidence with eligible locator/concept repository metadata | 456 |
| Repository groups / distinct labels | 11 / 11 |
| Conflicting-label groups | 0 |
| Fixed first-five selection includes the previously observed oracle group | Yes |
| Five-entry named catalog returned within 800 units | **No** |
| Packed response | 32 metadata units; truncated; no catalog item |
| Previously observed oracle evidence response | 1,036 units; fits 3,200 |
| Local diagnostic wall time | 6.073 s |

The named five-entry JSON is one whole context unit. It does not fit the frozen
800-unit allocation on the real metadata, although the invented fixture fits.
This rejects that allocation/packing design for this corpus. Do not interpret
the empty packed response as absent repositories, silently enlarge the budget,
return all repositories, tune ordering to the oracle, or declare the successful
synthetic control ready for production. Inclusion in the first five is an
ordering observation, not proof of suitable project coverage or user authorship.

Execution used the existing authorization-lock inode opened read-only, current
host scope checks, standard exposure filtering and a final stable-sequence check.
A process audit guard denied canonical/shared-projection mutation, external
processes and network effects. Required recovery or projection writes would abort
the diagnostic. Only existing host-local writer/source-operation lock maintenance
and the private result output were allowed. Guard self-checks refused an outside
write, SQLite creation and rename before the live run. The reviewer approved this
bounded execution after an earlier unsafe recovery/index path was rejected and
repaired; this is not a general sandbox audit.

Private script digest: `2959bed1bfad90f1f2154c7ff5d68ae27df712bdf944ca8143b306e1b5b757a3`.
The retained result contains aggregates and booleans only. No canonical,
projection, grant, credential, VPN or production-policy change was made.

**Verdict:** **CURRENT CATALOG DESIGN REJECTED — metadata exists, but the frozen whole-item allocation does not return it.**
