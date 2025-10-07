"""Serializers for finance harvest fact endpoints."""

from rest_framework import serializers

from apps.finance.models import DimCompany, DimSite, FactHarvest
from apps.harvest.models import ProductGrade


class CompanySummarySerializer(serializers.ModelSerializer):
    """Compact representation of a finance company."""

    id = serializers.IntegerField(source="company_id", read_only=True)
    geography = serializers.CharField(
        source="geography.name",
        allow_null=True,
        read_only=True,
    )

    class Meta:
        model = DimCompany
        fields = ("id", "display_name", "subsidiary", "geography", "currency")
        read_only_fields = fields


class SiteSummarySerializer(serializers.ModelSerializer):
    """Compact representation of a finance site."""

    id = serializers.IntegerField(source="site_id", read_only=True)
    name = serializers.CharField(source="site_name", read_only=True)

    class Meta:
        model = DimSite
        fields = ("id", "name", "source_model", "source_pk", "company_id")
        read_only_fields = fields


class ProductGradeSummarySerializer(serializers.ModelSerializer):
    """Compact representation of a harvest product grade."""

    class Meta:
        model = ProductGrade
        fields = ("id", "code", "name")
        read_only_fields = fields


class FactHarvestSerializer(serializers.ModelSerializer):
    """Read-only serializer for projected harvest facts."""

    batch = serializers.IntegerField(
        source="dim_batch_id",
        read_only=True,
        help_text="Identifier of the originating batch.",
    )
    company = CompanySummarySerializer(
        source="dim_company",
        read_only=True,
        help_text="Finance company details.",
    )
    site = SiteSummarySerializer(
        source="dim_site",
        read_only=True,
        help_text="Finance site details.",
    )
    product_grade = ProductGradeSummarySerializer(
        read_only=True,
        help_text="Product grade metadata for the lot.",
    )

    class Meta:
        model = FactHarvest
        fields = (
            "fact_id",
            "event",
            "lot",
            "event_date",
            "quantity_kg",
            "unit_count",
            "batch",
            "company",
            "site",
            "product_grade",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
