# Security and Privacy Third Focused Re-review

- **Reviewer:** independent security/privacy re-review agent (no prior context)
- **Date:** 2026-09-18
- **Scope:** `06-security-privacy-second-rereview.md`, `06-security-privacy-remediation.md`, and every
  cited location: `THREAT_MODEL.md`, ADR-0005, ADR-0010, ADR-0012, `SPIKES.md` (S04),
  `plans/00-phase-0-spikes.md`, `plans/01-foundation-tdd.md`. Consistency sweep also covered
  ADR-0001, ADR-0007, ADR-0011, `plans/02-onboarding-advisor.md`, `ROADMAP.md`,
  `MVP_DEPENDENCY_GRAPH.md`, `COMPATIBILITY.md`, `KNOWN_ISSUES.md`, `HANDOFF.md`, and PRD §21/§29.
- **Baseline commands run (read-only):**
  - `python3 -m unittest tests/dev/test_check_relay.py` — 5 tests, OK.
  - `python3 tools/check_relay.py` — exit 1: `review report is absent from lineage manifest:
    11-cold-claude-relay-drill.md` (a report that appeared during this review; not a security
    finding). This report (`09-…`) will likewise need a `STATUS.json` entry; the reviewer did not edit
    the manifest.
  - `grep` sweeps for `tty`, `typed phrase`, `interactive flow`, `authenticator`, `enrol`,
    `sandbox`, `tamper`, `atomic`, `exactly-once`, `proven_local` across `docs/`.

## Summary

The remediation does what 06 asked on paper. No TTY or typed-phrase approval language is left in any
normative document; the only remaining mentions are negations, such as "never proof of human presence".
The atomicity split is consistent across the threat model, ADR-0005, ADR-0010, S04 and Foundation, and
it has concrete crash and concurrency cases. `proven_local` now has one admission authority.

The new contract makes a much stronger claim than before: consequential agent-initiated mutations
are disabled without verified user presence (`THREAT_MODEL.md:67-74`). As written, that claim is
false against the abuse case that caused the 06 block, which is an ordinary injected model with an
authorized shell tool. The broker controls only the product's API path. It does not control the
same-user files and code that hold the approved state, the grants and the broker's own trust
anchor. The plan also does not specify credential enrollment, and it does not keep the test
authenticator out of production. So a new blocking finding (B2-R3) replaces B2-R2.

## Finding-by-finding disposition

| Prior finding | Result | Evidence and judgment |
|---|---|---|
| B2-R2 TTY is not human presence | **Closed as worded; superseded by B2-R3 (Blocking)** | TTY/PTY/typed/env/file presence is explicitly excluded (`THREAT_MODEL.md:67-74,151-152`; ADR-0005:46-51; ADR-0012:36-38; S04 `SPIKES.md:69-71`; plan 00:61-65; plan 01:125-127; plan 02:20-21; `COMPATIBILITY.md:19`). The adversarial PTY test is binary. No leftover TTY approval language exists. However, the replacement guarantee is only as strong as a trust base that the same shell can rewrite (see B2-R3). |
| H1 atomicity overclaim | **Closed at planning level** (Medium/Low notes N3, N5) | The Vault-only path makes signature verification, nonce and mutation one transaction. The multi-system path makes the nonce and the durable idempotent journal one transaction. Both are stated consistently in `THREAT_MODEL.md:76-80`, ADR-0005:53-56 and ADR-0010:48-53. Tests for two confirmers, pre/post-journal crash, effect-before-receipt, restart/retry and changed digest are in S04 (plan 00:66-67) and Foundation Slice 7 (plan 01:128-130). No contradictory promise remains. The residual gaps are policy recheck at effect time (N3) and the wording "exactly-once" (N5). |
| M3 `proven_local` authority | **Closed at planning level** (Medium note N4) | Core policy is the sole authority. Claude Code and Codex default to remote/unknown. Admission needs a pinned builtin adapter/runtime plus end-to-end model egress evidence. Labels cannot elevate the class, and drift revokes admission (`THREAT_MODEL.md:129-132`; ADR-0005:76-78; S04 `SPIKES.md:75-77`; plan 00:71-73). Because the default is deny, this is safe for the MVP. The "fake proven-local host succeeds" fixtures need the same test-double isolation as the authenticator (N4). |

## New findings

### B2-R3 — Blocking: the ApprovalBroker guards the API, not the same-user state it claims to protect

**Evidence.**
- The canonical Vault is plaintext YAML/JSON/Markdown (ADR-0001:32-33). The PRD requires it to be
  usable and editable through Obsidian and without the plugin (PRD §21, lines 1021-1052).
- Grants and scopes are stored "outside source content" but nowhere protected from the user account
  (`THREAT_MODEL.md:60-62`).
- The core, broker verifier and enrolled-credential store are an ordinary user-installed Python
  package (plan 01:5-6,17-26).
