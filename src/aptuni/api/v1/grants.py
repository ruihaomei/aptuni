"""Owner-created, manifest-bound grants for local v1 plugins."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import stat
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, TypeVar

from pydantic import BaseModel, ConfigDict

from aptuni.api.v1.errors import AptuniAPIError
from aptuni.api.v1.manifest import Capability, PluginManifest
from aptuni.application.developer_authorization import developer_authorization_lock
from aptuni.application.workspace import Workspace
from aptuni.domain.records import Module

_EXACT_ID = re.compile(r"^(?:act|grant)-[0-9a-f]{16}$")
_PLAN_TTL = timedelta(minutes=10)
_GrantT = TypeVar("_GrantT", bound="_GrantModel")


class _GrantModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class PluginGrantPlan(_GrantModel):
    contract: Literal["aptuni.plugin-grant-plan@1"] = "aptuni.plugin-grant-plan@1"
    action_id: str
    digest: str
    plugin_id: str
    plugin_version: str
    manifest_digest: str
    capabilities: tuple[Capability, ...]
    modules: tuple[Module, ...]
    nonce_id: str
    created_at: datetime
    expires_at: datetime
    required_capabilities: tuple[Capability, ...] = ()


class PluginGrant(_GrantModel):
    contract: Literal["aptuni.plugin-grant@1"] = "aptuni.plugin-grant@1"
    grant_id: str
    plugin_id: str
    plugin_version: str
    manifest_digest: str
    capabilities: tuple[Capability, ...]
    modules: tuple[Module, ...]
    nonce_id: str
    created_at: datetime
    plan_expires_at: datetime
    action_digest: str
    required_capabilities: tuple[Capability, ...] = ()


class PluginGrantManager:
    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    @property
    def root(self) -> Path:
        return self.workspace.state_dir / "developer"

    def plan(
        self,
        manifest: PluginManifest,
        *,
        capabilities: tuple[str, ...] | None = None,
        modules: tuple[str, ...] | None = None,
    ) -> PluginGrantPlan:
        if manifest.egress != ("none",):
            raise AptuniAPIError(
                "plugin_egress_unsupported",
                "Public API v1 authorizes local no-egress clients only; use an informed MCP grant for external egress.",
            )
        requested_capabilities = manifest.requested_capabilities
        selected_capabilities = tuple(requested_capabilities if capabilities is None else capabilities)
        selected_modules = tuple(manifest.modules if modules is None else modules)
        if not selected_capabilities or len(set(selected_capabilities)) != len(selected_capabilities):
            raise AptuniAPIError("plugin_capability_invalid", "Choose a unique non-empty capability subset.")
        if not set(selected_capabilities) <= set(requested_capabilities):
            raise AptuniAPIError("plugin_capability_denied", "The grant cannot exceed the manifest capabilities.")
        if not set(manifest.required_capabilities) <= set(selected_capabilities):
            raise AptuniAPIError(
                "plugin_required_capability_denied",
                "The grant must include every capability the plugin declares as required.",
            )
        if not selected_modules or len(set(selected_modules)) != len(selected_modules):
            raise AptuniAPIError("plugin_module_invalid", "Choose a unique non-empty module subset.")
        if not set(selected_modules) <= set(manifest.modules):
            raise AptuniAPIError("plugin_module_denied", "The grant cannot exceed the manifest modules.")
        if (
            "evidence.read" in selected_capabilities
            and "context.read" not in selected_capabilities
        ):
            raise AptuniAPIError("plugin_capability_invalid", "evidence.read requires context.read in the same grant.")
        if "profile.read" in selected_capabilities and "identity" not in selected_modules:
            raise AptuniAPIError(
                "plugin_module_invalid",
                "profile.read requires the identity module in the same grant.",
            )
        created_at = datetime.now(UTC)
        payload = {
            "plugin_id": manifest.id,
            "plugin_version": manifest.version,
            "manifest_digest": manifest.digest(),
            "capabilities": selected_capabilities,
            "modules": selected_modules,
            "nonce_id": secrets.token_hex(16),
            "created_at": created_at.isoformat(),
            "expires_at": (created_at + _PLAN_TTL).isoformat(),
        }
        if manifest.required_capabilities:
            payload["required_capabilities"] = manifest.required_capabilities
        digest = self._digest(payload)
        plan = PluginGrantPlan(
            action_id="act-" + digest[:16], digest="sha256:" + digest,
            **payload,
        )
        self._write(self.root / "pending" / f"{plan.action_id}.json", plan.model_dump(mode="json"))
        return plan

    def apply(self, action_id: str) -> PluginGrant:
        self._exact_id(action_id, "act-")
        grant_id = "grant-" + action_id.removeprefix("act-")
        with self.authorization_lock():
            try:
                plan = self.pending(action_id)
            except AptuniAPIError as error:
                if error.code != "plugin_action_not_found":
                    raise
                return self.load(grant_id)
            grant = PluginGrant(
                grant_id=grant_id,
                plugin_id=plan.plugin_id,
                plugin_version=plan.plugin_version,
                manifest_digest=plan.manifest_digest,
                capabilities=plan.capabilities,
                modules=plan.modules,
                nonce_id=plan.nonce_id,
                created_at=plan.created_at,
                plan_expires_at=plan.expires_at,
                action_digest=plan.digest,
                required_capabilities=plan.required_capabilities,
            )
            try:
                existing = self.load(grant_id)
            except AptuniAPIError as error:
                if error.code != "plugin_grant_not_found":
                    raise
                if plan.expires_at <= datetime.now(UTC):
                    self._unlink("pending", f"{action_id}.json")
                    message = "The plugin grant preview expired; plan it again."
                    raise AptuniAPIError("plugin_action_expired", message) from None
                self._write(
                    self.root / "grants" / f"{grant.grant_id}.json",
                    grant.model_dump(mode="json"),
                )
            else:
                if existing != grant:
                    message = "The existing plugin grant does not match its owner preview."
                    raise AptuniAPIError("plugin_grant_changed", message)
                grant = existing
            self._unlink("pending", f"{action_id}.json")
            return grant

    def cancel(self, action_id: str) -> bool:
        self._exact_id(action_id, "act-")
        with self.authorization_lock():
            try:
                plan = self.pending(action_id)
            except AptuniAPIError as error:
                if error.code == "plugin_action_not_found":
                    return False
                raise
            grant_id = "grant-" + action_id.removeprefix("act-")
            try:
                grant = self.load(grant_id)
            except AptuniAPIError as error:
                if error.code != "plugin_grant_not_found":
                    raise
            else:
                if grant.action_digest != plan.digest:
                    message = "The published plugin grant does not match its owner preview."
                    raise AptuniAPIError("plugin_grant_changed", message)
                self._unlink("grants", f"{grant_id}.json")
            return self._unlink("pending", f"{action_id}.json")

    def revoke(self, grant_id: str) -> bool:
        self._exact_id(grant_id, "grant-")
        with self.authorization_lock():
            return self._unlink("grants", f"{grant_id}.json")

    @contextmanager
    def authorization_lock(self) -> Iterator[None]:
        """Serialize authorization use and mutation across threads and processes."""
        try:
            with developer_authorization_lock(self.workspace.state_dir):
                yield
        except OSError as error:
            raise AptuniAPIError("plugin_grant_unsafe", "The plugin grant path is unsafe.") from error

    def list_grants(self) -> tuple[PluginGrant, ...]:
        descriptors = self._open_folder("grants", create=False)
        if descriptors is None:
            return ()
        state_fd, developer_fd, folder_fd = descriptors
        try:
            names = sorted(
                name
                for name in os.listdir(folder_fd)
                if name.startswith("grant-") and name.endswith(".json")
            )
        finally:
            os.close(folder_fd)
            os.close(developer_fd)
            os.close(state_fd)
        values: list[PluginGrant] = []
        for name in names:
            values.append(self.load(name.removesuffix(".json")))
        return tuple(values)

    def _unlink(self, folder: str, name: str) -> bool:
        descriptors = self._open_folder(folder, create=False)
        if descriptors is None:
            return False
        state_fd, developer_fd, folder_fd = descriptors
        try:
            try:
                os.unlink(name, dir_fd=folder_fd)
                os.fsync(folder_fd)
                return True
            except FileNotFoundError:
                return False
        finally:
            os.close(folder_fd)
            os.close(developer_fd)
            os.close(state_fd)

    def pending(self, action_id: str) -> PluginGrantPlan:
        return self._load(action_id, "pending", PluginGrantPlan, "plugin_action_not_found")

    def load(self, grant_id: str) -> PluginGrant:
        return self._load(grant_id, "grants", PluginGrant, "plugin_grant_not_found")

    def _load(self, exact_id: str, folder: str, model: type[_GrantT], code: str) -> _GrantT:
        self._exact_id(exact_id, "act-" if folder == "pending" else "grant-")
        try:
            descriptors = self._open_folder(folder, create=False)
            if descriptors is None:
                raise FileNotFoundError
            state_fd, developer_fd, folder_fd = descriptors
            try:
                descriptor = os.open(f"{exact_id}.json", os.O_RDONLY | os.O_NOFOLLOW, dir_fd=folder_fd)
                try:
                    info = os.fstat(descriptor)
                    if not stat.S_ISREG(info.st_mode) or info.st_size > 65_536:
                        raise OSError("grant_record_invalid")
                    raw = b""
                    while len(raw) <= info.st_size:
                        chunk = os.read(descriptor, min(65_537 - len(raw), 16_384))
                        if not chunk:
                            break
                        raw += chunk
                finally:
                    os.close(descriptor)
            finally:
                os.close(folder_fd)
                os.close(developer_fd)
                os.close(state_fd)
            value = model.model_validate_json(raw)
            self._validate_integrity(value)
            return value
        except (OSError, ValueError) as error:
            raise AptuniAPIError(code, "The exact plugin grant record is unavailable.") from error

    def _write(self, path: Path, value: object) -> None:
        folder = path.parent.name
        descriptors = self._open_folder(folder, create=True)
        assert descriptors is not None
        state_fd, developer_fd, folder_fd = descriptors
        temporary = f".{path.name}.{secrets.token_hex(8)}.tmp"
        try:
            descriptor = os.open(
                temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=folder_fd,
            )
            try:
                body = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
                offset = 0
                while offset < len(body):
                    written = os.write(descriptor, body[offset:])
                    if written == 0:
                        raise OSError("plugin_grant_short_write")
                    offset += written
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            os.rename(temporary, path.name, src_dir_fd=folder_fd, dst_dir_fd=folder_fd)
            os.fsync(folder_fd)
        except OSError as error:
            with suppress(FileNotFoundError):
                os.unlink(temporary, dir_fd=folder_fd)
            raise AptuniAPIError("plugin_grant_unsafe", "The plugin grant path is unsafe.") from error
        finally:
            os.close(folder_fd)
            os.close(developer_fd)
            os.close(state_fd)

    def _open_folder(self, folder: str, *, create: bool) -> tuple[int, int, int] | None:
        state = self.workspace.state_dir
        if state.is_symlink():
            raise AptuniAPIError("plugin_grant_unsafe", "The plugin grant path is unsafe.")
        if create:
            state.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            state_fd = os.open(state, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        except FileNotFoundError:
            return None
        try:
            developer_fd = self._child_directory(state_fd, "developer", create=create)
            if developer_fd is None:
                os.close(state_fd)
                return None
            folder_fd = self._child_directory(developer_fd, folder, create=create)
            if folder_fd is None:
                os.close(developer_fd)
                os.close(state_fd)
                return None
            return state_fd, developer_fd, folder_fd
        except Exception:
            os.close(state_fd)
            raise

    @staticmethod
    def _child_directory(parent_fd: int, name: str, *, create: bool) -> int | None:
        if create:
            with suppress(FileExistsError):
                os.mkdir(name, mode=0o700, dir_fd=parent_fd)
        try:
            return os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
        except FileNotFoundError:
            return None
        except OSError as error:
            raise AptuniAPIError("plugin_grant_unsafe", "The plugin grant path is unsafe.") from error

    @staticmethod
    def _digest(payload: object) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def _validate_integrity(self, value: _GrantModel) -> None:
        if isinstance(value, (PluginGrantPlan, PluginGrant)):
            payload = self._payload(value)
        else:
            raise ValueError("unknown plugin grant record")
        digest = self._digest(payload)
        if isinstance(value, PluginGrantPlan):
            if value.digest != "sha256:" + digest or value.action_id != "act-" + digest[:16]:
                raise ValueError("plugin grant plan integrity mismatch")
        elif (
            value.action_digest != "sha256:" + digest
            or value.grant_id != "grant-" + digest[:16]
        ):
            raise ValueError("plugin grant integrity mismatch")

    @staticmethod
    def _payload(value: PluginGrantPlan | PluginGrant) -> dict[str, object]:
        payload: dict[str, object] = {
            "plugin_id": value.plugin_id,
            "plugin_version": value.plugin_version,
            "manifest_digest": value.manifest_digest,
            "capabilities": value.capabilities,
            "modules": value.modules,
            "nonce_id": value.nonce_id,
            "created_at": value.created_at.isoformat(),
        }
        if isinstance(value, PluginGrantPlan):
            payload["expires_at"] = value.expires_at.isoformat()
        else:
            payload["expires_at"] = value.plan_expires_at.isoformat()
        if value.required_capabilities:
            payload["required_capabilities"] = value.required_capabilities
        return payload

    @staticmethod
    def _exact_id(value: str, prefix: str) -> None:
        if _EXACT_ID.fullmatch(value) is None or not value.startswith(prefix):
            raise AptuniAPIError("plugin_grant_not_found", "An exact core-generated plugin id is required.")
