from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from aptuni.api.v1 import PluginManifest, load_manifest


def manifest(**updates: object) -> PluginManifest:
    value: dict[str, object] = {
        "schema_version": 1,
        "contract": "aptuni.plugin@1",
        "id": "dev.aptuni.top_down_learning",
        "name": "Top-Down Learning",
        "version": "0.1.0",
        "api_version": "v1",
        "entry_point": "top_down_learning.plugin:create_plugin",
        "capabilities": ("context.read", "evidence.read", "memory.propose"),
        "modules": ("knowledge", "skills", "goals", "preferences", "projects"),
        "egress": ("none",),
        "retention": "canonical_proposals",
    }
    value.update(updates)
    return PluginManifest.model_validate(value)


def test_manifest_is_strict_versioned_and_has_stable_digest(tmp_path: Path) -> None:
    first = manifest()
    assert first.digest().startswith("sha256:")
    with pytest.raises(ValidationError):
        manifest(extra_field=True)
    with pytest.raises(ValidationError):
        manifest(capabilities=("context.read", "context.read"))
    with pytest.raises(ValidationError):
        manifest(modules=("knowledge", "knowledge"))
    with pytest.raises(ValidationError):
        manifest(capabilities=("vault.read",))
    with pytest.raises(ValidationError):
        manifest(api_version="v2")

    path = tmp_path / "aptuni-plugin.toml"
    path.write_text(
        """schema_version = 1
contract = "aptuni.plugin@1"
id = "dev.aptuni.top_down_learning"
name = "Top-Down Learning"
version = "0.1.0"
api_version = "v1"
entry_point = "top_down_learning.plugin:create_plugin"
capabilities = ["context.read"]
modules = ["knowledge"]
egress = ["none"]
retention = "none"
""",
        encoding="utf-8",
    )
    assert load_manifest(path).id == "dev.aptuni.top_down_learning"


def test_manifest_retention_and_egress_are_honest() -> None:
    with pytest.raises(ValidationError):
        manifest(capabilities=("memory.propose",), retention="none")
    with pytest.raises(ValidationError):
        manifest(capabilities=("context.read",), retention="canonical_proposals")
    with pytest.raises(ValidationError):
        manifest(egress=("none", "cloud_api"))
    with pytest.raises(ValidationError):
        manifest(capabilities=("evidence.read",), retention="none")
    with pytest.raises(ValidationError):
        manifest(capabilities=("profile.read",), modules=("knowledge",), retention="none")
