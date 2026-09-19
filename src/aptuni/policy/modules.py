"""Fail-closed module decisions (ADR-0007). A missing policy denies everything."""

from __future__ import annotations

from typing import cast

from aptuni.domain.ids import new_id
from aptuni.domain.records import MODULES, Module, ModulePolicy, ModuleSwitch
from aptuni.domain.temporal import utc_now


def default_policy() -> ModulePolicy:
    """Initial policy: every module may ingest and be exposed (PRD §6 defaults)."""
    return ModulePolicy(
        record_type="module_policy", id=new_id("pol"), schema_version=1, recorded_at=utc_now(), epoch=1,
        modules={m: ModuleSwitch(ingest_enabled=True, expose_enabled=True) for m in MODULES},
    )


def with_switch(policy: ModulePolicy, module: str, *, ingest: bool | None, expose: bool | None) -> ModulePolicy:
    """Return the next policy epoch with one module changed; ingest and expose stay independent."""
    current = policy.modules[cast(Module, module)]
    changed = ModuleSwitch(
        ingest_enabled=current.ingest_enabled if ingest is None else ingest,
        expose_enabled=current.expose_enabled if expose is None else expose,
    )
    modules = dict(policy.modules) | {module: changed}
    return ModulePolicy(record_type="module_policy", id=new_id("pol"), schema_version=1, recorded_at=utc_now(),
                        epoch=policy.epoch + 1, modules=modules)


def can_ingest(policy: ModulePolicy | None, module: str) -> bool:
    return policy is not None and module in policy.modules and policy.modules[module].ingest_enabled


def can_expose(policy: ModulePolicy | None, module: str) -> bool:
    return policy is not None and module in policy.modules and policy.modules[module].expose_enabled
