"""Load and cross-check the bundled plugin catalog and recipes (one TOML file per entry).

Community contributors add one file under ``plugins/`` or ``recipes/``; the loader rejects
duplicates, unknown references and invalid manifests with fixed error codes that never echo file
content.
"""

from __future__ import annotations

import hashlib
import json
import tomllib
from dataclasses import dataclass
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path

from pydantic import ValidationError

from aptuni.advisor.manifest import PluginManifest, Recipe


class CatalogError(ValueError):
    """The catalog is invalid; the message is a fixed code plus the offending file name."""


@dataclass(frozen=True)
class Catalog:
    plugins: dict[str, PluginManifest]
    recipes: dict[str, Recipe]

    def recipe_available(self, recipe_id: str) -> bool:
        """A recipe is installable only when every required plugin is shipped and supported."""
        recipe = self.recipes[recipe_id]
        return all(self.plugins[pid].maturity == "builtin" for pid in recipe.plugins)

    def version_digest(self) -> str:
        """A stable identifier for exactly this catalog, so a confirmation cannot outlive it."""
        body = json.dumps(
            {
                "plugins": {
                    pid: plugin.model_dump(mode="json")
                    for pid, plugin in sorted(self.plugins.items())
                },
                "recipes": {
                    rid: recipe.model_dump(mode="json")
                    for rid, recipe in sorted(self.recipes.items())
                },
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]

    def message_keys(self) -> set[str]:
        keys: set[str] = set()
        for plugin in self.plugins.values():
            keys |= plugin.message_keys()
        for recipe in self.recipes.values():
            keys |= recipe.message_keys()
        return keys


def _entries(root: Traversable, folder: str) -> list[tuple[str, dict[str, object]]]:
    directory = root.joinpath(folder)
    if not directory.is_dir():
        raise CatalogError(f"catalog_folder_missing:{folder}")
    loaded: list[tuple[str, dict[str, object]]] = []
    for entry in sorted(directory.iterdir(), key=lambda item: item.name):
        if not entry.name.endswith(".toml"):
            continue
        try:
            loaded.append((entry.name, tomllib.loads(entry.read_text(encoding="utf-8"))))
        except (tomllib.TOMLDecodeError, UnicodeDecodeError, RecursionError) as error:
            raise CatalogError(f"malformed_toml:{folder}/{entry.name}") from error
    return loaded


def load_catalog(root: Path | None = None) -> Catalog:
    """Load the bundled catalog, or a catalog rooted at ``root`` (tests, local development)."""
    base: Traversable = resources.files("aptuni.advisor").joinpath("catalog") if root is None else root
    plugins: dict[str, PluginManifest] = {}
    for name, data in _entries(base, "plugins"):
        try:
            plugin = PluginManifest.model_validate(data)
        except ValidationError as error:
            raise CatalogError(f"invalid_manifest:plugins/{name}") from error
        if plugin.id in plugins:
            raise CatalogError(f"duplicate_plugin:{plugin.id}")
        plugins[plugin.id] = plugin
    recipes: dict[str, Recipe] = {}
    for name, data in _entries(base, "recipes"):
        try:
            recipe = Recipe.model_validate(data)
        except ValidationError as error:
            raise CatalogError(f"invalid_recipe:recipes/{name}") from error
        if recipe.id in recipes:
            raise CatalogError(f"duplicate_recipe:{recipe.id}")
        unknown = [pid for pid in (*recipe.plugins, *recipe.later) if pid not in plugins]
        if unknown:
            raise CatalogError(f"unknown_plugin:{recipe.id}:{','.join(unknown)}")
        recipes[recipe.id] = recipe
    return Catalog(plugins, recipes)