- The only acknowledgement is "a compromised host process … has powerful local access"
  (`THREAT_MODEL.md:167-168`). The 06 review explicitly rejected that residual-risk statement as an
  answer to this abuse case (06:44-47).
- No document defines enrollment of the authenticator credential, the location of its public
  key/credential ID, or who may add or replace it. A grep for `enrol|public key|attestation|trust
  anchor|tamper` returns nothing normative.

**Concrete failure paths.** Each path starts from an instruction-injected Claude Code/Codex model
running its normal shell tool as the user:
1. It edits a pending candidate's `review_status` or a module's `expose_enabled`/`host_model_egress`
   grant directly in the Vault or config files. No challenge is ever requested.
2. It runs a future `enroll`/`add-authenticator` path, or overwrites the stored credential/public
   key, to register a software CTAP/virtual authenticator that it controls. That authenticator then
   produces "UV" signatures on demand.
3. It patches the installed verifier (`site-packages`) or the policy code so that it accepts any
   signature.

Each path yields the "same final mutation the gate claims to prevent" (06:39-42) without a human.
The S04 PTY test would still pass, so the test gives false assurance.

**Required actions (choose and document one honest contract, as 06 required):**
1. **State the enforcement boundary exactly.** The broker authorizes mutations through application
   services only. Direct writes by a same-user process to Vault, config, grant, enrollment or install
   paths are outside core enforcement, unless one of the controls below is in effect. Remove or
   qualify "consequential agent-initiated mutations are disabled" accordingly (`THREAT_MODEL.md:72-74`,
   ADR-0005:49-50, ADR-0012:37-38, `COMPATIBILITY.md:19`).
2. **Choose at least one control for the MVP hosts and make it testable:**
   - **(a) Host confinement precondition.** Ship and verify a required Claude Code/Codex
     sandbox/permission profile. It must deny host-shell writes to the Vault, config/grant store,
     credential/enrollment store and the installed package. `doctor` must detect when the profile is
     missing, and the product must report "approval guarantee not in effect" in that case.
   - **(b) Tamper evidence.** Every consequential state transition carries the broker signature over
     its canonical digest. The core verifies it on load or projection. Unsigned or invalid changes to
     review, grant or policy state are quarantined as untrusted observations, never honored. This
     also gives legitimate Obsidian/manual edits a defined path: they become proposals.
3. **Define the enrollment ceremony and protect the trust anchor.** The first enrollment happens
   during onboarding, bound to a UV ceremony that the host shell cannot drive. Adding, replacing or
   removing a credential requires UV from an existing enrolled credential. Enrollment is not an
   MCP/CLI-automatable action. The stored anchor is covered by control (a) or (b). This resolves the
   bootstrap ordering in plan 02:20-21, which requires UV before any credential can exist.
4. **Add S04/Foundation adversarial cases with binary pass criteria.** Under the chosen control, a
   host shell that:
   - edits a review or grant record,
   - edits `expose_enabled` or `host_model_egress`,
   - replaces or adds an enrolled credential,
   - patches the installed verifier, or
   - registers a software authenticator

   either cannot perform the write, or the change is detected and not honored, with a content-free
   audit event. The `THREAT_MODEL.md` abuse-case list (148-160) gains matching entries.

### H-A — High: test doubles for security authorities are not isolated from production

The remediation relies on "a test UV authenticator" in CI (`06-remediation:13-14`; S04; plan 01:126-127).
The S04/S12 fixtures also rely on a fake proven-local host. Nothing says where these live or how
production rejects them.

A software authenticator that reports UV=true, installed in the wheel or selectable by an env var or
config flag, is a complete broker bypass.

**Actions:**
- Put test authenticators and fake admission hosts in a test-only distribution or test directory.
  Slice 1 (plan 01:43-45) adds a wheel/sdist content assertion that they are absent from production
  artifacts.
- The production verifier accepts only credentials enrolled through the ceremony in B2-R3 step 3. It
  rejects known test/software AAGUIDs or key types.
- No env var, CLI flag or config key selects a broker implementation or disables UV.
- Add a negative test: the production build plus the test authenticator fails to approve.

### H-B — High: "trusted authenticator UI displays the bound digest" is not true of the named authenticators

The claim appears at `THREAT_MODEL.md:69-71` and ADR-0005:48-49. The named authenticators do not
support it:
- FIDO2 security keys have no display.
- The WebAuthn browser UI shows the RP/origin, not the action.
- The macOS Touch ID prompt text (`localizedReason`) is supplied by the calling process.

So the user sees whatever preview the requesting process renders. A shell-capable agent can use that
to get a harmful action approved:
1. It requests a challenge for a harmful pending action. The CLI may request challenges.
2. It prints a benign-looking preview in the host TUI.
3. For roaming keys, it drives the key over HID itself, because any process can request an
   assertion for a known RP ID and credential ID.
