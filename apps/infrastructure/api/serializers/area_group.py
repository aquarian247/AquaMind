"""
AreaGroup serializer for the infrastructure app.

This module defines serializers for hierarchical sea area groups.
"""

from rest_framework import serializers

from apps.infrastructure.models.area_group import AreaGroup
from apps.infrastructure.models.geography import Geography
from apps.infrastructure.api.serializers.geography import GeographySerializer
from apps.infrastructure.api.serializers.base import (
    TimestampedModelSerializer,
    NamedModelSerializer,
)


class AreaGroupSerializer(TimestampedModelSerializer, NamedModelSerializer):
    """Serializer for the AreaGroup model."""

    name = serializers.CharField(
        max_length=100,
        help_text="Unique name within the geography + parent group scope.",
    )
    code = serializers.CharField(
        max_length=32,
        required=False,
        allow_blank=True,
        help_text="Optional short code for operations and reporting.",
    )
    geography = serializers.PrimaryKeyRelatedField(
        queryset=Geography.objects.all(),
        help_text="ID of the geography this area-group belongs to.",
    )
    geography_details = GeographySerializer(
        source="geography",
        read_only=True,
        help_text="Detailed geography information.",
    )
    parent = serializers.PrimaryKeyRelatedField(
        queryset=AreaGroup.objects.all(),
        allow_null=True,
        required=False,
        help_text="Optional parent area-group for hierarchical grouping.",
    )
    parent_name = serializers.CharField(
        source="parent.name",
        read_only=True,
        allow_null=True,
        help_text="Name of the linked parent area-group.",
    )
    active = serializers.BooleanField(
        default=True,
        help_text="Indicates if the area-group is active.",
    )

    class Meta:
        model = AreaGroup
        fields = [
            "id",
            "name",
            "code",
            "geography",
            "geography_details",
            "parent",
            "parent_name",
            "active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "geography_details",
            "parent_name",
        ]

    def validate(self, attrs):
        """Ensure parent linkage is valid and remains within the same geography."""
        attrs = super().validate(attrs)

        parent = attrs.get("parent")
        geography = attrs.get("geography")

        if self.instance:
            if parent is None and "parent" not in attrs:
                parent = self.instance.parent
            if geography is None:
                geography = self.instance.geography

        if parent and self.instance and parent.id == self.instance.id:
            raise serializers.ValidationError(
                {"parent": "Area group cannot reference itself as parent."}
            )

        if parent and geography and parent.geography_id != geography.id:
            raise serializers.ValidationError(
                {
                    "parent": (
                        "Parent area group must belong to the same geography "
                        "as this area group."
                    )
                }
            )

        return attrs
