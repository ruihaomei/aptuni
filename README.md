<p align="center"><img src="assets/brand/logo/aptuni-icon.svg" width="120" alt="Aptuni"></p>

<h1 align="center">Aptuni</h1>
<p align="center"><b>Context, attuned to you.</b></p>
<p align="center">Personal context · Memory · MCP · Local-first</p>
<p align="center"><a href="README.zh-CN.md">简体中文</a> · <a href="LICENSE">Apache-2.0</a> · pre-alpha</p>

**Aptuni gives AI agents the right personal context without giving them everything about you.**
The more you use it, the better it understands what matters.

You stop re-explaining yourself to every agent. Your agent gets a small, relevant, verifiable slice
of who you are for the task at hand, and you keep the whole thing in open files you own.

> **Status: pre-alpha (Milestone 1).** The core runs end to end on macOS today. Interfaces will
> still change. See [what works now](#what-works-today) and [the roadmap](docs/dev/ROADMAP.md).

## Why Aptuni

- **Attunement over accumulation.** Agents get the smallest useful context for a task, not a dump
  of everything stored about you.
- **You own it.** Your Profile Vault is plain JSONL/Markdown on your disk. Indexes and memory
  engines are rebuildable projections, so you never lose yourself when a backend changes.
- **Evidence, not guesses.** A document that mentions XGBoost is `exposure`, not expertise. Every
  claim keeps its source, time and history.
- **Your switches.** Each module (knowledge, experience, preferences…) has separate *ingest* and
  *expose* controls. "Don't tell my agent about my work history" hides it without deleting it.
- **No extra API key required.** The default setup needs no Docker, no vector or graph database and
  no model key. Claude Code or Codex can be the intelligence you already have.

## Install with your agent

Open this repository in Claude Code or Codex and say:

> Read this repository and set up Aptuni for me.

The agent reads [`AGENTS.md`](AGENTS.md), asks which language you prefer, and walks through
`aptuni advise`: what sources you have, how you want to be remembered, and whether cloud models may
process your data. It shows the plan, including API keys, setup time, privacy and trade-offs,
before anything is installed.

## 60-second manual quickstart

Requires Python 3.13 and [uv](https://docs.astral.sh/uv/).

```sh
git clone <this repository> aptuni && cd aptuni
uv sync
uv run aptuni advise                      # a few plain-language questions; changes nothing
uv run aptuni init ~/Aptuni               # create your Profile Vault
uv run aptuni remember "Prefers concise, structured technical explanations." --module preferences
uv run aptuni source add-folder ~/Documents/cv --module experience --role application-materials
uv run aptuni sync SOURCE_ID              # minimized evidence from files you approved
uv run aptuni context "help me prepare for a data science interview" --module experience --evidence --budget 1500
```

Then connect an agent:

```sh
uv run aptuni adapter plan claude --module identity --module preferences --allow-host-model-egress
uv run aptuni adapter apply ACTION_ID     # you confirm in your own terminal
```

## What works today

| Area | Status |
|---|---|
| Profile Vault: facts, history, corrections, crash-safe writes, `doctor` | ✅ |
| Module permissions (ingest / expose, independently) | ✅ |
| Folder source (Markdown, text, CSV) with incremental sync and provenance | ✅ |
| GitHub source, Standard mode (bounded, exact commit provenance) | ✅ |
| Bilingual (English + Chinese) local search, rebuildable index | ✅ |
| Layered context (L0 identity card → L4 evidence) with a budget | ✅ |
| MCP server over local STDIO, permission-checked reads and quarantined memory proposals | ✅ |
| Claude Code and Codex adapters | ✅ |
| Plugin Advisor, Recipes, English / 简体中文 CLI | ✅ preview (`aptuni advise`) |
| MarginNote 4 source (macOS, direct read-only local sync, native IDs) | ✅ |
| Obsidian source and UI, Mem0, hybrid retrieval, Graphiti | 🗺 Milestones 2–3 |

Run `aptuni plugin list` and `aptuni recipe list` to see the same picture from the CLI.

## How it works

```text
Sources ──► Evidence ──► Profile + Memory ──► Context ──► Agents
(folders,    (minimized,   (temporal facts,    (L0–L4,     (MCP, Claude Code,
 GitHub,      provenance)   your switches)      budgeted)    Codex)
 MarginNote)
```

- **Profile ≠ Memory ≠ Context.** A Profile changes slowly, memory forms quickly, and context is
  the task-specific slice assembled at runtime.
- **Progressive disclosure.** Agents start from a short identity card and ask for more only when a
  task needs it.
- **Sources change safely.** Every sync is an immutable snapshot plus a reviewable delta. A deleted
  file withdraws evidence; it never silently rewrites history. Ambiguous changes wait for you.

Design decisions live in [`docs/dev/DECISIONS/`](docs/dev/DECISIONS/README.md), and the product
requirements in [`docs/product/PRD.md`](docs/product/PRD.md).

## Recipes

| Recipe | For | Needs |
|---|---|---|
| **Starter Lite** | Just make it work | nothing extra |
| **Researcher** | Notes, documents and code as knowledge evidence | optional `GITHUB_TOKEN` |
| Personal Memory | Learn from everyday conversations | Milestone 2 (Mem0) |
| Temporal Memory | Relationships that change over time | Milestone 3 (Graphiti) |

You choose an experience; Aptuni chooses the components. Recipes that are not installable yet are
shown with the closest working alternative.

## Privacy in one paragraph

Aptuni never scans your machine on its own, and discovering a source does not mean it has
permission to read it. Raw conversations are not kept by default. Agents see only modules you
expose, within a budget, and the adapter preview tells you exactly what leaves your device (for
example, context an agent reads is processed by that agent's model provider). See
[`SECURITY.md`](SECURITY.md) and the [threat model](docs/dev/THREAT_MODEL.md).

## Contributing

Plugins, recipes, translations and bug reports are welcome. Start with
[`CONTRIBUTING.md`](CONTRIBUTING.md). Adding a plugin to the Advisor catalog is one TOML file
plus two message lines.

## License

[Apache-2.0](LICENSE). Third-party notices are in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
