"""Serializers for NAV export endpoints."""

from rest_framework import serializers

from apps.finance.api.serializers.fact_harvest import CompanySummarySerializer
from apps.finance.models import DimCompany, NavExportBatch


class NavExportBatchCreateSerializer(serializers.Serializer):
    """Validates NAV export batch creation payloads."""

    company = serializers.PrimaryKeyRelatedField(queryset=DimCompany.objects.all())
    date_from = serializers.DateField()
    date_to = serializers.DateField()

    def validate(self, attrs):
        if attrs["date_from"] > attrs["date_to"]:
            raise serializers.ValidationError("date_from must be before or equal to date_to")
        return attrs


class NavExportBatchSerializer(serializers.ModelSerializer):
    """Read serializer for NAV export batches."""

    id = serializers.IntegerField(source="batch_id", read_only=True)
    company = CompanySummarySerializer(read_only=True)
    line_count = serializers.IntegerField(source="lines.count", read_only=True)

    class Meta:
        model = NavExportBatch
        fields = (
            "id",
            "company",
            "date_from",
            "date_to",
            "posting_date",
            "currency",
            "state",
            "created_at",
            "updated_at",
            "line_count",
        )
        read_only_fields = fields
