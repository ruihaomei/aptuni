"""Small dependency-free starter scaffold for an external Aptuni plugin."""

from __future__ import annotations

import json
import re
from pathlib import Path

from aptuni.api.v1.errors import AptuniAPIError
from aptuni.api.v1.manifest import PluginManifest


def scaffold_plugin(target: Path, *, plugin_id: str, name: str) -> tuple[Path, ...]:
    """Create a reviewable public-API-only starter. It never creates a Vault or grant."""
    package = plugin_id.rsplit(".", 1)[-1].replace("-", "_")
    if re.fullmatch(r"[a-z][a-z0-9_]*", package) is None:
        raise AptuniAPIError("invalid_plugin_package", "The plugin id must end in a valid Python package name.")
    manifest = PluginManifest(
        schema_version=1, contract="aptuni.plugin@1", id=plugin_id, name=name, version="0.1.0",
        api_version="v1", entry_point=f"{package}.plugin:create_plugin",
        capabilities=("context.read",), modules=("knowledge",), egress=("none",), retention="none",
    )
    destination = target.expanduser().resolve(strict=False)
    if target.is_symlink() or (destination.exists() and (not destination.is_dir() or any(destination.iterdir()))):
        raise AptuniAPIError("plugin_scaffold_target_not_empty", "Choose an absent or empty regular directory.")
    values = {
        "README.md": (
            f"# {name}\n\nA local Aptuni plugin using only `aptuni.api.v1`.\n\n"
            "Create an owner grant before connecting; the manifest grants nothing by itself.\n"
        ),
        "aptuni-plugin.toml": (
            'schema_version = 1\ncontract = "aptuni.plugin@1"\n'
            f'id = "{manifest.id}"\nname = {json.dumps(manifest.name, ensure_ascii=False)}\nversion = "0.1.0"\n'
            f'api_version = "v1"\nentry_point = "{manifest.entry_point}"\n'
            'capabilities = ["context.read"]\nmodules = ["knowledge"]\n'
            'egress = ["none"]\nretention = "none"\n'
        ),
        "pyproject.toml": (
            "[build-system]\nrequires = [\"hatchling\"]\nbuild-backend = \"hatchling.build\"\n\n"
            f"[project]\nname = \"{plugin_id.replace('_', '-')}\"\nversion = \"0.1.0\"\n"
            "requires-python = \">=3.13\"\ndependencies = [\"aptuni>=0.1,<0.2\"]\n\n"
            f"[project.entry-points.\"aptuni.plugins.v1\"]\n{package} = \"{manifest.entry_point}\"\n"
        ),
        f"src/{package}/__init__.py": "\"\"\"Plugin package.\"\"\"\n",
        f"src/{package}/plugin.py": (
            "from __future__ import annotations\n\nfrom aptuni.api.v1 import AptuniAPI\n\n\n"
            "class Plugin:\n    def __init__(self, api: AptuniAPI) -> None:\n        self.api = api\n\n"
            "    def run(self, query: str):\n"
            "        return self.api.query_context(query, modules=(\"knowledge\",))\n\n\n"
            "def create_plugin(api: AptuniAPI) -> Plugin:\n    return Plugin(api)\n"
        ),
        "tests/test_plugin.py": (
            "def test_plugin_contract_placeholder() -> None:\n"
            "    # Replace with a fake public API or an owner-granted integration fixture.\n"
            "    assert True\n"
        ),
    }
    written: list[Path] = []
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    for relative, content in values.items():
        path = destination / relative
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return tuple(written)
