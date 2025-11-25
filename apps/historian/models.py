from __future__ import annotations

import uuid

from django.db import models


class HistorianTag(models.Model):
    """Canonical list of historian tags imported from AVEVA."""

    tag_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tag_name = models.CharField(max_length=512)
    description = models.TextField(blank=True)
    tag_type = models.SmallIntegerField(null=True, blank=True)
    unit = models.CharField(max_length=128, blank=True)
    source_system = models.CharField(max_length=64, default="AVEVA")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "historian_tag"
        ordering = ["tag_name"]

    def __str__(self) -> str:
        return self.tag_name


class HistorianTagHistory(models.Model):
    """Snapshot of tag metadata (mirrors TagHistory rows)."""

    tag = models.ForeignKey(
        HistorianTag,
        on_delete=models.CASCADE,
        related_name="history",
        null=True,
        blank=True,
    )
    recorded_at = models.DateTimeField()
    tag_name = models.CharField(max_length=512)
    tag_type = models.SmallIntegerField(null=True, blank=True)
    unit = models.CharField(max_length=128, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "historian_tag_history"
        ordering = ["tag", "recorded_at"]
        indexes = [
            models.Index(fields=["tag", "recorded_at"]),
            models.Index(fields=["recorded_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.tag_name} @ {self.recorded_at:%Y-%m-%d %H:%M:%S}"


class HistorianTagLink(models.Model):
    """Maps an AVEVA tag to AquaMind infrastructure/environmental entities."""

    tag = models.OneToOneField(
        HistorianTag, on_delete=models.CASCADE, related_name="link"
    )
    sensor = models.ForeignKey(
        "infrastructure.Sensor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="historian_links",
    )
    container = models.ForeignKey(
        "infrastructure.Container",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="historian_links",
    )
    parameter = models.ForeignKey(
        "environmental.EnvironmentalParameter",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="historian_links",
    )
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "historian_tag_link"

    def __str__(self) -> str:
        return f"{self.tag.tag_name} link"
