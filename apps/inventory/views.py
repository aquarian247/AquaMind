"""Legacy import shim for inventory viewsets.

All functional viewsets now live in ``apps.inventory.api.viewsets``. Import
from that package for new development.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "apps.inventory.views is deprecated; import from apps.inventory.api.viewsets instead.",
    DeprecationWarning,
    stacklevel=2,
)

from apps.inventory.api import viewsets as api_viewsets
from apps.inventory.api.viewsets import *  # noqa: F401,F403

__all__ = getattr(api_viewsets, "__all__", [name for name in dir(api_viewsets) if not name.startswith("_")])
