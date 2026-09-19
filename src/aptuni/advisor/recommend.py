"""Pure Plugin Advisor recommendation (PRD §26–§30; plan 02 TDD step 2).

Users choose experiences; the Advisor chooses implementations. It never selects a ``planned``
plugin: an unavailable wish is *deferred* with a reason, and the closest installable recipe is
recommended instead. The function has no side effects; applying a recommendation is a separate,
confirmed step (ADR-0013).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Literal

from aptuni.advisor.catalog import Catalog
from aptuni.advisor.manifest import ApiKeyRef
from aptuni.i18n import LOCALES

SOURCE_KINDS = ("folder", "application_materials", "github", "marginnote", "obsidian", "notion", "zotero", "other")
MEMORY_EXPERIENCES = ("basic", "automatic", "temporal")
PRIVACY_MODES = ("quality", "minimize_cloud", "local_only")
HOSTS = ("claude_code", "codex", "cursor", "claude_desktop")

SOURCE_PLUGIN = {"folder": "source.folder", "application_materials": "source.folder", "github": "source.github",
                 "marginnote": "source.marginnote", "obsidian": "source.obsidian", "notion": "source.notion",
                 "zotero": "source.zotero"}
RESEARCH_SOURCES = frozenset({"github", "marginnote", "obsidian", "zotero"})
EXPERIENCE_RECIPE = {"automatic": "personal-memory", "temporal": "temporal-memory"}
FIRST_CLASS_HOSTS = ("claude_code", "codex")
DIFFICULTY_ORDER = ("easy", "moderate", "advanced")

HostRelease = Literal["allowed_with_disclosure", "refused_local_only", "no_host"]


class AdvisorError(ValueError):
    """The answers are outside the supported vocabulary (fixed code, no user text echoed)."""


@dataclass(frozen=True)
class SetupAnswers:
    locale: str
    sources: frozenset[str]
    memory: str
    privacy: str
    hosts: frozenset[str]

    def validate(self) -> None:
        checks = [(self.locale in LOCALES, "locale"), (self.memory in MEMORY_EXPERIENCES, "memory"),
                  (self.privacy in PRIVACY_MODES, "privacy"), (self.sources <= set(SOURCE_KINDS), "sources"),
                  (self.hosts <= set(HOSTS), "hosts")]
        for ok, name in checks:
            if not ok:
                raise AdvisorError(f"invalid_answer:{name}")


@dataclass(frozen=True)
class Choice:
    plugin_id: str
    reason: str  # i18n message key


@dataclass(frozen=True)
class Recommendation:
    recipe_id: str
    requested_recipe_id: str
    selected: tuple[Choice, ...]
    deferred: tuple[Choice, ...]
    required_api_keys: tuple[ApiKeyRef, ...]
    optional_api_keys: tuple[ApiKeyRef, ...]
    setup_minutes: tuple[int, int]
    docker: bool
    egress: tuple[str, ...]
    network: tuple[str, ...]
    host_release: HostRelease
    host_file_access: bool
    difficulty: str
    retention: tuple[str, ...]
    notes: tuple[str, ...]
    strengths: tuple[str, ...]
    weaknesses: tuple[str, ...]
    digest: str = field(default="")

    def to_dict(self) -> dict[str, Any]:
        return {
            "recipe_id": self.recipe_id, "requested_recipe_id": self.requested_recipe_id,
            "selected": [[c.plugin_id, c.reason] for c in self.selected],
            "deferred": [[c.plugin_id, c.reason] for c in self.deferred],
            "required_api_keys": [key.env for key in self.required_api_keys],
            "optional_api_keys": [key.env for key in self.optional_api_keys],
            "setup_minutes": list(self.setup_minutes), "docker": self.docker, "egress": list(self.egress),
            "network": list(self.network), "host_release": self.host_release,
            "host_file_access": self.host_file_access, "difficulty": self.difficulty,
            "retention": list(self.retention), "notes": list(self.notes),
            "strengths": list(self.strengths), "weaknesses": list(self.weaknesses),
        }


def _digest(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


def _base_recipe(answers: SetupAnswers) -> str:
    rich = bool(answers.sources & RESEARCH_SOURCES) or len(answers.sources - {"other"}) >= 2
    return "researcher" if rich else "starter-lite"


class _Builder:
    def __init__(self, catalog: Catalog, local_only: bool) -> None:
        self.catalog = catalog
        self.local_only = local_only
        self.host_file_access = False
        self.selected: dict[str, Choice] = {}
        self.deferred: dict[str, Choice] = {}
        self.notes: list[str] = []

    def want(self, plugin_id: str, reason: str) -> None:
        plugin = self.catalog.plugins.get(plugin_id)
        if plugin is None:
            self.deferred.setdefault(plugin_id, Choice(plugin_id, "advisor.reason.no_provider"))
        elif plugin.maturity == "planned":
            self.deferred.setdefault(plugin_id, Choice(plugin_id, "advisor.reason.planned"))
        elif plugin.maturity == "preview":
            self.deferred.setdefault(plugin_id, Choice(plugin_id, "advisor.reason.evidence_gate"))
        elif self.local_only and not plugin.requirements.local_only_supported:
            self.deferred.setdefault(plugin_id, Choice(plugin_id, "advisor.reason.excluded_privacy"))
        else:
            self.selected.setdefault(plugin_id, Choice(plugin_id, reason))


def recommend(answers: SetupAnswers, catalog: Catalog) -> Recommendation:
    """Recommend an installable recipe plus the plugins the user's answers call for."""
    answers.validate()
    base = _base_recipe(answers)
    requested = EXPERIENCE_RECIPE.get(answers.memory, base)
    builder = _Builder(catalog, answers.privacy == "local_only")
    recipe_id = requested if requested in catalog.recipes and catalog.recipe_available(requested) else base
    if recipe_id != requested:
        builder.notes.append("advisor.note.recipe_deferred")
    if recipe_id != requested and requested in catalog.recipes:
        for plugin_id in catalog.recipes[requested].plugins:
            if catalog.plugins[plugin_id].maturity != "builtin":
                builder.want(plugin_id, "advisor.reason.recipe_core")
    recipe = catalog.recipes[recipe_id]
    for plugin_id in (*recipe.plugins, *recipe.later):
        builder.want(plugin_id, "advisor.reason.recipe_core")
    for kind in sorted(answers.sources):
        if kind == "other":
            builder.notes.append("advisor.note.other_source")
        else:
            builder.want(SOURCE_PLUGIN[kind], "advisor.reason.named_source")
    release = _hosts(builder, answers)
    return _finish(builder, recipe_id, requested, release)


