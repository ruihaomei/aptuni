# Personal Context & Memory Framework

## Product Requirements Document v2.1

**Status:** Ready for implementation planning
**Primary development agents:** Claude Code, Codex
**Initial languages:** English / 简体中文
**Product form:** Open-source, local-first, modular Personal Context & Memory Framework
**Primary initial user:** Project creator / maintainer
**Long-term users:** Students, researchers, developers, knowledge workers, heavy AI-Agent users

---

# 1. Product Definition

This project is not merely a personal knowledge base, nor merely a memory backend.

It is a:

> **Local-first, modular, agent-native Personal Context & Memory Framework that helps AI agents understand a user progressively, accurately, efficiently, transparently, and with explicit user control.**

The system combines two complementary mechanisms:

1. **Cold-start Personal Profile**

   * Built from user-authorized existing sources.
   * Examples: MarginNote, Obsidian, Markdown, Word, Excel, PDF, GitHub, CV/application materials, Notion, future providers.
   * Used to establish the user's existing knowledge, experience, goals, projects and preferences.

2. **Continual Interaction Memory**

   * Formed gradually from future interactions between the user and AI agents.
   * Used to make the system increasingly personalized over time.
   * Memory forms quickly; stable Profile facts form conservatively.

Both eventually enter a unified:

> **Personal Context Layer**

which serves Claude Code, Codex, Cursor, Claude Desktop and future MCP-compatible agents.

---

# 2. Product North Star

The project must NOT optimize for:

> “Store as much information about the user as possible.”

It must optimize for:

> **At the right task and the right moment, provide the agent with the smallest amount of the most relevant, accurate, fresh, verifiable and user-permitted personal context.**

Conceptually:

$$
\text{Useful Personalization}
=
\frac{
\text{Relevant}
\times
\text{Accurate}
\times
\text{Fresh}
\times
\text{Permitted}
}{
\text{Tokens}+\text{Noise}
}
$$

This formula is a product principle rather than a literal scoring implementation.

The defining experience should be:

> **The system becomes more useful as it learns more, without feeling heavier as it grows.**

Two UX principles are therefore first-class requirements:

* **Technical lightness:** avoid unnecessary services, infrastructure and dependencies.
* **Psychological lightness:** users should rarely feel that they are “maintaining a knowledge system.”

Complexity should appear only when the user's needs have grown enough to justify it.

---

# 3. Core Conceptual Model

The following distinction is mandatory:

```text
Profile ≠ Memory ≠ Context
```

## Profile

Relatively stable understanding of the person.

Examples:

```text
identity
knowledge
experience
skills
projects
goals
interests
preferences
behavior
relationships
```

Profile changes comparatively slowly.

## Memory

Information learned from ongoing interactions.

Examples:

```text
episodic memory
recent observations
interaction patterns
candidate preferences
temporary goals
repeated corrections
```

Memory may form quickly.

## Context

The task-specific subset assembled for an Agent at runtime.

```text
Profile
   +
Memory
   +
Relevant evidence
   +
Context policy
   ↓
Task-specific Personal Context
```

The Agent should almost never receive the entire Profile or Memory store.

---

# 4. Canonical Truth

The user's portable Profile Vault is the source of truth.

Canonical information must use open formats wherever practical:

```text
Markdown
YAML
JSON / JSONL
OPML
```

Databases are projections, indexes or acceleration layers.

Therefore:

```text
Canonical Vault
       │
       ├── SQLite index
       ├── embedding index
       ├── Mem0
       ├── Graphiti
       ├── LlamaIndex integration
       └── future provider
```

Changing a backend must not cause the user to lose “themselves.”

Important consolidated memories must be exportable/projectable into the canonical open-format store.

---

# 5. Temporal Fact Model

Do not make Graphiti's data model the project's canonical schema.

Graphiti is an optional projection/backend.

The project's fact schema must support temporal state from Day 1:

```yaml
id:
module:
type:
statement:

valid_from:
valid_until:

observed_at:
ingested_at:

supersedes:
superseded_by:

source:
episode:

confidence:
review_status:
```

This enables:

```text
2025:
career_interest → Data Science

2026:
career_interest → Data Science + AI Product
```

without erasing history.

Graphiti is currently explicitly designed around temporal context graphs, incremental episodes, provenance and changing facts, so it is an important architectural reference, but not the owner of our data model.

---

# 6. Modular Personal Information Model

The initial module taxonomy should support at least:

```text
identity
knowledge
experience
skills
projects
goals
interests
preferences
behavior
relationships
memory
```

Every module must support separate controls:

```yaml
modules:
  experience:
    ingest_enabled: true
    expose_enabled: false
```

Definitions:

```text
ingest_enabled
→ may new information continue entering this module?

expose_enabled
→ may this module participate in runtime context retrieval?
```

