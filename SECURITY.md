# Security Policy

Aptuni holds personal context, so security and privacy reports get priority.

## Supported versions

Aptuni is **pre-alpha**. Only the latest `0.1.x` release and the latest commit on the default branch
are supported.

| Version | Supported |
|---|---|
| `0.1.x` | ✅ |
| `main` (pre-alpha) | ✅ |

## Reporting a vulnerability

Please report privately through **GitHub private vulnerability reporting** on this repository
(the *Security* tab → *Report a vulnerability*). Do not open a public issue, pull request or
discussion for a suspected vulnerability.

Include what you can:

- affected command, tool or file, and the commit you tested;
- steps to reproduce, using synthetic data only;
- impact: for example data exposure to an agent or host, a permission or module-policy bypass,
  loss or corruption of the Vault, or secret leakage.

**Never include real personal data, Vault content or credentials in a report.**

## Response

The maintainer is the response owner. For valid reports we aim to:

- acknowledge within **7 days**;
- share an assessment and remediation plan within **30 days**;
- credit reporters who wish to be named once a fix is available.

We follow coordinated disclosure: please allow a fix to ship before public discussion. We will agree
on a disclosure date with you.

## Scope and known boundaries

In scope: the `aptuni` package, the `aptuni-mcp` server, host adapter bundles, and the Advisor
catalog. Two boundaries are documented design limits, not vulnerabilities by themselves (see
[ADR-0013](docs/dev/DECISIONS/ADR-0013-honest-host-trust-boundary.md) and the
[threat model](docs/dev/THREAT_MODEL.md)):

- A shell-capable agent host (for example Claude Code or Codex) can read files on your device with
  its own tools, including the Vault, unless the host is confined. Aptuni cannot verify confinement.
- Context an agent reads through Aptuni is processed by that agent's model provider. The adapter
  preview discloses this before you approve it.

Reports showing that Aptuni itself releases more than it discloses, or crosses these boundaries
without disclosure, are in scope and welcome.
