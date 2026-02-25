"""
AreaGroup model for the infrastructure app.

This module defines optional hierarchy groups for sea areas.
Examples: Faroe "North/South/West" and deeper Scotland grouping trees.
"""

from django.db import models
from simple_history.models import HistoricalRecords

from apps.infrastructure.models.geography import Geography


class AreaGroup(models.Model):
    """
    Optional hierarchical grouping for sea areas.
    """

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=32, blank=True)
    geography = models.ForeignKey(
        Geography,
        on_delete=models.PROTECT,
        related_name="area_groups",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="children",
        null=True,
        blank=True,
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["geography", "parent", "name"],
                name="uniq_area_group_geo_parent_name",
            )
        ]

    history = HistoricalRecords()

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} / {self.name}"
        return self.name