Natural-language commands such as:

> “Don't tell my Agent about my work experience.”

should default to:

```yaml
expose_enabled: false
```

not deletion.

Only explicit language such as:

> “Stop updating this entirely.”

should disable ingestion.

Deletion/destruction must be a separate explicit action.

---

# 7. General Evidence Model

The system must NOT infer expertise merely because a concept appears in a document.

Knowledge is represented through evidence.

The initial general model is:

```text
Exposure
   ↓
Studied
   ↓
Applied
   ↓
Demonstrated
```

These states are independent evidence dimensions rather than simplistic labels.

Example:

```yaml
concept: XGBoost

evidence:
  - source_type: marginnote
    signal: studied

  - source_type: github
    repo: ctffr
    signal: applied

  - source_type: publication
    signal: demonstrated

knowledge_state:
  exposure: true
  studied: true
  applied: true
  demonstrated: true
```

An optional mastery score may later be calculated, but:

> **The score must never be presented as an objective measurement of human competence.**

It is merely a retrieval/planning signal.

The discrete evidence states remain authoritative.

---

# 8. MarginNote Flagship Source Provider

Core must remain source-agnostic.

However:

> **MarginNote should be an officially maintained flagship integration.**

Reasons:

1. It is the maintainer's primary learning system.
2. It can differentiate this project from generic document-RAG systems.
3. It becomes the reference implementation showing community contributors how a high-quality SourceProvider should exploit source-specific semantics.

MarginNote currently supports structured mind-map workflows and official Markdown / OPML export paths.

The integration should prefer OPML when hierarchy is important.

Do NOT implement:

```text
OPML
↓
flatten text
↓
chunks
```

Instead:

```text
MarginNote OPML
        ↓
preserve hierarchy
        ↓
map node / branch / depth / backlinks
        ↓
Knowledge Evidence Signals
        ↓
Knowledge Graph / Profile evidence
```

Initial source-specific signals:

```yaml
topic:
node_count:
max_depth:
note_density:
repeated_mentions:
source_maps:
last_updated:
```

These describe evidence density, NOT proficiency.

For the maintainer's personal setup:

> MarginNote is the primary authority for claims that something has genuinely been studied.

The presence of a book in a reading list alone is insufficient.

---

# 9. Generic Folder Source Provider

A first-class provider must allow:

> “Use this folder as a source.”

The user supplies a path.

The provider recursively discovers supported files.

Initial common formats should include:

```text
.md
.txt
.opml
.docx
.xlsx
.csv
.pdf
```

Later:

```text
pptx
html
epub
json
other community parsers
```

The Folder Provider must:

1. fingerprint files;
2. detect new/changed/deleted files;
3. use format-specific parsers;
4. preserve provenance down to file/sheet/page/section when practical;
5. avoid reprocessing unchanged files;
6. allow include/exclude patterns;
7. allow the user to assign a semantic role.

Example:

```yaml
source:
  type: folder
  path: ~/application-materials

authority:
  primary_for:
    - experience
    - projects
    - education
```

This is particularly important for the maintainer's application-material folder containing Markdown, Excel and Word documents.

---

# 10. GitHub Source Provider

GitHub becomes a major evidence source for:

```text
skills
projects
applied knowledge
demonstrated knowledge
technical experience
```

Three depth modes:

## Lite

```text
repository metadata
README
languages
topics
```

## Standard — Default

```text
Lite
+
directory structure
key files
dependencies
representative code
commit metadata where useful
```

## Deep — On demand

```text
actual implementation inspection
algorithms
tests
architecture
technical decisions
commit-level investigation
```

Default policy:

> **Standard by default, Deep on demand.**

The user may choose another mode.

This design prevents GitHub ingestion from becoming a token sink.

---

# 11. Plugin Architecture

The project must be designed as:

```text
Core
+
Independent Integrations
```

LlamaIndex is an important ecosystem reference because its current architecture explicitly separates core from independently installable integrations.

Initial plugin interfaces:

```text
SourceProvider
MemoryProvider
RetrieverProvider
InferenceProvider
AgentAdapter
InterfacePlugin
```

## SourceProvider

Where does information come from?

```text
MarginNote
Folder
Obsidian
GitHub
Markdown
Notion
Zotero
Google Drive
future sources
```

## MemoryProvider

Where/how does interaction memory operate?

```text
Builtin
Mem0
Graphiti
future backend
```

## RetrieverProvider

How is relevant context found?

```text
lexical
SQLite FTS
embeddings
hybrid
LlamaIndex
graph retrieval
```

## InferenceProvider

Who performs extraction/consolidation when model inference is required?

```text
current host Agent
local model
Ollama
cloud API
future providers
```

