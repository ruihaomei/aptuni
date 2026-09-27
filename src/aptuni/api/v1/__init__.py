"""Aptuni public developer API v1.

Everything exported here is versioned. Other ``aptuni`` modules are internal unless a document says
otherwise.
"""

from aptuni.api.v1.client import AptuniAPI, connect
from aptuni.api.v1.contracts import ContextItem, ContextResult, MemoryProposal, ReviewQueue
from aptuni.api.v1.errors import AptuniAPIError
from aptuni.api.v1.manifest import (
    CAPABILITIES,
    AptuniContextDeclaration,
    Capability,
    PluginManifest,
    load_manifest,
)
from aptuni.api.v1.scaffold import scaffold_plugin

__all__ = [
    "CAPABILITIES",
    "AptuniAPI",
    "AptuniAPIError",
    "AptuniContextDeclaration",
    "Capability",
    "ContextItem",
    "ContextResult",
    "MemoryProposal",
    "PluginManifest",
    "ReviewQueue",
    "connect",
    "load_manifest",
    "scaffold_plugin",
]
