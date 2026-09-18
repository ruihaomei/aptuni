# Design Rationale (distilled from the PRD design conversations)

> **Status:** reference document · **Companion to:** [PRD v2.1](PRD.md)
>
> The PRD says *what* to build. This file preserves *why* — decisions and trade-offs made across
> four rounds of Socratic design discussion between the maintainer and an AI product advisor.
> It is a depersonalized digest: the raw conversation log is kept privately by the maintainer and
> is intentionally not committed. When this file and the PRD disagree, **the PRD wins**; record the
> disagreement in `docs/dev/KNOWN_ISSUES.md`.

## 1. Origin and primary use case

- The project began as a **personal profile, not a personal knowledge base** (a knowledge base may
  come later; leave an interface for it).
- The first concrete job is **self-directed learning**: when the user says "teach me quantitative
  finance", the agent should already know the user's foundations (math, statistics, Python,
  optimization), what they have *actually* studied, and how they like to be taught — then teach
  in a targeted way.
- The second job is **everyday personalization**: the agent should understand the user better the
  more they interact ("compounding personalization"), without the user feeling they maintain a system.
- It became an open-source framework because the architecture is useful beyond one person; the
  maintainer dogfoods it daily and turns friction into requirements and regression tests.

## 2. Source authority — why MarginNote is special

- Reading lists are not evidence of study. A book on a list ("Deep Learning", "Convex Optimization")
  must **not** make the agent infer the user studied it.
- For the maintainer, **mind maps are the ground truth of what was genuinely studied**, because a
  mind map is where learning was actually recorded. Hence MarginNote is the primary authority for
  `studied` claims in the maintainer's setup, and the **hierarchy itself is knowledge** — never
  flatten OPML into text chunks.
- Application materials (CV, statements; Markdown/Word/Excel) are the primary authority for
  experience, projects and education. GitHub repositories are evidence for *applied* knowledge.
- Positioning insight: most tools treat MarginNote as documents; this project treats it as
  **structured learning-behaviour data**. That is a differentiator for MarginNote users while the
  core stays source-agnostic.

## 3. Evidence, not proficiency

- "Many nodes = mastery" is explicitly rejected. Source-specific **Knowledge Evidence Signals**
  (`node_count, max_depth, note_density, repeated_mentions, source_maps, last_updated`) describe
  *how much evidence exists*, never *how good the user is*.
- The four states **Exposure → Studied → Applied → Demonstrated** were first a MarginNote rule and
  were then promoted to a **source-agnostic General Evidence Model**: every source contributes
  evidence items with a `signal`; the knowledge state is derived from all evidence.
  - exposure: the concept appears (e.g., a node exists);
  - studied: substantive learning traces (child nodes, formulas, examples, notes);
  - applied: used in a real project/code;
  - demonstrated: externally validated output (coursework, research, publication, competition, project result).
- An optional mastery score may exist as a retrieval/planning signal only; agents must never present
  it as a competence level (maintainer answer, round 3, Q6).

## 4. The fact layer is the backbone

- A structured fact layer ("facts.yaml" in the early design) is the critical layer because it makes
  every downstream projection easy: Markdown ⇄ JSON/YAML → Mem0 or Graphiti.
- Early example shapes (kept as design intent, not final schema):

```yaml
- id: knowledge.survival-analysis.cox          # module.topic.subtopic, human-readable
  type: knowledge
  statement: "Studied Cox proportional hazards models."
  evidence_level: studied
  evidence:
    - source: marginnote_survival_analysis
      node: mn:survival:cox
      path: [Survival Analysis, Cox Model]      # hierarchy path is provenance
  valid_from: 2026-09-09
  valid_until: null
  confidence: high
  last_verified: 2026-09-18

- id: project.ctffr
  type: research_project
  title: "Machine Learning-based CT-FFR Prediction"
  roles: [modelling, validation, reproducibility]
  sources: [resume_2026, ps_master, manuscript_ctffr]
  valid_from: 2025-01
  valid_until: null
```

## 5. Incremental updates, proposals and agent autonomy