def _hosts(builder: _Builder, answers: SetupAnswers) -> HostRelease:
    """Select host adapters. Local-only privacy defers them: every shipped adapter needs host-model
    egress (ADR-0013), and a named shell-capable host can still read the Vault with its own tools."""
    builder.host_file_access = bool(answers.hosts & {*FIRST_CLASS_HOSTS, "cursor"})
    for host in sorted(answers.hosts):
        plugin_id = f"agent.{host}"
        if host not in FIRST_CLASS_HOSTS:
            builder.want(plugin_id, "advisor.reason.detected_host")
            builder.deferred[plugin_id] = Choice(plugin_id, "advisor.reason.protocol_only")
        elif builder.local_only:
            builder.deferred[plugin_id] = Choice(plugin_id, "advisor.reason.adapter_needs_egress")
        else:
            builder.want(plugin_id, "advisor.reason.detected_host")
    has_host = any(f"agent.{host}" in builder.selected for host in FIRST_CLASS_HOSTS)
    if not has_host:
        builder.selected.pop("agent.mcp", None)
        if builder.local_only and answers.hosts & set(FIRST_CLASS_HOSTS):
            builder.notes.append("advisor.note.local_only_hosts")
            return "refused_local_only"
        builder.notes.append("advisor.note.cli_only")
        return "no_host"
    builder.want("agent.mcp", "advisor.reason.recipe_core")
    if answers.privacy == "minimize_cloud":
        builder.notes.append("advisor.note.minimize_cloud")
    return "allowed_with_disclosure"


def _finish(builder: _Builder, recipe_id: str, requested: str, release: HostRelease) -> Recommendation:
    catalog = builder.catalog
    plugins = [catalog.plugins[pid] for pid in sorted(builder.selected)]
    keys = {key.env: key for plugin in plugins for key in plugin.requirements.api_keys}
    egress = {e for plugin in plugins for e in plugin.egress if e != "none"}
    if release != "allowed_with_disclosure":
        egress.discard("host_model")
    rec = Recommendation(
        recipe_id=recipe_id, requested_recipe_id=requested,
        selected=tuple(builder.selected[pid] for pid in sorted(builder.selected)),
        deferred=tuple(builder.deferred[pid] for pid in sorted(builder.deferred)),
        required_api_keys=tuple(keys[k] for k in sorted(keys) if keys[k].required),
        optional_api_keys=tuple(keys[k] for k in sorted(keys) if not keys[k].required),
        setup_minutes=(sum(p.setup.min_minutes for p in plugins), sum(p.setup.max_minutes for p in plugins)),
        docker=any(p.requirements.docker for p in plugins), egress=tuple(sorted(egress)),
        network=tuple(sorted({o for p in plugins for o in p.requirements.network})), host_release=release,
        host_file_access=builder.host_file_access,
        difficulty=max((p.setup.difficulty for p in plugins), key=DIFFICULTY_ORDER.index, default="easy"),
        retention=tuple(sorted({p.retention for p in plugins} - {"none"})),
        notes=tuple(dict.fromkeys(builder.notes)),
        strengths=tuple(dict.fromkeys(s for p in plugins for s in p.strengths)),
        weaknesses=tuple(dict.fromkeys(w for p in plugins for w in p.weaknesses)),
    )
    return Recommendation(**{**rec.__dict__, "digest": _digest(rec.to_dict())})
