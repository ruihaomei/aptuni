"""Bounded owner bridge for the separate Obsidian human interface (ADR-0023)."""

from __future__ import annotations

import os
from contextlib import suppress
from importlib.resources import files
from pathlib import Path
from typing import Any, Literal

from aptuni.application.errors import AptuniError
from aptuni.application.workspace import Workspace
from aptuni.domain.invariants import RecordSet
from aptuni.policy.profile_promotion import (
    AUTO_PROFILE_TYPES,
    ProfileReviewState,
    profile_review_state_of,
)
from aptuni.policy.promotion import ReviewState, pending_review_memories, review_state_of

CONTRACT = "aptuni.obsidian@1"
MAX_SECTION_ITEMS = 200
MAX_RECENT_ITEMS = 100
MAX_SUPPORT_ITEMS = 100
ASSETS = ("manifest.json", "main.js", "styles.css")


def _write_all(descriptor: int, content: bytes) -> None:
    offset = 0
    while offset < len(content):
        written = os.write(descriptor, content[offset:])
        if written == 0:
            raise OSError("short write while installing Obsidian plugin")
        offset += written


def _cleanup_install(plugins_fd: int, target_fd: int | None, created: os.stat_result) -> None:
    if target_fd is not None:
        for name in ASSETS:
            with suppress(FileNotFoundError):
                os.unlink(name, dir_fd=target_fd)
    with suppress(FileNotFoundError):
        current = os.stat("aptuni", dir_fd=plugins_fd, follow_symlinks=False)
        if (current.st_dev, current.st_ino) == (created.st_dev, created.st_ino):
            os.rmdir("aptuni", dir_fd=plugins_fd)


def _same_entry(parent_fd: int, name: str, expected: os.stat_result) -> bool:
    try:
        current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    return (current.st_dev, current.st_ino) == (expected.st_dev, expected.st_ino)


def _install_assets(plugins_fd: int) -> tuple[int, os.stat_result]:
    target_fd: int | None = None
    created: os.stat_result | None = None
    try:
        os.mkdir("aptuni", mode=0o700, dir_fd=plugins_fd)
        created = os.stat("aptuni", dir_fd=plugins_fd, follow_symlinks=False)
        target_fd = os.open(
            "aptuni", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=plugins_fd
        )
        package = files("aptuni.interfaces.obsidian_plugin")
        for name in ASSETS:
            descriptor = os.open(
                name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=target_fd,
            )
            try:
                _write_all(descriptor, package.joinpath(name).read_bytes())
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        os.fsync(target_fd)
        os.fsync(plugins_fd)
        return target_fd, created
    except Exception:
        if created is not None:
            _cleanup_install(plugins_fd, target_fd, created)
        if target_fd is not None:
            os.close(target_fd)
        raise