This separation enables a no-extra-API-key path:

> The user's existing Claude Code/Codex Agent can perform extraction and submit structured observations instead of requiring this project to call another model API.

## AgentAdapter

```text
MCP
Claude Code
Codex
Cursor
Claude Desktop
REST/SDK
```

## InterfacePlugin

```text
CLI
Obsidian
Web UI
future clients
```

---

# 12. Plugin Contract

Every plugin should publish machine-readable metadata.

Example:

```yaml
plugin:
  id: memory.mem0
  category: memory
  maturity: stable

requirements:
  docker: optional
  api_keys:
    - optional
  local_only_supported: true

experience:
  setup_minutes:
    min: 3
    max: 10
  difficulty: easy

capabilities:
  interaction_memory: true
  temporal_graph: false

tradeoffs:
  strengths:
    - automatic long-term memory
  weaknesses:
    - additional dependencies
```

This metadata powers the Plugin Advisor.

Community integrations should pass a common plugin conformance test suite.

---

# 13. Memory Providers

The project must not force one backend.

Architecture:

```text
Core API
   │
   ├── memory-builtin
   ├── memory-mem0
   ├── memory-graphiti
   └── memory-future-x
```

Switching providers must not affect:

```text
Profile
Obsidian
Claude
Context API
canonical truth
```

## Builtin Memory

Purpose:

> Zero-friction default.

Should work without:

```text
Docker
Neo4j
vector database
additional API key
```

Initial implementation can use open files + SQLite.

When working through an Agent host, the host Agent itself may extract structured observations and submit them through MCP.

## Mem0

Recommended for users who say:

> “I want my Agent to automatically learn from everyday interactions.”

Mem0 is currently a mature adjacent benchmark with roughly 65.5k GitHub stars and supports library/self-host/cloud paths plus agent-oriented integrations.

It should remain a replaceable backend, not canonical storage.

## Graphiti

Recommended for advanced users who say:

> “I want the system to understand changing relationships among people, projects, interests and events over time.”

Graphiti should initially be optional because of additional complexity.

Our schema must nevertheless remain ready for it.

---

# 14. Interaction Memory Lifecycle

Default lifecycle:

```text
Interaction
     ↓
Observation
     ↓
Candidate Memory
     ↓
Evidence accumulation
     ↓
Memory
     ↓
possibly stable Profile Fact
```

Important principle:

> **Memory forms quickly. Profile forms slowly.**

Raw conversation retention is:

```text
OFF by default
```

Default behavior:

```text
conversation
↓
extract observation/memory
↓
persist structured memory
↓
discard raw conversation
```

Users may configure per-source retention policies later.

---

# 15. Stable Preference Inference

Repeated observations may form preferences.

Example:

```yaml
type: preference
statement: prefers concise structured technical explanations

confidence: 0.91
support_count: 13
contradiction_count: 1
```

Preference confidence must respond primarily to new evidence.

Recency decay should be deliberately slow.

Default preference half-life:

```text
365 days
```

A reasonable conceptual form is:

$$
w_{\text{age}} = 2^{-\Delta t/365}
$$

but confidence should decay toward uncertainty rather than zero.

Pinned/explicitly declared preferences should not decay automatically.

New interaction evidence then acts like new likelihood evidence against the slowly decaying prior.

Exact statistical calibration should be empirically evaluated rather than hard-coded from theory alone.

---

# 16. Automatic Promotion + Retrospective Review

Stable preferences/Profile facts may be automatically promoted when system confidence crosses appropriate evidence thresholds.

They are NOT held back awaiting approval.

Instead:

```text
Candidate
↓
auto-promote
↓
Profile
↓
record review event
↓
later user audit
```

Promoted items must have:

```yaml
review_status: auto_promoted_pending_review
```

This preserves:

```text
freshness
+
user awareness
+
low interruption
```

---

# 17. Audit Reminder UX

Review reminders use a hybrid policy.

Default:

```text
critical conflict
→ immediately notify

unreviewed promoted changes >= 10
→ gentle reminder

otherwise
→ periodic reminder every 15 days
```

Default snooze:

```text
15 days
```

The reminder should appear unobtrusively after the Agent finishes the user's actual task.

Example:

> By the way — 10 profile updates have accumulated since your last review. They are already active, but you can review or edit them here: …

Do not repeatedly nag the user about the same pending review.

The Obsidian UI should eventually provide one-click:

```text
Accept
Edit
Reject
Pin
Forget
Show Evidence
Why does the system believe this?
```

---

# 18. Progressive Disclosure

Progressive Disclosure is a core architectural principle inspired by Claude-Mem's token-efficient retrieval approach.

Runtime layers:

