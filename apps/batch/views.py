"""Legacy import shim for batch viewsets.

Viewsets now live in ``apps.batch.api.viewsets``. Import from that package in
new code.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "apps.batch.views is deprecated; import from apps.batch.api.viewsets instead.",
    DeprecationWarning,
    stacklevel=2,
)

from apps.batch.api import viewsets as api_viewsets
from apps.batch.api.viewsets import *  # noqa: F401,F403

__all__ = [name for name in dir(api_viewsets) if not name.startswith("_")]
