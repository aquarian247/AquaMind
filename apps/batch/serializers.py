"""Legacy import shim for batch serializers.

This module exists for backwards compatibility only. All serializers have been
migrated to the modular API package ``apps.batch.api.serializers``. Import from
that package directly in new code.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "apps.batch.serializers is deprecated; import from apps.batch.api.serializers instead.",
    DeprecationWarning,
    stacklevel=2,
)

from apps.batch.api import serializers as api_serializers
from apps.batch.api.serializers import *  # noqa: F401,F403

__all__ = getattr(api_serializers, "__all__", [name for name in dir(api_serializers) if not name.startswith("_")])
