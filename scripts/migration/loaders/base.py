"""Base loader helpers for writing into AquaMind."""

from __future__ import annotations

from typing import Any, Dict, Optional

from django.db import transaction
from django.db.models import Model

from apps.migration_support.models import ExternalIdMap


class BaseLoader:
    """Shared conveniences for loaders (transactions + external ID tracking)."""

    atomic = transaction.atomic

    def __init__(self, dry_run: bool = False, source_system: str = "FishTalk") -> None:
        self.dry_run = dry_run
        self.source_system = source_system

    def atomic_context(self):
        return transaction.atomic

    def record_external_id(
        self,
        *,
        source_model: str,
        source_identifier: Any,
        instance: Model,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Upsert an ExternalIdMap entry for the given model instance."""
        if self.dry_run or not source_identifier:
            return

        ExternalIdMap.objects.update_or_create(
            source_system=self.source_system,
            source_model=source_model,
            source_identifier=str(source_identifier),
            defaults={
                "target_app_label": instance._meta.app_label,
                "target_model": instance._meta.model_name,
                "target_object_id": instance.pk,
                "metadata": metadata or {},
            },
        )