class ObsidianInterfaceCommands:
    """Mixed into AptuniService; no note/source operation is reachable through this interface."""

    workspace: Workspace

    def snapshot(self) -> tuple[int, RecordSet]:
        raise NotImplementedError

    def vault(self) -> Any:
        raise NotImplementedError

    def memories(self) -> list[Any]:
        raise NotImplementedError

    def review_pending(self) -> list[Any]:
        raise NotImplementedError

    def profile_review_pending(self) -> list[Any]:
        raise NotImplementedError

    def review_memory(
        self, memory_id: str, action: Literal["accept", "reject", "pin"]
    ) -> ReviewState:
        raise NotImplementedError

    def review_profile_fact(
        self, fact_id: str, action: Literal["accept", "reject"]
    ) -> ProfileReviewState:
        raise NotImplementedError

    def edit_memory(self, memory_id: str, statement: str) -> str:
        raise NotImplementedError

    def edit_profile_fact(self, fact_id: str, statement: str) -> str:
        raise NotImplementedError

    def memory_forget_preview(self, memory_id: str) -> Any:
        raise NotImplementedError

    def forget_memory_confirmed(self, memory_id: str, confirmed_digest: str) -> None:
        raise NotImplementedError

    def obsidian_snapshot(self) -> dict[str, Any]:
        seq, records = self.snapshot()
        profile = sorted(records.current_facts(), key=lambda record: record.recorded_at, reverse=True)
        revoked = records.revoked_ids()
        memories = sorted(
            (record for record in records.records()
             if record.record_type == "memory" and record.id not in revoked
             and records.superseded_by(record.id) is None),
            key=lambda record: record.recorded_at,
            reverse=True,
        )
        evidence = sorted(
            (record for record in records.current_evidence() if record.change_kind != "retraction"),
            key=lambda record: record.recorded_at, reverse=True,
        )
        recent = sorted(
            (record for record in records.records()
            if record.record_type in {"fact", "memory", "evidence", "review_event"}
            ),
            key=lambda record: record.recorded_at, reverse=True,
        )
        pending_memories = pending_review_memories(records)
        pending_profile = [
            fact for fact in records.current_facts()
            if profile_review_state_of(fact, records) == "auto_promoted_pending_review"
        ]
        pending = [*pending_memories, *pending_profile]
        sections = {
            "profile": profile,
            "memories": memories,
            "evidence": evidence,
            "recent_changes": recent,
            "pending_reviews": pending,
        }
        return {
            "contract": CONTRACT,
            "vault_seq": seq,
            "profile": [self._obsidian_item(record, records) for record in profile[:MAX_SECTION_ITEMS]],
            "memories": [self._obsidian_item(record, records) for record in memories[:MAX_SECTION_ITEMS]],
            "evidence": [self._obsidian_item(record, records) for record in evidence[:MAX_SECTION_ITEMS]],
            "recent_changes": [
                self._obsidian_item(record, records) for record in recent[:MAX_RECENT_ITEMS]
            ],
            "pending_reviews": [
                self._obsidian_item(record, records) for record in pending[:MAX_SECTION_ITEMS]
            ],
            "truncated": {
                name: len(items) > (MAX_RECENT_ITEMS if name == "recent_changes" else MAX_SECTION_ITEMS)
                for name, items in sections.items()
            },
        }

    def obsidian_evidence(self, record_id: str) -> dict[str, Any]:
        _, records = self.snapshot()
        if record_id not in records.ids():
            raise AptuniError("obsidian_record_not_found", "No canonical record has that id.")
        target = records.get(record_id)
        support_ids: list[str] = []

        def add_support(record: Any) -> None:
            if record.id != record_id and record.id not in support_ids:
                support_ids.append(str(record.id))

        def add_memory(memory: Any) -> None:
            add_support(memory)
            for evidence_id in memory.evidence_ids:
                if evidence_id in records.ids():
                    add_support(records.get(evidence_id))
            if memory.candidate_id in records.ids():
                candidate = records.get(memory.candidate_id)
                add_support(candidate)
                for derived_id in candidate.derived_from:
                    if derived_id in records.ids():
                        add_support(records.get(derived_id))

        if target.record_type == "evidence":
            support_ids.append(str(target.id))
        elif target.record_type == "memory":
            add_memory(target)
        elif target.record_type == "fact":
            for evidence_id in target.evidence_ids:
                if evidence_id in records.ids():
                    add_support(records.get(evidence_id))
            for memory_id in target.memory_ids:
                if memory_id in records.ids():
                    add_memory(records.get(memory_id))
        else:
            raise AptuniError(
                "obsidian_evidence_unsupported", "Evidence can be shown only for a Fact, Memory or Evidence record."
            )
        supports = [records.get(item) for item in support_ids[:MAX_SUPPORT_ITEMS]]
        return {
            "contract": CONTRACT,
            "record_id": record_id,
            "supports": [self._obsidian_item(record, records) for record in supports],
            "supports_truncated": len(support_ids) > MAX_SUPPORT_ITEMS,
        }

    def obsidian_action(
        self,
        record_id: str,
        action: str,
        *,
        statement: str | None = None,
        confirmed_digest: str | None = None,
    ) -> dict[str, Any]:
        _, records = self.snapshot()
        if record_id not in records.ids():
            raise AptuniError("obsidian_record_not_found", "No canonical record has that id.")
        record = records.get(record_id)
        if record.record_type == "memory" and action in {"accept", "reject", "pin"}:
            state = self.review_memory(record_id, action)  # type: ignore[arg-type]
            return self._action_result(record_id, action, state)
        if record.record_type == "memory" and action == "edit":
            if statement is None or not statement.strip():
                raise AptuniError("obsidian_statement_required", "Edit requires a non-empty replacement statement.")
            replacement = self.edit_memory(record_id, statement)
            return {"contract": CONTRACT, "action": action, "record_id": replacement,
                    "review_state": "accepted"}
        if record.record_type == "memory" and action == "forget":
            if confirmed_digest is None:
                preview = self.memory_forget_preview(record_id)
                return {
                    "contract": CONTRACT,
                    "action": action,
                    "record_id": record_id,
                    "confirmation_required": True,
                    "digest": preview.digest(),
                    "statement": preview.statement,
                    "module": preview.module,
                    "expires_at": preview.expires_at.isoformat(),
                }
            self.forget_memory_confirmed(record_id, confirmed_digest)
            return self._action_result(record_id, action, "revoked")
        if (record.record_type == "fact" and record.type in AUTO_PROFILE_TYPES
                and action in {"accept", "reject"}):
            state = self.review_profile_fact(record_id, action)  # type: ignore[arg-type]
            return self._action_result(record_id, action, state)
        if record.record_type == "fact" and record.type in AUTO_PROFILE_TYPES and action == "edit":
            if statement is None or not statement.strip():
                raise AptuniError("obsidian_statement_required", "Edit requires a non-empty replacement statement.")
            replacement = self.edit_profile_fact(record_id, statement)
            return {
                "contract": CONTRACT,
                "action": action,
                "record_id": replacement,
                "review_state": "accepted",
            }
        raise AptuniError(
            "obsidian_action_unsupported", "That action is not supported for this canonical record type."
        )

    def install_obsidian_interface(self, vault_path: Path) -> Path:
        raw = vault_path.expanduser().absolute()
        if raw.is_symlink():
            raise AptuniError("obsidian_install_unsafe", "The Obsidian vault path cannot be a symlink.")
        root = raw.resolve(strict=False)
        canonical = self.vault().root.resolve()
        if root == canonical or root in canonical.parents or canonical in root.parents:
            raise AptuniError("obsidian_install_overlap", "The Obsidian vault cannot overlap the Profile Vault.")
        path_fds, path_links = self._open_install_root(root)
        root_fd = path_fds[-1]
        config_fd: int | None = None
        plugins_fd: int | None = None
        target_fd: int | None = None
        plugins_created = False
        try:
            config_fd = self._open_config(root_fd)
            config_stat = os.fstat(config_fd)
            try:
                os.mkdir("plugins", mode=0o700, dir_fd=config_fd)
                plugins_created = True
            except FileExistsError:
                pass
            try:
                plugins_fd = os.open(
                    "plugins", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=config_fd
                )
            except OSError as error:
                raise AptuniError(
                    "obsidian_install_unsafe", "The Obsidian plugin directory must be a real directory."
                ) from error
            plugins_stat = os.fstat(plugins_fd)
            try:
                target_fd, target_stat = _install_assets(plugins_fd)
            except FileExistsError as error:
                raise AptuniError(
                    "obsidian_plugin_exists", "The Aptuni Obsidian plugin directory already exists."
                ) from error
            if (not all(_same_entry(parent_fd, name, expected)
                        for parent_fd, name, expected in path_links)
                    or not _same_entry(root_fd, ".obsidian", config_stat)
                    or not _same_entry(config_fd, "plugins", plugins_stat)
                    or not _same_entry(plugins_fd, "aptuni", target_stat)):
                _cleanup_install(plugins_fd, target_fd, target_stat)
                raise AptuniError(
                    "obsidian_install_unsafe", "The Obsidian vault changed during plugin installation."
                )
            return root / ".obsidian" / "plugins" / "aptuni"
        finally:
            if target_fd is not None:
                os.close(target_fd)
            if plugins_fd is not None:
                os.close(plugins_fd)
            if plugins_created and config_fd is not None:
                with suppress(OSError):
                    os.rmdir("plugins", dir_fd=config_fd)
            if config_fd is not None:
                os.close(config_fd)
            for descriptor in reversed(path_fds):
                os.close(descriptor)

    @staticmethod
    def _open_install_root(root: Path) -> tuple[list[int], list[tuple[int, str, os.stat_result]]]:
        descriptors: list[int] = []
        links: list[tuple[int, str, os.stat_result]] = []
        try:
            current = os.open(root.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            descriptors.append(current)
            for name in root.parts[1:]:
                descriptor = os.open(
                    name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current
                )
                expected = os.fstat(descriptor)
                links.append((current, name, expected))
                descriptors.append(descriptor)
                current = descriptor
        except OSError as error:
            for descriptor in reversed(descriptors):
                os.close(descriptor)
            raise AptuniError("obsidian_vault_required", "Choose an existing Obsidian vault.") from error
        return descriptors, links

    @staticmethod
    def _open_config(root_fd: int) -> int:
        try:
            return os.open(
                ".obsidian", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd
            )
        except OSError as error:
            raise AptuniError(
                "obsidian_vault_required", "Choose an existing Obsidian vault with a .obsidian folder."
            ) from error

    @staticmethod
    def _action_result(record_id: str, action: str, state: str) -> dict[str, Any]:
        return {"contract": CONTRACT, "action": action, "record_id": record_id, "review_state": state}

    @staticmethod
    def _obsidian_item(record: Any, records: RecordSet) -> dict[str, Any]:
        locator = getattr(record.provenance, "locator", None) if hasattr(record, "provenance") else None
        text = (getattr(record, "statement", None) or getattr(record, "excerpt", None)
                or getattr(record, "subject", None) or getattr(record, "decision", ""))
        review_state: str | None = None
        actions: list[str] = []
        if record.record_type in {"fact", "memory", "evidence"}:
            actions.append("show_evidence")
        if record.record_type == "memory":
            review_state = review_state_of(record, records)
            if (record.id not in records.revoked_ids()
                    and records.superseded_by(record.id) is None):
                actions.extend(("accept", "edit", "reject", "pin", "forget"))
        elif record.record_type == "fact" and record.type in AUTO_PROFILE_TYPES:
            review_state = profile_review_state_of(record, records)
            if (
                record.type == "profile.evidence_signal"
                and review_state != "revoked"
                and records.superseded_by(record.id) is None
            ):
                actions.extend(("edit", "reject"))
            elif review_state == "auto_promoted_pending_review":
                actions.extend(("accept", "edit", "reject"))
        return {
            "id": str(record.id),
            "kind": str(record.record_type),
            "type": str(getattr(record, "type", "")),
            "module": str(getattr(record, "module", "")),
            "text": str(text),
            "recorded_at": record.recorded_at.isoformat(),
            "change_kind": str(getattr(record, "change_kind", "")),
            "review_state": review_state,
            "trust": str(getattr(record, "trust", "")),
            "source_id": getattr(getattr(record, "provenance", None), "source_id", None),
            "provider": str(getattr(locator, "provider", "")),
            "episode": str(getattr(getattr(record, "provenance", None), "episode", "")),
            "actions": actions,
        }
