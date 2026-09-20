"""Privacy inventory: every managed/external copy is visible without exposing its content."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from aptuni.adapters.manager import AdapterManager
from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace

REPO = Path(__file__).resolve().parents[2]


def test_inventory_lists_managed_unmanaged_and_external_copies_without_content(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path / "state")
    service = AptuniService(workspace)
    service.init(tmp_path / "Aptuni")
    marker = "PRIVATE-INVENTORY-MARKER"
    service.remember(marker, "preferences")

    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "note.md").write_text("SOURCE-SECRET-MARKER", encoding="utf-8")
    source = service.add_folder_source(source_root, ("knowledge",), "notes")
    service.sync(source.id)
    service.search("source marker")  # materialize the derived projection

    manager = AdapterManager(workspace)
    plan = manager.plan("codex", ("preferences",), allow_host_model_egress=True,
                        allow_memory_proposals=True)
    grant, _ = manager.apply(plan.action_id)

    before = service.status().seq
    inventory = service.privacy_inventory()
    assert service.status().seq == before, "inventory must be read-only"
    copies = {copy.id: copy for copy in inventory.copies}

    assert copies["canonical_vault"].present and copies["canonical_vault"].bytes > 0
    assert copies["source_state"].present and copies["source_state"].bytes > 0
    assert copies["retrieval_projection"].present and copies["retrieval_projection"].bytes > 0
    assert copies["adapter_grants"].present and copies["adapter_grants"].managed
    assert copies["profile_exports"].present is None and not copies["profile_exports"].managed
    external = copies[f"host_external:{grant.grant_id}"]
    assert external.present is None and not external.managed
    assert external.deletion_control == "externally_controlled_unknown"
    original = copies[f"source_original:{source.id}"]
    assert original.location == str(source_root.resolve()) and not original.managed
    assert inventory.actions["forget"] == "revoke visibility; keep canonical audit history"
    assert "external host copies" in inventory.actions["purge"]

    payload = json.dumps(inventory.to_dict(), ensure_ascii=False)
    assert marker not in payload and "SOURCE-SECRET-MARKER" not in payload


def test_privacy_status_cli_is_scriptable(tmp_path: Path) -> None:
    state = tmp_path / "state"
    env = dict(os.environ, APTUNI_STATE_DIR=str(state), PYTHONPATH=str(REPO / "src"))

    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "-m", "aptuni", *args], env=env, capture_output=True,
                              text=True, check=False)

    assert run("init", str(tmp_path / "Aptuni")).returncode == 0
    done = run("privacy", "status", "--json")
    assert done.returncode == 0, done.stderr
    payload = json.loads(done.stdout)
    assert payload["schema_version"] == 1
    assert payload["vault_seq"] == 1
    assert {copy["id"] for copy in payload["copies"]} >= {
        "canonical_vault", "source_state", "retrieval_projection", "adapter_grants",
        "adapter_bundles", "pending_actions", "memory_confirmations", "privacy_actions",
        "privacy_receipts", "deletion_ledger", "profile_exports",
    }
