"""Serializers for harvest event endpoints."""

from rest_framework import serializers

from apps.harvest.models import HarvestEvent


class HarvestEventSerializer(serializers.ModelSerializer):
    """Read-only serializer for harvest events."""

    batch_number = serializers.CharField(
        source="batch.batch_number",
        read_only=True,
        help_text="Batch number associated with this harvest event.",
    )
    assignment_container = serializers.CharField(
        source="assignment.container.name",
        read_only=True,
        help_text="Name of the container linked to the batch assignment at harvest time.",
    )
    dest_geography_name = serializers.CharField(
        source="dest_geography.name",
        read_only=True,
        help_text="Display name of the destination geography.",
    )
    dest_subsidiary_display = serializers.CharField(
        source="get_dest_subsidiary_display",
        read_only=True,
        help_text="Human readable destination subsidiary label.",
    )

    class Meta:
        model = HarvestEvent
        fields = (
            "id",
            "event_date",
            "batch",
            "batch_number",
            "assignment",
            "assignment_container",
            "dest_geography",
            "dest_geography_name",
            "dest_subsidiary",
            "dest_subsidiary_display",
            "document_ref",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