```text
L0 — Identity card
        ↓
L1 — Context index
        ↓
L2 — Relevant modules
        ↓
L3 — Relevant facts / memories
        ↓
L4 — Evidence / raw source
```

For:

> “Teach me quantitative finance.”

the Agent might receive:

```text
L0:
math student
Python
statistics
optimization

L1:
probability
statistics
ML
optimization
limited finance evidence

L2:
relevant knowledge and goals

L3:
specific known topics

L4:
only if verification is needed
```

The Agent should not receive unrelated internships or projects unless retrieval finds them relevant.

---

# 19. Context API

The Core API should expose task-oriented operations rather than raw storage operations alone.

Conceptual API:

```text
get_identity_card()
search_context(query, modules, budget)
get_fact(id)
get_evidence(fact_id)

observe(event)
remember(memory)
forget(memory_id)

get_profile(module)
update_profile(...)
audit_profile()

enable_module(...)
disable_module(...)

list_sources()
sync_source(...)
```

Context queries must support a token/context budget.

Example:

```json
{
  "query": "teach me quantitative finance",
  "modules": ["knowledge", "skills", "goals", "preferences"],
  "token_budget": 1500
}
```

---

# 20. MCP-First Agent Interface

Core interoperability target:

```text
MCP
+
REST/SDK
```

Host-specific adapters should be thin.

Initial supported hosts:

```text
Claude Code
Codex
Cursor
Claude Desktop
```

The current MCP standard explicitly allows servers to expose tools, resources and prompts to compatible hosts, making it appropriate as the primary Agent interface.

Avoid creating core semantics that depend on one Agent vendor.

---

# 21. Obsidian as a First-Class Human UI

Obsidian is not merely an export destination.

Target product:

> **Personal Context for Obsidian**

Long-term panels/views:

```text
Profile
Knowledge
Memory
Sources
Evidence
Goals
Recent Changes
Pending Reviews
Knowledge Map
Plugin Configuration
```

Human-readable profile files should use:

```text
Markdown
YAML frontmatter
wikilinks where helpful
```

The vault should remain usable even without the plugin.

The plugin adds interaction, not lock-in.

---

# 22. Dynamic Source Updating

Never completely rebuild the Profile whenever one source changes.

Required pipeline:

```text
Source
   ↓
Fingerprint / Hash
   ↓
Changed?
   │
   ├── no → skip
   │
   └── yes
          ↓
       Parse diff
          ↓
     Candidate Delta
          ↓
   Conflict detection
          ↓
      Validation
          ↓
        Apply
          ↓
 rebuild affected projections
```

Example:

```text
MarginNote OPML

new:
Competing Risks
Fine-Gray Model
```

should generate a focused delta rather than rewriting the entire knowledge profile.

---

# 23. Guardrails

Mandatory guards:

## Provenance Guard

Important claims require evidence.

```text
claim → evidence → source
```

## Unsupported Claim Guard

Forbidden:

```text
XGBoost mentioned
→ proficient in XGBoost
```

Allowed:

```text
MarginNote evidence
→ studied

GitHub implementation
→ applied

publication/project output
→ demonstrated
```

## Conflict Guard

New facts should supersede rather than silently overwrite historical facts.

## Staleness Guard

Time-sensitive preferences/goals must retain temporal meaning.

## Permission Guard

Disabled modules cannot enter runtime context.

## Retention Guard

Raw interactions must not be persisted when retention policy says not to.

---

# 24. Agent-Guided Setup

The installation experience must be built for:

> **Users who ask their Agent to install the repository.**

A user should be able to say:

> “Read this repository and configure it for me.”

The Agent should guide them through setup conversationally.

## Step 0 — Language

The first question is always:

```text
Which language would you like to use?

1. English
2. 简体中文
```

English and Simplified Chinese are officially maintained.

Other language packs are community-extensible.

Repository documentation strategy:

```text
README.md          → English
README.zh-CN.md    → Simplified Chinese
```

Interactive user-facing strings should use an i18n system rather than duplicated logic.

---

# 25. Source Onboarding UX

Do NOT automatically scan the user's machine.

First ask:

> What information would you like to use to help your Agent understand you?

Offer examples to avoid blank-page anxiety:

```text
Obsidian
MarginNote
Notion
GitHub
CV / application materials
a document folder
Zotero
other
```

The user may skip.

Then offer:

> “Would you like me to scan for likely sources and show you what I find?”

Only scan if explicitly selected.

Critical principle:

> **Discovery ≠ Permission.**

Even detected sources require confirmation before ingestion.

Before expensive cold-start processing, show:

```text
files discovered
approximate processing scope
whether model calls are required
estimated token/cost category
```

Local deterministic parsing should happen before expensive model extraction wherever practical.

---

# 26. Experience-Based Plugin Advisor

Never ask beginners:

