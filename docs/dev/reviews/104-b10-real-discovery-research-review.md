# Review 104 — Bounded real-data discovery research interface

- **Date:** 2026-10-04.
- **Scope:** `tools/agent_e2e_discovery.py`, its synthetic tests, and the inherited
  dispatch/packing helpers in `tools/agent_e2e_mock.py`. Relevant contracts:
  ADR-0024, ADR-0025 and ADR-0031, plus the existing host authorization,
  exposure and context-packing implementations.
- **Independence:** this reviewer proposed the bounded discovery hypothesis and
  authored the earlier synthetic baseline mock, but did not author this backend
  or its tests. This review concerns the new real-data boundary.
- **Method:** static code/contract review and synthetic tests only. No live Vault,
  grant contents, private labels, oracle response, owner transcript or sealed
  prompts were read. No live backend or model call was performed by this reviewer.

## Decision and permission interpretation

No blocking defect was found for **one frozen development probe of the original
m05 project-selection task**, using the existing Codex grant and explicit owner
Full setup. Approval is limited to the reviewed bytes, fixed sequence, two task
attempts, fixed selection and budgets, with raw results retained privately. It
does not approve production installation, additional grants, automatic activation,
a finalist claim or evaluation on the sealed holdout.

The repository basename is personal source metadata, even when its repository is
public. The permission assessment therefore rests on its canonical origin and
exposure, not on an assumption that titles are harmless. This implementation reads
the label only from an already exposable Knowledge **Evidence** record's GitHub
locator/concept extension. It requires both `context.read` and `evidence.read`,
the requested module grant, and informed host-model egress. ADR-0025 permits
minimized Evidence within explicitly enabled Full; the original task expressly
requests discovery of prior projects. A bounded set of these permitted labels is
within that task and Evidence data class. This is a new research representation
of permitted Evidence, not authorization to expose owner SourceConfig inventory.

SourceConfig records do not pass the Evidence filter and their fields are not
inspected or exported by this path. Normal canonical snapshot deserialization
still occurs; this is not a claim that the trusted local process cannot read the
Vault. ADR-0024's public SDK remains unchanged, and the existing informed-egress
host boundary is checked rather than replaced. The reviewer has not independently
verified the live grant's values: execution must load the specified existing grant
and refuse when any required permission is absent.

## Disclosure and accounting checks

The server starts OFF. It reuses pre-validation task-attempt counting, including
refused requests, and permits only the one initial session Full setup with
Knowledge and 32 units. Setup must return no items. Disable and status cannot
reset the two-attempt or shared actual-unit counters. Ordinary `search` delegates
to the existing activation/context path with the current remaining budget.

Every content retrieval holds the existing authorization inode lock, reloads
access, checks both scopes and requested modules, and checks host-model egress.
The canonical sequence must match the frozen value before retrieval and again
before disclosure. The first stage considers only currently exposable Knowledge
Evidence, rejects credential-bearing records, and checks the GitHub locator's
repository identifier and ASCII owner/repository grammar. It preserves the stable
first-five selection; no oracle name or semantic ranking is introduced.

The catalog exposes only process-local opaque anchors and repository basenames,
bounded to 48 UTF-8 bytes with a visible ellipsis inside the cap. It is tainted,
untrusted data. Case-folded bounded-label collisions refuse before disclosure or
map installation. The tool contract explains truncation, partial selection and
the absence of authorship or competence evidence. The catalog is one packed unit
capped at 800 units, and a map is installed only when that unit is returned.

The second stage accepts one disclosed opaque anchor, rechecks current exposure
and permissions, and admits at most the first 20 stable Evidence IDs for that
group. Unknown identifiers, repository IDs and evidence references are not
repaired into valid anchors. Hydration uses normal Evidence ContextUnits with
canonical citations, source provenance, trust and signals, capped at 3200 units.
Both stages charge actual packed units against the shared 4000-unit limit.
Neither a label nor an anchor is itself proof of personal contribution or results.

## Effect guard

The guard refuses canonical/shared projection writes, outside-scratch mutation,
subprocess execution and network connect/bind effects exercised by this path.
Only the existing writer/source-operation lock maintenance and private scratch
writes are allowed. The authorization lock is opened read-only without creating
or replacing it. The MCP SDK stdout exception requires a FIFO descriptor with the
original stdout pipe's device and inode; it does not admit an arbitrary integer
file descriptor. The guard is a scoped Python audit hook, not an OS sandbox or
proof against hostile same-user code. Service and adapter-manager construction
before guard installation does not itself load a Vault or mutate state.

## Verification and reviewed identities

- **24 tests passed:** the eight discovery tests plus 16 inherited mock tests.
  These cover OFF/setup, denied modules and egress, fresh scope revocation,
  withdrawal/sequence drift, Evidence-only and credential filtering, preserved
  provenance, counters/budgets, compact collisions/identity handling, actual lexical
  behavior, and the isolated write/subprocess guard checks.
- The new actual MCP STDIO test uses a fully invented workspace and grant. It
  verifies empty setup/catalog, disable denial and unchanged canonical sequence.
  Positive catalog/hydration filtering is tested separately with synthetic service
  records; the STDIO test does not establish live GitHub discovery usefulness.
- Explicit-file **Ruff**, **mypy** for the backend and whitespace checks passed.

SHA-256 identities:

- Backend: `5c14990e1ee5ec88e46f63810a2bd1698045cef191e51cc59f873438dc97bfca`.
- Discovery tests: `07aa408d542cd4434f0d49304994851716f1c6be0a2704bde185415d8a715021`.
- Inherited mock/helper: `a929f8e97c500c6303979c27451314662548e4901e0dc4fa711896b5cd84020a`.

## Interpretation limits

Stable first-five selection is deliberately partial. Stable first-20 hydration
and whole-unit packing may omit the useful evidence even when it exists. These
are outcomes to retain in the development probe, not reasons to expand budgets,
select an oracle group or repair a query during the frozen run. A successful
probe would establish feasibility for that task and state only. Earlier failed
contracts and operational state-drift failures remain separate recorded results.

**Verdict:** **APPROVE** — ONE FROZEN DEVELOPMENT PROBE ONLY