- Never "re-summarize the whole profile whenever a file changes": it wastes tokens **and** corrupts
  previously-correct facts.
- Pipeline: hash → changed? → parse diff → **candidate delta** → conflict detection → validation →
  apply → rebuild only affected indexes.
- A delta is a reviewable **update proposal**, e.g.:

```yaml
update_id: 2026-09-18-001
source: { marginnote: survival_analysis.opml }
changes:
  - action: add
    target: knowledge.survival-analysis.competing-risks
    evidence: { node: mn:survival:competing-risks }
    proposed_statement: "Studied competing risks analysis."
impact: [profile/knowledge.md, indexes/knowledge_index.md]
```

- The agent's autonomy lives inside a structured loop — **detect → reason → propose → validate →
  apply** — which is where the host agent's judgement is most useful and least risky.

## 6. Guardrails (origin of PRD §23)

- **Provenance:** every important claim traces to a source.
- **Conflict:** an old CV says `rank: 3`, a new CV says `rank: 2` → do not delete; close the old
  fact (`valid_until`) and open the new one (`valid_from`). This also pre-aligns with Graphiti.
- **Unsupported claim:** "XGBoost appears in MarginNote" ⇒ `studied XGBoost`, never `proficient`.
- **Staleness:** career goal 2025 → Data Scientist; 2026 → AI Product / Data Science — keep both,
  with time semantics.

## 7. Profile vs Memory, and backend neutrality

- Profile (slow, stable) and Memory (fast, interaction-derived) are separate but **both flow into
  Context**. Memory is a *provider* behind the core API (`memory-builtin | memory-mem0 |
  memory-graphiti | memory-future-x`); swapping it must not affect the agent host, the profile,
  Obsidian, or the Context API.
- Graphiti's temporal knowledge graph is admired (valid_from/valid_until, provenance to episodes,
  incremental updates), but the design discussion noted a public report that its temporal
  versioning applies well to **edges** while **node attributes can be overwritten** (to be verified
  in `docs/dev/research/03-graphiti.md`). Conclusion: **borrow Graphiti's ideas, do not adopt its
  schema as canonical**; our fact layer carries temporal fields from Day 1 and Graphiti is a projection.
- "Memory forms quickly, Profile forms slowly": repeated requests such as *"not too long", "give
  the conclusion first", "use Markdown", "math in `$...$`"* gradually become a preference fact like
  `prefers concise structured technical explanations (confidence 0.91, support 13, contradiction 1)`.

## 8. Modules are switches, not deletions

- Eleven modules (identity … memory) exist so a user can "unplug" one: "today I don't want the
  agent to know my experience" ⇒ the context policy excludes the module from retrieval; data stays.
- Two switches (`ingest_enabled`, `expose_enabled`) keep the permission model clear. Natural-language
  requests default to *expose off*; only explicit "destroy / stop updating" stops ingestion
  (maintainer answer, round 3, Q5). Deletion is a separate explicit action.

## 9. Plugins, choice paralysis, Recipes

- Plugin categories grew from "sources only" to Source / Memory / Retriever / (Inference) /
  AgentAdapter / Interface. Community contributors should be able to add one integration (e.g.
  `source-zotero`) without understanding the whole project — the LlamaIndex lesson is its
  **ecosystem architecture** (core + independent integration packages), not its RAG features.
- Many plugins create choice paralysis for beginners, so: short plugin descriptions in the repo,
  sensible defaults, and a **conversational Plugin Advisor** that asks plain-language questions and
  outputs a **Recipe** (a coherent plugin combination) that the agent then installs, configures and
  smoke-tests. Recipes (e.g. `researcher`, `privacy-first`, `temporal-memory`) beat a raw marketplace.
- A Recipe example from the discussion adds fields worth keeping: `agents: {mcp, claude_code, codex}`
  and `privacy: {storage: local, extraction: cloud_allowed}`.

## 10. The maintainer's eight foundational answers (round 3)