> “Do you want Mem0 or Graphiti?”

Ask:

> “How would you like your Agent to remember you?”

Example experiences:

### Basic

> Remember confirmed profile information and stable preferences.

Likely backend:

```text
Builtin
```

### Recommended

> Automatically learn useful things from everyday conversations so the Agent understands you better over time.

Likely backend:

```text
Mem0 or suitable automatic memory provider
```

### Advanced

> Understand how my people, projects, interests and facts change and relate over time.

Likely backend:

```text
Graphiti
```

If users do not understand a choice, provide one concrete example.

Users choose experiences.

The system chooses implementation.

---

# 27. Privacy Experience

Ask in plain language:

> Can your personal data be processed by cloud models?

Options:

```text
1. Yes — prioritize quality
2. Yes — but minimize cloud processing
3. No — everything must stay local
```

Plugin Advisor filters candidates accordingly.

Every recommendation requiring additional setup must display:

```text
Required API keys
Estimated setup time
Benefits
Tradeoffs
```

Example:

```text
Cloud-assisted memory
API keys: OpenAI
Setup: approximately 3–5 minutes
+ stronger extraction
+ simple setup
- personal data leaves local device
- ongoing API cost
```

The project MUST provide a useful configuration requiring:

```text
zero extra API keys
```

---

# 28. Adaptive Complexity

Default experience:

```text
Lite
```

When justified by scale or observed retrieval quality, the system may recommend an upgrade.

Example:

> Your context has grown substantially. Semantic retrieval may now improve recall. Would you like to enable it?

Do not install infrastructure merely because it exists.

Principle:

> **Complexity grows with value, not with ambition.**

---

# 29. Personal Context Recipes

“Recipe” is a first-class product concept.

Repository:

```text
recipes/
├── starter-lite.yaml
├── privacy-first.yaml
├── personal-memory.yaml
├── obsidian-user.yaml
├── researcher.yaml
├── developer.yaml
├── power-user.yaml
└── temporal-memory.yaml
```

Recipe contains a coherent plugin combination.

Example:

```yaml
recipe: researcher

core:
  profile: builtin

sources:
  folder:
    enabled: true
  github:
    enabled: true
  obsidian:
    enabled: true

memory:
  provider: mem0

retrieval:
  provider: hybrid

interface:
  obsidian: true

agents:
  mcp: true

privacy:
  storage: local
```

The Plugin Advisor generates a Recipe before installation.

User sees:

```text
recommended configuration
why it fits
setup burden
API-key requirements
privacy implications
```

Then says:

> “Install this.”

Agent performs:

```text
install
configure
validate
smoke test
```

---

# 30. Default Official Recipes

## Starter Lite

Goal:

> Just make it work.

```text
Core
Builtin memory
Markdown/YAML
SQLite
FTS
MCP
```

Requirements:

```text
No Docker
No vector DB
No graph DB
No additional API key
```

## Personal Memory

Goal:

> My Agent should increasingly understand me.

```text
Core
Mem0
Hybrid Retriever
MCP
```

## Researcher

Goal:

> Rich knowledge and research sources.

```text
Core
Folder sources
Obsidian
GitHub
optional MarginNote
Hybrid retrieval
MCP
```

## Temporal Memory

Goal:

> Model evolving relationships and state.

```text
Core
Graphiti
graph/hybrid retrieval
MCP
```

---

# 31. Maintainer's Initial Recipe

The maintainer's initial dogfooding configuration should be:

```text
Profile Core

+ MarginNote Flagship Source
+ Application-Materials Folder Source
+ GitHub Source
  Standard default / Deep on demand

+ Obsidian

+ Mem0
+ Hybrid Retrieval

+ MCP

+ Claude Code
+ Codex
```

Graphiti:

```text
schema-compatible from Day 1
not required on Day 1
```

Enable when accumulated temporal relationships justify it.

This dogfooding configuration is important:

> The maintainer should use the product daily while building it.

Real friction should continuously become product requirements and regression tests.

---

# 32. Primary Open-Source Benchmark

The primary repository benchmark is:

> **Mem0**

We are NOT copying Mem0's product architecture.

We are studying its repository/product execution.

Its current repository demonstrates several patterns directly relevant to this project:

```text
agent-oriented installation
clear quickstart
multiple deployment paths
integrations/
skills/
tests/
docs/
AGENTS.md
CLAUDE.md
Claude/Codex/Cursor plugin surfaces
community files
```

Its current repository has roughly 65.5k stars, making it a useful example of mature positioning and contributor-facing execution.

Secondary architectural references:

```text
LlamaIndex
→ core + independent integrations

Graphiti
→ temporal context/provenance

Claude-Mem
→ progressive disclosure

Khoj
→ Obsidian/personal-AI UX

memU
→ Wiki-first Agent-managed memory
```

