"""Serializers for harvest lot endpoints."""

from rest_framework import serializers

from apps.harvest.models import HarvestLot


class HarvestLotSerializer(serializers.ModelSerializer):
    """Read-only serializer for harvest lots."""

    event_date = serializers.DateTimeField(
        source="event.event_date",
        read_only=True,
        help_text="Timestamp of the harvest event that produced this lot.",
    )
    batch = serializers.IntegerField(
        source="event.batch_id",
        read_only=True,
        help_text="Batch identifier associated with the harvest event.",
    )
    batch_number = serializers.CharField(
        source="event.batch.batch_number",
        read_only=True,
        help_text="Batch number tied to the harvest event.",
    )
    product_grade_code = serializers.CharField(
        source="product_grade.code",
        read_only=True,
        help_text="Code representing the product grade.",
    )
    product_grade_name = serializers.CharField(
        source="product_grade.name",
        read_only=True,
        help_text="Human readable product grade name.",
    )

    class Meta:
        model = HarvestLot
        fields = (
            "id",
            "event",
            "event_date",
            "batch",
            "batch_number",
            "product_grade",
            "product_grade_code",
            "product_grade_name",
            "live_weight_kg",
            "gutted_weight_kg",
            "fillet_weight_kg",
            "unit_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
