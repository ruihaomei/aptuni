"""Supported public developer interfaces.

Only versioned namespaces below this package carry compatibility guarantees. Application, domain,
Vault and provider modules are internal implementation details.
"""

from aptuni.api import v1

__all__ = ["v1"]
