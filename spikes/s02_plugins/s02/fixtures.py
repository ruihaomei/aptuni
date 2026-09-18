"""Fixture plugin distributions for S02, built offline as wheels (no build backend download).

Every provider module writes a marker file on import so tests can prove that discovery never
executes plugin code.
"""

from __future__ import annotations

import base64
import hashlib
import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

GROUP = "personal_context_core.providers"
CONTRACT = "source/1"

MARKER_CODE = (
    "import os, pathlib\n"
    "_d = os.environ.get('S02_MARKER_DIR')\n"
    "if _d:\n"
    "    pathlib.Path(_d, __name__).write_text('imported')\n"
)

PROVIDER_CODE = MARKER_CODE + (
    "\nclass Provider:\n"
    "    def probe(self):\n"
    "        return {'items': 1}\n"
)

SNEAKY_CODE = MARKER_CODE + (
    "\nimport socket\n\n"
    "class Provider:\n"
    "    def probe(self):\n"
    "        s = socket.socket()\n"
    "        s.settimeout(0.2)\n"
    "        try:\n"
    "            s.connect(('127.0.0.1', 9))\n"
    "        except OSError:\n"
    "            pass\n"
    "        finally:\n"
    "            s.close()\n"
    "        return {'items': 1}\n"
)

BROKEN_CODE = MARKER_CODE + "\nraise RuntimeError('fixture: broken at import')\n"


@dataclass(frozen=True)
class FixtureDist:
    name: str
    version: str
    package: str
    modules: dict[str, str]
    manifest: dict[str, object] | None
    requires: tuple[str, ...] = ()
    entry_points: dict[str, str] = field(default_factory=dict)


def _manifest(plugin_id: str, *, contract: str = CONTRACT, network: str = "none") -> dict[str, object]:
    return {
        "id": plugin_id, "category": "source", "contract": contract, "maturity": "experimental",
        "capabilities": ["enumerate"], "requirements": {"network": network, "api_keys": []},
        "privacy": {"data_leaves_device": "never" if network == "none" else "optional"},
        "setup_minutes": {"min": 1, "max": 2},
    }


def fixture_dists(dep_version: str = "1.0.0") -> list[FixtureDist]:
    """Return all fixture distributions; ``dep_version`` lets tests simulate transitive drift."""
    ep = "{pkg}.provider:Provider"
    return [
        FixtureDist("pcx-fixture-dep", dep_version, "pcx_fixture_dep",
                    {"__init__.py": f"VERSION = {dep_version!r}\n"}, None),
        FixtureDist("pcx-fixture-good", "1.0.0", "pcx_fixture_good",
                    {"__init__.py": "", "provider.py": PROVIDER_CODE + "\nimport pcx_fixture_dep\n"},
                    _manifest("source.fixture_good"), requires=("pcx-fixture-dep>=1",),
                    entry_points={"fixture_good": ep.format(pkg="pcx_fixture_good")}),
        FixtureDist("pcx-fixture-dup", "1.0.0", "pcx_fixture_dup",
                    {"__init__.py": "", "provider.py": PROVIDER_CODE},
                    _manifest("source.fixture_good"),
                    entry_points={"fixture_dup": ep.format(pkg="pcx_fixture_dup")}),
        FixtureDist("pcx-fixture-broken", "1.0.0", "pcx_fixture_broken",
                    {"__init__.py": "", "provider.py": BROKEN_CODE},
                    _manifest("source.fixture_broken"),
                    entry_points={"fixture_broken": ep.format(pkg="pcx_fixture_broken")}),
        FixtureDist("pcx-fixture-future", "1.0.0", "pcx_fixture_future",
                    {"__init__.py": "", "provider.py": PROVIDER_CODE},
                    _manifest("source.fixture_future", contract="source/2"),
                    entry_points={"fixture_future": ep.format(pkg="pcx_fixture_future")}),
        FixtureDist("pcx-fixture-sneaky", "1.0.0", "pcx_fixture_sneaky",
                    {"__init__.py": "", "provider.py": SNEAKY_CODE},
                    _manifest("source.fixture_sneaky", network="none"),
                    entry_points={"fixture_sneaky": ep.format(pkg="pcx_fixture_sneaky")}),
    ]


def _record_hash(data: bytes) -> str:
    return "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()


def build_wheel(dist: FixtureDist, out_dir: Path) -> Path:
    """Write a minimal PEP 427 wheel for ``dist`` and return its path."""
    stem = f"{dist.name.replace('-', '_')}-{dist.version}"
    info = f"{stem}.dist-info"
    files: dict[str, bytes] = {f"{dist.package}/{name}": code.encode() for name, code in dist.modules.items()}
    if dist.manifest is not None:
        files[f"{dist.package}/plugin_manifest.json"] = json.dumps(dist.manifest, indent=1).encode()
    metadata = [f"Metadata-Version: 2.1", f"Name: {dist.name}", f"Version: {dist.version}"]
    metadata += [f"Requires-Dist: {req}" for req in dist.requires]
    files[f"{info}/METADATA"] = ("\n".join(metadata) + "\n").encode()
    files[f"{info}/WHEEL"] = b"Wheel-Version: 1.0\nGenerator: s02-fixtures\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
    if dist.entry_points:
        lines = [f"[{GROUP}]"] + [f"{k} = {v}" for k, v in dist.entry_points.items()]
        files[f"{info}/entry_points.txt"] = ("\n".join(lines) + "\n").encode()
    record = [f"{path},{_record_hash(data)},{len(data)}" for path, data in files.items()]
    record.append(f"{info}/RECORD,,")
    files[f"{info}/RECORD"] = ("\n".join(record) + "\n").encode()
    out_dir.mkdir(parents=True, exist_ok=True)
    wheel = out_dir / f"{stem}-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, data in files.items():
            archive.writestr(path, data)
    return wheel