Do not blindly fork any of them.

Borrow principles, not accidental complexity.

---

# 33. Open-Source Repository Quality Bar

A visitor should understand within roughly one minute:

```text
What problem is this solving?
Why is it different?
Can I use it without an API key?
How do I install it with my Agent?
What does it look like?
How can I contribute a plugin?
```

README top section should eventually contain:

```text
memorable logo
one-sentence value proposition
short visual demo
"Install with your Agent" entry
60-second manual quickstart
supported sources/agents
architecture diagram
Recipes
```

Documentation should follow progressive disclosure:

```text
Quickstart
→ Concepts
→ Recipes
→ Integrations
→ Advanced Architecture
→ Plugin Development
→ API Reference
```

GitHub itself recommends a clear README, license and contribution/community files, and repository topics/social preview are explicit repository discoverability features.

---

# 34. Community Growth Requirements

Repository should include early:

```text
LICENSE
README.md
README.zh-CN.md
CONTRIBUTING.md
CODE_OF_CONDUCT.md
SECURITY.md
CHANGELOG.md
CITATION.cff
CODEOWNERS
```

GitHub's community profile explicitly checks files such as README, LICENSE, CODE_OF_CONDUCT and CONTRIBUTING.

Use clear repository topics such as:

```text
ai-agents
memory
personal-ai
personalization
mcp
obsidian
knowledge-management
long-term-memory
context-engineering
agent-memory
```

GitHub topics are directly used for project discovery.

Community contribution strategy:

```text
good first issue
help wanted
plugin wanted
integration
documentation
recipe
```

GitHub explicitly surfaces `good first issue` opportunities and uses them to improve contributor discoverability.

Enable Discussions for:

```text
showcase
ideas
plugin requests
recipes
questions
community integrations
```

Issues remain for actionable work.

---

# 35. Flagship Plugin Standard

MarginNote establishes the quality bar.

Every future flagship plugin should demonstrate:

```text
source-specific semantics
incremental updates
strong provenance
low token usage
documentation
tests
sample fixture
example Recipe
plugin metadata
visual onboarding
```

The community should be able to copy its structure as:

```text
plugin-template/
```

Potential future flagship integrations:

```text
Zotero
Obsidian
Notion
Readwise
GitHub
Google Drive
```

---

# 36. Development-Agent Thin Harness

The repository itself must be highly friendly to AI coding agents.

Claude Code and Codex should be able to alternate without losing project knowledge.

The repository, not conversation history, is the durable project memory.

## Canonical Agent Contract

Root:

```text
AGENTS.md
```

is the cross-Agent development contract.

It contains only durable, always-relevant information:

```text
product principles
architecture invariants
build commands
testing commands
dependency rules
security rules
definition of done
where project state lives
```

Codex currently reads hierarchical `AGENTS.md` project instructions directly.

## Claude Compatibility

Root:

```text
CLAUDE.md
```

should import:

```text
@AGENTS.md
```

and contain only Claude-specific guidance.

Claude Code officially supports this pattern for repositories that already use `AGENTS.md`.

Keep both extremely concise.

Claude Code's own documentation recommends keeping `CLAUDE.md` concise and moving task-specific workflows to skills or scoped rules rather than loading everything every session.

---

# 37. Agent Development State

Maintain durable project state in files.

Recommended:

```text
docs/dev/
├── STATE.md
├── ROADMAP.md
├── HANDOFF.md
├── DECISIONS/
├── KNOWN_ISSUES.md
└── RESEARCH_NOTES.md
```

## STATE.md

Current truth:

```text
current milestone
implemented
in progress
blocked
next highest-priority task
latest validation state
```

## HANDOFF.md

Short-lived operational handoff:

```text
what was changed
what remains
files touched
tests run
known failures
recommended next action
```

It should remain short.

## DECISIONS/

Architecture Decision Records.

Example:

```text
ADR-0001-canonical-open-format.md
ADR-0002-plugin-boundaries.md
ADR-0003-memory-provider-interface.md
```

Important decisions must not live only in chat history.

Anthropic's current agentic guidance explicitly recommends structured state, progress files and Git checkpoints for long-horizon multi-context work.

---

# 38. Claude Code / Codex Handoff Protocol

At task start, Agent must:

```text
read AGENTS.md
read STATE.md
read relevant ADRs
inspect current git status
run appropriate baseline checks
```

During development:

```text
work incrementally
write tests with behavior changes
avoid unrelated refactors
update ADR when architectural contract changes
```

Before ending a substantial task:

```text
run required tests
run lint/type checks
verify changed behavior
update STATE.md
update HANDOFF.md if work remains
commit/checkpoint when appropriate
```

