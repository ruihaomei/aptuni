"""Entry-point plugin registry prototype (S02 spike; ADR-0002).

Discovery reads distribution metadata and a manifest file located with ``find_spec`` on the
top-level package, which does not execute plugin code. Activation is explicit, requires an approval
bound to the manifest hash and the complete installed dependency closure, isolates import failures,
and uses an audit hook to *detect* (never contain) undeclared network use during a probe.
"""

from __future__ import annotations

import base64
import hashlib
import importlib.metadata as md
import importlib.util
import json
import re
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GROUP = "personal_context_core.providers"
SUPPORTED_CONTRACTS = frozenset({"source/1"})
REQUIRED_KEYS = ("id", "category", "contract", "maturity", "capabilities", "requirements", "privacy")
TRUST_WARNING = ("Activated plugins run in-process as trusted code with your user privileges; "
                 "manifests are disclosures, not a sandbox.")
NETWORK_WARNING = "Undeclared network use is checked by an audit hook: detection only, not containment."
_NAME_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


@dataclass
class Discovered:
    entry_name: str
    value: str
    dist_name: str
    dist_version: str
    plugin_id: str | None
    manifest: dict[str, Any] | None
    manifest_sha256: str | None
    status: str
    error: str | None


def _normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _read_manifest(value: str) -> tuple[dict[str, Any], str]:
    top = value.split(":", 1)[0].split(".", 1)[0]
    spec = importlib.util.find_spec(top)  # top-level lookup: finds, does not execute
    if spec is None or not spec.submodule_search_locations:
        raise ValueError(f"package {top!r} not found")
    raw = (Path(next(iter(spec.submodule_search_locations))) / "plugin_manifest.json").read_bytes()
    manifest = json.loads(raw)
    missing = [key for key in REQUIRED_KEYS if key not in manifest]
    if missing:
        raise ValueError(f"manifest missing {missing}")
    return manifest, "sha256:" + hashlib.sha256(raw).hexdigest()


def discover(group: str = GROUP) -> list[Discovered]:
    """List installed plugins and their manifests without importing any plugin module."""
    found: list[Discovered] = []
    for ep in md.entry_points(group=group):
        dist = ep.dist
        item = Discovered(ep.name, ep.value, dist.metadata["Name"], dist.version, None, None, None, "ok", None)
        try:
            item.manifest, item.manifest_sha256 = _read_manifest(ep.value)
            item.plugin_id = str(item.manifest["id"])
            if item.manifest["contract"] not in SUPPORTED_CONTRACTS:
                item.status, item.error = "incompatible_contract", f"contract {item.manifest['contract']}"
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            item.status, item.error = "manifest_error", str(exc)
        found.append(item)
    counts: dict[str, int] = {}
    for item in found:
        if item.plugin_id:
            counts[item.plugin_id] = counts.get(item.plugin_id, 0) + 1
    for item in found:
        if item.plugin_id and counts[item.plugin_id] > 1:
            item.status, item.error = "duplicate_id", f"duplicate plugin id {item.plugin_id}"
    return found


# -------------------------------------------------------------------- closure
def _file_hash(path: Path) -> str:
    return "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(path.read_bytes()).digest()).rstrip(b"=").decode()


def _verify_files(dist: md.Distribution) -> list[str]:
    bad = []
    for file in dist.files or ():
        if file.hash is None:
            continue
        path = Path(dist.locate_file(file))
        if not path.exists() or _file_hash(path) != f"{file.hash.mode}={file.hash.value}":
            bad.append(str(file))
    return bad


def closure(dist_name: str) -> list[dict[str, Any]]:
    """Resolve the installed dependency closure and fingerprint every distribution."""
    seen: dict[str, dict[str, Any]] = {}
    queue = [dist_name]
    while queue:
        name = _normalize(queue.pop())
        if name in seen:
            continue
        dist = md.distribution(name)
        requires = [r for r in (dist.requires or []) if "extra ==" not in r]
        record = dist.read_text("RECORD") or ""
        seen[name] = {
            "name": dist.metadata["Name"], "version": dist.version,
            "record_digest": "sha256:" + hashlib.sha256(record.encode()).hexdigest(),
            "requires": requires, "installer": (dist.read_text("INSTALLER") or "").strip(),
            "direct_url": dist.read_text("direct_url.json"), "tampered_files": _verify_files(dist),
        }
        queue.extend(m.group(1) for r in requires if (m := _NAME_RE.match(r)))
    return sorted(seen.values(), key=lambda d: _normalize(d["name"]))


