"""Versioned provider extension registry.

The common contract never inspects provider fields. Each provider family
registers a schema version with its required/optional fields. A version the
running core does not understand is preserved losslessly but forces review.
"""

from __future__ import annotations

from dataclasses import dataclass
from s05a.records import ContractError, Extension, Operation


@dataclass(frozen=True)
class ExtensionSpec:
    required: frozenset[str]
    optional: frozenset[str] = frozenset()


class ExtensionRegistry:
    def __init__(self) -> None:
        self._specs: dict[tuple[str, int], ExtensionSpec] = {}

    def register(self, schema: str, version: int, spec: ExtensionSpec) -> None:
        key = (schema, version)
        if key in self._specs:
            raise ContractError("extension_already_registered")
        self._specs[key] = spec

    def understands(self, extension: Extension) -> bool:
        return (extension.schema, extension.version) in self._specs

    def validate(self, extension: Extension) -> None:
        spec = self._specs.get((extension.schema, extension.version))
        if spec is None:
            raise ContractError("extension_unknown")
        keys = set(extension.fields)
        if not spec.required <= keys:
            raise ContractError("extension_required_field_missing")
        if keys - spec.required - spec.optional:
            raise ContractError("extension_field_unexpected")

    def gate(self, op: Operation) -> Operation:
        """Validate understood locators; route not-understood versions to review."""
        for locator in (op.before, op.after):
            if locator is None:
                continue
            if not self.understands(locator.extension):
                return op.needing_review("extension_version_unknown")
            self.validate(locator.extension)
        return op


def default_registry() -> ExtensionRegistry:
    registry = ExtensionRegistry()
    registry.register("folder.locator", 1, ExtensionSpec(frozenset({"relative_path"}), frozenset({"format_anchor"})))
    registry.register(
        "marginnote.locator",
        1,
        ExtensionSpec(
            frozenset({"canonical_node_id", "ancestor_path", "vendor_node_id"}),
            frozenset({"unknown_attributes", "export_scope", "parent_node_id", "children_signature", "sibling_index"}),
        ),
    )
    registry.register(
        "github.locator",
        1,
        ExtensionSpec(frozenset({"repository_id", "commit", "path", "blob"}), frozenset({"owner_name", "mode", "selection_reason"})),
    )
    return registry