4. The user touches the key.

A related risk is click-only or password-reuse dialogs: an agent with Accessibility/computer-use
permissions can click through them.

Implementability on macOS is also unproven. A Secure Enclave key with access control that only the
broker can use needs a code-signed helper with keychain entitlements. A pip-installed Python CLI
cannot hold such a key exclusively.

**Actions:**
- Name the MVP broker architecture for macOS 26.2 and verify its feasibility in S04. Examples:
  - a signed native helper that owns a Secure Enclave key under `biometryCurrentSet` or
    device-password access control, or
  - python-fido2 against a roaming key, with its weaker display semantics stated explicitly.
- The broker fetches the pending action by ID and derives both the digest and the displayed summary
  itself. It never uses requester-supplied text.
- Require per-action UV with no reuse window. Allow no click-only approval.
- Restate the roaming-key residual risk ("user presence, not what-you-see-is-what-you-sign").
- Add tests:
  - a requester-supplied display string differing from the digest is rejected;
  - no approval can be obtained through an allowable reuse duration;
  - where feasible, an Accessibility-driven click cannot approve.

### N3 — Medium: deferred journal effects must recheck policy

`THREAT_MODEL.md:78-80` and ADR-0005:55-56 let retries reuse the approved intent indefinitely.

**Actions:**
- For network/provider effects that disclose data, workers recheck the current grant and epoch before
  each effect.
- The approval expiry bounds effect start.
- If a grant is revoked or the scope narrows, the intent moves to a terminal `cancelled_policy` state
  rather than running.
- A purge (which reduces exposure) continues regardless.
- Add a test: revoke egress between journal commit and worker execution, and assert no network effect
  occurs.

### N4 — Medium: fake proven-local admission path

The abuse case at `THREAT_MODEL.md:159-160` ("fake proven-local host succeeds") and S04/S12 need an
explicit test-only admission mechanism that production cannot reach. Apply the H-A isolation rules.
Define "drift" as a per-session hash recheck of adapter and runtime before any L0/personal release.

### N5 — Low: wording and consistency

- ADR-0005:96 says "exactly-once". Change it to "exactly one durable intent; effects at-least-once
  through idempotent adapters or dedupe keys", matching 06:82-85 and ADR-0010:51-52.
- Replace the generic terms "out-of-band/scoped confirmation" (`THREAT_MODEL.md:58`), "interactive
  flow" (`THREAT_MODEL.md:85`), "strong confirmation" (`THREAT_MODEL.md:143`) and "interactive
  confirmation flow" (ADR-0011:42) with an explicit reference to the ApprovalBroker.
- Update `KNOWN_ISSUES.md` KI-011 and the `STATUS.json` security stream after this review.

## Closed at planning level vs. needing execution evidence

| Item | Planning level | Execution evidence still required |
|---|---|---|
| PTY/typed input cannot approve | Closed | S04 adversarial PTY run |
| Vault-only atomic commit / multi-system journal split | Closed | S01 protocol; S04 and Slice 7 crash/concurrency runs |
| `proven_local` admission authority | Closed (N4 note) | None for MVP (hosts denied); real admission later |
| Broker vs. same-user file/code/enrollment tampering | **Open — B2-R3** | Adversarial tamper suite under the chosen control |
| Test authenticator isolation | Open — H-A | Wheel-content and negative production test |
| Broker display integrity and macOS feasibility | Open — H-B | S04 feasibility on macOS 26.2 with the chosen authenticator |

## Re-review gate

- [x] No TTY/typed-phrase approval language remains; PTY attempt is a binary S04/Foundation test.
- [x] Atomicity language distinguishes Vault-only commit from durable multi-system intent.
- [x] Concurrent/crash/idempotency tests cover nonce, journal, side effect, receipt, and retry.
- [x] `proven_local` has a single core admission authority with pinned real-host evidence.
- [ ] Enforcement boundary against same-user shell writes to Vault/grants/enrollment/install is
      stated honestly and backed by host confinement and/or signed-state tamper evidence (B2-R3).
- [ ] Enrollment ceremony and trust-anchor protection defined; bootstrap order with onboarding fixed.
- [ ] Adversarial tamper suite (record/grant edit, credential swap, verifier patch, software
      authenticator) has binary pass criteria in S04/Foundation.
- [ ] Test authenticator and fake proven-local host are excluded from production and rejected by it.
- [ ] Broker derives its own display from canonical action; macOS broker architecture named and
      feasibility-tested; per-action UV with no reuse/click-only path.

**Final judgment:** B2-R2 is closed as worded, and H1 and M3 are closed at planning level. The
replacement contract still promises protection against injected shell-capable agents that the
broker cannot enforce while state, grants, enrollment, and code remain writable by the same user.

**Verdict:** **BLOCK**