| # | Question | Decision |
|---|----------|----------|
| 1 | Source of truth | The Markdown/YAML Profile Vault is canonical; Mem0/Graphiti/vector DBs are projections. Interactions may first land in an episode store, but consolidated long-term information must be projectable to open formats, or users "lose themselves" when switching backends. |
| 2 | How automatic is interaction memory | Agent writes automatically; only high-risk/conflicting memories need confirmation. Graded: episodic memory fully automatic (may reuse a backend's mature automatic mechanism, e.g. Mem0's); stable preferences/profile facts need stronger evidence; sensitive modules stricter. After a batch settles, a low-friction "by the way" reminder points to a review file (path + link) after the agent finishes the user's task. |
| 3 | Keep raw conversations? | No by default — keep only extracted memory; per-source retention policies allowed. Lightness matters more than completeness. |
| 4 | What the agent knows by default | Only a **tiny L0 identity/preferences card is auto-injected**; everything else is fetched through tool search. This is the most natural implementation of progressive disclosure. |
| 5 | Unplugging a module | Both switches exist; plain "don't give the agent X" = expose off; ingestion stops only on explicit request. |
| 6 | Knowledge mastery output | Both discrete evidence states and an optional score; the score is auxiliary and never a competence level. |
| 7 | First agent hosts | Core only knows **MCP + REST/SDK**; Claude Code, Codex, Cursor, Claude Desktop are the first thin adapters — never a Claude-only project. |
| 8 | How local is local-first | Storage is local by default; the extraction model is pluggable (local or cloud, if the user permits). |

## 11. Setup experience (round 4) — "friction-free" is the product

- **Adaptive complexity (option C)**: start Lite; the agent proposes upgrades when justified
  ("your context has grown to 8,000 entries — enable semantic retrieval?"). Beginners follow the
  default path; advanced users open "Advanced configuration".
- **Language first** (English / 简体中文 officially maintained; other languages via community),
  then plain-language questions; the installer can also choose which language pack to install.
- **Data scale is inferred by the agent** from the sources the user names; ask only when unsure.
  Friction-free, psychologically light setup is the primary UX principle.
- **Memory experience in plain words** (Basic / Recommended / Advanced), with a concrete example when
  the user is unsure, and a default recommendation.
- **Privacy**: three plain options; every cloud option lists required API keys, setup minutes,
  benefits and drawbacks; a **zero-API-key configuration always exists**.
- **Source onboarding**: (1) ask the user first (skippable; show example sources to avoid blank-page
  anxiety); (2) offer an agent scan only if chosen; (3) confirm before ingestion. Rationale: cold
  start can cost many tokens; choice and confirmation reduce the user's "token anxiety" and increase
  their sense of control over their own profile.
- **GitHub**: Standard by default, Deep on demand — reduces token anxiety; user may override.
- **Preference decay**: slow decay (half-life ≈ 1 year) acting as a weakly-decaying prior that new
  evidence (likelihood) updates; fast forgetting would make the agent feel like it doesn't know the
  user. Recent preferences are updated conservatively; old ones remain revisable.
- **Promotion + review**: auto-promote first, log it, remind later ("by the way") once ~10 changes
  accumulate — timely updates *and* the user's right to know.
- **Reminder policy** (all user-configurable): critical conflict → immediately; ≥ N stable
  candidates (default 10) → gentle reminder; otherwise periodic (default 15 days); snooze default
  15 days; never nag about the same pending review.

## 12. Open-source ambition and development relay

- Learn repository execution from a benchmark project (Mem0), be user-friendly and visually
  legible, and learn GitHub discoverability so the project attracts users, stars and contributors.
- Borrowing policy evolved from "just copy the embedding code if it's simple" to the PRD §41 order:
  **dependency > adapter > clean-room inspired implementation > direct copy (with license handling)**.
- Claude Code builds; Codex takes over when Claude's quota runs out (and vice versa). A **thin
  development harness** must let them relay seamlessly and accumulate experience, and leave clean
  extension points for community developers.
- A memorable name and icon are wanted (image-generation assisted) via a lightweight brand workflow
  that must not block engineering.
