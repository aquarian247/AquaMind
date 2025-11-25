from __future__ import annotations

from django.db import models


class ExternalIdMap(models.Model):
    """Maps legacy source identifiers to AquaMind objects."""

    source_system = models.CharField(max_length=32, help_text="External system identifier, e.g. 'FishTalk'.")
    source_model = models.CharField(max_length=64, help_text="Source table or entity name.")
    source_identifier = models.CharField(max_length=128, help_text="Primary identifier in the source system.")
    target_app_label = models.CharField(max_length=64, help_text="Target Django app label (apps.batch, apps.inventory, etc.).")
    target_model = models.CharField(max_length=64, help_text="Target Django model name.")
    target_object_id = models.BigIntegerField(help_text="Primary key in AquaMind.")
    metadata = models.JSONField(default=dict, blank=True, help_text="Optional JSON payload for extra mapping info (dates, notes, etc.).")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'External ID Map'
        verbose_name_plural = 'External ID Maps'
        unique_together = ('source_system', 'source_model', 'source_identifier')
        indexes = [
            models.Index(fields=['source_system', 'source_model']),
            models.Index(fields=['target_app_label', 'target_model', 'target_object_id']),
        ]

    def __str__(self) -> str:
        return f"{self.source_system}:{self.source_model}:{self.source_identifier} -> {self.target_model}({self.target_object_id})"