Next Agent should not need the previous conversation.

Desired experience:

```text
Claude quota exhausted
        ↓
open Codex
        ↓
Codex reads repo state
        ↓
continues correctly
```

and vice versa.

---

# 39. Agent Skills

Do not overload AGENTS.md.

Create reusable skills such as:

```text
skills/
├── research-upstream/
├── add-source-provider/
├── add-memory-provider/
├── add-retriever/
├── add-recipe/
├── run-evals/
├── release/
├── audit-licenses/
├── docs-update/
└── brand-workflow/
```

A plugin contributor's Agent should be able to say:

> “Add a Zotero SourceProvider.”

and the skill should guide it through:

```text
plugin scaffold
contract implementation
fixtures
tests
metadata
docs
Recipe example
```

---

# 40. Agent Development Guardrails

The harness must enforce at least:

```text
investigate before editing
test before declaring completion
do not silently change schema
do not introduce heavy dependency without ADR
do not copy upstream source without license review
do not treat generated indexes as canonical truth
do not persist secrets
do not rewrite unrelated user data
```

Use automated checks where possible rather than relying only on prompts.

Claude Code supports hooks for deterministic enforcement where prompt instructions alone are insufficient.

---

# 41. License Provenance

When borrowing from open source:

Preferred order:

```text
dependency
>
adapter
>
clean-room inspired implementation
>
direct code copy
```

Direct copy requires explicit license/copyright handling.

Repository should maintain:

```text
THIRD_PARTY_NOTICES.md
```

and automated dependency/license checks.

---

# 42. Proposed Repository Shape

Target monorepo direction:

```text
/
├── README.md
├── README.zh-CN.md
├── AGENTS.md
├── CLAUDE.md
├── LICENSE
├── CONTRIBUTING.md
├── SECURITY.md
├── CODE_OF_CONDUCT.md
├── CHANGELOG.md
│
├── docs/
│   ├── quickstart/
│   ├── concepts/
│   ├── recipes/
│   ├── integrations/
│   ├── plugin-development/
│   └── dev/
│
├── packages/
│   ├── core/
│   ├── cli/
│   ├── mcp/
│   ├── sdk/
│   └── server/
│
├── plugins/
│   ├── sources/
│   │   ├── folder/
│   │   ├── marginnote/
│   │   ├── github/
│   │   └── obsidian/
│   │
│   ├── memory/
│   │   ├── builtin/
│   │   ├── mem0/
│   │   └── graphiti/
│   │
│   ├── retrieval/
│   │   ├── fts/
│   │   ├── hybrid/
│   │   └── llamaindex/
│   │
│   └── interfaces/
│       └── obsidian/
│
├── recipes/
│
├── skills/
│
├── schemas/
│
├── tests/
│   ├── core/
│   ├── contracts/
│   ├── integrations/
│   └── evals/
│
└── examples/
```

Exact package boundaries may change after implementation spikes.

Do not prematurely create dozens of empty packages merely to match this diagram.

---

# 43. Recommended Implementation Stack

Default technical direction:

```text
Python
→ core/profile/memory contracts
→ source parsing
→ Mem0/Graphiti/LlamaIndex ecosystem alignment
→ MCP/server

SQLite
→ builtin persistence / FTS

Pydantic
→ schemas/contracts

TypeScript
→ Obsidian plugin
→ only where ecosystem requires it
```

Prefer one-language implementation for the MVP where possible.

Do not create microservices for the initial version.

---

# 44. Brand & Naming Workstream

A memorable product name and icon are required before public launch, but naming should NOT block core engineering.

Use a temporary codename during development.

Do not casually choose generic names such as `ContextOS` or `ContextWeave`; adjacent projects already use those names today, illustrating why collision checking is necessary.

Create a `brand-workflow` skill.

Workflow:

```text
Product thesis
↓
brand attributes
↓
name candidates
↓
GitHub/PyPI/npm/web collision scan
↓
shortlist
↓
human selection
↓
icon design brief
↓
image-generation concepts
↓
human selection
↓
visual QA
↓
final assets
```

Desired brand attributes:

```text
personal
alive
memory/context
lightweight
trustworthy
modular
intelligent
not creepy
not corporate
recognizable at small size
```

Icon requirements:

```text
works at favicon size
works in light/dark mode
recognizable without text
simple silhouette
not generic "AI brain + sparkle"
```

Use image generation for exploration, then maintain final production assets in standard project formats.

---

# 45. Visual Quality

The project should be visually legible before it becomes feature-complete.

Required visual assets eventually include:

```text
logo
social preview
architecture diagram
30–60 second demo GIF/video
setup flow screenshot
Obsidian screenshot
Recipe visual
```

Visual design should explain the product rather than decorate it.

---

