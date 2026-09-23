# ADR-0023: Keep the Obsidian owner interface behind a local versioned bridge

- **Status:** Accepted
- **Date:** 2026-09-23
- **Deciders:** maintainer (fixed M2 priority) · implementing agent · independent reviewer
- **Builds on:** ADR-0002, ADR-0007, ADR-0011, ADR-0013, ADR-0017, ADR-0018, ADR-0020
- **Needs maintainer confirmation:** no for the bounded plugin; enabling it remains an owner action
- **Accepted:** 2026-09-24 after independent Review 62

## Context

The Obsidian source reads approved notes into minimized Evidence. The requested human interface has
the opposite responsibility: show Aptuni's canonical owner state and invoke owner review actions.
Combining them would make discovery imply ingestion or let a UI write source notes as canonical
state. Direct Vault parsing in JavaScript would duplicate schema, temporal and permission logic.

## Decision

Ship `interface.obsidian` as a local desktop plugin over `aptuni interface obsidian` contract v1.
The Python application bridge owns bounded Profile, Memory, Evidence, Recent Changes, Pending
Reviews and evidence-lineage views, with explicit truncation indicators. Mutations dispatch only
to existing Accept/Edit/Reject/Pin and Profile-review services. Forget remains preview plus explicit
digest confirmation, and both stages reject a Memory replaced by a correction. Every item declares
its currently valid actions so historical rows do not present stale mutations. The whole dashboard
is projected from one captured Vault sequence.

The plugin invokes a configurable Aptuni executable with Node `execFile` and fixed argument arrays,
never through a shell. It rejects every response not carrying exact contract
`aptuni.obsidian@1`, parses bounded JSON, renders with text-only DOM APIs, retains results only in
the live view and writes no content cache. Settings store only the executable path. Installation
copies fixed bundled `manifest.json`, `main.js` and `styles.css` into a new exact plugin directory;
directory descriptors pin the vault/config/plugin chain against swaps, and the installer refuses
symlinks and existing targets and never edits Obsidian's enabled-plugin configuration.

`source.obsidian` and `interface.obsidian` share no scope or lifecycle. The interface never scans or
writes notes and does not grant ingestion. It is an owner surface, so it may display owner-visible
modules hidden from agents; mutations still pass all application-layer module, currentness,
confirmation and canonical validation gates.

## Consequences

- The first slice is useful without a frontend build tool or new runtime dependency.
- Obsidian Desktop and a local Aptuni executable are required; mobile cannot use the Node process
  bridge and remains unsupported.
- The JSON bridge becomes a public versioned plugin contract and needs independent compatibility
  and security review before acceptance.
- Backlinks, Canvas, note editing, source synchronization controls and richer history visualization
  are deliberately deferred.

## Verification

Test the read/action allowlists, evidence lineage, bounds, currentness and Forget confirmation;
exercise JSON CLI journeys; statically reject shell execution and HTML injection; verify exact
install scope and refusal paths; run existing lifecycle/privacy regressions and obtain independent
public-plugin/security review.
