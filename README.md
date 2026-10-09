<p align="center"><img src="https://raw.githubusercontent.com/ruihaomei/aptuni/v0.2.0b10/assets/brand/logo/aptuni-icon.svg" width="120" alt="Aptuni"></p>

<h1 align="center">Aptuni</h1>
<p align="center"><b>Context, attuned to you.</b></p>
<p align="center">Personal context · Memory · MCP · Local-first</p>
<p align="center"><a href="https://github.com/ruihaomei/aptuni/blob/v0.2.0b10/README.zh-CN.md">简体中文</a> · <a href="https://github.com/ruihaomei/aptuni/blob/v0.2.0b10/LICENSE">Apache-2.0</a> · v0.2.0b10 beta</p>

**Aptuni gives AI agents the right personal context without giving them everything about you.**
The more you use it, the better it understands what matters.

You stop re-explaining yourself to every agent. Your agent gets a small, relevant, verifiable slice
of who you are for the task at hand, and you keep the whole thing in open files you own.

> **Status: Beta (0.2.0b10).** The core, Agent activation and the plugin platform run end to end on
> supported macOS and Ubuntu 24.04/ext4 systems, and Top-Down Learning ships as Flagship Plugin #1.
> Interfaces may still change before Stable. See [what works now](#what-works-today) and the
> [roadmap](https://github.com/ruihaomei/aptuni/blob/v0.2.0b10/docs/dev/ROADMAP.md).

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

Paste this into Claude Code or Codex:

> Install and set up Aptuni for me: run `uv tool install aptuni==0.2.0b10` (install uv first if it is
> missing), then run `aptuni guide agent` and follow it.

Your agent asks a few questions in the chat — your language, which parts of you Aptuni may learn
from, whether cloud models may process your data, which agents to connect and whether you want the
Top-Down Learning plugin — and runs every command itself. You type exactly one command in your own
terminal, `aptuni setup apply ACTION_ID`, and then `APPLY`: an agent is never allowed to approve
access to your data for you. The agent then connects Claude Code or Codex and tells you how to use
Aptuni, which stays OFF until you turn it on for a task.

### Or set it up yourself in a terminal

Install the public package with Python 3.13 and [uv](https://docs.astral.sh/uv/):

```sh
uv tool install aptuni==0.2.0b10
aptuni --version
```

Then run the guided setup in a terminal and answer a few questions:

```sh
aptuni setup plan
```

It asks your language, explains in three lines what Aptuni keeps (Profile, Memory, Evidence), and
asks which parts of you Aptuni may learn from — a local folder, Obsidian, GitHub, Notion or
MarginNote. Press Enter to skip them all; you can add sources later. For each source you choose it
asks for the exact folder or repository right away. Notion and MarginNote need a browser
authorization or a macOS permission prompt, so the plan lists the exact commands to run afterwards.
Nothing is created until you confirm the plan with `aptuni setup apply ACTION_ID` and type `APPLY`.


You can drive the same flow yourself. It is two commands, and the first one creates only a private,
expiring plan record — no Vault, source, grant, or host bundle:

```sh
aptuni setup plan --folder ~/Documents/notes --host claude_code
aptuni setup apply ACTION_ID       # you type APPLY in your own terminal
```

`setup plan` prints the recommended components and why, the API keys and setup time, **exactly
which of your modules an agent will be able to read and which operator receives them**, the exact
folders it will read, **every file it will write and where**, and the exact ordered steps — then
stops. None of those effects happens until you confirm that one plan, and the confirmation is bound
to its digest, so an edited plan can never be applied.

Aptuni writes the agent integration into its own directory and does **not** modify your host's
configuration; you point the host at it yourself. If a step fails, the run stops there and resumes
where it left off; a source that cannot be read right now does not stop it and is listed with a
retry command. `aptuni setup cancel ACTION_ID` revokes the agent access it granted and tells you
exactly what remains — your Vault, sources and evidence are never deleted for you.

## Already have a Vault? (reinstall or new machine)

Your Vault is a plain folder you own; everything else Aptuni keeps is rebuildable local state. After
a reinstall, on a new machine, or when the local state was removed, reconnect instead of creating a
new Vault:

```sh
aptuni attach ~/Aptuni            # the folder that contains HEAD.json
aptuni status
```

`attach` only reads and verifies the Vault, then points this installation at it; nothing inside the
Vault changes. It refuses a folder that is not a Vault, a Vault that fails verification, and a
switch away from a Vault this installation already uses. `aptuni setup plan --vault ~/Aptuni` also
recognizes an existing Vault and shows "use your existing Profile Vault" instead of creating one.
Grants and host integrations are local state, so plan them again after attaching.

## 60-second manual quickstart

Requires the installed Python 3.13 package above.

```sh
aptuni advise                      # a few plain-language questions; changes nothing
aptuni init ~/Aptuni               # create your Profile Vault (or let `setup apply` do it)
aptuni remember "Prefers concise, structured technical explanations." --module preferences
aptuni source add-folder ~/Documents/cv --module experience --role application-materials
aptuni sync SOURCE_ID              # minimized evidence from files you approved
aptuni context "help me prepare for a data science interview" --module experience --evidence --budget 1500
```

Then connect an agent:

```sh
aptuni adapter plan claude --module identity --module preferences --allow-host-model-egress
aptuni adapter apply ACTION_ID     # you confirm in your own terminal
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
| Verified backup and restore of the canonical Vault | ✅ |
| MarginNote 4 source (macOS, direct read-only local sync, native IDs) | ✅ |
| Obsidian source (vault-aware, wikilinks and property names as structure) | ✅ |
| Notion source (official MCP, exact pages/databases only) | ✅ |
| Mem0 local projection (`infer=False`, whole-store rebuild deletion) | ✅ preview |
| Opt-in hybrid search (SQLite + accepted-memory Mem0 ranks) | ✅ preview |
| Obsidian owner review UI | ✅ desktop |
| Flagship plugin: [Top-Down Learning](https://github.com/ruihaomei/aptuni/tree/v0.2.0b10/examples/plugins/top_down_learning) — just-in-time learning from your verified context, portable to local or cloud Agents | ✅ Beta |
| Graphiti | 🗺 Milestone 3 |

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

Design decisions live in [`docs/dev/DECISIONS/`](https://github.com/ruihaomei/aptuni/blob/v0.2.0b10/docs/dev/DECISIONS/README.md), and the product
requirements in [`docs/product/PRD.md`](https://github.com/ruihaomei/aptuni/blob/v0.2.0b10/docs/product/PRD.md).

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
[`SECURITY.md`](https://github.com/ruihaomei/aptuni/blob/v0.2.0b10/SECURITY.md) and the [threat model](https://github.com/ruihaomei/aptuni/blob/v0.2.0b10/docs/dev/THREAT_MODEL.md).

These commands make that concrete:

```sh
aptuni privacy status                  # every copy Aptuni manages, and the ones it cannot delete for you
aptuni privacy purge preview <id>      # the exact records and copies a deletion would remove
aptuni privacy purge confirm <action>  # irreversible, and only for that one preview
aptuni privacy purge cancel <action>   # abandon a confirmed purge that deleted nothing
```

`privacy status` names external copies plainly — exports you made yourself, your original source
files, and transcripts held by an agent's provider — because Aptuni cannot delete those and will
not pretend otherwise. The purge receipt reports, per copy, what actually happened.

### Optional Mem0 projection preview

Mem0 is a disposable local projection of memories you have already accepted in Aptuni; it never
owns Profile truth and does not receive raw conversations. Install the `mem0` extra, run a local
Ollama embedding model, then manage the projection explicitly:

```sh
aptuni memory provider status
aptuni memory provider rebuild
aptuni search "how should I structure experiments?" --hybrid
aptuni memory provider delete
```

Rebuilds always use `infer=False`. Privacy deletion never relies on Mem0's record-level delete:
Aptuni removes the whole managed projection immediately. Forgetting marks the projection stale and
excludes the revoked memory on the next explicit rebuild. The preview is not selected automatically
by setup or Recipes. `search --hybrid` requires a fresh, fully cleaned projection and combines only
rank positions; Mem0 scores never become canonical. Default search and the Context API remain on
the builtin SQLite/FTS path.

Two preview limits are worth knowing. The semantic lane has no relevance floor yet, so a query with
no keyword match can still return accepted memories up to `--limit`; judge the results, do not
assume them. And the reported `score` is only comparable within one invocation — plain search and
`--hybrid` use different scales.

## Your Obsidian vault, as structure

An Obsidian vault is more than a folder of Markdown, so Aptuni reads it as a graph:

```sh
aptuni source add-obsidian ~/Vault --module knowledge
aptuni sync SOURCE_ID
aptuni evidence --source SOURCE_ID
```

A folder is only a vault if it contains `.obsidian/`; anything else is refused and pointed at
`add-folder`. The vault's own `.obsidian/` configuration and `.trash/` are excluded before
anything is read, and only `.md` files are opened — images, PDFs and other attachments are
counted, never parsed.

Each note contributes its **structure**, not its prose: the note name, its folder, its wikilink
targets, its tags and aliases, and the *names* of its frontmatter properties. Property **values**
stay private: the frontmatter block is never a source of excerpt text, and no property value
enters the stored locator, so an `employer:` or `salary:` property cannot reach an agent's context
through the property block. (If you also write that value in the note's body, the body is what gets
excerpted — as it would from any source.) Links and
tags inside code blocks are not treated as structure, and unusual frontmatter is reported rather
than guessed at. See `docs/dev/DECISIONS/ADR-0017-obsidian-vault-source.md`.

## Review Aptuni inside Obsidian

The Obsidian owner interface is separate from the source above: installing it grants no note
ingestion and the plugin never scans or writes your notes. Install its three bundled files into an
existing desktop vault, then enable **Aptuni** yourself in Obsidian's Community plugins settings:

```sh
aptuni interface obsidian install ~/Vault
```

Open Aptuni from the ribbon to inspect Profile, Memory, Evidence, recent changes, pending reviews
and promotion state. Accept, edit, reject, pin, forget and evidence actions reuse Aptuni's existing
canonical review rules; Forget always shows a digest-bound confirmation first. The plugin stores
only its local Aptuni executable setting, not returned personal content. If `aptuni` is not on
Obsidian's PATH, set its absolute path in the plugin settings. Obsidian mobile is not supported.
See `docs/dev/DECISIONS/ADR-0023-obsidian-owner-interface.md`.

## Exact Notion scope through official MCP

Notion is an optional source, never Aptuni's storage. Connect once through Notion's official hosted
MCP server, then approve only the pages or databases you actually want to ingest:

```sh
aptuni source connect-notion
aptuni source add-notion https://www.notion.so/EXACT_PAGE_ID --module knowledge --role notes
aptuni sync SOURCE_ID
aptuni evidence --source SOURCE_ID
```

The OAuth/PKCE credentials stay in macOS Keychain; no Notion API token enters the Vault or state
directory. Sync checks only the connected `self` principal, then calls official `fetch` for those
exact roots—no workspace search, recent-page scan, descendant discovery or write tool. Aptuni
retains stable page/database provenance and a short Evidence excerpt, then discards the raw MCP
response. Truncated or unknown content makes the
snapshot partial rather than withdrawing earlier Evidence. Remove the connection with
`aptuni source disconnect-notion`. See `docs/dev/DECISIONS/ADR-0021-official-notion-mcp-source.md`.

## It learns without interrupting you

Telling Aptuni something about yourself does not open a queue you have to work through:

```sh
aptuni observe "Prefers deterministic reproducible experiment pipelines." --module knowledge
# Noted and in use as mem_… — Aptuni added this on its own because you said it yourself.
```

The memory is active immediately, and it is marked as one Aptuni added on its own. You review it
when you feel like it, not before it counts:

```sh
aptuni memory review list                  # what Aptuni learned on its own
aptuni memory review accept  MEMORY_ID     # keep it
aptuni memory review edit    MEMORY_ID "…" # correct it; the original stays in your history
aptuni memory review reject  MEMORY_ID     # stop using it
aptuni memory review pin     MEMORY_ID     # keep it and stop reminding me about it
```

Three things are still **asked before** they take effect, not after: anything an agent proposes
rather than you, anything in a sensitive module (`identity`, `relationships`, `behavior` by
default), and anything that contradicts a record still standing. Those keep the typed confirmation.

Reminders are a line of text, never a prompt — by default when ten are waiting or after fifteen
days, whichever comes first, and `aptuni memory review snooze` defers it. Turn the whole thing off
with `aptuni memory review policy --auto-promotion off`. See
`docs/dev/DECISIONS/ADR-0018-automatic-promotion-and-retrospective-review.md`.

## Measure your setup over time

The owner can run a private, repeatable dogfood loop against the ordinary Context path:

```sh
aptuni evaluate setup
aptuni evaluate trial "What should my agent know for this task?"
aptuni evaluate trial --evidence "What does my source note say about this?"   # also measures L4 Evidence
aptuni evaluate score TRIAL_ID --useful ID... --rest-noise   # every unlisted record is noise
aptuni evaluate discard TRIAL_ID...                           # drop test or mislabelled trials
aptuni evaluate capture
aptuni evaluate report
```

Only a query digest, canonical IDs, explicit labels and content-free metrics persist in local state;
query text and returned context do not. Reports cover usefulness/noise, unsupported useful records,
provenance, exposure correctness, source changes, promotion/review state and context-unit
efficiency, separately for Profile/Memory-only and with-Evidence trials. Rerunning the same query
later shows first-versus-latest usefulness for that query, and unscored trials are listed so they
can be labelled later. Only you label results; `aptuni evaluate reset` deletes the complete derived
evaluation dataset.

## Backups you can actually restore

`aptuni export` writes a readable copy of your current Profile. It is for reading, and it cannot be
restored. The restorable copy is a backup:

```sh
aptuni backup create ~/aptuni-backups/2026-09-20   # a verified copy, outside your Vault
aptuni backup verify ~/aptuni-backups/2026-09-20   # checks it without touching your Vault
aptuni backup list   ~/aptuni-backups              # what you have, and whether each still verifies
aptuni backup restore preview <path>               # exactly what a restore would replace, drop and keep
aptuni backup restore confirm <action>             # only for that one preview
```

A backup is a complete unencrypted copy of your canonical records, including modules you have
hidden, so where you keep it matters. Two things it will not do: it never resurrects a record you
purged, on any machine, because deletions travel with your Vault; and it never overwrites a folder
that already has files in it.

## Contributing

Plugins, recipes, translations and bug reports are welcome. Start with
[`CONTRIBUTING.md`](https://github.com/ruihaomei/aptuni/blob/v0.2.0b10/CONTRIBUTING.md). Adding a plugin to the Advisor catalog is one TOML file
plus two message lines.

## License

[Apache-2.0](https://github.com/ruihaomei/aptuni/blob/v0.2.0b10/LICENSE). Third-party notices are in [`THIRD_PARTY_NOTICES.md`](https://github.com/ruihaomei/aptuni/blob/v0.2.0b10/THIRD_PARTY_NOTICES.md).