# 46. Product Evaluation

Build an evaluation suite early.

Important eval dimensions:

## Context relevance

Did the system retrieve useful personal context?

## Noise

How much irrelevant personal information was inserted?

## Token efficiency

How many tokens were required to produce the personalization benefit?

## Provenance

Can every material claim be traced?

## Memory precision

How many stored memories were actually stable/useful?

## Preference adaptation

Can preferences change when behavior changes?

## Temporal correctness

Does the system distinguish old/current facts?

## Permission correctness

Can disabled modules leak into context?

## Backend portability

Can Mem0/Graphiti/builtin be changed without losing canonical user data?

## Source update correctness

Does changing one source update only affected facts?

## Plugin conformance

Can third-party plugins safely satisfy the common contract?

---

# 47. Product Success Metrics

Initial metrics should include:

```text
Time to First Useful Personalization
setup completion rate
number of required user decisions
cold-start processing cost
context tokens per personalized task
retrieval precision
unsupported-profile-claim rate
provenance coverage
manual correction rate
memory acceptance/rejection rate
plugin install success rate
Agent setup success rate
```

Qualitative north-star signal:

> Users stop repeatedly explaining themselves to their Agent.

---

# 48. MVP Scope

## MVP / Milestone 1 — Portable Personal Context Core

Deliver:

```text
canonical schema
Profile modules
module permissions
facts/provenance
Folder Source
MarginNote Source
GitHub Standard Source
Builtin Memory
SQLite/FTS retrieval
Progressive Disclosure
MCP
CLI
English
Simplified Chinese
Starter Lite Recipe
Researcher Recipe
Plugin metadata spec
Plugin Advisor basic flow
Claude Code adapter
Codex adapter
development harness
tests
```

Goal:

> The maintainer can actually use it daily.

## Milestone 2 — Daily Driver

Add:

```text
Mem0 provider
hybrid retrieval
Obsidian source
Obsidian interface/plugin MVP
GitHub Deep mode
automatic Profile promotion
review workflow
Personal Memory Recipe
maintainer's full personal setup
```

## Milestone 3 — Ecosystem

Add:

```text
Graphiti provider
LlamaIndex retrieval integration
plugin scaffold/template
community plugin registry
advanced Recipes
more source providers
visual plugin marketplace/catalog
```

## Milestone 4 — Public Growth

Add:

```text
polished docs site
demo media
benchmarks
public roadmap
MCP registry/distribution where suitable
community showcases
regular releases
ecosystem metrics
```

---

# 49. Explicit Non-Goals for MVP

Do NOT initially build:

```text
a full Notion replacement
a full Obsidian replacement
a giant web dashboard
a social network
a proprietary vector database
a proprietary graph database
a new LLM framework
a universal RAG platform
a cloud SaaS control plane
```

The project's moat is:

> **Personal context orchestration + portable profile + memory integration + progressive personalization.**

Not infrastructure reinvention.

---

# 50. First-Time Agent Installation Experience

Ideal UX:

User:

> “Install this repo for me.”

Agent:

```text
1. asks language
2. inspects repository instructions
3. checks environment
4. asks what sources user already has
5. optionally offers source discovery
6. asks desired memory experience in plain language
7. asks privacy preference
8. detects Agent hosts
9. selects Recipe
10. shows:
    - plugins
    - why
    - API keys
    - setup minutes
    - privacy
    - tradeoffs
11. asks one final confirmation
12. installs
13. validates
14. performs smoke test
15. shows where the user's Profile Vault lives
```

Advanced users may open:

```text
Advanced configuration
```

and override every provider.

---

# 51. Mandatory Implementation Sequence for Claude Code

Before writing production code, the first development Agent must:

```text
1. Read this PRD completely.
2. Inspect current Mem0 repository structure and onboarding UX.
3. Inspect LlamaIndex integration architecture.
4. Inspect Graphiti's current data model/API.
5. Inspect current MCP SDK/version.
6. Inspect Claude Code + Codex project-instruction mechanisms.
7. Produce architecture ADR proposals.
8. Produce MVP dependency graph.
9. Produce implementation plan with milestones.
10. Identify assumptions requiring proof-of-concept spikes.
11. Only then start implementation.
```

The implementation plan should clearly distinguish:

```text
must-have MVP
dogfooding feature
architecture seam
future extension
nice-to-have
```

Do not implement the entire future architecture in advance.

---

# 52. Final Product Principle

The user owns:

```text
their Profile
their Memory
their Evidence
their Sources
their History
their Provider choices
```

The framework owns only:

> the protocol for turning those assets into excellent personal context.

A successful implementation should feel less like:

> “I installed another knowledge-management system.”

and more like:

> “My Agents finally understand me, and I still own everything they know about me.”
