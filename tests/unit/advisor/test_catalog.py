"""Plugin manifests and recipes: versioned, cross-checked, and honest about maturity (ADR-0014)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aptuni.advisor.catalog import CatalogError, load_catalog
from aptuni.i18n import LOCALES, has_message

PLUGIN = """
schema_version = 1
id = "source.folder"
category = "source"
contract_version = 1
maturity = "builtin"
milestone = "M1"
name = "plugin.source.folder.name"
summary = "plugin.source.folder.summary"
egress = ["none"]
retention = "source_minimized"
strengths = ["plugin.source.folder.strength"]
weaknesses = ["plugin.source.folder.weakness"]

[capabilities]
incremental_sync = true

[requirements]
docker = false
local_only_supported = true
network = []

[setup]
min_minutes = 1
max_minutes = 3
difficulty = "easy"
"""

RECIPE = """
schema_version = 1
id = "starter-lite"
name = "recipe.starter-lite.name"
goal = "recipe.starter-lite.goal"
plugins = ["source.folder"]
"""


def _write(root: Path, plugin: str = PLUGIN, recipe: str = RECIPE) -> Path:
    (root / "plugins").mkdir(parents=True)
    (root / "recipes").mkdir()
    (root / "plugins" / "one.toml").write_text(plugin, encoding="utf-8")
    (root / "recipes" / "one.toml").write_text(recipe, encoding="utf-8")
    return root


def test_bundled_catalog_is_valid_and_contains_m1_recipes() -> None:
    catalog = load_catalog()
    assert {"starter-lite", "researcher"} <= set(catalog.recipes)
    assert catalog.recipe_available("starter-lite")
    assert catalog.recipe_available("researcher")
    for recipe_id in ("personal-memory", "temporal-memory"):
        assert not catalog.recipe_available(recipe_id), "planned backends must not look installable"


def test_bundled_catalog_matches_shipped_code() -> None:
    catalog = load_catalog()
    builtin = {pid for pid, plugin in catalog.plugins.items() if plugin.maturity == "builtin"}
    assert builtin == {"source.folder", "source.github", "source.marginnote", "memory.builtin",
                       "retrieval.sqlite_fts", "agent.mcp", "agent.claude_code", "agent.codex", "interface.cli"}
    for planned in ("memory.mem0", "memory.graphiti", "retrieval.hybrid", "interface.obsidian"):
        assert catalog.plugins[planned].maturity == "planned"


def test_every_catalog_message_exists_in_every_locale() -> None:
    catalog = load_catalog()
    for key in catalog.message_keys():
        for locale in LOCALES:
            assert has_message(key, locale), f"{locale} is missing {key}"


def test_starter_lite_needs_no_key_docker_or_network() -> None:
    catalog = load_catalog()
    for plugin_id in catalog.recipes["starter-lite"].plugins:
        plugin = catalog.plugins[plugin_id]
        assert not plugin.requirements.docker
        assert not [key for key in plugin.requirements.api_keys if key.required]
        assert plugin.requirements.network == ()


def test_duplicate_plugin_ids_are_rejected(tmp_path: Path) -> None:
    root = _write(tmp_path)
    (root / "plugins" / "two.toml").write_text(PLUGIN, encoding="utf-8")
    with pytest.raises(CatalogError, match="duplicate_plugin"):
        load_catalog(root)


def test_recipe_referencing_unknown_plugin_is_rejected(tmp_path: Path) -> None:
    root = _write(tmp_path, recipe=RECIPE.replace("source.folder", "source.nowhere"))
    with pytest.raises(CatalogError, match="unknown_plugin"):
        load_catalog(root)


@pytest.mark.parametrize(("old", "new"), [
    ('id = "source.folder"', 'id = "memory.folder"'),  # id prefix must match category
    ("schema_version = 1\nid", "schema_version = 2\nid"),  # unknown schema version
    ("min_minutes = 1", "min_minutes = 9"),  # min > max
    ("docker = false", "docker = false\nsurprise = true"),  # extra fields forbidden
    ('egress = ["none"]', 'egress = ["cloud_api"]'),  # network egress needs declared origins
    ("network = []", 'network = ["https://-"]'),  # degenerate origin
])
def test_invalid_manifest_is_rejected(tmp_path: Path, old: str, new: str) -> None:
    root = _write(tmp_path, plugin=PLUGIN.replace(old, new, 1))
    with pytest.raises(CatalogError, match="invalid_manifest"):
        load_catalog(root)


def test_malformed_toml_is_rejected_without_echoing_content(tmp_path: Path) -> None:
    root = _write(tmp_path, plugin="secret-token = [")
    with pytest.raises(CatalogError) as caught:
        load_catalog(root)
    assert "secret-token" not in str(caught.value)


def test_pathologically_nested_toml_fails_closed(tmp_path: Path) -> None:
    root = _write(tmp_path, plugin="x = " + "[" * 5000 + "]" * 5000)
    with pytest.raises(CatalogError):
        load_catalog(root)


def test_catalog_digest_covers_manifest_content_not_only_ids_and_maturity(tmp_path: Path) -> None:
    first = load_catalog(_write(tmp_path / "first"))
    changed = PLUGIN.replace('retention = "source_minimized"', 'retention = "canonical"')
    second = load_catalog(_write(tmp_path / "second", plugin=changed))

    assert first.version_digest() != second.version_digest()
