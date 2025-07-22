"""
Utility modules for the AquaMind project.

This package contains various utility modules used throughout the AquaMind application,
including helpers for OpenAPI schema generation, database compatibility, and other
common functionality.
"""

# Ensure Schemathesis runtime hooks are import-able via
#     SCHEMATHESIS_HOOKS="aquamind.utils.schemathesis_hooks"
# Importing here makes the sub-module discoverable without requiring the caller
# to reference the full dotted path explicitly (the environment variable loader
# imports the parent package first, then resolves sub-modules).
from importlib import import_module as _import_module

# Lazy-import so it does not add overhead unless actually requested.
# The attempt is wrapped in a try/except to avoid breaking unrelated code paths
# if Schemathesis is not installed / used.
try:
    _import_module(".schemathesis_hooks", package=__name__)
except ModuleNotFoundError:
    # Hooks module might be removed in slim deployments; ignore silently.
    pass