def _fingerprint(entries: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
    return [(_normalize(e["name"]), e["version"], e["record_digest"]) for e in entries]


# -------------------------------------------------------------------- approval / activation
def _by_id(plugin_id: str) -> Discovered | None:
    return next((d for d in discover() if d.plugin_id == plugin_id), None)


def approve(plugin_id: str, approvals_path: Path) -> dict[str, Any]:
    item = _by_id(plugin_id)
    if item is None or item.status != "ok":
        raise ValueError(f"cannot approve {plugin_id}: {item.error if item else 'not installed'}")
    entries = closure(item.dist_name)
    tampered = {e["name"]: e["tampered_files"] for e in entries if e["tampered_files"]}
    if tampered:
        raise ValueError(f"cannot approve {plugin_id}: installed files do not match RECORD {tampered}")
    record = {"plugin_id": plugin_id, "dist": item.dist_name, "manifest_sha256": item.manifest_sha256,
              "closure": [{k: v for k, v in e.items() if k != "tampered_files"} for e in entries],
              "approved_at": datetime.now(timezone.utc).isoformat()}
    approvals = json.loads(approvals_path.read_text(encoding="utf-8")) if approvals_path.exists() else {}
    approvals[plugin_id] = record
    approvals_path.write_text(json.dumps(approvals, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return record


def _check_approval(item: Discovered, approval: dict[str, Any] | None) -> str | None:
    if approval is None:
        return "not approved"
    current = closure(item.dist_name)
    if any(e["tampered_files"] for e in current):
        return "closure drift (installed files differ from RECORD): renewed approval required"
    if item.manifest_sha256 != approval["manifest_sha256"] or _fingerprint(current) != _fingerprint(approval["closure"]):
        return "closure drift (manifest or dependency set changed): renewed approval required"
    return None


def _probe_network(provider: Any) -> list[str]:
    events: list[str] = []
    active = {"on": True}

    def hook(event: str, _args: tuple[Any, ...]) -> None:
        if active["on"] and event.startswith("socket.") and event not in events:
            events.append(event)

    sys.addaudithook(hook)
    try:
        provider.probe()
    finally:
        active["on"] = False
    return events


def activate(plugin_ids: list[str], approvals_path: Path) -> dict[str, Any]:
    approvals = json.loads(approvals_path.read_text(encoding="utf-8")) if approvals_path.exists() else {}
    discovered = discover()
    result: dict[str, Any] = {"active": [], "failed": {}, "warnings": [TRUST_WARNING, NETWORK_WARNING]}
    for plugin_id in plugin_ids:
        matches = [d for d in discovered if d.plugin_id == plugin_id]
        if not matches:
            result["failed"][plugin_id] = "not installed"
            continue
        item = matches[0]
        if item.status != "ok":
            result["failed"][plugin_id] = f"{item.status.replace('_', ' ')}: {item.error}"
            continue
        reason = _check_approval(item, approvals.get(plugin_id))
        if reason:
            result["failed"][plugin_id] = reason
            continue
        try:
            provider = md.EntryPoint(item.entry_name, item.value, GROUP).load()()
        except Exception as exc:  # noqa: BLE001 - plugin failures must be isolated, never fatal
            result["failed"][plugin_id] = f"import failed: {type(exc).__name__}: {exc}"
            continue
        events = _probe_network(provider)
        declared = item.manifest["requirements"].get("network", "none") if item.manifest else "none"
        if events and declared == "none":
            result["failed"][plugin_id] = f"undeclared network use detected during probe: {events}"
            continue
        result["active"].append(plugin_id)
    return result


def isolate_bytecode() -> Path:
    """Point bytecode caching at a fresh core-owned directory.

    pip lists ``.pyc`` files in RECORD without hashes, so a forged ``.pyc`` whose header matches the
    source mtime/size passes RECORD verification and is executed. With ``sys.pycache_prefix`` set,
    installed ``__pycache__`` directories are never read; sources (which RECORD does hash) are
    compiled into the private prefix instead.
    """
    prefix = Path(tempfile.mkdtemp(prefix="pcx-pycache-"))
    sys.pycache_prefix = str(prefix)
    return prefix


def discovered_as_dicts() -> list[dict[str, Any]]:
    return [asdict(d) for d in discover()]
