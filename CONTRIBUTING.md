# Contributing to Aptuni

Thank you for helping make personal context more useful and more trustworthy. Aptuni is pre-alpha,
so small, focused contributions are easiest to land.

## Ways to help

| You want to… | Start here |
|---|---|
| Report a bug | Open an issue with the command, what you expected, and what happened. Never paste private Vault content. |
| Add a plugin to the Advisor catalog | One TOML file in `src/aptuni/advisor/catalog/plugins/` plus its message lines in both `src/aptuni/i18n/messages/en.toml` and `zh-CN.toml` ([ADR-0014](docs/dev/DECISIONS/ADR-0014-plugin-catalog-recipes-and-advisor.md)). |
| Add a Recipe | One TOML file in `src/aptuni/advisor/catalog/recipes/`. A recipe is installable only when every required plugin is `builtin`. |
| Add a source provider | Read [ADR-0006](docs/dev/DECISIONS/ADR-0006-source-snapshots-and-candidate-deltas.md): providers emit immutable snapshots and reviewable candidate deltas; they never write facts directly. |
| Improve a translation | Keys and `{placeholders}` must match across locales; tests enforce it. |
| Report a vulnerability | Do **not** open a public issue; see [SECURITY.md](SECURITY.md). |

## Development setup

```sh
python3.13 -m venv .tools && .tools/bin/pip install uv   # once
.tools/bin/uv sync
.tools/bin/uv run pytest
.tools/bin/uv run ruff check . && .tools/bin/uv run mypy src
python3.13 tools/check_relay.py
```

All four must pass before a pull request is reviewed.

## Ground rules

- **Tests with behavior.** Add a failing test first or together with the change. Cover failure,
  privacy and rebuild paths, not only the happy path.
- **Privacy first.** Fixtures are synthetic or sanitized. Never commit personal data, tokens or
  real Vault content. Error messages use fixed codes and never echo user content.
- **Contracts change through ADRs.** Public schemas, plugin contracts, MCP tool semantics and new
  heavy dependencies need an ADR in `docs/dev/DECISIONS/`.
- **Reuse order:** dependency, then adapter, then clean-room implementation, then direct copy.
  A direct copy needs a license review and an entry in
  [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
- **Evidence, not inflation.** A mention is `exposure`, never expertise. Do not add code that
  infers skill levels from document mentions.
- **Brand.** Before changing the README, docs or UI text, read
  [docs/brand/BRAND_GUIDELINES.md](docs/brand/BRAND_GUIDELINES.md). Aptuni is a personal context
  layer, not a memory database.

## Working with AI coding agents

This repository is built to be continued by Claude Code, Codex and other agents. [AGENTS.md](AGENTS.md)
is the shared contract. [docs/dev/STATE.md](docs/dev/STATE.md) and
[docs/dev/HANDOFF.md](docs/dev/HANDOFF.md) record where work stands, so an agent never needs a
previous chat. Please keep them current when your change moves the project state.

## Commits and pull requests

- Use [Conventional Commits](https://www.conventionalcommits.org/) (`feat(sources): …`, `fix(vault): …`).
- Keep pull requests small and single-purpose. Describe user-visible behavior and how you tested it.
- By contributing you agree that your contribution is licensed under the
  [Apache License 2.0](LICENSE).

## Code of conduct

Participation is governed by the [Code of Conduct](CODE_OF_CONDUCT.md).
