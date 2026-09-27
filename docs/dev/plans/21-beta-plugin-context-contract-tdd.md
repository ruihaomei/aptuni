# Plan 21 — Beta Plugin Context Declaration TDD

## Goal

Extend `aptuni.plugin@1` additively so a third-party Agent plugin declares required and optional
Aptuni context capabilities, while the existing owner grant remains the sole authority and old v1
manifests/grants remain valid.

## Boundary

- Add one optional manifest table, `aptuni.required` plus `aptuni.optional`; do not create another
  permission system or interpret host mention syntax.
- Preserve legacy `capabilities = [...]` manifests and their exact digest. A manifest uses either
  the legacy field or the new table, never both.
- A grant must include every declared required capability, may include any optional subset, and can
  never exceed the declaration. Exact modules, live revocation, privacy visibility, no-egress and
  application policy remain unchanged.
- Public API calls are task/call scoped. Invoking an approved plugin needs no separate Profile /
  Memory / Full activation; it receives only context it explicitly queries through its exact grant.
- Aptuni still does not discover or execute third-party entry points.

## Failing-first matrix

1. New manifests parse disjoint, unique, non-empty required/optional declarations and reject mixed
   legacy/new forms.
2. Legacy manifests retain their pre-extension digest and grant behavior.
3. Owner grant planning rejects omission of a required capability and accepts omission of optional
   capabilities.
4. Required/optional intent is owner-visible in the plan/grant and integrity-bound without breaking
   legacy stored records.
5. Revocation, module exposure, privacy purge and manifest drift still stop an already-connected
   client.
6. Scaffold emits the new declaration form.
7. Top-Down Learning declares required context plus optional memory proposal; its learning journey
   works without the optional grant, while gap capture fails closed until granted.

## Exit evidence

Focused manifest/public-API/CLI/flagship/privacy tests; strict compatibility regression; Ruff;
strict mypy; full repository gate; independent contract/privacy review; ADR-0024 amendment;
STATE/HANDOFF update and local checkpoint.
