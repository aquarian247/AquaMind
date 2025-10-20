"""Serializers for intercompany transaction endpoints."""

from rest_framework import serializers

from apps.finance.api.serializers.fact_harvest import (
    CompanySummarySerializer,
    ProductGradeSummarySerializer,
)
from apps.finance.models import IntercompanyPolicy, IntercompanyTransaction


class LifeCycleStageSummarySerializer(serializers.Serializer):
    """Compact representation of a lifecycle stage."""

    id = serializers.IntegerField()
    stage_name = serializers.CharField()


class IntercompanyPolicySummarySerializer(serializers.ModelSerializer):
    """Compact representation of an intercompany pricing policy."""

    id = serializers.IntegerField(source="policy_id", read_only=True)
    from_company = CompanySummarySerializer(read_only=True)
    to_company = CompanySummarySerializer(read_only=True)
    product_grade = ProductGradeSummarySerializer(
        read_only=True,
        allow_null=True,
    )
    lifecycle_stage = LifeCycleStageSummarySerializer(
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = IntercompanyPolicy
        fields = (
            "id",
            "pricing_basis",
            "method",
            "markup_percent",
            "price_per_kg",
            "from_company",
            "to_company",
            "product_grade",
            "lifecycle_stage",
        )
        read_only_fields = fields


class UserSummarySerializer(serializers.Serializer):
    """Compact representation of a user."""

    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()


class IntercompanyTransactionSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for intercompany transactions.

    Supports polymorphic sources (HarvestEvent or BatchTransferWorkflow).
    """

    policy = IntercompanyPolicySummarySerializer(
        read_only=True,
        help_text="Policy metadata including participating companies.",
    )
    approved_by_details = UserSummarySerializer(
        source="approved_by",
        read_only=True,
        allow_null=True,
    )

    # Polymorphic source information
    source_type = serializers.CharField(
        read_only=True,
        help_text="Type of source (harvestevent or batchtransferworkflow)",
    )
    source_id = serializers.IntegerField(
        source="object_id",
        read_only=True,
        help_text="ID of the source object",
    )
    source_display = serializers.CharField(
        read_only=True,
        help_text="Human-readable source identifier",
    )

    class Meta:
        model = IntercompanyTransaction
        fields = (
            "tx_id",
            # Polymorphic source
            "source_type",
            "source_id",
            "source_display",
            # Legacy field (deprecated)
            "event",
            # Transaction details
            "posting_date",
            "amount",
            "currency",
            "state",
            "policy",
            # Approval tracking
            "approved_by",
            "approved_by_details",
            "approval_date",
            # Audit
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
