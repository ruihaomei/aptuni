"""Versioned plugin manifest and recipe schemas (PRD §12, §29; ADR-0002, ADR-0014).

A manifest describes a plugin for the Advisor; it is metadata, never a sandbox or an activation.
``maturity`` is honest: ``builtin`` ships and is supported; ``preview`` has code in the tree but is
held behind an evidence gate; ``planned`` does not exist yet. The Advisor selects only ``builtin``.
Text fields are i18n message keys so every locale renders the same catalog.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Category = Literal["source", "memory", "retrieval", "agent", "interface"]
Maturity = Literal["builtin", "preview", "planned"]
Egress = Literal["none", "source_origin", "host_model", "cloud_api"]
Difficulty = Literal["easy", "moderate", "advanced"]

PLUGIN_ID = r"^(source|memory|retrieval|agent|interface)\.[a-z0-9_]+$"
RECIPE_ID = r"^[a-z0-9]+(-[a-z0-9]+)*$"
MESSAGE_KEY = r"^[a-z0-9_.-]+$"
ENV_NAME = r"^[A-Z][A-Z0-9_]*$"
ORIGIN = r"^https://[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$"


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ApiKeyRef(_Frozen):
    """An environment-variable reference; the secret itself is never stored in the catalog or Vault."""

    env: str = Field(pattern=ENV_NAME)
    required: bool
    purpose: str = Field(pattern=MESSAGE_KEY)


class Requirements(_Frozen):
    docker: bool
    local_only_supported: bool
    network: tuple[str, ...] = Field(default=(), description="exact HTTPS origins contacted")
    api_keys: tuple[ApiKeyRef, ...] = ()

    @model_validator(mode="after")
    def _origins(self) -> Requirements:
        if any(not re.fullmatch(ORIGIN, origin) for origin in self.network):
            raise ValueError("network entries must be exact https origins")
        return self


class SetupEffort(_Frozen):
    min_minutes: int = Field(ge=0, le=240)
    max_minutes: int = Field(ge=0, le=240)
    difficulty: Difficulty

    @model_validator(mode="after")
    def _ordered(self) -> SetupEffort:
        if self.min_minutes > self.max_minutes:
            raise ValueError("min_minutes must not exceed max_minutes")
        return self


class PluginManifest(_Frozen):
    schema_version: Literal[1]
    id: str = Field(pattern=PLUGIN_ID)
    category: Category
    contract_version: int = Field(ge=1)
    maturity: Maturity
    milestone: str = Field(pattern=r"^M[0-9]+$")
    name: str = Field(pattern=MESSAGE_KEY)
    summary: str = Field(pattern=MESSAGE_KEY)
    capabilities: dict[str, bool] = Field(default_factory=dict)
    requirements: Requirements
    setup: SetupEffort
    egress: tuple[Egress, ...]
    retention: Literal["none", "source_minimized", "canonical", "provider_managed"]
    strengths: tuple[str, ...] = ()
    weaknesses: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _consistent(self) -> PluginManifest:
        if self.id.split(".", 1)[0] != self.category:
            raise ValueError("plugin id prefix must equal its category")
        if not self.egress:
            raise ValueError("egress must be declared (use 'none')")
        if "none" in self.egress and len(self.egress) > 1:
            raise ValueError("'none' egress cannot be combined")
        if "cloud_api" in self.egress and self.requirements.local_only_supported:
            raise ValueError("cloud_api egress cannot claim local-only support")
        if {"source_origin", "cloud_api"} & set(self.egress) and not self.requirements.network:
            raise ValueError("networked egress must declare its exact origins")
        return self

    def message_keys(self) -> set[str]:
        keys = {self.name, self.summary, *self.strengths, *self.weaknesses}
        keys.update(key.purpose for key in self.requirements.api_keys)
        return keys


class Recipe(_Frozen):
    """A coherent plugin combination; sources and host adapters come from the user's answers."""

    schema_version: Literal[1]
    id: str = Field(pattern=RECIPE_ID)
    name: str = Field(pattern=MESSAGE_KEY)
    goal: str = Field(pattern=MESSAGE_KEY)
    plugins: tuple[str, ...] = Field(min_length=1)
    later: tuple[str, ...] = Field(default=(), description="plugins this recipe adds once they ship")
    suggested_sources: tuple[str, ...] = ()

    def message_keys(self) -> set[str]:
        return {self.name, self.goal}
