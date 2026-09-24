"""Strict ``aptuni.plugin@1`` SDK-client manifest."""

from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aptuni.domain.records import Module

Capability = Literal[
    "profile.read", "memory.read", "context.read", "evidence.read", "memory.propose", "memory.review.read",
]
CAPABILITIES: tuple[str, ...] = Capability.__args__  # type: ignore[attr-defined]
PluginEgress = Literal["none", "host_model", "cloud_api", "source_origin"]
PluginRetention = Literal["none", "canonical_proposals"]


class PluginManifest(BaseModel):
    """Requested plugin authority. A manifest is metadata and grants no access by itself."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[1]
    contract: Literal["aptuni.plugin@1"]
    id: str = Field(pattern=r"^[a-z0-9]+(?:[._-][a-z0-9]+)+$")
    name: str = Field(min_length=1, max_length=80)
    version: str = Field(pattern=r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:[-+][0-9A-Za-z.-]+)?$")
    api_version: Literal["v1"]
    entry_point: str = Field(pattern=r"^[a-zA-Z_][a-zA-Z0-9_.]*:[a-zA-Z_][a-zA-Z0-9_]*$")
    capabilities: tuple[Capability, ...] = Field(min_length=1)
    modules: tuple[Module, ...] = Field(min_length=1)
    egress: tuple[PluginEgress, ...] = Field(min_length=1)
    retention: PluginRetention

    @model_validator(mode="after")
    def _coherent(self) -> PluginManifest:
        if len(set(self.capabilities)) != len(self.capabilities):
            raise ValueError("capabilities must be unique")
        if len(set(self.modules)) != len(self.modules):
            raise ValueError("modules must be unique")
        if len(set(self.egress)) != len(self.egress):
            raise ValueError("egress declarations must be unique")
        if "none" in self.egress and len(self.egress) != 1:
            raise ValueError("none egress cannot be combined")
        proposes = "memory.propose" in self.capabilities
        if proposes != (self.retention == "canonical_proposals"):
            raise ValueError("canonical_proposals retention is required exactly when memory.propose is requested")
        if "evidence.read" in self.capabilities and "context.read" not in self.capabilities:
            raise ValueError("evidence.read requires context.read")
        if "profile.read" in self.capabilities and "identity" not in self.modules:
            raise ValueError("profile.read requires the identity module")
        return self

    def digest(self) -> str:
        value = json.dumps(self.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_manifest(path: Path) -> PluginManifest:
    """Load one regular UTF-8 TOML file. Symlinks are refused at the authorization boundary."""
    if path.is_symlink() or not path.is_file():
        raise ValueError("plugin manifest must be a regular file")
    return PluginManifest.model_validate(tomllib.loads(path.read_text(encoding="utf-8")))
